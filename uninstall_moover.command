#!/bin/zsh
set -e

LABEL="com.local.moover"
PLIST_TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$(id -u)" "$PLIST_TARGET" 2>/dev/null || true
rm -f "$PLIST_TARGET"

echo "Uninstalled $LABEL."
