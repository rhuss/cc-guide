#!/usr/bin/env bash
# Smoke test for the GitHub Markdown adapter (T038): scaffold the fixture guide, build, check,
# package, and prove that a planted confidential term fails the check.
#   usage: bash tests/adapters/test_gfm.sh
# Env: CC_GUIDE_NODE_MODULES=<dir> reuses a prepared node_modules (see scaffold.sh);
#      KEEP=1 keeps the temporary guide project for inspection.
set -uo pipefail

REPO=$(cd "$(dirname "$0")/../.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/cc-guide-gfm.XXXXXX")
guide=$tmp/guide
log=$tmp/make.log
fail=0

pass() { echo "PASS gfm: $1"; }
failed() { echo "FAIL gfm: $1"; fail=1; }
finish() {
  if [[ $fail -ne 0 || "${KEEP:-0}" == 1 ]]; then
    echo "guide project kept in $guide"
  else
    rm -rf "$tmp"
  fi
  exit $fail
}

if ! bash "$REPO/tests/adapters/scaffold.sh" gfm "$guide" >"$tmp/scaffold.log" 2>&1; then
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
if [[ -f "$guide/build/site/README.html" ]]; then
  pass "rendered table of contents build/site/README.html"
else
  failed "rendered table of contents missing"
fi
if grep -q 'guide:attr mini-version -->1\.2\.3<!--' "$guide/build/site/index.html"; then
  pass "baseline attribute rendered"
else
  failed "baseline attribute not rendered"
fi

# Generated regions: a stale value is rewritten by make site; an unknown name fails.
install=$guide/docs/admin/install.md
cp "$install" "$tmp/install.md"
sed -i.bak 's|<!-- guide:attr mini-commit-short -->[^<]*<!--|<!-- guide:attr mini-commit-short -->0000000<!--|' "$install" && rm -f "$install.bak"
if make -C "$guide" site >"$log" 2>&1 && cmp -s "$install" "$tmp/install.md"; then
  pass "make site rewrites a stale generated region"
else
  failed "stale generated region was not rewritten"; tail -10 "$log"
fi
printf '\nSee <!-- guide:attr mini-nope -->x<!-- /guide:attr -->.\n' >> "$install"
if make -C "$guide" check >"$log" 2>&1; then
  failed "make check passed with an unknown generated region"
elif grep -q "mini-nope" "$log"; then
  pass "unknown generated region fails make check"
else
  failed "make check failed, but not for the unknown region"; tail -10 "$log"
fi
cp "$tmp/install.md" "$install"

# Plant a confidential term in a shareable page: make check must fail and name it.
page=$guide/docs/user/start.md
printf '\nACME Corp runs this service in production.\n' >> "$page"
if make -C "$guide" check >"$log" 2>&1; then
  failed "make check passed with a planted confidential term"
elif grep -Eq '\[confidential\]|leak.*ACME' "$log" && grep -q 'user/start' "$log"; then
  pass "planted confidential term fails make check"
else
  failed "make check failed, but not for the planted term"; tail -20 "$log"
fi

finish
