# peers

**Every coding plan you already pay for. One office.**

A dropdown in Cursor, Claude, Codex, or the next app that ships one, is for *you*. The agent in the chair still has one badge. `peers` is how that agent walks down the hall and spends the *other* plans — in the app you're already in.

Not two seniors. A desk. The peer who's good at the job does the job. Several go deep when the question needs depth. They read each other when it matters. Lean-in is two lines so the prior is leverage, not a costume.

Identity theft is not a joke: never call yourself.

```
peers auto "add /health. accept: tests pass"
peers research "SQLite or Postgres on a single VPS?"
peers huddle
```

## Install

Python 3.9+, no pip. We don't sell plans. We use whatever you already logged into.

```bash
git clone https://github.com/StayLameBro/peers.git
cd peers
./install.sh
peers doctor
```

`doctor` lists what's on PATH and who's actually signed in. It will not hang on "Press any key to sign in."

## Login (peers has no account)

If something says `STATUS: auth`, that CLI is not logged in. **This is not a peers bug.** Run the login in a **real terminal** (not an agent sandbox), then `peers doctor`.

| CLI | Login |
| --- | --- |
| Cursor / Grok / Composer | `cursor-agent login` |
| Claude / Opus / Sonnet | `claude auth login` |
| Codex | `codex login` |
| Gemini | `gemini` (follows its own login) |
| OpenCode, Z.AI, Kimi, Ollama, … | `opencode /connect` |

```bash
cursor-agent login
peers doctor
```

`cursor-agent status` prints **Starting login process...** even when you **are** logged in. That is Cursor's banner. `ok cursor … logged in` from `peers doctor` means you're in.

If `STATUS: auth` and doctor already shows that CLI as `ok`: retry the **same** peer once. Don't hop to a different model. If doctor shows `AUTH`, run the login command above.

## Hook up a plan

Three ways. Pick the lazy one.

**1. You already have the CLI.** Cursor, Claude Code, Codex, Gemini, Copilot, Goose, Aider, Kimi — if it's on PATH and logged in, it shows up. That's it.

**2. Everything else, including Z.AI, Moonshot/Kimi, Qwen, MiniMax, Groq, OpenRouter, Ollama.** OpenCode is the public gateway:

```bash
opencode /connect          # pick Z.AI, Moonshot, Ollama, …
peers zai "…"              # GLM
peers kimi "…"             # Moonshot
peers ollama "…"           # local
peers moonshot/kimi-k2.5   # any OpenCode provider/model id
```

API keys stay in that CLI. peers never asks for them.

**3. A CLI we haven't heard of.** `~/.config/peers/config.json` — bin path + argv template. See `examples/config.json`.

| You logged into | Then |
| --- | --- |
| Cursor CLI (`cursor-agent`) | `grok`, `composer` |
| Claude Code (`claude`) | `opus`, `sonnet`, `haiku` |
| Codex CLI (`codex`) | `codex`, `gpt` |
| Gemini CLI | `gemini` |
| OpenCode | `zai`, `kimi`, `ollama`, `qwen`, … or `peers provider/model` |
| Kimi CLI | `kimi` (else OpenCode moonshot) |
| Copilot / Goose / Aider | those names |
| Local weights | `opencode /connect` → Ollama → `peers ollama` |

Use the plans you actually pay for. `auto` picks the peer who's good at this. `--with a,b,c` names the desk (`peers providers` for names). You stay native; we only spawn the others.

One plan: `peers auto` can still reach another *model* on that CLI (Opus vs Sonnet, Grok vs Composer). Same-product disagreement is weaker. Native Task for yourself, always.

## 30 seconds

```bash
cd your-project

peers auto "Implement the feature. Accept: the test file goes green."
# STATUS: running → … 12s  last line → RESULT

peers research "What breaks if we put this on SQLite?"
peers huddle
```

Same question, several priors (names from `peers providers`):

```bash
peers both --with opus,codex,gemini "SQLite or Postgres? Single VPS, backups matter."
peers huddle
```

Different jobs to different peers:

```bash
peers parallel <<'EOF'
opus review: review the /health diff
codex worker: implement /health. accept: tests pass
gemini research: cite how similar services expose health
EOF
```

## Why

One model has a local optimum. Other priors catch what the first compressed away — if they can **see the work**, not just a summary, and if you don't bury them in a personality essay.

- **A dropdown is for you. This is for the agent.** Desktop apps already let *you* switch models. They do not let Claude spend your Cursor plan, or Grok spend your Claude plan.
- **The right peer for the job.** `auto` routes on keywords. Cheap mechanical work doesn't need Opus. Long research doesn't need a 2-line summary.
- **Several, not a pair.** `research` and `--with a,b,c` fan out. Default desk is up to three different products. Pool of four so the machine doesn't melt.
- **Huddle is them reading each other.** Independent first. Then the thread.
- **Never yourself.** Claude does not `peers opus`. Cursor does not `peers grok`. Codex does not `peers gpt`.
- **Performance and efficiency.** Native subagents eat *your* usage — this session's tools, tiny parallel. Long work on another plan: `peers` (their quota). Lean-ins stay two lines so the prior helps instead of hindering.
- **Never hang on login.** `STATUS: auth` is a real login prompt (`Press any key`). Cursor's status banner is not. If `peers doctor` still shows ok, retry that peer once.

## Commands

| Command | What it does |
| --- | --- |
| `peers auto "task"` | The peer who's good at this (not you) |
| `peers grok "task"` | Cursor / Grok |
| `peers opus "task"` | Claude Opus |
| `peers codex "task"` | Codex CLI |
| `peers zai "task"` | GLM via OpenCode |
| `peers kimi "task"` | Moonshot (Kimi CLI or OpenCode) |
| `peers ollama "task"` | Local, via OpenCode |
| `peers research "q"` | Several peers, different slices, go deep |
| `peers both --with a,b,c "q"` | Same question, independent takes |
| `peers huddle` | They read the thread |
| `peers parallel` | Different tasks, `who role: task` per line |
| `peers note "take"` | Your memo, so you never spawn yourself |
| `peers providers` | What's on PATH |
| `peers doctor` | Logins (will not hang) |
| `peers setup` | Reinstall skills + PATH shims |
| `peers thread` | Desk path for this repo |

Any alias works. `peers providers` lists what's actually ready. Unknown `provider/model` goes through OpenCode.

Roles: `worker` (default), `research`, `review`, `consult`.

Flags (all optional): `--note`, `--full`, `--fresh`, `--thread name`, `--with a,b,c`, `--dry-run`.

## Skills

`peers setup` drops a short **peers** skill into:

- `~/.claude/skills` — Claude Code
- `~/.cursor/skills` — Cursor
- `~/.codex/skills` — Codex
- `~/.agents/skills` — anything else that reads the Agent Skills spec (new desktops included)

The YAML description is the GUI blurb: send work to a *different* plan, never yourself. The body is a command card, not a manifesto — extra prose in a skill fights the host's system prompt, so we keep it thin. `/peers` in Claude Code.

## Config (optional)

Never required. `~/.config/peers/config.json` — default desk, bin overrides, custom providers:

```json
{
  "desk": [],
  "bin": {},
  "custom": [{
    "id": "mycli",
    "bin": "my-agent",
    "args": ["{bin}", "-p", "{prompt}"],
    "aliases": ["mycli"],
    "login": "my-agent login"
  }]
}
```

`desk` is optional aliases from `peers providers`. `pair` still works as a 2-name `desk`. Copy `examples/config.json` and edit. `{bin}` `{prompt}` `{model}` `{role}` are substituted. Keys stay in that CLI.

Desk files live in `~/.local/share/peers/desk` (`PEERS_HOME` to override). Mode `0700`. **Never point `PEERS_HOME` at this git checkout** — transcripts would get committed. Tests use `tests/.desk/` (gitignored).

macOS and Linux. Python 3.9+. Zero pip packages. MIT.
