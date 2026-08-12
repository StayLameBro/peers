#!/usr/bin/env bash
# install.sh — put peer on PATH and install editor skills
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BIN="${PEERDESK_BIN:-$HOME/.local/bin}"
SHARE="${XDG_DATA_HOME:-$HOME/.local/share}/peerdesk"

if [ ! -f "$HERE/peer" ]; then
  echo "install.sh: run this from a peerdesk checkout (./peer missing)" >&2
  exit 1
fi

mkdir -p "$BIN" "$SHARE"
cp "$HERE/peer" "$SHARE/peer"
rm -rf "$SHARE/skills" "$SHARE/commands"
cp -R "$HERE/skills" "$SHARE/skills"
cp -R "$HERE/commands" "$SHARE/commands"
chmod +x "$SHARE/peer"

ln -sfn "$SHARE/peer" "$BIN/peer"
ln -sfn "$SHARE/peer" "$BIN/grok46"
ln -sfn "$SHARE/peer" "$BIN/opus-peer"

case ":$PATH:" in
  *":$BIN:"*) ;;
  *)
    echo "Add this to your shell rc (~/.zshrc or ~/.bashrc):"
    echo "  export PATH=\"$BIN:\$PATH\""
    echo
    ;;
esac

"$BIN/peer" setup
echo
echo "Next:"
echo "  peer doctor"
echo "  cd your-project && peer grok \"your task\""
