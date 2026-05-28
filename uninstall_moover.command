#!/bin/zsh
set -e

LABEL="com.local.moover"
PLIST_TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"
APP_SUPPORT="$HOME/Library/Application Support/Moover"

launchctl bootout "gui/$(id -u)" "$PLIST_TARGET" 2>/dev/null || true
rm -f "$PLIST_TARGET"
rm -f "$APP_SUPPORT/moover.py"
rmdir "$APP_SUPPORT" 2>/dev/null || true

echo "Uninstalled $LABEL."
