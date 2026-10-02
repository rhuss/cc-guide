#!/usr/bin/env bash
# Smoke test for the Antora adapter (T025): scaffold the fixture guide, build, check,
# package, and prove that a planted confidential term fails the check.
#   usage: bash tests/adapters/test_antora.sh
# Env: CC_GUIDE_NODE_MODULES=<dir> reuses a prepared node_modules (see scaffold.sh);
#      KEEP=1 keeps the temporary guide project for inspection.
set -uo pipefail

REPO=$(cd "$(dirname "$0")/../.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/cc-guide-antora.XXXXXX")
guide=$tmp/guide
log=$tmp/make.log
fail=0

pass() { echo "PASS antora: $1"; }
failed() { echo "FAIL antora: $1"; fail=1; }
finish() {
  if [[ $fail -ne 0 || "${KEEP:-0}" == 1 ]]; then
    echo "guide project kept in $guide"
  else
    rm -rf "$tmp"
  fi
  exit $fail
}

if ! bash "$REPO/tests/adapters/scaffold.sh" antora "$guide" >"$tmp/scaffold.log" 2>&1; then
  failed "scaffold"; tail -20 "$tmp/scaffold.log"; finish
fi
pass "scaffold"

if make -C "$guide" doctor check dist >"$log" 2>&1; then
  pass "make doctor check dist"
else
  failed "make doctor check dist"; tail -30 "$log"; finish
fi

name=$(cd "$guide" && uv run --quiet tools/guide/guidecfg.py get slug)-$(cd "$guide" && uv run --quiet tools/guide/guidecfg.py get baseline.captured)
shareable=$guide/dist/$name.tar.gz
internal=$guide/dist/$name-INTERNAL.tar.gz
[[ -f "$shareable" ]] && pass "shareable tarball $name.tar.gz" || failed "shareable tarball missing"
[[ -f "$internal" ]] && pass "internal tarball $name-INTERNAL.tar.gz" || failed "internal tarball missing"
if [[ -f "$shareable" ]]; then
  if tar tzf "$shareable" | grep -q '/internal/'; then
    failed "shareable tarball contains an internal/ path"
  else
    pass "shareable tarball has no internal/ path"
  fi
fi
if [[ -f "$internal" ]] && tar tzf "$internal" | grep -q '/internal/notes.html'; then
  pass "internal tarball contains the internal pages"
else
  failed "internal tarball lacks internal/notes.html"
fi
if [[ -f "$guide/build/site/guide/_exports/index.html" ]]; then
  pass "html-single export build/site/guide/_exports/index.html"
else
  failed "html-single export missing"
fi
if grep -q 'minisvc 1\.2\.3' "$guide/build/site/guide/index.html"; then
  pass "baseline attribute rendered"
else
  failed "baseline attribute not rendered"
fi

# Plant a confidential term in a shareable page: make check must fail and name it.
page=$guide/content/modules/ROOT/pages/user/start.adoc
printf '\nACME Corp runs this service in production.\n' >> "$page"
if make -C "$guide" check >"$log" 2>&1; then
  failed "make check passed with a planted confidential term"
elif grep -Eq '\[confidential\]|leak.*ACME' "$log" && grep -q 'user/start' "$log"; then
  pass "planted confidential term fails make check"
else
  failed "make check failed, but not for the planted term"; tail -20 "$log"
fi

finish
