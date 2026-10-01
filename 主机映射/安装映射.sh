#!/bin/bash
# Install the F24 -> Fn mapping for the current user (needed by firmware v2 only).
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/ensure_fn_mapping.py"
BASE="$HOME/Library/Application Support/ATK-YOGO-Fn"
AGENT="$HOME/Library/LaunchAgents/local.atk-yogo.fn-map.plist"
mkdir -p "$BASE" "$HOME/Library/LaunchAgents"
cp "$SRC" "$BASE/ensure_fn_mapping.py"
/usr/bin/python3 - "$BASE" "$AGENT" <<'PY'
import plistlib,sys
base,agent=sys.argv[1],sys.argv[2]
with open(agent,'wb') as f:
  plistlib.dump({'Label':'local.atk-yogo.fn-map','ProgramArguments':['/usr/bin/python3',base+'/ensure_fn_mapping.py'],
   'RunAtLoad':True,'StartInterval':5,'ProcessType':'Background',
   'StandardOutPath':base+'/fn-map.log','StandardErrorPath':base+'/fn-map-error.log'},f)
PY
plutil -lint "$AGENT"
launchctl bootout "gui/$(id -u)" "$AGENT" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$AGENT"
echo "Installed. Mapping is applied within a few seconds of the keyboard connecting."
