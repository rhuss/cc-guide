#!/usr/bin/env bash
# Smoke test for captured visuals (specs/008-captured-visuals): scaffold a gfm guide, add the
# fixture recipe, capture with podman, and check images, sidecars, redaction, and cleanup.
#   usage: bash tests/adapters/test_visuals.sh
# Env: KEEP=1 keeps the temporary guide project for inspection.
# Prints "SKIP: podman not available" and exits 0 when podman cannot run containers.
set -uo pipefail

REPO=$(cd "$(dirname "$0")/../.." && pwd)
FIXTURE=$REPO/tests/adapters/fixtures/visuals

if ! podman info >/dev/null 2>&1; then
  echo "SKIP: podman not available"
  exit 0
fi

tmp=$(mktemp -d "${TMPDIR:-/tmp}/cc-guide-visuals.XXXXXX")
guide=$tmp/guide
log=$tmp/make.log
fail=0

pass() { echo "PASS visuals: $1"; }
failed() { echo "FAIL visuals: $1"; fail=1; }
finish() {
  if [[ $fail -ne 0 || "${KEEP:-0}" == 1 ]]; then
    echo "guide project kept in $guide"
  else
    rm -rf "$tmp"
  fi
  exit $fail
}
now() { python3 -c 'import time; print(time.time())'; }
took() { python3 -c "import sys; print(f'{float(sys.argv[2]) - float(sys.argv[1]):.1f}s')" "$1" "$(now)"; }

if ! CC_GUIDE_SKIP_NPM=1 bash "$REPO/tests/adapters/scaffold.sh" gfm "$guide" >"$tmp/scaffold.log" 2>&1; then
  failed "scaffold"; tail -20 "$tmp/scaffold.log"; finish
fi
pass "scaffold"

# The recipe and the guide's visuals/ directory; host values only in the scratch copy.
cp "$FIXTURE/visuals.yaml" "$guide/visuals.yaml"
mkdir -p "$guide/visuals"
cp -R "$FIXTURE/visuals/." "$guide/visuals/"
host=$(hostname)
user=$(id -un)
for f in "$guide/visuals/demo/colors.sh" "$guide/visuals/seed/index.html"; do
  sed -i.bak -e "s|@@HOME@@|$HOME|g" -e "s|@@USER@@|$user|g" -e "s|@@HOST@@|$host|g" "$f" && rm -f "$f.bak"
done

start=$(now)
if make -C "$guide" visuals >"$log" 2>&1; then
  pass "make visuals ($(took "$start"))"
else
  failed "make visuals"; tail -40 "$log"; finish
fi

svg=$guide/docs/assets/visuals/colors.svg
side=$guide/visuals/colors.visual.yaml
[[ -f "$svg" ]] && pass "colors.svg written" || failed "colors.svg missing"
[[ -f "$side" ]] && pass "colors.visual.yaml written" || failed "colors.visual.yaml missing"
if [[ -f "$svg" ]]; then
  grep -q 'data:font/woff2;base64,' "$svg" && pass "font embedded" || failed "no embedded font"
  grep -q 'fill="#4e9a06" class="b">PASS' "$svg" && pass "bold green PASS" || failed "bold green PASS missing"
  grep -q 'fill="#ff7800"' "$svg" && pass "truecolor run" || failed "truecolor run missing"
  grep -q 'data:image/png;base64,' "$svg" && pass "emoji embedded as a bitmap (FR-016)" || failed "no emoji bitmap"
  # three emoji lines: the rocket, a ZWJ sequence drawn as one ligature glyph, and U+26A0
  # U+FE0F drawn as an emoji (not as text); the sidecar keeps both sequences whole
  if uv run --quiet --no-project --with pyyaml python - "$svg" "$side" <<'PY'
import sys, yaml
svg, side = open(sys.argv[1], encoding="utf-8").read(), yaml.safe_load(open(sys.argv[2], encoding="utf-8"))
zwj = chr(0x1F469) + chr(0x200D) + chr(0x1F4BB)
warn = chr(0x26A0) + chr(0xFE0F)
ok = svg.count("<image") == 3 and chr(0x26A0) not in svg and zwj in side["text"] and warn in side["text"]
sys.exit(0 if ok else 1)
PY
  then
    pass "ZWJ sequence and U+FE0F emoji drawn as one emoji each, kept whole in the sidecar"
  else
    failed "ZWJ sequence or U+FE0F emoji rendered wrong"
  fi
fi
if [[ -f "$side" ]]; then
  grep -q '^  \$ sh /visuals/demo/colors.sh$' "$side" && pass "prompt line in sidecar" || failed "prompt line missing"
  grep -q '66%' "$side" && pass "block bar in sidecar" || failed "block bar missing"
  grep -q 'home-path: 1' "$side" && pass "home path redaction counted" || failed "home path not counted"
  for rule in user-at bearer api-key; do
    grep -q "^    $rule: 1$" "$side" && pass "$rule redaction counted" || failed "$rule not counted"
  done
fi

png=$guide/docs/assets/visuals/table.png
tside=$guide/visuals/table.visual.yaml
[[ -f "$png" ]] && pass "table.png written" || failed "table.png missing"
[[ -f "$tside" ]] && pass "table.visual.yaml written" || failed "table.visual.yaml missing"
if [[ -f "$tside" ]]; then
  grep -q 'columnheader "accuracy"' "$tside" && pass "sidecar outline names the accuracy column" \
    || failed "accuracy missing from the sidecar text"
  grep -q "label: '1'" "$tside" && pass "highlight label 1 recorded" || failed "highlight label missing"
  # web redaction: a path split across inline elements, an input value, an attribute
  grep -q 'Runs in /home/user/runs on example-host' "$tside" && pass "web page text redacted across elements" \
    || failed "web page text not redacted"
  for rule in user-path hostname home-path api-key; do
    grep -Eq "^    $rule: [1-9]" "$tside" && pass "web $rule redaction counted" || failed "web $rule not counted"
  done
fi
# FR-019: the callout badge covers no other visible text (web.place_badge records what it
# covers in the run's scratch result, never in the sidecar).
result=$(ls -t "$guide"/.guide/visuals/*/out/table.result.json 2>/dev/null | head -1)
if [[ -n "$result" ]] && python3 -c '
import json, sys
badges = json.load(open(sys.argv[1])).get("badges") or []
sys.exit(0 if badges and all(b["covers"] == 0 for b in badges) else 1)' "$result"; then
  pass "callout badge covers no other text (FR-019)"
else
  failed "callout badge covers other text or was not placed"; [[ -n "$result" ]] && cat "$result"
fi

# SC-004: no home path, user name in path form, or host name in images or sidecars.
leaks=0
for value in "$HOME" "/home/$user" "/Users/$user" "$user@" "$host" "${host%%.*}" \
             "abcdefghijklmnop1234" "abcdefghijklmnopqrstuvwxyz0123456789"; do
  if grep -rqF -- "$value" "$guide/docs/assets/visuals" "$guide"/visuals/*.visual.yaml; then
    echo "  found $value"; leaks=1
  fi
done
[[ $leaks -eq 0 ]] && pass "no host values or tokens in images or sidecars (SC-004)" || failed "host values leaked"

# SC-002: an unchanged recipe renders a byte-identical CLI image.
sum_svg=$(shasum "$svg" | cut -d' ' -f1)
if make -C "$guide" visuals VISUALS=colors >"$log" 2>&1 && [[ "$(shasum "$svg" | cut -d' ' -f1)" == "$sum_svg" ]]; then
  pass "second capture of colors is byte-identical (SC-002)"
else
  failed "second capture of colors differs or failed"; tail -20 "$log"
fi

# US3: embed both visuals with visual: citations; make check passes, and fails with a
# [visuals] error while a declared image is missing.
python3 "$REPO/tests/adapters/add_visuals.py" gfm "$guide" --embed-only
if make -C "$guide" check >"$log" 2>&1; then
  pass "make check with embedded visuals"
else
  failed "make check with embedded visuals"; tail -30 "$log"
fi
mv "$png" "$tmp/table.png"
if make -C "$guide" check >"$log" 2>&1; then
  failed "make check passed without table.png"
elif grep -q '\[visuals\].*table.png' "$log"; then
  pass "missing table.png fails make check with a [visuals] error"
else
  failed "make check failed, but not with a [visuals] error"; tail -20 "$log"
fi
mv "$tmp/table.png" "$png"

# US4: visual drift. GNU make turns any failing status into 2, so the exact exit codes
# (0 no drift, 10 drift) come from the script itself.
drift() { (cd "$guide" && uv run --quiet tools/guide/visuals.py drift "$@"); }
sum_before=$(shasum "$png" | cut -d' ' -f1)
for round in 1 2; do
  start=$(now)
  drift >"$tmp/drift$round.md" 2>&1
  status=$?
  if [[ $status -eq 0 ]]; then
    pass "visual drift round $round: no drift ($(took "$start"), SC-002)"
  else
    failed "visual drift round $round exited $status"; tail -30 "$tmp/drift$round.md"
  fi
done
seed=$guide/visuals/seed/index.html
cp "$seed" "$tmp/index.html"
sed -i.bak 's|<th scope="col">loss</th>|<th scope="col">val-loss</th>|' "$seed" && rm -f "$seed.bak"
drift >"$tmp/drift3.md" 2>&1
status=$?
if [[ $status -eq 10 ]]; then
  pass "changed table header: visual drift exits 10"
else
  failed "changed table header: visual drift exited $status"; tail -30 "$tmp/drift3.md"
fi
if grep -q '## `table`' "$tmp/drift3.md" && grep -q 'Status: \*\*drifted\*\*' "$tmp/drift3.md" \
   && grep -q '^+.*columnheader "val-loss"' "$tmp/drift3.md"; then
  pass "drift report names table and the new columnheader line"
else
  failed "drift report lacks the table finding"; cat "$tmp/drift3.md"
fi
[[ "$(shasum "$png" | cut -d' ' -f1)" == "$sum_before" ]] && pass "committed table.png unchanged by drift (FR-030)" \
  || failed "drift changed the committed table.png"
cp "$tmp/index.html" "$seed"

# US2 AS3, FR-012, FR-013: a step that never matches fails that visual only, writes a
# debug image to the run directory, and leaves no image in the guide.
cp "$guide/visuals.yaml" "$tmp/visuals.yaml"
cat >>"$guide/visuals.yaml" <<'YAML'
  broken:
    kind: web
    env: site
    steps:
      - goto: /
      - wait: "#missing"
YAML
(cd "$guide" && uv run --quiet tools/guide/visuals.py capture broken) >"$log" 2>&1
status=$?
if [[ $status -eq 1 ]] && grep -q 'step 2 (wait #missing)' "$log"; then
  pass "failing step: exit 1 with step and selector"
else
  failed "failing step exited $status"; tail -20 "$log"
fi
if compgen -G "$guide/.guide/visuals/*/debug/broken-step2.png" >/dev/null; then
  pass "debug image in the run directory (FR-013)"
else
  failed "no debug image"
fi
[[ ! -e "$guide/docs/assets/visuals/broken.png" && ! -e "$guide/visuals/broken.visual.yaml" ]] \
  && pass "no image or sidecar for the failed visual" || failed "failed visual wrote files"
cp "$tmp/visuals.yaml" "$guide/visuals.yaml"

# SC-006: nothing the run created remains (also after the failed run).
if [[ -z "$(podman ps -a --filter label=io.cc-guide.capture=1 -q)" && \
      -z "$(podman network ls --filter label=io.cc-guide.capture=1 -q)" ]]; then
  pass "no labeled container or network left (SC-006)"
else
  failed "labeled containers or networks remain"
fi

finish
