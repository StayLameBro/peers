#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"
export PEERS_HOME="$HERE/tests/.desk"
rm -rf "$PEERS_HOME"
mkdir -p "$PEERS_HOME"
python3 -m py_compile peers providers.py dossiers.py
python3 peers | grep -q "one office"
python3 peers | grep -q "cursor-agent login"
python3 peers version | grep -q "peers 0.3"
python3 tests/test_providers.py

# live desk must never be tracked
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if git ls-files | grep -E '(^|/)(observed\.md|transcript\.md|handoff\.md|live\.md)$|/(runs|threads)/|\.jsonl$'; then
    echo "fail: live desk/transcript files are tracked" >&2
    exit 1
  fi
fi

# dry-run must not call a model; --allow-self so CI/dev shells inside Cursor still compile the grok path
out="$(python3 peers grok --dry-run --allow-self --cwd "$HERE" "noop task")"
echo "$out" | grep -q "STATUS: dry-run"
echo "$out" | grep -q "THREAD:"
prompt="$(echo "$out" | awk -F': ' '/^PROMPT:/{print $2; exit}')"
grep -q "Ship." "$prompt"

# from Cursor, grok is yourself — must refuse
set +e
err="$(PEERS_CALLER=cursor python3 peers grok --dry-run --cwd "$HERE" "noop" 2>&1)"
rc=$?
set -e
[ "$rc" -ne 0 ]
echo "$err" | grep -qi "yourself"

# from Cursor, opus is a different product — dry-run ok without claude installed
out="$(PEERS_CALLER=cursor python3 peers opus --dry-run --cwd "$HERE" "noop task")"
echo "$out" | grep -q "STATUS: dry-run"
prompt="$(echo "$out" | awk -F': ' '/^PROMPT:/{print $2; exit}')"
grep -q "Judgment" "$prompt"

# both dry-run with an explicit desk (not locked to two)
out="$(python3 peers both --with grok,opus --dry-run --allow-self --cwd "$HERE" "hard call")"
echo "$out" | grep -q "STATUS: dry-run"
echo "$out" | grep -q "DESK:"

out="$(python3 peers both --with grok,opus,codex --dry-run --allow-self --cwd "$HERE" "hard call")"
echo "$out" | grep -q "codex"

# research fans out with slices
out="$(python3 peers research --with grok,gemini --dry-run --allow-self --cwd "$HERE" "sqlite vs postgres")"
echo "$out" | grep -q "DESK:"
echo "$out" | grep -q "dry-run"

# from Cursor, both --with grok,opus must NOT spawn grok (that's you)
out="$(PEERS_CALLER=cursor python3 peers both --with grok,opus --dry-run --cwd "$HERE" "hard call")"
echo "$out" | grep -q "NATIVE:"
echo "$out" | grep -q "opus"

python3 peers note --cwd "$HERE" "smoke note from tests"

# PEERS_HOME must not be the git checkout
set +e
err="$(PEERS_HOME="$HERE" python3 peers note --cwd "$HERE" "nope" 2>&1)"
rc=$?
set -e
[ "$rc" -ne 0 ]
echo "$err" | grep -qi "checkout"

# PEERS_BIN must not interpolate into anything
set +e
err="$(PEERS_BIN='$(id)' python3 peers setup 2>&1)"
rc=$?
set -e
[ "$rc" -ne 0 ]
echo "$err" | grep -qi "PEERS_BIN"

echo "smoke ok"
