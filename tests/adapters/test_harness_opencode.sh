#!/usr/bin/env bash
# Per-harness adapter check for OpenCode (FR-014, SC-007, SC-008): the installer
# copies the six command shims into <project>/.opencode/plugins/guide/command/, and
# each shim chains guide:preflight and the matching guide:<name> skill.
#   usage: bash tests/adapters/test_harness_opencode.sh
# Lightweight on purpose: the OpenCode dimension added alongside the per-format
# smoke tests. It needs only bash.
set -uo pipefail

REPO=$(cd "$(dirname "$0")/../.." && pwd)
INSTALL="$REPO/guide/opencode/install.sh"
COMMANDS=(create evolve preview export validate upstream)
fail=0
pass() { echo "PASS opencode: $1"; }
failed() { echo "FAIL opencode: $1"; fail=1; }

tmp=$(mktemp -d "${TMPDIR:-/tmp}/cc-guide-oc-test.XXXXXX")
trap 'rm -rf "$tmp"' EXIT

if bash "$INSTALL" --project-dir "$tmp" >"$tmp/install.log" 2>&1; then
  pass "install.sh ran"
else
  failed "install.sh failed"; cat "$tmp/install.log"; echo "FAILURES in opencode harness check"; exit "$fail"
fi

dir="$tmp/.opencode/plugins/guide/command"
for c in "${COMMANDS[@]}"; do
  shim="$dir/$c.md"
  if [[ -f "$shim" ]]; then
    if grep -q "guide:preflight" "$shim" && grep -q "guide:$c" "$shim"; then
      pass "shim $c.md installed and chains preflight and guide:$c"
    else
      failed "shim $c.md installed but does not chain preflight and guide:$c"
    fi
  else
    failed "shim $c.md not installed at $dir"
  fi
done

count=$(ls -1 "$dir"/*.md 2>/dev/null | wc -l | tr -d ' ')
[[ "$count" == 6 ]] && pass "exactly six shims installed" || failed "expected six shims, found $count"

[[ $fail -eq 0 ]] && echo "opencode harness check OK" || echo "FAILURES in opencode harness check"
exit $fail
