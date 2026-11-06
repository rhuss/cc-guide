#!/usr/bin/env bash
# Per-harness adapter check for Codex (FR-014, SC-007): the Codex manifest is valid
# JSON, its version matches the Claude manifest, it points at the shared skills
# directory, and the six guide commands are discoverable there as skills.
#   usage: bash tests/adapters/test_harness_codex.sh
# Lightweight on purpose: this is the harness dimension added alongside the heavier
# per-format smoke tests, so it needs only python3 (no node, npx, or Playwright).
set -uo pipefail

REPO=$(cd "$(dirname "$0")/../.." && pwd)
PLUGIN="$REPO/guide"
CODEX="$PLUGIN/.codex-plugin/plugin.json"
CLAUDE="$PLUGIN/.claude-plugin/plugin.json"
COMMANDS=(create evolve preview export validate upstream)
fail=0
pass() { echo "PASS codex: $1"; }
failed() { echo "FAIL codex: $1"; fail=1; }

json_get() { python3 -c "import json,sys; v=json.load(open(sys.argv[1])); print(v.get(sys.argv[2], ''))" "$1" "$2" 2>/dev/null; }

if python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$CODEX" 2>/dev/null; then
  pass "manifest is valid JSON"
else
  failed "manifest is not valid JSON ($CODEX)"; echo "FAILURES in codex harness check"; exit "$fail"
fi

skills=$(json_get "$CODEX" skills)
[[ "$skills" == "./skills/" ]] && pass "skills points at ./skills/" || failed "skills is '$skills', expected ./skills/"

cv=$(json_get "$CODEX" version)
clv=$(json_get "$CLAUDE" version)
if [[ -n "$cv" && "$cv" == "$clv" ]]; then
  pass "version $cv matches the Claude manifest"
else
  failed "version mismatch: codex=$cv claude=$clv"
fi

for c in "${COMMANDS[@]}"; do
  skill="$PLUGIN/skills/$c/SKILL.md"
  if [[ -f "$skill" ]] && grep -qE "^name:[[:space:]]*$c[[:space:]]*$" "$skill"; then
    pass "command $c is discoverable as skill $c"
  else
    failed "command $c is not discoverable (missing $skill or name mismatch)"
  fi
done

# Launch path (FR-010, FR-014, SC-007): Codex has no command layer, so preflight
# runs only via each skill's self-invocation guard. Assert every command skill
# self-invokes guide:preflight, so a regression that drops the guard fails here
# instead of silently launching a command with no capability detection.
for c in "${COMMANDS[@]}"; do
  skill="$PLUGIN/skills/$c/SKILL.md"
  if [[ -f "$skill" ]] && grep -q "guide:preflight" "$skill"; then
    pass "skill $c self-invokes guide:preflight (Codex launch path)"
  else
    failed "skill $c does not self-invoke guide:preflight; Codex would launch with no preflight"
  fi
done

# Preflight keeps the harness-agnostic stop gates it must enforce on every harness.
PREFLIGHT="$PLUGIN/skills/preflight/SKILL.md"
if grep -q "needs the superpowers plugin for this harness" "$PREFLIGHT"; then
  pass "preflight keeps the superpowers-absent stop gate (FR-011)"
else
  failed "preflight lost the superpowers-absent stop gate (FR-011)"
fi
if grep -q "There is no single-agent fallback" "$PREFLIGHT"; then
  pass "preflight keeps the multi_agent-absent stop gate (FR-017)"
else
  failed "preflight lost the multi_agent-absent stop gate (FR-017)"
fi

[[ $fail -eq 0 ]] && echo "codex harness check OK" || echo "FAILURES in codex harness check"
exit $fail
