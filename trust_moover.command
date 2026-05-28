#!/bin/zsh
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

xattr -dr com.apple.quarantine "$ROOT" 2>/dev/null || true
chmod +x "$ROOT"/*.command
chmod +x "$ROOT/moover.py"

echo "Moover is ready to run on this Mac."
