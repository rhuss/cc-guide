#!/usr/bin/env bash
# Report the companion components available for a guide project.
#   usage: deps.sh [--dir DIR]
# Prints JSON {superpowers: bool, prose: bool, excalidraw_allowed: bool}:
#   superpowers, prose: an entry "superpowers@*" or "prose@*" exists in
#     $HOME/.claude/plugins/installed_plugins.json
#   excalidraw_allowed: .claude/settings.local.json or .claude/settings.json in DIR
#     (default: the current directory) has a permissions.allow entry starting
#     with "mcp__excalidraw"
set -uo pipefail

dir=.
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) dir=${2:?--dir requires a value}; shift 2 ;;
    -h|--help) echo "usage: deps.sh [--dir DIR]"; exit 0 ;;
    *) echo "usage: deps.sh [--dir DIR]" >&2; exit 2 ;;
  esac
done

registry="${HOME}/.claude/plugins/installed_plugins.json"
settings=()
for f in "$dir/.claude/settings.local.json" "$dir/.claude/settings.json"; do
  [[ -f "$f" ]] && settings+=("$f")
done

if [[ -z "${CC_GUIDE_NO_JQ:-}" ]] && command -v jq >/dev/null 2>&1; then
  has_plugin() { # has_plugin <prefix>
    [[ -f "$registry" ]] || { echo false; return; }
    jq --arg p "$1@" '[(.plugins // {}) | keys[] | select(startswith($p))] | length > 0' "$registry" 2>/dev/null || echo false
  }
  superpowers=$(has_plugin superpowers)
  prose=$(has_plugin prose)
  excalidraw=false
  for f in ${settings[@]+"${settings[@]}"}; do
    if [[ $(jq '[.permissions.allow // [] | .[] | strings | select(startswith("mcp__excalidraw"))] | length > 0' "$f" 2>/dev/null) == true ]]; then
      excalidraw=true
    fi
  done
  jq -n --argjson s "$superpowers" --argjson p "$prose" --argjson e "$excalidraw" \
    '{superpowers: $s, prose: $p, excalidraw_allowed: $e}'
else
  python3 - "$registry" ${settings[@]+"${settings[@]}"} <<'PY'
import json, sys
registry, settings = sys.argv[1], sys.argv[2:]

def load(path):
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}

keys = list((load(registry).get("plugins") or {}).keys())
allowed = False
for path in settings:
    allow = ((load(path).get("permissions") or {}).get("allow") or [])
    allowed = allowed or any(isinstance(a, str) and a.startswith("mcp__excalidraw") for a in allow)
print(json.dumps({
    "superpowers": any(k.startswith("superpowers@") for k in keys),
    "prose": any(k.startswith("prose@") for k in keys),
    "excalidraw_allowed": allowed,
}, indent=2))
PY
fi
