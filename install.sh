#!/usr/bin/env bash
# install.sh — put peers on PATH and install editor skills
# Works from a checkout, or: curl -fsSL https://raw.githubusercontent.com/StayLameBro/peers/main/install.sh | bash
set -euo pipefail

REPO="${PEERS_REPO:-https://github.com/StayLameBro/peers.git}"
BIN="${PEERS_BIN:-$HOME/.local/bin}"
case "$BIN" in
  /*) ;;
  *) echo "install.sh: PEERS_BIN must be an absolute path" >&2; exit 1 ;;
esac
if ! printf '%s' "$BIN" | grep -Eq '^/[A-Za-z0-9._/-]+$'; then
  echo "install.sh: PEERS_BIN has unsafe characters" >&2
  exit 1
fi
SHARE="${XDG_DATA_HOME:-$HOME/.local/share}/peers"

if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
  HERE=""
fi

if [ -z "$HERE" ] || [ ! -f "$HERE/peers" ]; then
  SRC="${XDG_DATA_HOME:-$HOME/.local/share}/peers-src"
  if [ -d "$SRC/.git" ]; then
    git -C "$SRC" pull --ff-only
  else
    mkdir -p "$(dirname "$SRC")"
    git clone --depth 1 "$REPO" "$SRC"
  fi
  HERE="$SRC"
fi

if [ ! -f "$HERE/peers" ] || [ ! -f "$HERE/providers.py" ] || [ ! -f "$HERE/dossiers.py" ]; then
  echo "install.sh: peers + providers.py + dossiers.py missing in $HERE" >&2
  exit 1
fi

mkdir -p "$BIN" "$SHARE"
chmod 700 "$SHARE" 2>/dev/null || true
cp "$HERE/peers" "$SHARE/peers"
cp "$HERE/providers.py" "$SHARE/providers.py"
cp "$HERE/dossiers.py" "$SHARE/dossiers.py"
rm -rf "$SHARE/skills" "$SHARE/commands" "$SHARE/dossiers"
cp -R "$HERE/skills" "$SHARE/skills"
cp -R "$HERE/commands" "$SHARE/commands"
cp -R "$HERE/dossiers" "$SHARE/dossiers"
chmod +x "$SHARE/peers"

ln -sfn "$SHARE/peers" "$BIN/peers"
ln -sfn "$SHARE/peers" "$BIN/peer"
rm -f "$BIN/grok46" "$BIN/opus-peer"

path_has_bin=0
case ":$PATH:" in
  *":$BIN:"*) path_has_bin=1 ;;
esac

if [ "$path_has_bin" -eq 0 ]; then
  rc=""
  if [ -n "${ZSH_VERSION:-}" ] || [ -f "$HOME/.zshrc" ]; then
    rc="$HOME/.zshrc"
  elif [ -f "$HOME/.bashrc" ]; then
    rc="$HOME/.bashrc"
  else
    rc="$HOME/.profile"
  fi
  if [ -f "$rc" ] && grep -q 'peers: PATH' "$rc" 2>/dev/null; then
    :
  else
    printf '\n# peers: PATH\nexport PATH="%s:$PATH"\n' "$BIN" >> "$rc"
    echo "ok   added $BIN to PATH in $rc"
  fi
  export PATH="$BIN:$PATH"
fi

"$BIN/peers" setup
echo "Next:  peers doctor"
