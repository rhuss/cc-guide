#!/usr/bin/env bash
# Per-harness adapter check for Claude Code (FR-014, SC-003, SC-007): the Claude
# manifest is valid and listed in the marketplace, the six slash-command wrappers
# exist and are thin (preflight then the matching skill, no duplicated logic), and
# the six commands resolve to discoverable skills.
#   usage: bash tests/adapters/test_harness_claude.sh
# Lightweight on purpose: the Claude dimension added alongside the per-format smoke
# tests. It needs only python3.
set -uo pipefail

REPO=$(cd "$(dirname "$0")/../.." && pwd)
PLUGIN="$REPO/guide"
MANIFEST="$PLUGIN/.claude-plugin/plugin.json"
MARKETPLACE="$REPO/.claude-plugin/marketplace.json"
COMMANDS=(create evolve preview export validate upstream)
fail=0
pass() { echo "PASS claude: $1"; }
failed() { echo "FAIL claude: $1"; fail=1; }

if python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$MANIFEST" 2>/dev/null; then
  pass "manifest is valid JSON"
else
  failed "manifest is not valid JSON ($MANIFEST)"; echo "FAILURES in claude harness check"; exit "$fail"
fi

# The marketplace lists the guide plugin with source ./guide.
if python3 - "$MARKETPLACE" <<'PY' 2>/dev/null
import json, sys
m = json.load(open(sys.argv[1]))
plugins = m.get("plugins", [])
ok = any(p.get("name") == "guide" and p.get("source") == "./guide" for p in plugins)
sys.exit(0 if ok else 1)
PY
then
  pass "marketplace lists guide with source ./guide"
else
  failed "marketplace does not list guide with source ./guide"
fi

# The six slash-command wrappers exist and are thin: each invokes guide:preflight
# and the matching guide:<name> skill, and duplicates no skill logic (kept small).
for c in "${COMMANDS[@]}"; do
  wrapper="$PLUGIN/commands/$c.md"
  skill="$PLUGIN/skills/$c/SKILL.md"
  if [[ ! -f "$wrapper" ]]; then
    failed "command wrapper $c.md missing"; continue
  fi
  if grep -q "guide:preflight" "$wrapper" && grep -q "guide:$c" "$wrapper"; then
    pass "wrapper $c.md chains preflight and guide:$c"
  else
    failed "wrapper $c.md does not chain preflight and guide:$c"
  fi
  if [[ -f "$skill" ]] && grep -qE "^name:[[:space:]]*$c[[:space:]]*$" "$skill"; then
    pass "command $c resolves to skill $c"
  else
    failed "command $c does not resolve to skill $c"
  fi
done

[[ $fail -eq 0 ]] && echo "claude harness check OK" || echo "FAILURES in claude harness check"
exit $fail
