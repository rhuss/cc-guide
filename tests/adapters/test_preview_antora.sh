#!/usr/bin/env bash
# Preview smoke test for the Antora adapter (T047): the watcher serves the site,
# rebuilds on a change, keeps the last good site when a build breaks, and recovers.
# The fixture is branded (guide.yaml branding block): changing logo_text, creating and
# editing ui/supplemental/ (absent when the preview starts), and creating and editing a
# logo file named in guide.yaml must each rebuild (specs/002-antora-branding, FR-023).
#   usage: bash tests/adapters/test_preview_antora.sh
# Env: CC_GUIDE_NODE_MODULES=<dir> reuses a prepared node_modules (see scaffold.sh);
#      KEEP=1 keeps the temporary guide project.
set -uo pipefail

REPO=$(cd "$(dirname "$0")/../.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/cc-guide-preview.XXXXXX")
guide=$tmp/guide
log=$tmp/watch.log
fail=0
pid=""

pass() { echo "PASS antora preview: $1"; }
failed() { echo "FAIL antora preview: $1"; fail=1; }
finish() {
  if [[ -n "$pid" ]]; then kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; fi
  if [[ $fail -ne 0 ]]; then echo "--- watcher log"; tail -40 "$log"; fi
  if [[ $fail -ne 0 || "${KEEP:-0}" == 1 ]]; then echo "guide project kept in $guide"; else rm -rf "$tmp"; fi
  exit $fail
}
trap finish INT TERM

wait_for() { # wait_for <seconds> <command...>: poll until the command succeeds
  local deadline=$(( $(date +%s) + $1 )); shift
  until "$@" >/dev/null 2>&1; do
    [[ $(date +%s) -ge $deadline ]] && return 1
    sleep 1
  done
}
served_has() { curl -fsS "http://127.0.0.1:$port/guide/user/start.html" | grep -q "$1"; }
logo_has() { curl -fsS "http://127.0.0.1:$port/_/img/logo-guide.svg" | grep -q "$1"; }
ui_has() { curl -fsS "http://127.0.0.1:$port/_/$1" | grep -q "$2"; }
log_count() { grep -c "$1" "$log" 2>/dev/null || true; }
count_at_least() { [[ $(log_count "$1") -ge $2 ]]; }

if ! bash "$REPO/tests/adapters/scaffold.sh" antora "$guide" > "$tmp/scaffold.log" 2>&1; then
  failed "scaffold"; tail -20 "$tmp/scaffold.log"; finish
fi
# A branded fixture: the watcher follows guide.yaml and rebuilds the branding overlay.
printf 'branding:\n  logo_text: Preview Brand One\n' >> "$guide/guide.yaml"
port=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')

node "$guide/tools/guide/preview-watch.mjs" --root "$guide" --no-open --port "$port" > "$log" 2>&1 &
pid=$!

if wait_for 90 curl -fsS "http://127.0.0.1:$port/guide/index.html"; then
  pass "serves the site on port $port"
else
  failed "site not served within 90 s"; finish
fi
if curl -fsS -H 'Accept: text/html' "http://127.0.0.1:$port/guide/index.html" | grep -q 'browser-sync'; then
  pass "browser-sync client injected (pages served as text/html)"
else
  failed "browser-sync client missing from the served page"
fi

page=$guide/content/modules/ROOT/pages/user/start.adoc
cp "$page" "$tmp/start.adoc"
printf '\nPreview marker one.\n' >> "$page"
if wait_for 60 served_has 'Preview marker one'; then pass "rebuilds after a change"; else failed "change not served within 60 s"; fi

ok_before=$(log_count 'build ok')
printf '\nSee xref:does-not-exist.adoc[a missing page].\n' >> "$page"
if wait_for 60 count_at_least 'build FAILED' 1; then
  pass "a broken page fails the build"
  if served_has 'Preview marker one'; then pass "last good site still served"; else failed "last good site not served after a failed build"; fi
  [[ $(log_count 'build ok') -eq $ok_before ]] && pass "failed build did not swap the site" || failed "a failed build was swapped in"
else
  failed "broken page did not fail the build"
fi

cp "$tmp/start.adoc" "$page"
printf '\nPreview marker two.\n' >> "$page"
if wait_for 60 served_has 'Preview marker two'; then pass "recovers after the fix"; else failed "fix not served within 60 s"; fi

# FR-023: a changed branding block rebuilds the header logo.
if logo_has 'Preview Brand One'; then pass "serves the branded logo"; else failed "branded logo not served"; fi
sed -i.bak 's/logo_text: Preview Brand One/logo_text: Preview Brand Two/' "$guide/guide.yaml" && rm -f "$guide/guide.yaml.bak"
if wait_for 60 logo_has 'Preview Brand Two'; then
  pass "rebuilds the logo after a logo_text change"
else
  failed "changed logo_text not served within 60 s"
fi

# FR-023: ui/supplemental/ did not exist when the preview started; creating it and then
# editing a file in it each rebuild, without touching guide.yaml.
[[ -e "$guide/ui" ]] && failed "the fixture already has ui/ (the test needs it absent)"
mkdir -p "$guide/ui/supplemental/css"
printf '.doc { color: inherit; } /* OverlayMarkerOne */\n' > "$guide/ui/supplemental/css/extra.css"
if wait_for 60 ui_has css/extra.css OverlayMarkerOne; then
  pass "rebuilds when ui/supplemental/ is created while the preview runs"
else
  failed "a new ui/supplemental/css/extra.css not served within 60 s"
fi
printf '.doc { color: inherit; } /* OverlayMarkerTwo */\n' > "$guide/ui/supplemental/css/extra.css"
if wait_for 60 ui_has css/extra.css OverlayMarkerTwo; then
  pass "rebuilds after an overlay file changes"
else
  failed "changed ui/supplemental/css/extra.css not served within 60 s"
fi

# FR-023: guide.yaml names a logo file that does not exist yet (the build fails and keeps
# the last good site); creating the file, then changing it, each rebuild.
failed_before=$(log_count 'build FAILED')
python3 - "$guide/guide.yaml" <<'PY'
import sys
path = sys.argv[1]
text = open(path).read()
assert "  logo_text: Preview Brand Two\n" in text
open(path, "w").write(text.replace("  logo_text: Preview Brand Two\n",
                                   "  logo: assets/own-logo.svg\n  logo_alt: Own preview logo\n"))
PY
if wait_for 60 count_at_least 'build FAILED' $((failed_before + 1)); then
  pass "a missing logo file fails the rebuild"
else
  failed "naming a missing logo file did not fail the rebuild"
fi
mkdir -p "$guide/assets"
printf '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><title>OwnLogoOne</title></svg>\n' > "$guide/assets/own-logo.svg"
if wait_for 60 logo_has OwnLogoOne; then
  pass "rebuilds when the named logo file appears"
else
  failed "the created logo file not served within 60 s"
fi
printf '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><title>OwnLogoTwo</title></svg>\n' > "$guide/assets/own-logo.svg"
if wait_for 60 logo_has OwnLogoTwo; then
  pass "rebuilds after the logo file changes"
else
  failed "the changed logo file not served within 60 s"
fi

finish
