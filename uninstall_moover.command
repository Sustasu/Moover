#!/bin/zsh
set -e

APP_SUPPORT="$HOME/Library/Application Support/Moover"

for LABEL in com.local.moover com.local.automatic-cursor-mover; do
  PLIST_TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"
  launchctl bootout "gui/$(id -u)" "$PLIST_TARGET" 2>/dev/null || true
  rm -f "$PLIST_TARGET"
done

rm -f "$APP_SUPPORT/moover.py"
rmdir "$APP_SUPPORT" 2>/dev/null || true

rm -f /tmp/moover.log /tmp/moover.err
rm -f /tmp/automatic-cursor-mover.log /tmp/automatic-cursor-mover.err

echo "Uninstalled Moover."
