# grok (Grok 4.6 via Cursor)

**Lean-in:** Ship. Long agent loops, tight diffs, few tokens. Acceptance tests over ceremony.

## Training / harness (why the prior is this shape)

xAI + Cursor co-training on real IDE sessions. Post-training rewards *finishing the loop* (edit → run → fix) more than writing a perfect plan. Token-efficient on agentic benches vs Claude (public reports: far fewer output tokens per SWE-style task). Less constitutional-refusal RL than Claude — more willing to edit, scrape, and keep going. CursorBench / SWE-Marathon oriented, not Humanity's Last Exam.

## Wins

- Volume implementation inside a repo you can see
- UI / product-shaped diffs (the Cursor prior)
- Long-running tool loops without a strategy memo
- Cheap enough to be the default worker on a Cursor plan

## Reluctance / failure modes

- Can skip an edge case that wasn't in the acceptance line
- Will not volunteer a deep "what did we just assume?" the way Opus does
- If you wrap it in 40 process rules it wastes the efficiency the post-training bought
- Same-product self-call (`peers grok` from Cursor) is a loop — native Task instead

## How to use without hindering

Give an acceptance test. Don't give a personality. Don't say "be careful" (it just hedges). Counterpart should Read the transcript for rejected options, not trust the RESULT card alone.

## Evidence (leads)

- Artificial Analysis / CursorBench / DeepSWE movement on Grok 4.6 (2026)
- Public token-per-task comparisons vs Opus on SWE-style work
- Cursor sets `CURSOR_AGENT=1` — that's you, don't spawn yourself
