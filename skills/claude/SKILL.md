---
name: peers
description: >-
  Send work to a different coding plan than Claude. Never Claude/Opus/Sonnet.
  Triggers: peers, huddle, research, delegate, farm out.
---

# peers

You are Claude. Native Task for same-model / this-session tools. `peers` is a
*different* plan — their usage, not yours.

Watch bash heartbeats (`STATUS: running`, `… 12s`, then RESULT). Don't cat
unless the memo is thin. Don't spawn a watcher.

```bash
peers auto "task with an acceptance test"
peers research "question that needs depth"
peers both --with a,b,c "same question"
peers note "my independent take"
peers huddle
peers doctor
peers thread
```

`a,b,c` are names from `peers providers`. Never your own product.

| Situation | Route |
|---|---|
| This session's MCP / browser / 30s grep | native Task |
| The peer who's good at this | `peers auto` |
| Deep research, several slices | `peers research` |
| Same question, several priors | `peers both --with a,b,c` |
| Different jobs | `peers parallel` |
| Login / 401 | `peers doctor` — do not retry |

Never `peers opus` / `peers claude` / `peers sonnet`. After a desk run, huddle.
`STATUS: auth` or an empty transcript means that branch is out — skip it.
