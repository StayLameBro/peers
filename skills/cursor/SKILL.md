---
name: peerdesk
description: Delegates to peer models on a shared thread — Grok 4.6 (native Task or peer grok), Claude Opus (peer opus), DeepSeek (peer ds). Use when work can run in parallel, when a second senior should implement or review, when models should read each other's transcripts, or when the user says delegate, huddle, ask Opus, consult Claude, or farm out.
---

# peerdesk

Opus and Grok 4.6 are **peers on a shared desk**. Same repo = same thread.

```bash
peer opus --note "what you already know" "task"
peer huddle
peer cat last
```

Same-product Grok work uses the **Task** tool (`model: "cursor-grok-4.6-high"`), not `peer grok`. When you Task a Grok colleague, tell them the thread path (`peer thread` prints it) so they can Read Opus’s transcripts under `/tmp/peer/`.

| Situation | Route |
|---|---|
| Independent coding in Cursor | Task, `cursor-grok-4.6-high` |
| Claude’s world / second opinion | `peer opus` |
| Hard call | `peer both` then `peer huddle` |
| Cheap mechanical | `peer ds` |
| This session’s MCP / browser | native Task `inherit` |

You read RESULT. The peer Reads TRANSCRIPT paths when the card isn’t enough. After `both`, huddle.
