---
name: peerdesk
description: Use when work can split across Grok 4.6, Opus, or DeepSeek, when models should share a thread and read each other's transcripts, or when the user says delegate, huddle, ask Grok, ask Opus, or farm out.
---

# peerdesk

Grok 4.6 and Opus are peers on a shared desk. Same repo = same thread.

```bash
peer grok "task"
peer opus --agent review
peer both "hard question"
peer huddle
peer cat last
```

`--note` is what you already know. After `both`, huddle so they read each other. Disagreement is the signal.
