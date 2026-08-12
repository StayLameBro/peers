# peerdesk

**Two senior models. One desk.**

Grok 4.6 and Claude Opus as peers — not a boss and a junior. They share a thread, read each other’s transcripts when a short card isn’t enough, and huddle when they disagree.

DeepSeek is optional cheap help for mechanical work.

```
peer grok "add /health. accept: tests pass"
peer opus --agent review
peer huddle
```

Same repo = same thread. No flags required.

## Install

You need Python 3.9+, plus at least one of [Cursor CLI](https://cursor.com/docs/cli) (`cursor-agent`) or [Claude Code](https://claude.com/product/claude-code) (`claude`).

```bash
git clone https://github.com/StayLameBro/peerdesk.git
cd peerdesk
./install.sh
peer doctor
```

`install.sh` puts `peer`, `grok46`, and `opus-peer` on your `PATH` and installs skills for Claude Code, Cursor, and Codex.

## 30 seconds

```bash
cd your-project

peer grok "Implement the feature. Accept: the test file goes green."
# prints RESULT + TRANSCRIPT paths — read the card first

peer opus --agent review
# Opus sees Grok’s card and can open the transcript

peer huddle
# they read each other on purpose
```

Hard call (two independent takes, then they talk):

```bash
peer both "Should we use SQLite or Postgres for this? Constraints: single VPS, backups matter."
peer huddle
```

## Why

One model has a local optimum. A second senior with a different prior catches what the first compressed away — if it can **see the work**, not just a summary.

- **Cards are cheap.** You read `RESULT`, not a novel.
- **Transcripts stay on the desk.** The other model `Read`s them when the card is missing the why / what-failed / what they rejected.
- **Huddle is the collaboration step.** `both` is independent on purpose. Then they look at each other.

## Commands

| Command | What it does |
|---|---|
| `peer grok "task"` | Grok 4.6 does the work |
| `peer opus "task"` | Claude Opus does the work |
| `peer opus --agent review` | Opus reviews the last run on this repo’s thread |
| `peer both "question"` | Both take it independently |
| `peer huddle` | Each reads the other’s transcript and responds |
| `peer ds "task"` | DeepSeek (optional, if you have `dsv4`) |
| `peer doctor` | Check your machine |
| `peer setup` | Reinstall skills + PATH shims |
| `peer cat last` | Print a full transcript |

Roles: `worker` (default), `research`, `review`, `consult`.

Useful flags (all optional):

- `--note "what you already know"` — don’t make them rediscover it
- `--full` — inline transcripts
- `--fresh` — ignore thread history (independent take)
- `--thread name` — override the auto thread (defaults to the repo folder name)
- `--dry-run` — write the prompt, don’t call a model

## Skills

`peer setup` installs a **peerdesk** skill (and a **delegate** alias) so Claude Code, Cursor, and Codex will actually use this instead of spawning a same-model subagent.

Claude Code also gets `/peer` and `/grok`.

## Requirements

| You want | Install |
|---|---|
| Grok 4.6 | Cursor CLI — `cursor-agent` on PATH, logged in |
| Claude Opus | Claude Code — `claude` on PATH |
| DeepSeek workers | optional `dsv4` (OpenCode wrapper) |

Zero Python dependencies. macOS and Linux.

## License

MIT
