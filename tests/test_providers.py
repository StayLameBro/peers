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
    check(P.is_self("cursor-grok-4.6-high"), "cursor must not call CLI grok id")
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
    check(P.AUTH_FAIL.search("handler returns 401 for bad tokens") is None, "bare 401 is not auth")
    check(P.AUTH_FAIL.search("Starting login process...") is None, "cursor login chatter is not auth")
    state, detail = P.classify_auth(1, "", "401 OAuth access token has been revoked")
    check(state == "auth", f"401 classified as auth, got {state} {detail}")
    state, detail = P.classify_auth(0, "Press any key to sign in...", "")
    check(state == "auth", f"login prompt classified as auth, got {state}")

    chatter = (
        "Starting login process...\nAuthenticating with Cursor...\n"
        "Checking authentication status...\n✓ Login successful!\nLogged in\n"
    )
    state, detail = P._parse_cursor_probe(0, chatter, "")
    check(state == "ok", f"cursor chatter+logged in is ok, got {state} {detail}")
    state, detail = P._parse_cursor_probe(142, "Starting login process...\n", "")
    check(state == "timeout", f"cursor status timeout is timeout not auth, got {state} {detail}")
    state, detail = P._parse_cursor_probe(0, "Press any key to sign in...", "")
    check(state == "auth", f"press any key is auth, got {state}")

    prov, model, alias = P.resolve("grok")
    check(prov.id == "cursor" and model == "cursor-grok-4.6-high" and alias == "grok", "resolve grok")
    prov, model, alias = P.resolve("grok-4.6")
    check(model == "cursor-grok-4.6-high" and alias == "grok-4.6", "resolve grok-4.6 alias")
    argv = P._cursor_argv("cursor-agent", model, "noop", False, "worker")
    check("--model" in argv and "cursor-grok-4.6-high" in argv, "cursor argv uses CLI grok id")
    check("grok-4.6" not in argv, "cursor argv must not send bare grok-4.6")
    prov, model, alias = P.resolve("composer")
    check(prov.id == "cursor" and model == "composer-2.5" and alias == "composer", "resolve composer")
    argv = P._cursor_argv("cursor-agent", model, "noop", False, "worker")
    check("composer-2.5" in argv, "cursor argv keeps composer-2.5")
    prov, model, alias = P.resolve("cursor-grok-4.6-high")
    check(model == "cursor-grok-4.6-high" and alias == "cursor-grok-4.6-high", "resolve CLI grok id")
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

    print("test_providers ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
