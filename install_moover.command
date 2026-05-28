#!/bin/zsh
set -e

LABEL="com.local.moover"
PLIST_TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"
APP_SUPPORT="$HOME/Library/Application Support/Moover"
PYTHON="/usr/bin/python3"

mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$APP_SUPPORT"
cp "$(dirname "$0")/moover.py" "$APP_SUPPORT/moover.py"
chmod +x "$APP_SUPPORT/moover.py"

"$PYTHON" - "$PLIST_TARGET" "$APP_SUPPORT" "$LABEL" <<'PY'
import plistlib
import sys
from pathlib import Path

plist_target = Path(sys.argv[1])
app_support = Path(sys.argv[2])
label = sys.argv[3]

plist = {
    "Label": label,
    "ProgramArguments": [
        "/usr/bin/python3",
        str(app_support / "moover.py"),
    ],
    "WorkingDirectory": str(app_support),
    "RunAtLoad": True,
    "StandardOutPath": "/tmp/moover.log",
    "StandardErrorPath": "/tmp/moover.err",
}

plist_target.write_bytes(plistlib.dumps(plist))
PY

plutil -lint "$PLIST_TARGET" >/dev/null
launchctl bootout "gui/$(id -u)" "$PLIST_TARGET" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_TARGET"
launchctl kickstart -k "gui/$(id -u)/$LABEL"

echo "Installed and started $LABEL."
echo "Moover script location: $APP_SUPPORT/moover.py"
echo "Moover will run until it is uninstalled."
echo "Logs: /tmp/moover.log"
