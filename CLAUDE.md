# CLAUDE.md

This is the public **peers** repo. Follow `AGENTS.md`. Extra for Claude Code:

## You are Claude

Native Task for Opus/Sonnet/Haiku. `peers` is a *different* plan. Never `peers opus` / `peers claude`.

`STATUS: auth` is that other CLI's login, not a peers outage. `peers doctor`. If that row is `ok`, retry the same peer once — Cursor prints `Starting login process` even when logged in. If `AUTH`, tell the human to run `cursor-agent login` (or that CLI's login) in a **real terminal**, then `peers doctor`. Do not hop to ds/ollama as a substitute.

## PRs and commits

You will open PRs on this repo. Make them good:

- Branch off `main`. Don't commit to `main` unless asked.
- Commit message: why, 1–2 sentences. `bash tests/smoke.sh` before push.
- PR title: specific. PR body: `## Summary` (bullets a reviewer can scan) and `## Test plan` (checkboxes). No transcript files. No "as an AI". No padding.
- Skills, README, and doctor output must stay true for someone who only has Codex, or only OpenCode — not just Cursor+Claude.

## Layout

| Path | What |
| --- | --- |
| `peers` | CLI |
| `providers.py` | adapters, auth probes, aliases |
| `dossiers.py` + `dossiers/` | routing + 2-line lean-ins |
| `skills/{claude,cursor,agents}/` | host skills |
| `tests/smoke.sh` | CI |

Desk: `~/.local/share/peers/desk`. Not this git tree.
