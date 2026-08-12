---
name: peers
description: >-
  Send work to a different coding plan than Cursor. Never Cursor/Grok/Composer.
  Triggers: peers, huddle, research, delegate, farm out.
---

# peers

You are Cursor. Same-product work uses the Task tool (`inherit` / the model
you already are). `peers` is a *different* plan.

Watch bash heartbeats (`STATUS: running`, `… 12s`, then RESULT). Don't cat
unless the memo is thin. Don't Task a watcher.

```bash
peers auto --note "what you already know" "task"
peers research "question that needs depth"
peers both --with a,b,c "same question"
peers note "my independent take"
peers huddle
peers doctor
peers thread
```

`a,b,c` are names from `peers providers`. When you Task a same-product
colleague, give them `peers thread` so they can Read the other memos.

| Situation | Route |
|---|---|
| Independent coding in Cursor | Task, `inherit` |
| The peer who's good at this | `peers auto` |
| Deep research, several slices | `peers research` |
| Same question, several priors | `peers both --with a,b,c` |
| This session's MCP / browser | native Task `inherit` |
| Login / 401 | `peers doctor` |

Never `peers cursor` / `peers grok` / `peers composer`. After a desk run,
`peers note` your take, then huddle.
