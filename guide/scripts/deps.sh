#!/usr/bin/env bash
# Report the companion components available for a guide project.
#   usage: deps.sh [--dir DIR] [--session-dir DIR]
# Prints JSON {superpowers: bool, prose: bool, excalidraw_allowed: bool,
#              excalidraw_allowed_in: [paths]}:
#   superpowers, prose: an entry "superpowers@*" or "prose@*" exists in
#     $HOME/.claude/plugins/installed_plugins.json
#   excalidraw_allowed: a permissions.allow entry starting with "mcp__excalidraw"
#     exists in any settings file Claude Code may read for the controlling session:
#       1. .claude/settings.local.json or .claude/settings.json in the guide project
#          (--dir, default: the current directory)
#       2. .claude/settings.local.json or .claude/settings.json in the session
#          directory (--session-dir, default: the current directory; its git
#          toplevel when it is inside a git repository)
#       3. $HOME/.claude/settings.json (user settings)
#     The guide project's settings apply only to sessions started there; the
#     session directory and user settings apply to the session that runs now.
#   excalidraw_allowed_in: the settings files (absolute paths, in the order above)
#     that hold such an entry; empty when excalidraw_allowed is false
set -uo pipefail

usage="usage: deps.sh [--dir DIR] [--session-dir DIR]"
dir=.
session_dir=.
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) dir=${2:?--dir requires a value}; shift 2 ;;
    --session-dir) session_dir=${2:?--session-dir requires a value}; shift 2 ;;
    -h|--help) echo "$usage"; exit 0 ;;
    *) echo "$usage" >&2; exit 2 ;;
  esac
done

abspath() { # abspath <dir>: physical absolute path, or the input when it does not exist
  (CDPATH= cd -- "$1" 2>/dev/null && pwd -P) || printf '%s\n' "$1"
}

guide_root=$(abspath "$dir")
session_root=$(abspath "$session_dir")
if toplevel=$(git -C "$session_root" rev-parse --show-toplevel 2>/dev/null) && [[ -n "$toplevel" ]]; then
  session_root=$(abspath "$toplevel")
fi
home_root=$(abspath "$HOME")

registry="${HOME}/.claude/plugins/installed_plugins.json"
settings=()
for f in "$guide_root/.claude/settings.local.json" "$guide_root/.claude/settings.json" \
         "$session_root/.claude/settings.local.json" "$session_root/.claude/settings.json" \
         "$home_root/.claude/settings.json"; do
  [[ -f "$f" ]] || continue
  seen=false
  for s in ${settings[@]+"${settings[@]}"}; do
    [[ "$s" == "$f" ]] && seen=true
  done
  [[ $seen == false ]] && settings+=("$f")
done

if [[ -z "${CC_GUIDE_NO_JQ:-}" ]] && command -v jq >/dev/null 2>&1; then
  has_plugin() { # has_plugin <prefix>
    [[ -f "$registry" ]] || { echo false; return; }
    jq --arg p "$1@" '[(.plugins // {}) | keys[] | select(startswith($p))] | length > 0' "$registry" 2>/dev/null || echo false
  }
  superpowers=$(has_plugin superpowers)
  prose=$(has_plugin prose)
  found=()
  for f in ${settings[@]+"${settings[@]}"}; do
    if [[ $(jq '[.permissions.allow // [] | .[] | strings | select(startswith("mcp__excalidraw"))] | length > 0' "$f" 2>/dev/null) == true ]]; then
      found+=("$f")
    fi
  done
  jq -n --argjson s "$superpowers" --argjson p "$prose" \
    '{superpowers: $s, prose: $p, excalidraw_allowed: ($ARGS.positional | length > 0), excalidraw_allowed_in: $ARGS.positional}' \
    --args ${found[@]+"${found[@]}"}
else
  python3 - "$registry" ${settings[@]+"${settings[@]}"} <<'PY'
import json, sys
registry, settings = sys.argv[1], sys.argv[2:]

def load(path):
    try:
        with open(path) as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}

def allows_excalidraw(path):
    permissions = load(path).get("permissions")
    allow = (permissions.get("allow") if isinstance(permissions, dict) else None) or []
    return isinstance(allow, list) and any(isinstance(a, str) and a.startswith("mcp__excalidraw") for a in allow)

keys = list((load(registry).get("plugins") or {}).keys())
found = [path for path in settings if allows_excalidraw(path)]
print(json.dumps({
    "superpowers": any(k.startswith("superpowers@") for k in keys),
    "prose": any(k.startswith("prose@") for k in keys),
    "excalidraw_allowed": bool(found),
    "excalidraw_allowed_in": found,
}, indent=2))
PY
fi
