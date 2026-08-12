"""Provider adapters — any coding CLI already on the machine.

We never sell plans. We use whatever the user already logged into.
Doctor probes auth with stdin closed and a hard timeout so we never
sit on "Press any key to sign in". Callers must not invoke themselves.
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator

try:
    import fcntl
except ImportError:  # Windows later; flock is Unix/macOS
    fcntl = None  # type: ignore[assignment]

AUTH_FAIL = re.compile(
    r"press any key to sign in|starting login process|"
    r"401|oauth access token has been revoked|not logged in|"
    r"please (?:log|sign) in|authentication required|"
    r"loggedin\"?\s*:\s*false|unauthorized",
    re.I,
)
AUTH_OK = re.compile(r"logged in|login successful|\"loggedin\"\s*:\s*true", re.I)


def which(name: str) -> str | None:
    if not name:
        return None
    return shutil.which(name)


def config_path() -> Path:
    return Path(os.environ.get("PEERS_CONFIG") or Path.home() / ".config/peers/config.json")


_probe_cache: dict[str, tuple[str, str]] = {}
_probe_lock = threading.Lock()
_config_cache: dict | None = None


def load_config() -> dict:
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    p = config_path()
    if not p.exists():
        _config_cache = {}
        return _config_cache
    try:
        _config_cache = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _config_cache = {}
    return _config_cache


def detect_caller() -> str | None:
    """Which product is running *this* process — so we refuse to call it again."""
    override = os.environ.get("PEERS_CALLER")
    if override:
        return override.strip().lower() or None
    if os.environ.get("CURSOR_CONVERSATION_ID") or os.environ.get("CURSOR_AGENT") in (
        "1",
        "true",
        "TRUE",
        "yes",
    ):
        return "cursor"
    if any(os.environ.get(k) for k in ("CLAUDECODE", "CLAUDE_CODE", "CLAUDE_CODE_ENTRYPOINT")):
        return "claude"
    if os.environ.get("CODEX_SANDBOX") or os.environ.get("CODEX_THREAD_ID"):
        return "codex"
    argv0 = Path(sys.argv[0]).name.lower() if sys.argv else ""
    if argv0 in ("claude", "cursor-agent", "codex", "gemini", "opencode", "goose", "copilot"):
        return {"cursor-agent": "cursor"}.get(argv0, argv0)
    return None


def allow_self() -> bool:
    v = os.environ.get("PEERS_ALLOW_SELF", "")
    return v in ("1", "true", "TRUE", "yes")


@dataclass
class Provider:
    id: str
    bins: tuple[str, ...]
    hint: str
    login: str
    models: dict[str, str]
    timeout: int = 1200
    env_bin: str | None = None
    argv: Callable[..., list[str]] = field(repr=False, default=lambda *a, **k: [])
    probe_argv: Callable[[str], list[str] | None] | None = field(default=None, repr=False)
    parse_probe: Callable[[int, str, str], tuple[str, str]] | None = field(
        default=None, repr=False
    )

    def find(self) -> str | None:
        cfg = load_config()
        override = (cfg.get("bin") or {}).get(self.id) or (
            os.environ.get(self.env_bin) if self.env_bin else None
        )
        # CURSOR_AGENT=1 means "we are inside Cursor", not a binary path.
        if override and Path(str(override)).name not in ("1", "true", "TRUE"):
            s = str(override).strip()
            if "/" in s or s.startswith("."):
                op = Path(s).expanduser()
                if op.is_absolute() and op.is_file() and not op.is_symlink():
                    return str(op.resolve())
            else:
                hit = which(s)
                if hit:
                    return hit
        for b in self.bins:
            hit = which(b)
            if hit:
                return hit
        return None

    def resolve_model(self, requested: str | None) -> str:
        if not requested:
            return self.models.get("default") or next(iter(self.models.values()), "")
        return self.models.get(requested, requested)


def _quiet_env() -> dict[str, str]:
    env = os.environ.copy()
    env["CI"] = "1"
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"
    env["CLICOLOR"] = "0"
    return env


def run_quiet(argv: list[str], timeout: int = 8) -> tuple[int, str, str]:
    """Never attach a TTY. Never wait for a keypress. Hard-timeout."""
    try:
        p = subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_quiet_env(),
            start_new_session=True,
        )
        return p.returncode, p.stdout or "", p.stderr or ""
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        return 142, out, err + f"\npeers: probe timeout after {timeout}s\n"
    except FileNotFoundError:
        return 3, "", f"not found: {argv[0]}\n"


def safe_read_path(
    raw: str,
    extra_roots: list[Path] | None = None,
    max_bytes: int = 2_000_000,
) -> str | None:
    """Read a peer-emitted OUTPUT path. Refuse escapes, symlinks, other uids."""
    raw = (raw or "").strip()
    if not raw or any(c in raw for c in "\n\r\x00"):
        return None
    p = Path(raw)
    try:
        if p.exists() and p.is_symlink():
            return None
        resolved = p.resolve()
    except (OSError, RuntimeError):
        return None
    if not resolved.is_file() or resolved.is_symlink():
        return None
    try:
        st = resolved.stat()
    except OSError:
        return None
    if hasattr(os, "getuid") and st.st_uid != os.getuid():
        return None
    roots: list[Path] = []
    tmp = os.environ.get("TMPDIR") or os.environ.get("TMP") or "/tmp"
    candidates = list(extra_roots or []) + [
        Path(tmp),
        Path("/tmp"),
        Path.home() / ".local/share/peers",
    ]
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        candidates.append(Path(xdg) / "peers")
    for r in candidates:
        try:
            roots.append(r.resolve())
        except OSError:
            continue
    for root in roots:
        try:
            resolved.relative_to(root)
            break
        except ValueError:
            continue
    else:
        return None
    try:
        data = resolved.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return data[:max_bytes]


def classify_auth(rc: int, stdout: str, stderr: str) -> tuple[str, str]:
    blob = f"{stdout}\n{stderr}"
    if AUTH_FAIL.search(blob):
        if "401" in blob or "revoked" in blob.lower():
            return "auth", "token revoked / 401 — re-login"
        if "press any key" in blob.lower() or "starting login" in blob.lower():
            return "auth", "needs login (would hang on 'Press any key to sign in')"
        return "auth", "not authenticated"
    if rc == 142:
        if AUTH_FAIL.search(blob) or "sign in" in blob.lower():
            return "auth", "login prompt (timed out — not hung)"
        return "timeout", "probe timed out"
    if AUTH_OK.search(blob) and rc == 0:
        return "ok", "logged in"
    if rc == 0:
        return "ok", "reachable"
    return "auth", (stderr or stdout).strip().splitlines()[-1][:120] if (stderr or stdout).strip() else f"exit {rc}"


def _cursor_argv(bin: str, model: str, prompt: str, force: bool, role: str) -> list[str]:
    args = [bin, "-p", "--output-format", "text", "--model", model]
    if force:
        args.append("--force")
    args.append(prompt)
    return args


def _claude_argv(bin: str, model: str, prompt: str, force: bool, role: str) -> list[str]:
    tools = {
        "worker": "Edit,Write,Read,Glob,Grep,Bash",
        "research": "Read,Glob,Grep,WebSearch,WebFetch",
        "review": "Read,Glob,Grep",
        "consult": "Read,Glob,Grep,WebSearch,WebFetch",
    }.get(role, "Edit,Write,Read,Glob,Grep,Bash")
    args = [bin, "-p", "--output-format", "text", "--model", model, "--allowedTools", tools]
    if force:
        args.append("--dangerously-skip-permissions")
    args.append(prompt)
    return args


# OpenCode is the only CLI that can share a process: one `opencode serve`,
# many `opencode run --attach`. Claude, Cursor, Codex, and Gemini are one-shot.
_OPENCODE_URL_OK = re.compile(r"^https?://[A-Za-z0-9.[\]:_-]+$")
_opencode_lock = threading.RLock()
_opencode_cached_url: str | None = None


def desk_home() -> Path:
    """Same default as the CLI: PEERS_HOME or ~/.local/share/peers/desk."""
    if os.environ.get("PEERS_HOME"):
        return Path(os.environ["PEERS_HOME"])
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local/share"
    return base / "peers" / "desk"


def opencode_state_path() -> Path:
    """Pid/url file under the desk dir — never the git checkout, never /tmp/peers."""
    return desk_home() / "opencode-serve.json"


def reset_opencode_gateway() -> None:
    global _opencode_cached_url
    with _opencode_lock:
        _opencode_cached_url = None


def _set_opencode_cache(url: str | None) -> None:
    global _opencode_cached_url
    _opencode_cached_url = url


def _serve_host() -> str:
    return (
        os.environ.get("PEERS_OPENCODE_HOST")
        or os.environ.get("OPENCODE_SERVER_HOSTNAME")
        or "127.0.0.1"
    ).strip() or "127.0.0.1"


def _attach_host(bind_host: str) -> str:
    if bind_host in ("0.0.0.0", "::", "[::]"):
        return "127.0.0.1"
    return bind_host


def _configured_port() -> int | None:
    for key in ("PEERS_OPENCODE_PORT", "OPENCODE_SERVER_PORT"):
        raw = (os.environ.get(key) or "").strip()
        if raw.isdigit():
            n = int(raw)
            if 1 <= n <= 65535:
                return n
    return None


def _normalize_attach_url(raw: str | None) -> str | None:
    raw = (raw or "").strip().rstrip("/")
    if not raw or raw.lower() in ("0", "off", "none", "false"):
        return None
    if "://" not in raw and re.match(r"^(127\.0\.0\.1|localhost|\[::1\]):\d+$", raw):
        raw = "http://" + raw
    if "@" in raw or not _OPENCODE_URL_OK.match(raw):
        return None
    return raw


def _env_attach_url() -> str | None:
    for key in ("PEERS_OPENCODE_URL", "OPENCODE_SERVER_URL"):
        url = _normalize_attach_url(os.environ.get(key))
        if url:
            return url
    return None


def _pid_alive(pid: int) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _opencode_healthy(url: str, timeout: float = 0.5) -> bool:
    """GET /global/health. 401 still counts — password-protected OpenCode."""
    health = url.rstrip("/") + "/global/health"
    req = urllib.request.Request(health, method="GET")
    password = os.environ.get("OPENCODE_SERVER_PASSWORD") or ""
    if password:
        user = os.environ.get("OPENCODE_SERVER_USERNAME") or "opencode"
        token = base64.b64encode(f"{user}:{password}".encode()).decode("ascii")
        req.add_header("Authorization", f"Basic {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if getattr(resp, "status", 200) != 200:
                return False
            body = resp.read(256)
            if not body:
                return True
            try:
                data = json.loads(body.decode("utf-8", "replace"))
            except json.JSONDecodeError:
                return True
            return data.get("healthy", True) is not False
    except urllib.error.HTTPError as e:
        return e.code in (401, 403)
    except (OSError, urllib.error.URLError):
        return False


def _read_state() -> dict:
    path = opencode_state_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_state(*, url: str, pid: int | None, owned: bool) -> None:
    path = opencode_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"url": url, "owned": bool(owned)}
    if pid:
        payload["pid"] = int(pid)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    tmp.replace(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _drop_state() -> None:
    path = opencode_state_path()
    try:
        path.unlink()
    except OSError:
        pass


def _url_from_state() -> str | None:
    data = _read_state()
    url = _normalize_attach_url(str(data.get("url") or ""))
    if not url:
        return None
    pid = data.get("pid")
    if isinstance(pid, int) and pid > 0 and not _pid_alive(pid):
        _drop_state()
        return None
    if _opencode_healthy(url):
        return url
    if isinstance(pid, int) and pid > 0 and _pid_alive(pid):
        return None
    _drop_state()
    return None


@contextmanager
def _state_lock() -> Iterator[None]:
    path = opencode_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lockp = path.with_name(path.name + ".lock")
    fh = open(lockp, "a+")
    try:
        if fcntl is not None:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        if fcntl is not None:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        fh.close()


def _port_listening(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except OSError:
        return False


def _free_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host if host not in ("0.0.0.0", "::") else "127.0.0.1", 0))
        return int(s.getsockname()[1])


def _default_probe_url() -> str:
    host = _attach_host(_serve_host())
    port = _configured_port() or 4096
    return f"http://{host}:{port}"


def discover_opencode_url(*, probe_default: bool = False) -> str | None:
    """Env or live desk state. No process start. Safe for dry-run / tests."""
    env = _env_attach_url()
    if env:
        return env
    with _opencode_lock:
        cached = _opencode_cached_url
    if cached and _opencode_healthy(cached):
        return cached
    url = _url_from_state()
    if url:
        with _opencode_lock:
            _set_opencode_cache(url)
        return url
    if probe_default:
        guess = _default_probe_url()
        if _opencode_healthy(guess):
            _write_state(url=guess, pid=None, owned=False)
            with _opencode_lock:
                _set_opencode_cache(guess)
            return guess
    return None


def _start_opencode_serve(bin: str) -> str | None:
    bind = _serve_host()
    host = bind if bind not in ("0.0.0.0", "::") else "127.0.0.1"
    port = _configured_port()
    if port is None:
        port = 4096 if not _port_listening(host, 4096) else _free_port(host)
    url = f"http://{_attach_host(bind)}:{port}"
    home = desk_home()
    home.mkdir(parents=True, exist_ok=True)
    log_path = home / "opencode-serve.log"
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["CLICOLOR"] = "0"
    try:
        log_fh = open(log_path, "a", encoding="utf-8")
    except OSError:
        log_fh = subprocess.DEVNULL
    try:
        proc = subprocess.Popen(
            [bin, "serve", "--hostname", bind, "--port", str(port)],
            cwd=str(home),
            stdin=subprocess.DEVNULL,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=env,
        )
    except OSError:
        return None
    finally:
        if log_fh is not subprocess.DEVNULL:
            try:
                log_fh.close()
            except OSError:
                pass
    deadline = time.time() + 12
    while time.time() < deadline:
        if proc.poll() is not None:
            return None
        if _opencode_healthy(url):
            _write_state(url=url, pid=proc.pid, owned=True)
            _set_opencode_cache(url)
            return url
        time.sleep(0.15)
    if proc.poll() is None:
        try:
            proc.terminate()
        except OSError:
            pass
    return None


def ensure_opencode_gateway(bin: str) -> str | None:
    """Reuse a running serve, or start one. Shared across jobs and peers invocations."""
    url = discover_opencode_url(probe_default=True)
    if url:
        return url
    if not bin:
        return None
    with _opencode_lock:
        url = discover_opencode_url(probe_default=True)
        if url:
            return url
        with _state_lock():
            url = discover_opencode_url(probe_default=True)
            if url:
                return url
            return _start_opencode_serve(bin)


def attach_opencode_dir(argv: list[str], cwd: Path | str) -> list[str]:
    """Point an attached `opencode run` at this job's project. No-op without --attach."""
    if "--attach" not in argv or "--dir" in argv or not argv:
        return argv
    return argv[:-1] + ["--dir", str(Path(cwd).resolve()), argv[-1]]


def _opencode_argv(bin: str, model: str, prompt: str, force: bool, role: str) -> list[str]:
    args = [bin, "run"]
    url = discover_opencode_url()
    if url:
        args += ["--attach", url]
    if model:
        args += ["-m", model]
    args.append(prompt)
    return args


def _kimi_argv(bin: str, model: str, prompt: str, force: bool, role: str) -> list[str]:
    args = [bin, "-p", prompt]
    if model:
        args += ["--model", model]
    return args


def _dsv4_argv(bin: str, model: str, prompt: str, force: bool, role: str) -> list[str]:
    agent = role if role in ("worker", "research", "bench", "kernel") else "worker"
    args = [bin, "--agent", agent, "--timeout", "600"]
    if model:
        args += ["--model", model]
    args.append(prompt)
    return args


def _codex_argv(bin: str, model: str, prompt: str, force: bool, role: str) -> list[str]:
    args = [bin, "exec", "--sandbox", "workspace-write", "--ask-for-approval", "never"]
    if model:
        args += ["-m", model]
    args.append(prompt)
    return args


def _gemini_argv(bin: str, model: str, prompt: str, force: bool, role: str) -> list[str]:
    args = [bin, "-p", prompt, "--output-format", "text"]
    if model:
        args += ["-m", model]
    if force:
        args.append("--yolo")
    return args


def _aider_argv(bin: str, model: str, prompt: str, force: bool, role: str) -> list[str]:
    args = [bin, "--yes-always", "--message", prompt]
    if model:
        args += ["--model", model]
    return args


def _copilot_argv(bin: str, model: str, prompt: str, force: bool, role: str) -> list[str]:
    args = [bin, "-p", prompt]
    if force:
        args += ["--allow-all-tools", "--yolo"]
    if model:
        args += ["--model", model]
    return args


def _goose_argv(bin: str, model: str, prompt: str, force: bool, role: str) -> list[str]:
    args = [bin, "run", "--no-session", "-t", prompt]
    if model:
        args += ["--model", model]
    return args


def _parse_claude_probe(rc: int, stdout: str, stderr: str) -> tuple[str, str]:
    try:
        data = json.loads(stdout.strip() or "{}")
    except json.JSONDecodeError:
        return classify_auth(rc, stdout, stderr)
    if data.get("loggedIn") is True:
        who = data.get("email") or data.get("subscriptionType") or "logged in"
        return "ok", str(who)
    if data.get("loggedIn") is False:
        return "auth", "not logged in — claude auth login"
    return classify_auth(rc, stdout, stderr)


def _parse_cursor_probe(rc: int, stdout: str, stderr: str) -> tuple[str, str]:
    blob = f"{stdout}\n{stderr}"
    if "press any key" in blob.lower() or "starting login process" in blob.lower():
        if "logged in" in blob.lower() and "press any key" not in blob.lower():
            return "ok", "logged in"
        # status sometimes prints "Starting login" even when it then succeeds
        if re.search(r"✓\s*login successful|logged in", blob, re.I) and rc == 0:
            return "ok", "logged in"
        return "auth", "needs login — cursor-agent login"
    return classify_auth(rc, stdout, stderr)


PROVIDERS: dict[str, Provider] = {
    "cursor": Provider(
        id="cursor",
        bins=("cursor-agent", "agent"),
        env_bin="PEERS_CURSOR_BIN",
        hint="Cursor CLI — your Cursor plan. https://cursor.com/docs/cli",
        login="cursor-agent login",
        models={
            "default": "grok-4.6",
            "grok": "grok-4.6",
            "grok-4.6": "grok-4.6",
            "composer": "composer-2.5",
            "composer-2.5": "composer-2.5",
            "auto": "auto",
        },
        argv=_cursor_argv,
        probe_argv=lambda b: [b, "status"],
        parse_probe=_parse_cursor_probe,
    ),
    "claude": Provider(
        id="claude",
        bins=("claude",),
        env_bin="PEERS_CLAUDE_BIN",
        hint="Claude Code — your Claude plan. https://claude.com/product/claude-code",
        login="claude auth login",
        models={
            "default": "opus",
            "opus": "opus",
            "sonnet": "sonnet",
            "haiku": "haiku",
            "fable": "fable",
        },
        argv=_claude_argv,
        probe_argv=lambda b: [b, "auth", "status"],
        parse_probe=_parse_claude_probe,
    ),
    "codex": Provider(
        id="codex",
        bins=("codex",),
        hint="OpenAI Codex CLI — your ChatGPT/Codex plan.",
        login="codex login",
        models={"default": "", "gpt": "", "codex": ""},
        argv=_codex_argv,
        probe_argv=lambda b: [b, "--version"],
    ),
    "gemini": Provider(
        id="gemini",
        bins=("gemini",),
        hint="Gemini CLI — your Google AI plan.",
        login="gemini",
        models={"default": "", "gemini": "", "flash": "gemini-2.5-flash", "pro": "gemini-2.5-pro"},
        argv=_gemini_argv,
        probe_argv=lambda b: [b, "--version"],
    ),
    "opencode": Provider(
        id="opencode",
        bins=("opencode", "opencode-cli"),
        hint="OpenCode — 75+ providers (Z.AI, Kimi, local, OpenRouter, …). opencode /connect",
        login="opencode /connect",
        models={"default": "", "deepseek": "opencode/deepseek-v4-flash-free"},
        argv=_opencode_argv,
        probe_argv=lambda b: [b, "--version"],
    ),
    "kimi": Provider(
        id="kimi",
        bins=("kimi",),
        hint="Kimi Code CLI — Moonshot plan. Or: opencode /connect moonshot",
        login="kimi login  (or opencode /connect)",
        models={"default": "", "k2": ""},
        argv=_kimi_argv,
        probe_argv=lambda b: [b, "--version"],
    ),
    "dsv4": Provider(
        id="dsv4",
        bins=("dsv4",),
        hint="DeepSeek V4 Flash via OpenCode wrapper (cheap mechanical work)",
        login="install dsv4; needs a working `opencode`",
        models={"default": "", "deepseek": "opencode/deepseek-v4-flash-free"},
        timeout=600,
        argv=_dsv4_argv,
        probe_argv=lambda b: None,  # dsv4 treats any arg as a task — don't probe
    ),
    "aider": Provider(
        id="aider",
        bins=("aider",),
        hint="Aider — API keys in your env. https://aider.chat",
        login="export OPENAI_API_KEY / ANTHROPIC_API_KEY",
        models={"default": ""},
        argv=_aider_argv,
        probe_argv=lambda b: [b, "--version"],
    ),
    "copilot": Provider(
        id="copilot",
        bins=("copilot",),
        hint="GitHub Copilot CLI — your Copilot plan.",
        login="copilot login",
        models={"default": ""},
        argv=_copilot_argv,
        probe_argv=lambda b: [b, "--version"],
    ),
    "goose": Provider(
        id="goose",
        bins=("goose",),
        hint="Block Goose — your configured provider.",
        login="goose configure",
        models={"default": ""},
        argv=_goose_argv,
        probe_argv=lambda b: [b, "--version"],
    ),
}

ALIASES: dict[str, tuple[str, str]] = {
    "grok": ("cursor", "grok-4.6"),
    "grok-4.6": ("cursor", "grok-4.6"),
    "composer": ("cursor", "composer-2.5"),
    "cursor": ("cursor", "default"),
    "opus": ("claude", "opus"),
    "sonnet": ("claude", "sonnet"),
    "haiku": ("claude", "haiku"),
    "claude": ("claude", "default"),
    "codex": ("codex", "default"),
    "gpt": ("codex", "default"),
    "gemini": ("gemini", "default"),
    "flash": ("gemini", "flash"),
    "pro": ("gemini", "pro"),
    "opencode": ("opencode", "default"),
    "zai": ("opencode", "zai/glm-4.6"),
    "glm": ("opencode", "zai/glm-4.6"),
    "kimi": ("opencode", "moonshot/kimi-k2.5"),
    "moonshot": ("opencode", "moonshot/kimi-k2.5"),
    "qwen": ("opencode", "qwen/qwen3-coder"),
    "ollama": ("opencode", "ollama/llama3.2"),
    "minimax": ("opencode", "minimax/MiniMax-M2.5"),
    "groq": ("opencode", "groq/llama-3.3-70b-versatile"),
    "ds": ("dsv4", "default"),
    "deepseek": ("dsv4", "default"),
    "dsv4": ("dsv4", "default"),
    "aider": ("aider", "default"),
    "copilot": ("copilot", "default"),
    "goose": ("goose", "default"),
}

SELF_ALIASES: dict[str, set[str]] = {
    "cursor": {"cursor", "grok", "grok-4.6", "composer", "composer-2.5"},
    "claude": {"claude", "opus", "sonnet", "haiku", "fable"},
    "codex": {"codex", "gpt"},
    "gemini": {"gemini", "flash", "pro"},
    "opencode": {
        "opencode", "zai", "glm", "kimi", "moonshot", "qwen",
        "ollama", "minimax", "groq",
    },
    "kimi": {"kimi", "moonshot"},
    "dsv4": {"ds", "dsv4", "deepseek"},
    "aider": {"aider"},
    "copilot": {"copilot"},
    "goose": {"goose"},
}

NATIVE: dict[str, str] = {
    "cursor": "Use the native Task tool (inherit / the model you already are). Do not shell out to peers for this product.",
    "claude": "Use the native Task/subagent tool for this product. Do not shell out to peers opus/claude.",
    "codex": "Stay in this Codex session (or spawn a Codex subagent). Do not shell out to peers codex.",
}

def resolve(who: str, model_override: str | None = None) -> tuple[Provider, str, str]:
    """Alias, provider id, OpenCode `provider/model`, or a custom config id."""
    key = who.lower().strip()
    if key == "kimi" and PROVIDERS["kimi"].find():
        prov = PROVIDERS["kimi"]
        return prov, prov.resolve_model(model_override), "kimi"
    if key in ALIASES:
        pid, mkey = ALIASES[key]
        prov = PROVIDERS[pid]
        model = prov.resolve_model(model_override or (None if mkey == "default" else mkey))
        return prov, model, key
    if key in PROVIDERS:
        prov = PROVIDERS[key]
        return prov, prov.resolve_model(model_override), key
    if "/" in key:
        oc = PROVIDERS["opencode"]
        return oc, model_override or key, key
    known = ", ".join(list(ALIASES)[:16])
    raise KeyError(
        f"unknown peer '{who}'. Try: peers providers\n"
        f"Known: {known}…\n"
        f"Or an OpenCode id: peers zai/glm-4.6   peers moonshot/kimi-k2.5\n"
        f"Or opencode /connect, then that name works here."
    )


def is_self(who: str, caller: str | None = None) -> bool:
    if allow_self():
        return False
    caller = caller if caller is not None else detect_caller()
    if not caller:
        return False
    try:
        prov, _model, alias = resolve(who)
    except KeyError:
        return False
    blocked = SELF_ALIASES.get(caller, set())
    return alias in blocked or prov.id == caller or who.lower() in blocked


def self_message(who: str, caller: str | None = None) -> str:
    caller = caller or detect_caller() or "this product"
    others = [a for a in available_aliases(exclude_self=True, authed=False) if not is_self(a, caller)]
    native = NATIVE.get(caller, "Use your native subagent/Task tool.")
    alt = f"  other:  peers {' | peers '.join(others[:5])}" if others else "  other:  peers providers  # install another CLI"
    return (
        f"refusing to call '{who}' from inside {caller} — that is calling yourself.\n"
        f"  native: {native}\n"
        f"{alt}\n"
        f"  auto:   peers auto \"task\"   # picks a *different* authenticated peer"
    )


def probe(prov: Provider, *, force: bool = False) -> tuple[str, str]:
    """Return (ok|miss|auth|timeout, detail). Never hangs."""
    with _probe_lock:
        if not force and prov.id in _probe_cache:
            return _probe_cache[prov.id]
    bin = prov.find()
    if not bin:
        result = ("miss", prov.hint)
        _probe_cache[prov.id] = result
        return result
    if prov.probe_argv is None:
        result = ("ok", bin)
        _probe_cache[prov.id] = result
        return result
    argv = prov.probe_argv(bin)
    if not argv:
        result = ("ok", bin)
        _probe_cache[prov.id] = result
        return result
    rc, out, err = run_quiet(argv, timeout=8)
    parser = prov.parse_probe or classify_auth
    state, detail = parser(rc, out, err)
    if state == "ok":
        detail = f"{bin}  {detail}".strip()
    result = (state, detail)
    _probe_cache[prov.id] = result
    return result


def available_aliases(*, exclude_self: bool = True, authed: bool = False) -> list[str]:
    caller = detect_caller() if exclude_self else None
    out: list[str] = []
    seen: set[tuple[str, str]] = set()
    for alias, (pid, mkey) in ALIASES.items():
        if exclude_self and caller and is_self(alias, caller):
            continue
        prov = PROVIDERS[pid]
        if not prov.find():
            continue
        if authed:
            state, _ = probe(prov)
            if state != "ok":
                continue
        sig = (pid, mkey)
        if sig in seen and alias not in (
            "grok", "opus", "codex", "gemini", "ds", "zai", "kimi", "ollama",
        ):
            continue
        seen.add(sig)
        out.append(alias)
    return out


# Preferred desk order — different products first. Not a two-person club.
DESK_PREFER: tuple[str, ...] = (
    "grok", "opus", "codex", "gemini", "kimi", "zai",
    "composer", "sonnet", "ds", "ollama", "cursor", "claude",
)


def pick_desk(n: int = 3) -> list[str]:
    """Up to n authenticated peers, different products first. Config `desk` or `pair` wins."""
    n = max(1, min(int(n), 4))
    have_list = available_aliases(exclude_self=True, authed=True)
    have = set(have_list)
    if not have:
        return []
    cfg = load_config()
    configured = cfg.get("desk") or cfg.get("pair")
    picked: list[str] = []
    seen_prov: set[str] = set()
    if isinstance(configured, list):
        for a in configured:
            if a in have and a not in picked:
                picked.append(a)
                try:
                    seen_prov.add(resolve(a)[0].id)
                except KeyError:
                    pass
            if len(picked) >= n:
                return picked
    def consider(name: str) -> None:
        if name not in have or name in picked:
            return
        try:
            pid = resolve(name)[0].id
        except KeyError:
            return
        if pid in seen_prov:
            return
        seen_prov.add(pid)
        picked.append(name)

    for name in DESK_PREFER:
        consider(name)
        if len(picked) >= n:
            return picked
    for name in have_list:
        consider(name)
        if len(picked) >= n:
            return picked
    for name in have_list:
        if name not in picked:
            picked.append(name)
        if len(picked) >= n:
            break
    return picked


def pick_pair() -> tuple[str, str] | None:
    desk = pick_desk(2)
    if len(desk) >= 2:
        return desk[0], desk[1]
    return None


def pick_one(prefer: str | None = None) -> str | None:
    have = available_aliases(exclude_self=True, authed=True)
    if prefer and prefer in have:
        return prefer
    for name in (
        "grok", "opus", "codex", "gemini", "composer", "sonnet",
        "kimi", "zai", "ollama", "ds", "cursor", "claude",
    ):
        if name in have:
            return name
    return have[0] if have else None


def status_rows() -> list[tuple[str, str, str, str]]:
    """(id, bin_or_empty, state, detail)."""
    rows = []
    for p in PROVIDERS.values():
        hit = p.find() or ""
        if not hit:
            rows.append((p.id, "", "miss", p.hint))
            continue
        state, detail = probe(p)
        rows.append((p.id, hit, state, detail))
    return rows


def apply_custom_from_config() -> None:
    """Optional ~/.config/peers/config.json custom providers."""
    for item in load_config().get("custom") or []:
        pid = str(item.get("id") or "").strip()
        bin_name = str(item.get("bin") or pid)
        if not pid:
            continue
        tmpl = list(item.get("args") or ["{bin}", "{prompt}"])

        def _argv(
            b: str,
            model: str,
            prompt: str,
            force: bool,
            role: str,
            _tmpl=tmpl,
        ) -> list[str]:
            out = []
            for part in _tmpl:
                out.append(
                    str(part)
                    .replace("{bin}", b)
                    .replace("{prompt}", prompt)
                    .replace("{model}", model or "")
                    .replace("{role}", role)
                )
            return out

        PROVIDERS[pid] = Provider(
            id=pid,
            bins=(bin_name,),
            hint=str(item.get("hint") or f"custom provider {pid}"),
            login=str(item.get("login") or ""),
            models={"default": str(item.get("model") or "")},
            argv=_argv,
            probe_argv=lambda b: None,
        )
        for al in item.get("aliases") or [pid]:
            ALIASES[str(al)] = (pid, "default")


apply_custom_from_config()
