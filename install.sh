#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"

mkdir -p "$BIN_DIR"
ln -sf "$DIR/bin/wbw-harvester" "$BIN_DIR/wbw-harvester"

echo "✅ Harvester installed. You can now run 'wbw-harvester' from anywhere."
