#!/bin/zsh
set -e

LABEL="com.local.moover"
PLIST_SOURCE="$(dirname "$0")/$LABEL.plist"
PLIST_TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"
APP_SUPPORT="$HOME/Library/Application Support/Moover"

mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$APP_SUPPORT"
cp "$(dirname "$0")/moover.py" "$APP_SUPPORT/moover.py"
chmod +x "$APP_SUPPORT/moover.py"
cp "$PLIST_SOURCE" "$PLIST_TARGET"
launchctl bootout "gui/$(id -u)" "$PLIST_TARGET" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_TARGET"
launchctl kickstart -k "gui/$(id -u)/$LABEL"

echo "Installed and started $LABEL."
echo "Moover script location: $APP_SUPPORT/moover.py"
echo "Active window enabled."
echo "Logs: /tmp/moover.log"
