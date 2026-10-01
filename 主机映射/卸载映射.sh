#!/bin/bash
# Remove the LaunchAgent and only the F24 -> Fn entry this tool created.
# --dry-run: show what would change, touch nothing.
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
AGENT="$HOME/Library/LaunchAgents/local.atk-yogo.fn-map.plist"
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
if [ $DRY = 0 ]; then
  launchctl bootout "gui/$(id -u)" "$AGENT" 2>/dev/null || true
  rm -f "$AGENT"
fi
DRY=$DRY /usr/bin/python3 - "$DIR" <<'PY'
import json,os,sys
sys.path.insert(0,sys.argv[1]);import ensure_fn_mapping as e
dry=os.environ['DRY']=='1'
for label,match in e.TARGETS:
  services=e.parse_services(e.run(match,['--get','UserKeyMapping']))
  if not services or not any(a==e.SRC for s in services for a,_ in s):continue
  rest={tuple(p for p in s if p[0]!=e.SRC) for s in services}
  if len(rest)!=1:print(f'{label}: interfaces have different mappings; left unchanged');continue
  keep=[{'HIDKeyboardModifierMappingSrc':a,'HIDKeyboardModifierMappingDst':b} for a,b in rest.pop()]
  print(f'{label}: remove F24->Fn, keep {len(keep)} other mapping(s)'+(' (dry run)' if dry else ''))
  if not dry:e.run(match,['--set',json.dumps({'UserKeyMapping':keep})])
PY
[ $DRY = 0 ] && echo "Removed. You may delete ~/Library/Application Support/ATK-YOGO-Fn manually."
exit 0
