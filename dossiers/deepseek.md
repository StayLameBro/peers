# deepseek (V4 Flash via dsv4 / OpenCode)

**Lean-in:** Cheap mechanical. Codemods, renames, obvious tests. If it needs judgment, say blocked.

## Training / harness

Open-weights, aggressive price, long context. Flash variant is *not* the long-horizon specialist — public writeups: instruction-following on multi-constraint prompts and long agent loops are the documented gaps. `dsv4` treats any extra argv as the *task* (never pass `--help`). Prints `OUTPUT: /tmp/...` — empty file = failure, not success. Timeouts with empty transcripts: treat as blocked.

## Wins

- Renames, generated tests, boilerplate, "do this 40 times"
- Price: farm work you would not spend Opus on

## Reluctance / failure modes

- Will guess architecture if you let it
- Empty transcript / timeout — do not retry blindly; `peers doctor`
- Conversational models in OpenCode `run -t` can ask a question and die (no TTY)

## How to use without hindering

One mechanical job per call. Tight file list. Don't ask it to review Grok. Don't use it as the research desk unless the question is mechanical.
