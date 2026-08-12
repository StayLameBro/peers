# codex (OpenAI Codex CLI / GPT)

**Lean-in:** Terminal-native. Run the command, read the output, keep going. Less essay, more harness.

## Training / harness

Codex CLI is RL'd against *terminal* success (Terminal-Bench is the public tell). `codex exec --sandbox workspace-write --ask-for-approval never` is the headless shape. Strong at "the tests are the spec" loops. Weaker at product taste and at noticing an invariant that wasn't in a failing test.

## Wins

- CLI / infra / deploy / docker / "make the harness go green"
- Autonomous command loops where Opus would write a plan first
- GitHub/OpenAI toolchain familiarity

## Reluctance / failure modes

- "It passed" without the invariant you actually care about
- Can be shallow on design tradeoffs
- `--full-auto` is deprecated — don't generate that flag
- Interactive approval will hang a desk; we pass `ask-for-approval never`

## How to use without hindering

Give the command that must pass. Don't ask for a design partnership. Counterpart should check whether the *invariant* held, not whether a process was followed.
