"""Compact model priors — routing + lean-ins, not personality dumps.

Full dossiers live in dossiers/*.md (Read only when counterpart behavior matters).
Putting those essays in every prompt wastes tokens and *hinders* (Claude over-verifies,
Grok over-explains, everyone roleplays). Lean-ins are permission, not a costume.
"""
from __future__ import annotations

from pathlib import Path

DIR = Path(__file__).resolve().parent / "dossiers"

# Permission to use the prior. Never "you are bad at X".
LEAN: dict[str, str] = {
    "grok": (
        "Ship. Long agent loops, tight diffs, few tokens. "
        "Acceptance tests over ceremony. Don't pad, don't interview the user."
    ),
    "composer": (
        "IDE-native implementer. Parallel edits, fast iteration inside the repo. "
        "Don't write a design doc unless the task is a design doc."
    ),
    "cursor": (
        "Same desk as Grok/Composer. Implement. Don't shell out to yourself."
    ),
    "opus": (
        "Judgment, not checklists. Catch the assumption the implementer compressed away. "
        "Do not spawn a verify/subagent loop. Do not call yourself via peers."
    ),
    "sonnet": (
        "Fast Claude prior: solid review and mid-size edits. Same rule — no self-call, no verify theater."
    ),
    "haiku": (
        "Cheap Claude. Mechanical edits and summaries. Don't take architectural calls."
    ),
    "claude": (
        "Claude prior. Judgment over templates. Native Task for your own model."
    ),
    "codex": (
        "Terminal-native. Run the commands, read the output, keep going. "
        "You win on harness/CLI loops; don't stop to write a strategy memo."
    ),
    "gpt": (
        "Same Codex/GPT prior. Agentic terminal work. Less essay, more command output."
    ),
    "gemini": (
        "Long context + multimodal. If screenshots/PDFs/HTML dumps matter, use them. "
        "Don't summarize the repo when you can open the files."
    ),
    "ds": (
        "Cheap mechanical. Codemods, renames, obvious tests. "
        "Don't invent architecture. If blocked, say blocked — don't guess."
    ),
    "deepseek": (
        "Cheap mechanical. Codemods, renames, obvious tests. Don't invent architecture."
    ),
    "dsv4": (
        "Cheap mechanical. Codemods, renames, obvious tests. Don't invent architecture."
    ),
    "aider": (
        "Repo-map + diffs. Small, committable edits. Don't take over product calls."
    ),
    "copilot": (
        "GitHub-native. PRs, reviews, repo glue. Don't re-architect in a drive-by."
    ),
    "goose": (
        "Recipe/run agent. Do the task and exit. Don't start a conversation."
    ),
    "zai": (
        "GLM via OpenCode. Implement. Don't narrate. Don't hop to yourself."
    ),
    "glm": (
        "GLM via OpenCode. Implement. Don't narrate. Don't hop to yourself."
    ),
    "kimi": (
        "Moonshot. Long context, keep going. Don't write a strategy memo."
    ),
    "moonshot": (
        "Moonshot via OpenCode. Long context, keep going. Don't write a strategy memo."
    ),
    "ollama": (
        "Local model. Mechanical. If it's dumb, say blocked — don't bluff."
    ),
    "qwen": (
        "Coder prior via OpenCode. Implement. Don't invent product calls."
    ),
    "groq": (
        "Fast hosted. Short loops. Don't take architecture."
    ),
    "minimax": (
        "Via OpenCode. Do the task. Don't call yourself."
    ),
    "opencode": (
        "Whatever /connect selected. Do the task. Don't hop to yourself."
    ),
}

# What the OTHER model should know — one line, so they look in the right place.
COUNTER: dict[str, str] = {
    "grok": "Ships fast and token-light; can skip an edge case the card doesn't mention. Read the transcript for what they rejected.",
    "composer": "Fast IDE agent; watch for incomplete multi-file follow-through.",
    "opus": "Strong at catching compressed assumptions; can over-hedge or over-verify if you ask it to. Trust DISAGREE more than STATUS.",
    "sonnet": "Good mid-size review; less stubborn than Opus on hard calls.",
    "codex": "Will run the terminal; watch for 'it passed locally' without the actual invariant.",
    "gpt": "Same as Codex — harness-strong, can be shallow on product judgment.",
    "gemini": "Will ingest a lot of context; can be generic if you don't point at files.",
    "ds": "Mechanical. If the task needed judgment, treat the result as a draft.",
    "deepseek": "Mechanical. If the task needed judgment, treat the result as a draft.",
    "dsv4": "Mechanical. If the task needed judgment, treat the result as a draft.",
    "haiku": "Cheap and thin. Don't treat it as a senior review.",
    "aider": "Diff-shaped. Check the commit, not the prose.",
    "copilot": "PR-shaped. Check whether it actually ran tests.",
    "goose": "One-shot runner. Empty or conversational output usually means it stalled.",
    "zai": "GLM via OpenCode. Treat as an implementer; check the diff, not the prose.",
    "glm": "GLM via OpenCode. Treat as an implementer; check the diff, not the prose.",
    "kimi": "Long-context Moonshot. Watch for generic answers if you didn't point at files.",
    "moonshot": "Long-context Moonshot. Watch for generic answers if you didn't point at files.",
    "ollama": "Local. Quality is whatever is pulled. Verify.",
    "qwen": "Coder prior. Check the diff.",
    "groq": "Fast and thin. Don't treat it as a senior review.",
    "minimax": "Via OpenCode. Check the diff.",
    "opencode": "Whatever model /connect selected. Read the transcript if the card is thin.",
}

# (needles, preferred aliases in order, weight)
RULES: list[tuple[tuple[str, ...], tuple[str, ...], int]] = [
    (("review", "audit", "security", "correctness", "edge case", "invariant", "regress"),
     ("opus", "sonnet", "codex", "grok"), 5),
    (("consult", "should we", "tradeoff", "architecture", "design"),
     ("opus", "grok", "codex", "gemini"), 4),
    (("terminal", "cli", "bash", "infra", "deploy", "k8s", "docker", "harness"),
     ("codex", "grok", "composer", "opus"), 5),
    (("ui", "css", "frontend", "react", "layout", "pixel"),
     ("grok", "composer", "opus", "gemini"), 3),
    (("screenshot", "image", "pdf", "video", "multimodal"),
     ("gemini", "gpt", "opus", "grok"), 6),
    (("codemod", "rename", "mechanical", "boilerplate", "generate tests"),
     ("ds", "haiku", "composer", "aider"), 5),
    (("research", "cite", "url", "web", "paper", "compare", "survey"),
     ("grok", "gemini", "opus", "kimi", "gpt"), 5),
    (("long context", "whole repo", "million token"),
     ("gemini", "kimi", "gpt", "opus"), 4),
]


def lean_in(who: str) -> str:
    return LEAN.get(who, "Peer. Do the task. Use your prior. Don't perform it. Don't call yourself.")


def counterpart(who: str) -> str:
    return COUNTER.get(who, "Different prior. Read their transcript if the card is thin.")


def dossier_path(who: str) -> Path | None:
    for name in (who, {"ds": "deepseek", "dsv4": "deepseek", "gpt": "codex"}.get(who, who)):
        p = DIR / f"{name}.md"
        if p.exists():
            return p
    return None


def route(task: str, role: str, have: list[str]) -> str | None:
    """Pick from `have` using cheap keyword overlap. No model call."""
    if not have:
        return None
    text = f"{role} {task}".lower()
    scores = {a: 0 for a in have}
    for needles, aliases, weight in RULES:
        if any(n in text for n in needles):
            for i, a in enumerate(aliases):
                if a in scores:
                    scores[a] += weight * (len(aliases) - i)
    if role == "review":
        for a, w in (("opus", 6), ("sonnet", 4), ("codex", 2)):
            if a in scores:
                scores[a] += w
    if role == "research":
        for a, w in (("grok", 4), ("gemini", 4), ("kimi", 3), ("opus", 3), ("gpt", 2)):
            if a in scores:
                scores[a] += w
    if role == "worker":
        for a, w in (("grok", 3), ("composer", 2), ("codex", 2), ("ds", 1)):
            if a in scores:
                scores[a] += w
    best = max(have, key=lambda a: (scores[a], -have.index(a)))
    return best


def _family(who: str) -> str:
    w = who.lower()
    groups = (
        (("grok", "composer", "cursor"), "cursor"),
        (("opus", "sonnet", "haiku", "claude", "fable"), "claude"),
        (("codex", "gpt"), "codex"),
        (("kimi", "moonshot"), "kimi"),
        (("zai", "glm"), "zai"),
        (("ds", "deepseek", "dsv4"), "ds"),
        (("gemini", "flash", "pro"), "gemini"),
    )
    for names, fam in groups:
        if w in names:
            return fam
    return w


def route_many(task: str, role: str, have: list[str], n: int = 3) -> list[str]:
    """Top-N by the same cheap scores, different products first. No model call."""
    if not have or n < 1:
        return []
    text = f"{role} {task}".lower()
    scores = {a: 0 for a in have}
    for needles, aliases, weight in RULES:
        if any(needle in text for needle in needles):
            for i, a in enumerate(aliases):
                if a in scores:
                    scores[a] += weight * (len(aliases) - i)
    if role == "review":
        for a, w in (("opus", 6), ("sonnet", 4), ("codex", 2)):
            if a in scores:
                scores[a] += w
    if role == "research":
        for a, w in (("grok", 4), ("gemini", 4), ("kimi", 3), ("opus", 3), ("gpt", 2)):
            if a in scores:
                scores[a] += w
    if role == "worker":
        for a, w in (("grok", 3), ("composer", 2), ("codex", 2), ("ds", 1)):
            if a in scores:
                scores[a] += w
    ranked = sorted(have, key=lambda a: (scores[a], -have.index(a)), reverse=True)
    out: list[str] = []
    seen: set[str] = set()
    for a in ranked:
        fam = _family(a)
        if fam in seen:
            continue
        seen.add(fam)
        out.append(a)
        if len(out) >= n:
            return out
    for a in ranked:
        if a not in out:
            out.append(a)
        if len(out) >= n:
            break
    return out


_SLICES = (
    "Slice: current practice and primary sources. Go as deep as the question needs. Cite URLs. No padding.",
    "Slice: failure modes, constraints, and what a fast answer usually skips. Go deep. Cite URLs.",
    "Slice: alternatives, cost, and operational reality. Go deep. Cite URLs.",
    "Slice: papers, specs, and the long-context trail. Quote claims. Cite URLs.",
)
_SLICE_PREF = {
    "grok": 0, "composer": 0, "cursor": 0, "zai": 0, "glm": 0,
    "opus": 1, "sonnet": 1, "claude": 1,
    "codex": 2, "gpt": 2, "ds": 2, "ollama": 2, "aider": 2,
    "gemini": 3, "kimi": 3, "moonshot": 3, "qwen": 3,
}


def research_slices(names: list[str]) -> dict[str, str]:
    """Cheap angle split so several researchers don't write the same memo."""
    if not names:
        return {}
    if len(names) == 1:
        return {names[0]: "Go as deep as the question needs. Cite URLs. No padding."}
    used: set[int] = set()
    out: dict[str, str] = {}
    n = len(_SLICES)
    for who in names:
        idx = _SLICE_PREF.get(who, 0)
        for _ in range(n):
            if idx not in used:
                break
            idx = (idx + 1) % n
        used.add(idx)
        out[who] = _SLICES[idx]
    return out
