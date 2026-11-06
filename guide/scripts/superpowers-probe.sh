#!/usr/bin/env bash
# Advisory superpowers version check for cc-guide (FR-016).
#   usage: superpowers-probe.sh [VERSION]
#
# Presence of superpowers is decided by capability exposure in the session (the
# controller sees superpowers' skills), NOT by this script and NOT by reading any
# plugin registry or install path. This script only compares a best-effort reported
# VERSION against the single known-good threshold in ../compat.yaml and prints JSON:
#   {version, known, ok, problems[]}
# It is advisory and never blocks. Exit status:
#   0  VERSION is at or above the threshold, or VERSION was not reported
#   3  an advisory problem was recorded in problems[]: VERSION is below the
#      threshold, or compat.yaml was not found next to the plugin scripts
# A version that is not reported (no argument) simply skips the comparison.
set -uo pipefail

here=$(cd "$(dirname "$0")" && pwd)
compat="$here/../compat.yaml"
version="${1:-}"
problems=()

have_jq() { [[ -z "${CC_GUIDE_NO_JQ:-}" ]] && command -v jq >/dev/null 2>&1; }

# threshold: the known_good_version scalar from compat.yaml
threshold=$(sed -n 's/^known_good_version:[[:space:]]*"\{0,1\}\([0-9][0-9.]*\)"\{0,1\}.*/\1/p' "$compat" 2>/dev/null | head -1)

# ge <a> <b>: succeeds when dotted-numeric version a is >= version b
ge() {
  awk -v a="$1" -v b="$2" 'BEGIN {
    n = split(a, x, "."); m = split(b, y, ".");
    for (i = 1; i <= (n > m ? n : m); i++) {
      if ((x[i] + 0) > (y[i] + 0)) exit 0;
      if ((x[i] + 0) < (y[i] + 0)) exit 1;
    }
    exit 0 }'
}

known=false
if [[ ! -f "$compat" ]]; then
  problems+=("compat.yaml not found next to the plugin scripts: $compat")
fi

if [[ -n "$version" && -n "$threshold" ]]; then
  if ge "$version" "$threshold"; then
    known=true
  else
    problems+=("superpowers $version is older than the known-good $threshold; update superpowers for the active harness (advisory, continuing)")
  fi
fi

emit() { # emit <version> <known>
  if have_jq; then
    { [[ ${#problems[@]} -gt 0 ]] && printf '%s\n' "${problems[@]}"; } | jq -R . | jq -s \
      --arg v "$1" --argjson known "$2" \
      '{version: (if $v == "" then null else $v end), known: $known, ok: true, problems: .}'
  else
    python3 -I - "$1" "$2" ${problems[@]+"${problems[@]}"} <<'PY'
import json, sys
v, known = sys.argv[1], sys.argv[2]
print(json.dumps({"version": v or None, "known": known == "true",
                  "ok": True, "problems": sys.argv[3:]}, indent=2))
PY
  fi
}

emit "$version" "$known"
[[ ${#problems[@]} -gt 0 ]] && exit 3
exit 0
