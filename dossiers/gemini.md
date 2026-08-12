# gemini (Gemini CLI)

**Lean-in:** Long context + multimodal. Open the files / images. Don't summarize the repo from memory.

## Training / harness

Google long-context + native multimodal. Headless: `gemini -p --yolo --output-format text`. Wins when the artifact is a screenshot, PDF, HTML dump, or a million-token dump that other CLIs won't eat. Can be generic if you only give a one-line task and no paths.

## Wins

- Screenshots, PDFs, video frames, huge logs
- "Here's the whole tree, find X"
- Google-stack repos

## Reluctance / failure modes

- Generic advice if not pointed at files
- `--yolo` is required for unattended edits; without it the desk hangs on consent
- Not the first pick for a tight semantic refactor (Opus) or a Cursor-native UI diff (Grok)

## How to use without hindering

Attach or path the artifact. Don't ask it to be a tasteful senior reviewer of a 200-line PR — that's Opus.
