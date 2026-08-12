---
name: peerdesk
description: Use when work can split across Grok 4.6, Opus, or DeepSeek, when a second senior should implement or review, when models should share a thread and read each other's transcripts, or when the user says delegate, huddle, ask Grok, consult Cursor, or farm out.
---

# peerdesk

Grok 4.6 and Opus are **peers on a shared desk**. DeepSeek is optional cheap help. Same repo = same thread. No flags required.

```bash
peer grok "task with an acceptance test"
peer opus --agent review
peer huddle
```

Read the printed **RESULT**. Open **TRANSCRIPT** (or `peer cat last`) if the card is thin, blocked, or they disagree. `--note` is what you already know.

| Situation | Command |
|---|---|
| Independent coding / long-running / UI | `peer grok "…"` |
| Research | `peer grok --agent research "…"` |
| Second opinion | `peer grok --agent review` or `peer opus --agent review` |
| Hard call | `peer both "…"` then `peer huddle` |
| Cheap mechanical | `peer ds "…"` (optional) |
| This session’s MCP / browser / chat | native subagent — don’t hop CLIs |

Do not default to a same-model subagent for work the other senior should own.

After `both`, huddle. Disagreement is the signal.
