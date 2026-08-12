# opus (Claude Opus via Claude Code)

**Lean-in:** Judgment, not checklists. Catch the assumption the implementer compressed away. No verify-loop. No self-call.

## Training / harness (why the prior is this shape)

Anthropic post-training (constitutional + helpfulness/harmlessness + *extended thinking*). Claude 5-generation docs: thinking on by default, gains on long-horizon agentic coding, code review, bug-finding with few false positives. Also: if you *ask* it to verify / use a subagent to QA / follow an output template, it over-does that — Thariq's context-engineering notes exist because the RL *will* turn a checklist into a ritual.

Claude Code's Task tool is the native same-model spawn. `peers opus` from inside Claude is the same brain with a tax.

## Wins

- Review: the missing invariant, the wrong assumption, the file:line the card skipped
- Hard product/architecture calls where two priors should disagree
- Dense reasoning (HLE / MMLU-class) when the task is actually that
- Refactors where one wrong assumption cascades

## Reluctance / failure modes

- Over-verify if the prompt says "double-check" or "use a subagent to confirm"
- Over-refuse / over-hedge on dual-use-adjacent or "be careful" framing
- Will try to call *itself* via a CLI if a skill says "delegate to Opus"
- 401 / revoked OAuth — fail fast (`claude auth login`), don't sit in a retry loop
- Format scaffolding in the prompt makes the output worse, not better

## How to use without hindering

Point at paths. One honesty constraint. No output schema beyond the RESULT card the desk already requires. Don't tell it what kind of thinker it is. Counterpart: trust DISAGREE more than a polite STATUS: done.

## Evidence (leads)

- Anthropic: "What's new in Opus 5" — review/bug-finding, long-horizon, thinking default
- Thariq / Claude 5 context-engineering: judgment over rule lists; no verify loops
- This desk: `CLAUDECODE` / Claude Code session = you
