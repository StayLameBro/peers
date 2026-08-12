"""Provider adapters — any coding CLI already on the machine.

We never sell plans. We use whatever the user already logged into.
Doctor probes auth with stdin closed and a hard timeout so we never
sit on "Press any key to sign in". Callers must not invoke themselves.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

AUTH_FAIL = re.compile(
    r"press any key to sign in|"
    r"oauth access token has been revoked|"
    r"not logged in|"
    r"please (?:log|sign) in|authentication required|"
    r"loggedin\"?\s*:\s*false|"
    r"unauthorized",
    re.I,
)
AUTH_OK = re.compile(r"logged in|login successful|\"loggedin\"\s*:\s*true", re.I)
CURSOR_LOGIN_CHATTER = re.compile(r"starting login process|authenticating with cursor", re.I)


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
    """Probes only. CI=1 so status doesn't wait on a TTY."""
    env = os.environ.copy()
    env["CI"] = "1"
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"
    env["CLICOLOR"] = "0"
    return env


def _run_env() -> dict[str, str]:
    """Real agent runs. Do not force CI=1 — Cursor then starts a fake login."""
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["CLICOLOR"] = "0"
    env.pop("CI", None)
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
    if AUTH_OK.search(blob) and rc == 0:
        return "ok", "logged in"
    if AUTH_FAIL.search(blob):
        if "revoked" in blob.lower() or re.search(r"401\s+oauth", blob, re.I):
            return "auth", "token revoked / 401 — re-login"
        if "press any key" in blob.lower():
            return "auth", "needs login (would hang on 'Press any key to sign in')"
        return "auth", "not authenticated"
    if rc == 142:
        if "press any key" in blob.lower():
            return "auth", "login prompt (timed out — not hung)"
        return "timeout", "probe timed out"
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


def _opencode_argv(bin: str, model: str, prompt: str, force: bool, role: str) -> list[str]:
    args = [bin, "run"]
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
    """`cursor-agent status` always prints 'Starting login process' even when logged in."""
    blob = f"{stdout}\n{stderr}"
    if AUTH_OK.search(blob):
        return "ok", "logged in"
    if "press any key" in blob.lower():
        return "auth", "needs login — cursor-agent login"
    if rc == 142:
        return "timeout", "cursor-agent status timed out — retry"
    if rc == 0:
        return "ok", "reachable"
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
    rc, out, err = run_quiet(argv, timeout=12 if prov.id == "cursor" else 8)
    parser = prov.parse_probe or classify_auth
    state, detail = parser(rc, out, err)
    chatter = CURSOR_LOGIN_CHATTER.search(f"{out}\n{err}")
    if (
        prov.id == "cursor"
        and state in ("auth", "timeout")
        and "press any key" not in f"{out}\n{err}".lower()
    ):
        rc, out, err = run_quiet(argv, timeout=12)
        state, detail = parser(rc, out, err)
        chatter = CURSOR_LOGIN_CHATTER.search(f"{out}\n{err}")
    if state == "ok":
        detail = f"{bin}  {detail}".strip()
    elif prov.id == "cursor" and state == "timeout" and chatter:
        # Status hung on its own banner. Don't block the real -p run.
        state, detail = "ok", f"{bin}  status timed out (chatty login banner)"
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
