# AGENTS.md

Public repo: **peers** — every coding plan you already pay for, one office.
Python 3.9+, stdlib only. CLI entry: `peers` (alias `peer`).

## Do

- Keep skills host-general. YAML is the GUI blurb. Body is a command card. Do not assume the maintainer's laptop (no "Grok on this Mac", no `cursor-grok-4.6-high` as the only Task model).
- Login is **per CLI**, not peers. Spell the exact command (`cursor-agent login`, `claude auth login`, `opencode /connect`). Cursor's status banner `Starting login process` is not a logout.
- Desk files live in `~/.local/share/peers/desk`. Never point `PEERS_HOME` at this checkout. Never commit transcripts, `observed.md`, `*.jsonl`, or `tests/.desk/`.
- Tests: `bash tests/smoke.sh`. No pip.

## Don't

- Don't call a product from inside itself (`peers grok` from Cursor, `peers opus` from Claude).
- Don't dump dossiers into every prompt. Lean-ins stay two lines.
- Don't substitute a different prior when one CLI returns `STATUS: auth`. Doctor, then retry the same peer once, or log that CLI in.

## Commits

Imperative, 1–2 sentences, **why** not a file list. No secrets, no desk dumps.

## Pull requests

Title: what changed and why a stranger should care.

Body, always:

```
## Summary
- …

## Test plan
- [ ] bash tests/smoke.sh
- [ ] …
```

PRs are for the public. No laptop-specific "works on my machine", no chat logs, no Office quote-stuffing in the PR body. Brief and accurate beats a manifesto.
