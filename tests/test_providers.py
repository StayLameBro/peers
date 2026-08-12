#!/usr/bin/env python3
"""Unit tests — no coding CLIs required."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import providers as P  # noqa: E402


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"fail: {msg}")


def main() -> int:
    os.environ.pop("PEERS_ALLOW_SELF", None)

    os.environ["PEERS_CALLER"] = "cursor"
    check(P.detect_caller() == "cursor", "caller cursor")
    check(P.is_self("grok"), "cursor must not call grok")
    check(P.is_self("composer"), "cursor must not call composer")
    check(not P.is_self("opus"), "cursor may call opus")
    check(not P.is_self("ds"), "cursor may call ds")
    msg = P.self_message("grok")
    check("yourself" in msg, "self message")
    check("peers auto" in msg, "self message points at auto")

    os.environ["PEERS_CALLER"] = "claude"
    check(P.is_self("opus"), "claude must not call opus")
    check(P.is_self("sonnet"), "claude must not call sonnet")
    check(not P.is_self("grok"), "claude may call grok")

    os.environ["PEERS_ALLOW_SELF"] = "1"
    check(not P.is_self("opus"), "allow-self override")
    del os.environ["PEERS_ALLOW_SELF"]

    blob = "Press any key to sign in..."
    check(P.AUTH_FAIL.search(blob) is not None, "detect cursor login prompt")
    blob = "401 OAuth access token has been revoked"
    check(P.AUTH_FAIL.search(blob) is not None, "detect claude 401")
    state, detail = P.classify_auth(1, "", "401 OAuth access token has been revoked")
    check(state == "auth", f"401 classified as auth, got {state} {detail}")
    state, detail = P.classify_auth(0, "Press any key to sign in...", "")
    check(state == "auth", f"login prompt classified as auth, got {state}")

    prov, model, alias = P.resolve("grok")
    check(prov.id == "cursor" and model == "grok-4.6" and alias == "grok", "resolve grok")
    prov, model, alias = P.resolve("opus")
    check(prov.id == "claude" and model == "opus", "resolve opus")
    try:
        P.resolve("not-a-peer")
        raise SystemExit("fail: unknown alias should raise")
    except KeyError:
        pass

    prov, model, alias = P.resolve("zai")
    check(prov.id == "opencode" and "zai" in model and alias == "zai", "resolve zai → opencode")
    prov, model, alias = P.resolve("moonshot/kimi-k2.5")
    check(prov.id == "opencode" and model == "moonshot/kimi-k2.5", "resolve OpenCode provider/model")
    prov, model, alias = P.resolve("kimi")
    check(alias == "kimi", "resolve kimi alias")
    check(prov.id in ("kimi", "opencode"), "kimi is CLI or OpenCode gateway")

    os.environ["PEERS_CALLER"] = "opencode"
    check(P.is_self("zai"), "opencode must not call zai via gateway")
    check(P.is_self("kimi"), "opencode must not call kimi via gateway")
    check(not P.is_self("opus"), "opencode may call opus")
    del os.environ["PEERS_CALLER"]

    os.environ["PEERS_CALLER"] = "codex"
    check(P.is_self("gpt"), "codex must not call gpt")
    check(not P.is_self("opus"), "codex may call opus")
    del os.environ["PEERS_CALLER"]

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        good = root / "out.txt"
        good.write_text("hello from dsv4", encoding="utf-8")
        got = P.safe_read_path(str(good), extra_roots=[root])
        check(got == "hello from dsv4", "safe_read_path allows extra_roots")
        check(P.safe_read_path("/etc/passwd", extra_roots=[root]) is None, "refuse /etc/passwd")
        link = root / "link"
        try:
            link.symlink_to(good)
            check(P.safe_read_path(str(link), extra_roots=[root]) is None, "refuse symlink")
        except OSError:
            pass

    P._config_cache = {"bin": {"claude": "./not-a-real-bin"}}
    hit = P.PROVIDERS["claude"].find()
    check(hit is None or "not-a-real-bin" not in str(hit), "reject relative bin override")
    P._config_cache = {}

    import dossiers as D
    have = ["grok", "opus", "ds"]
    check(D.route("review the auth invariant", "review", have) == "opus", "route review → opus")
    check(D.route("rename the leftover foo_bar symbols", "worker", have) == "ds", "route mechanical → ds")
    many = D.route_many("survey sqlite vs postgres papers", "research", ["grok", "opus", "gemini", "ds"], n=3)
    check(len(many) == 3, f"route_many n=3, got {many}")
    check("ds" not in many, "research desk should not pick mechanical first")
    slices = D.research_slices(["grok", "opus", "gemini"])
    check(len(set(slices.values())) == 3, "research slices should differ")
    check("Ship" in D.lean_in("grok"), "grok lean-in")
    check("verify" in D.lean_in("opus").lower() or "Judgment" in D.lean_in("opus"), "opus lean-in")
    check(D.dossier_path("grok") is not None, "grok dossier file")
    check(D.dossier_path("opus") is not None, "opus dossier file")

    _test_opencode_attach()

    print("test_providers ok")
    return 0


def _test_opencode_attach() -> None:
    """Gateway attach is argv + desk state. No live OpenCode required."""
    import json
    import signal
    import socket
    import tempfile
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    saved = {
        k: os.environ.get(k)
        for k in (
            "PEERS_HOME",
            "PEERS_OPENCODE_URL",
            "OPENCODE_SERVER_URL",
            "PEERS_OPENCODE_PORT",
            "OPENCODE_SERVER_PORT",
            "OPENCODE_SERVER_PASSWORD",
        )
    }

    def restore() -> None:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        P.reset_opencode_gateway()

    def pop_gateway_env() -> None:
        for k in (
            "PEERS_OPENCODE_URL",
            "OPENCODE_SERVER_URL",
            "PEERS_OPENCODE_PORT",
            "OPENCODE_SERVER_PORT",
            "OPENCODE_SERVER_PASSWORD",
        ):
            os.environ.pop(k, None)
        P.reset_opencode_gateway()

    try:
        pop_gateway_env()
        os.environ["PEERS_OPENCODE_URL"] = "http://127.0.0.1:4096"
        argv = P._opencode_argv("opencode", "zai/glm-4.6", "noop", False, "worker")
        check("--attach" in argv, "env URL adds --attach")
        check("http://127.0.0.1:4096" in argv, "env URL is the attach target")
        check("-m" in argv and "zai/glm-4.6" in argv, "model still passed")
        check("OPENCODE_SERVER_PASSWORD" not in " ".join(argv), "password not on argv")
        os.environ["OPENCODE_SERVER_PASSWORD"] = "secret-not-for-logs"
        argv = P._opencode_argv("opencode", "ollama/llama3.2", "noop", False, "worker")
        check("secret-not-for-logs" not in " ".join(argv), "do not put password on argv")

        os.environ["PEERS_OPENCODE_URL"] = "http://user:pass@127.0.0.1:4096"
        check(P.discover_opencode_url() is None, "reject userinfo in attach URL")

        pop_gateway_env()
        argv = P._opencode_argv("opencode", "qwen/qwen3-coder", "noop", False, "worker")
        check("--attach" not in argv, "no attach without a configured gateway")

        claude = P._claude_argv("claude", "opus", "noop", False, "worker")
        check("--attach" not in claude, "Claude is one-shot")
        cursor = P._cursor_argv("cursor-agent", "grok-4.6", "noop", False, "worker")
        check("--attach" not in cursor, "Cursor is one-shot")
        codex = P._codex_argv("codex", "", "noop", False, "worker")
        check("--attach" not in codex, "Codex is one-shot")

        with tempfile.TemporaryDirectory() as td:
            os.environ["PEERS_HOME"] = td
            pop_gateway_env()
            os.environ["PEERS_HOME"] = td
            check(
                str(P.opencode_state_path()).startswith(td),
                "state file lives under PEERS_HOME",
            )
            P._write_state(url="http://127.0.0.1:9", pid=99999999, owned=True)
            check(P.discover_opencode_url() is None, "dead pid in state is ignored")

            class Health(BaseHTTPRequestHandler):
                def do_GET(self) -> None:
                    body = b'{"healthy":true,"version":"test"}'
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)

                def log_message(self, *_a: object) -> None:
                    return

            httpd = HTTPServer(("127.0.0.1", 0), Health)
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            port = httpd.server_address[1]
            url = f"http://127.0.0.1:{port}"
            P._write_state(url=url, pid=os.getpid(), owned=False)
            P.reset_opencode_gateway()
            got = P.discover_opencode_url()
            check(got == url, f"live state file is reused, got {got}")
            argv = P._opencode_argv("opencode", "moonshot/kimi-k2.5", "noop", False, "worker")
            check(argv[argv.index("--attach") + 1] == url, "argv attaches to state URL")
            with_dir = P.attach_opencode_dir(argv, td)
            check("--dir" in with_dir, "--dir added when attaching")
            check(str(Path(td).resolve()) in with_dir, "--dir is the job cwd")
            httpd.shutdown()

            fake = Path(td) / "fake-opencode"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "from http.server import BaseHTTPRequestHandler, HTTPServer\n"
                "port = int(sys.argv[sys.argv.index('--port') + 1])\n"
                "host = sys.argv[sys.argv.index('--hostname') + 1]\n"
                "class H(BaseHTTPRequestHandler):\n"
                "    def do_GET(self):\n"
                "        b = b'{\"healthy\":true,\"version\":\"fake\"}'\n"
                "        self.send_response(200)\n"
                "        self.send_header('Content-Type', 'application/json')\n"
                "        self.send_header('Content-Length', str(len(b)))\n"
                "        self.end_headers()\n"
                "        self.wfile.write(b)\n"
                "    def log_message(self, *a):\n"
                "        return\n"
                "HTTPServer((host, port), H).serve_forever()\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", 0))
                serve_port = s.getsockname()[1]
            pop_gateway_env()
            os.environ["PEERS_HOME"] = td
            os.environ["PEERS_OPENCODE_PORT"] = str(serve_port)
            started = P.ensure_opencode_gateway(str(fake))
            pid = None
            try:
                check(started == f"http://127.0.0.1:{serve_port}", f"start serve, got {started}")
                state = json.loads(P.opencode_state_path().read_text(encoding="utf-8"))
                check(state.get("owned") is True, "peers-started serve is owned")
                pid = state.get("pid")
                check(isinstance(pid, int) and P._pid_alive(pid), "owned pid is recorded")
                again = P.ensure_opencode_gateway(str(fake))
                check(again == started, "second ensure reuses the same serve")
                state2 = json.loads(P.opencode_state_path().read_text(encoding="utf-8"))
                check(state2.get("pid") == pid, "reuse does not spawn a second serve")
                argv = P._opencode_argv("opencode", "zai/glm-4.6", "noop", False, "worker")
                check("--attach" in argv and started in argv, "started gateway is on argv")
            finally:
                if not pid:
                    try:
                        pid = json.loads(P.opencode_state_path().read_text(encoding="utf-8")).get("pid")
                    except (OSError, json.JSONDecodeError):
                        pid = None
                if isinstance(pid, int):
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except OSError:
                        pass
    finally:
        restore()


if __name__ == "__main__":
    raise SystemExit(main())
