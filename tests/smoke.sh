#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"
python3 -m py_compile peer
python3 peer | grep -q "two senior models"
python3 peer version | grep -q peerdesk
out="$(python3 peer grok --dry-run --cwd "$HERE" "noop task")"
echo "$out" | grep -q "STATUS: dry-run"
echo "$out" | grep -q "THREAD:"
echo "smoke ok"
