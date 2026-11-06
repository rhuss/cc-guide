#!/usr/bin/env bash
# Emit the capability-detection record for a guide run (the capability-detection
# contract, FR-007).
#   usage: deps.sh [--harness claude|codex|opencode]
#                  [--superpowers true|false] [--superpowers-version V]
#                  [--multi-agent true|false] [--prose true|false]
#                  [--excalidraw true|false] [--dir DIR] [--session-dir DIR]
#
# The capability booleans (superpowers, prose, excalidraw, multi_agent) are decided
# by in-session capability exposure: the controller (the preflight skill) reads its
# OWN exposed skills and tools and passes the results here. This script does NOT
# read a plugin registry or a settings file to decide them (FR-005, FR-007). Each
# boolean defaults to false; --harness defaults to claude; --superpowers-version is
# best-effort and may be omitted (reported as null).
#
# Prints JSON:
#   {harness, superpowers, superpowers_version, multi_agent, prose, excalidraw,
#    excalidraw_allowed, excalidraw_allowed_in}
#
# excalidraw_allowed / excalidraw_allowed_in are the Claude-only settings/permission
# wiring (FR-010). They are computed ONLY when harness == claude, from the settings
# files Claude Code may read for the controlling session:
#   1. .claude/settings.local.json or .claude/settings.json in the guide project
#      (--dir, default: the current directory)
#   2. .claude/settings.local.json or .claude/settings.json in the session
#      directory (--session-dir, default: the current directory; its git toplevel
#      when it is inside a git repository)
#   3. $HOME/.claude/settings.json (user settings)
# On any other harness they are false / [] and unused.
set -uo pipefail

usage="usage: deps.sh [--harness H] [--superpowers B] [--superpowers-version V] [--multi-agent B] [--prose B] [--excalidraw B] [--dir DIR] [--session-dir DIR]"
dir=.
session_dir=.
harness=claude
superpowers=false
superpowers_version=""
multi_agent=false
prose=false
excalidraw=false

# bool NORMALIZES an argument to the literal string true or false.
bool() { [[ "${1:-}" == true || "${1:-}" == 1 || "${1:-}" == yes ]] && echo true || echo false; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir) dir=${2:?--dir requires a value}; shift 2 ;;
    --session-dir) session_dir=${2:?--session-dir requires a value}; shift 2 ;;
    --harness) harness=${2:?--harness requires a value}; shift 2 ;;
    --superpowers) superpowers=${2:?--superpowers requires a value}; superpowers=$(bool "$superpowers"); shift 2 ;;
    --superpowers-version) superpowers_version=${2:?--superpowers-version requires a value}; shift 2 ;;
    --multi-agent) multi_agent=${2:?--multi-agent requires a value}; multi_agent=$(bool "$multi_agent"); shift 2 ;;
    --prose) prose=${2:?--prose requires a value}; prose=$(bool "$prose"); shift 2 ;;
    --excalidraw) excalidraw=${2:?--excalidraw requires a value}; excalidraw=$(bool "$excalidraw"); shift 2 ;;
    -h|--help) echo "$usage"; exit 0 ;;
    *) echo "$usage" >&2; exit 2 ;;
  esac
done

abspath() { # abspath <dir>: physical absolute path, or the input when it does not exist
  (CDPATH= cd -- "$1" 2>/dev/null && pwd -P) || printf '%s\n' "$1"
}

# Claude-only settings/permission wiring for Excalidraw (FR-010). Other harnesses
# manage permissions differently and need no settings file for v1.
found=()
if [[ "$harness" == claude ]]; then
  guide_root=$(abspath "$dir")
  session_root=$(abspath "$session_dir")
  if toplevel=$(git -C "$session_root" rev-parse --show-toplevel 2>/dev/null) && [[ -n "$toplevel" ]]; then
    session_root=$(abspath "$toplevel")
  fi
  home_root=$(abspath "$HOME")

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
    for f in ${settings[@]+"${settings[@]}"}; do
      if [[ $(jq '[.permissions.allow // [] | .[] | strings | select(startswith("mcp__excalidraw"))] | length > 0' "$f" 2>/dev/null) == true ]]; then
        found+=("$f")
      fi
    done
  else
    while IFS= read -r line; do
      [[ -n "$line" ]] && found+=("$line")
    done < <(python3 -I - ${settings[@]+"${settings[@]}"} <<'PY'
import json, sys

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

for path in sys.argv[1:]:
    if allows_excalidraw(path):
        print(path)
PY
)
  fi
fi

if [[ -z "${CC_GUIDE_NO_JQ:-}" ]] && command -v jq >/dev/null 2>&1; then
  jq -n --arg harness "$harness" --argjson sp "$superpowers" --arg spv "$superpowers_version" \
    --argjson ma "$multi_agent" --argjson prose "$prose" --argjson ex "$excalidraw" \
    '{harness: $harness, superpowers: $sp,
      superpowers_version: (if $spv == "" then null else $spv end),
      multi_agent: $ma, prose: $prose, excalidraw: $ex,
      excalidraw_allowed: ($ARGS.positional | length > 0),
      excalidraw_allowed_in: $ARGS.positional}' \
    --args ${found[@]+"${found[@]}"}
else
  python3 -I - "$harness" "$superpowers" "$superpowers_version" "$multi_agent" "$prose" "$excalidraw" ${found[@]+"${found[@]}"} <<'PY'
import json, sys
harness, sp, spv, ma, prose, ex = sys.argv[1:7]
found = sys.argv[7:]
print(json.dumps({
    "harness": harness,
    "superpowers": sp == "true",
    "superpowers_version": spv or None,
    "multi_agent": ma == "true",
    "prose": prose == "true",
    "excalidraw": ex == "true",
    "excalidraw_allowed": bool(found),
    "excalidraw_allowed_in": found,
}, indent=2))
PY
fi
