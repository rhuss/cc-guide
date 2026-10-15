#!/usr/bin/env bash
# Neutral theme smoke test for the Antora adapter (specs/003-neutral-branding): scaffold
# the fixture guide, build it once without branding (the navbar reference), then with
# `wordmark`, `theme: neutral`, and `footer: none`; check the outlined logo, the alt text,
# the vendored fonts, the theme stylesheet, the red navbar rule and the absence of Google
# Fonts requests in Chromium, a clean git status, and the neutral theme check of check.py.
#   usage: bash tests/adapters/test_antora_neutral.sh
# Env: CC_GUIDE_NODE_MODULES=<dir> reuses a prepared node_modules (see scaffold.sh);
#      BASELINE_REF=<commit> the plugin before the feature (default b0db967, the last
#      commit on main before it; needs a full clone);
#      KEEP=1 keeps the temporary guide projects for inspection.
set -uo pipefail

REPO=$(cd "$(dirname "$0")/../.." && pwd)
BASELINE_REF=${BASELINE_REF:-b0db967}
tmp=$(mktemp -d "${TMPDIR:-/tmp}/cc-guide-neutral.XXXXXX")
guide=$tmp/guide
log=$tmp/make.log
fail=0

pass() { echo "PASS antora neutral: $1"; }
failed() { echo "FAIL antora neutral: $1"; fail=1; }
finish() {
  if [[ $fail -ne 0 || "${KEEP:-0}" == 1 ]]; then
    echo "guide projects kept in $tmp"
  else
    rm -rf "$tmp"
  fi
  exit $fail
}
g() { git -C "$guide" -c commit.gpgsign=false -c core.hooksPath=/dev/null \
  -c user.name="Fixture Author" -c user.email=fixture@example.com "$@"; }

# set_branding <yaml lines> [<guide dir>]: replace the branding block of guide.yaml
# (or remove it with "").
set_branding() {
  uv run --quiet --no-project --with pyyaml python - "${2:-$guide}/guide.yaml" "$1" <<'EOF'
import sys
import yaml
path, block = sys.argv[1], sys.argv[2]
lines = open(path).read().splitlines()
out, skip = [], False
for line in lines:
    if line.startswith("branding:"):
        skip = True
        continue
    if skip and (line.startswith(" ") or not line.strip()):
        continue
    skip = False
    out.append(line)
text = "\n".join(out).rstrip("\n") + "\n"
if block:
    text += block.rstrip("\n") + "\n"
yaml.safe_load(text)
open(path, "w").write(text)
EOF
}

# check_neutral_site <site dir> <alt> <logo kind: wordmark|hat>: every page with a header
# shows logo-guide.svg with the alt text and links css/theme-neutral.css, no footer shows
# the Demo Platform, _/font/ holds the vendored fonts and OFL.txt, and the logo has no
# <text> element (a hat logo keeps the hat and the MPL-2.0 notice).
check_neutral_site() {
  uv run --quiet --no-project --with pyyaml python - "$REPO" "$@" <<'EOF'
import re
import sys
from pathlib import Path
import yaml
repo, site, alt, kind = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
manifest = yaml.safe_load((repo / "guide/adapters/antora/branding/fonts/fonts.yaml").read_text())
problems = []
headed = 0
for page in sorted(p for p in site.rglob("*.html") if "_exports" not in p.parts):
    html = page.read_text()
    rel = page.relative_to(site)
    img = re.search(r'<img [^>]*class="navbar-logo-img"[^>]*>', html)
    if not img:
        continue
    headed += 1
    if not re.search(r'src="[^"]*img/logo-guide\.svg"', img.group(0)):
        problems.append(f"{rel}: header logo is not logo-guide.svg")
    got = re.search(r'alt="([^"]*)"', img.group(0)).group(1)
    if got != alt:
        problems.append(f"{rel}: alt is {got!r}")
    if not re.search(r'<link [^>]*href="[^"]*css/theme-neutral\.css"', html):
        problems.append(f"{rel}: does not link css/theme-neutral.css")
    footer = re.search(r'<footer class="footer">([\s\S]*?)</footer>', html)
    if footer and ("demo.redhat.com" in footer.group(1) or "Demo Platform" in footer.group(1)):
        problems.append(f"{rel}: footer shows the Red Hat Demo Platform notice")
for name in [e["file"] for e in manifest["files"]] + ["OFL.txt"]:
    if not (site / "_" / "font" / name).is_file():
        problems.append(f"_/font/{name} missing")
logo = (site / "_" / "img" / "logo-guide.svg").read_text()
if "<text" in logo:
    problems.append("logo-guide.svg still has a <text> element")
if "<path" not in logo:
    problems.append("logo-guide.svg has no outlined glyphs")
hat = "Mozilla Public License" in logo
if kind == "hat" and not hat:
    problems.append("hat logo lost the MPL-2.0 notice")
if kind == "wordmark" and hat:
    problems.append("wordmark logo carries the Red Hat logo template")
if not headed:
    problems.append(f"no page in {site} has a navbar-logo-img header")
for p in problems[:20]:
    print(p)
print(f"{headed} pages with a header checked, {len(problems)} problem(s)")
sys.exit(1 if problems else 0)
EOF
}

# probe <site dir>: the measure_neutral.mjs JSON for the guide's built site.
probe() { node "$REPO/tests/adapters/measure_neutral.mjs" "$guide" "$1"; }

# json_get <json> <python expression over d>: evaluate an expression on parsed JSON.
json_get() { uv run --quiet --no-project python -c 'import json,sys; d=json.loads(sys.argv[1]); print(eval(sys.argv[2]))' "$1" "$2"; }

if ! bash "$REPO/tests/adapters/scaffold.sh" antora "$guide" >"$tmp/scaffold.log" 2>&1; then
  failed "scaffold"; tail -20 "$tmp/scaffold.log"; finish
fi
pass "scaffold"
# Setup files (a node_modules symlink, npm's package-lock.json) are excluded or committed,
# so the status check below sees only what builds write.
mkdir -p "$guide/.git/info" && echo node_modules >> "$guide/.git/info/exclude"
g add -A && g commit --quiet -m "Scaffold the fixture guide"

# --- reference: the stock navbar --------------------------------------------------------
if make -C "$guide" site >"$log" 2>&1 && stock=$(probe "$guide/build/site"); then
  stock_height=$(json_get "$stock" 'd["navbarHeight"]')
  # Positive control for the neutral checks: the stock page asks Google for its fonts
  # (so the route really intercepts) and, with Google blocked, loads no Red Hat face.
  if [[ $(json_get "$stock" 'd["googleRequests"] >= 1 and not any(f.startswith("Red Hat") for f in d["loaded"])') != True ]]; then
    failed "stock control: expected a blocked Google Fonts request and no Red Hat face: $stock"
  fi
  pass "stock build: navbar ${stock_height} px high, $(json_get "$stock" 'd["googleRequests"]') Google Fonts request(s) blocked, faces $(json_get "$stock" 'd["loaded"]')"
else
  failed "stock build and probe"; tail -30 "$log"; finish
fi

# --- US1: a neutral wordmark guide (FR-006, FR-012 to FR-015, FR-026, SC-001, SC-002) ----
NEUTRAL="branding:
  wordmark: OpenClaw on OpenShift
  theme: neutral
  footer: none"
set_branding "$NEUTRAL"
g add -A && g commit --quiet -m "Neutral branding"
if make -C "$guide" check >"$log" 2>&1; then
  pass "make check (neutral wordmark)"
else
  failed "make check (neutral wordmark)"; tail -30 "$log"; finish
fi
for view in site site-internal; do
  if check_neutral_site "$guide/build/$view" "OpenClaw on OpenShift" wordmark >"$tmp/$view.check" 2>&1; then
    pass "build/$view: outlined wordmark, alt text, theme stylesheet, fonts ($(tail -1 "$tmp/$view.check"))"
  else
    failed "build/$view: neutral theme"; cat "$tmp/$view.check"
  fi
done
if neutral=$(probe "$guide/build/site"); then
  faces=$(json_get "$neutral" 'all(f in d["loaded"] for f in ("Red Hat Text normal", "Red Hat Display normal", "Red Hat Mono normal")) and d["bodyFont"].startswith("\"Red Hat Text\"")')
  shadow=$(json_get "$neutral" 'd["navbarShadow"]')
  height=$(json_get "$neutral" 'd["navbarHeight"]')
  google=$(json_get "$neutral" 'd["googleRequests"]')
  [[ $faces == True ]] && pass "Chromium loads the vendored Red Hat Text, Display, and Mono with Google Fonts blocked, body in Red Hat Text ($(json_get "$neutral" 'd["loaded"]'))" \
    || failed "vendored fonts not loaded: $neutral"
  [[ $google == 0 ]] && pass "the neutral page makes no Google Fonts request" \
    || failed "the neutral page made $google Google Fonts request(s)"
  [[ $shadow == "rgb(238, 0, 0) 0px -3px 0px 0px inset" ]] && pass "navbar shows the red rule ($shadow)" \
    || failed "navbar box shadow is $shadow"
  [[ $height == "$stock_height" ]] && pass "navbar height unchanged ($height px)" \
    || failed "navbar height $height px, stock $stock_height px"
else
  failed "probe of the neutral build"
fi
if [[ -z "$(g status --porcelain)" ]]; then
  pass "git status clean after the neutral build"
else
  failed "git status not clean after the build"; g status --porcelain
fi
rm -f "$guide/build/site/_/font/OFL.txt"
if (cd "$guide" && uv run --quiet tools/guide/check.py) >"$log" 2>&1; then
  failed "check.py passed without _/font/OFL.txt"
elif grep -q "neutral theme font missing: OFL.txt" "$log"; then
  pass "check.py reports a missing vendored font (FR-026)"
else
  failed "check.py failed, but not for the missing font"; tail -10 "$log"
fi

# --- US2: the hat variant with outlined text (FR-007) ---------------------------------------
set_branding "branding:
  logo_text: OpenShift AI
  theme: neutral
  footer: none"
g add -A && g commit --quiet -m "Hat variant"
if make -C "$guide" check >"$log" 2>&1; then
  pass "make check (neutral logo_text)"
  if check_neutral_site "$guide/build/site" "Red Hat OpenShift AI" hat >"$tmp/hat.check" 2>&1; then
    pass "build/site: Red Hat logo with outlined product name ($(tail -1 "$tmp/hat.check"))"
  else
    failed "build/site: hat variant"; cat "$tmp/hat.check"
  fi
else
  failed "make check (neutral logo_text)"; tail -30 "$log"
fi

# --- US3: existing guides build exactly as before the feature (SC-004) ---------------------
# baseline_plugin: export guide/ and tests/ as of BASELINE_REF into $tmp/baseline once.
baseline_plugin() {
  [[ -d "$tmp/baseline/guide" ]] && return 0
  if ! git -C "$REPO" cat-file -e "$BASELINE_REF^{commit}" 2>/dev/null; then
    failed "BASELINE_REF $BASELINE_REF is not a commit in $REPO (shallow clone? fetch the full history or set BASELINE_REF)"
    return 1
  fi
  mkdir -p "$tmp/baseline"
  git -C "$REPO" archive "$BASELINE_REF" guide tests | tar -x -C "$tmp/baseline"
}

# pdf_page1 <pdf>: content stream digest and text of the first page.
pdf_page1() {
  uv run --quiet --no-project --with pypdf python - "$1" <<'PY'
import hashlib
import sys
from pypdf import PdfReader
page = PdfReader(sys.argv[1]).pages[0]
print(hashlib.sha256(page.get_contents().get_data()).hexdigest())
print(page.extract_text())
PY
}

# unchanged <name> <branding block or "">: scaffold with the BASELINE_REF plugin, build
# site, site-internal, and the PDF, refresh the toolkit from this branch, build again,
# and compare. The refreshed fixture stays in $tmp/<name> (US5 reuses it).
unchanged() {
  local name=$1 block=$2 dir=$tmp/$1 epoch
  epoch=$(date +%s)
  if ! bash "$tmp/baseline/tests/adapters/scaffold.sh" antora "$dir" >"$tmp/scaffold-$name.log" 2>&1; then
    failed "$name: scaffold with the $BASELINE_REF plugin"; tail -20 "$tmp/scaffold-$name.log"; return
  fi
  [[ -n $block ]] && set_branding "$block" "$dir"
  if ! SOURCE_DATE_EPOCH=$epoch make -C "$dir" pdf >"$log" 2>&1; then
    failed "$name: make pdf with the $BASELINE_REF toolkit"; tail -30 "$log"; return
  fi
  mkdir -p "$tmp/before-$name"
  mv "$dir/build/site" "$dir/build/site-internal" "$tmp/before-$name/"
  mv "$dir"/dist/*.pdf "$tmp/before-$name/before.pdf"
  bash "$REPO/guide/scripts/scaffold-project.sh" --format antora --toolkit-only "$dir" >/dev/null
  if ! (make -C "$dir" clean >/dev/null 2>&1 && SOURCE_DATE_EPOCH=$epoch make -C "$dir" pdf >"$log" 2>&1); then
    failed "$name: make pdf after the toolkit refresh"; tail -30 "$log"; return
  fi
  for view in site site-internal; do
    if diff -r "$tmp/before-$name/$view" "$dir/build/$view" >"$tmp/$name-$view.diff" 2>&1; then
      pass "$name: build/$view identical before and after the feature (SC-004)"
    else
      failed "$name: build/$view differs after the feature"; head -20 "$tmp/$name-$view.diff"
    fi
  done
  if [[ "$(pdf_page1 "$tmp/before-$name/before.pdf")" == "$(pdf_page1 "$dir"/dist/*.pdf)" ]]; then
    pass "$name: PDF title page has the same text and content stream (SC-004)"
  else
    failed "$name: PDF title page differs after the feature"
    diff <(pdf_page1 "$tmp/before-$name/before.pdf") <(pdf_page1 "$dir"/dist/*.pdf) | head -20
  fi
}

if baseline_plugin; then
  unchanged unbranded ""
  unchanged branded "branding:
  logo_text: Agent Starter Kits
  footer:
    text: Agent Starter Kits on GitHub
    url: https://github.com/red-hat-data-services/agentic-starter-kits"
fi

# --- US4: the neutral PDF (FR-018, FR-019) ------------------------------------------------
# pdf_fonts <pdf>: the embedded fonts of all pages, one "<subtype> <name>" per line.
# Chromium embeds variable fonts (the vendored Red Hat fonts) as unnamed Type3 fonts.
pdf_fonts() {
  uv run --quiet --no-project --with pypdf python - "$1" <<'PY'
import sys
from pypdf import PdfReader
fonts = set()
for page in PdfReader(sys.argv[1]).pages:
    for ref in ((page.get("/Resources") or {}).get("/Font") or {}).values():
        font = ref.get_object()
        fonts.add(f"{font.get('/Subtype')} {font.get('/BaseFont', '-')}")
print("\n".join(sorted(fonts)))
PY
}

# pdf_type3_and_others <pdf>: first line the number of distinct Type3 font programs
# (by their glyph procedure streams), then the names of all other fonts.
pdf_type3_and_others() {
  uv run --quiet --no-project --with pypdf python - "$1" <<'PY'
import hashlib
import sys
from pypdf import PdfReader
type3, others = set(), set()
for page in PdfReader(sys.argv[1]).pages:
    for ref in ((page.get("/Resources") or {}).get("/Font") or {}).values():
        font = ref.get_object()
        if font.get("/Subtype") == "/Type3":
            procs = font["/CharProcs"]
            type3.add(hashlib.sha256(b"".join(procs[k].get_object().get_data() for k in sorted(procs))).hexdigest())
        else:
            others.add(str(font.get("/BaseFont", "-")))
print(len(type3))
print("\n".join(sorted(others)))
PY
}

# pdf_red_rule <pdf>: page 1 has a #151515 band with a row of red (#e00) pixels directly
# below it across most of the band's width.
pdf_red_rule() {
  uv run --quiet --no-project --with pypdfium2 --with pillow python - "$1" <<'PY'
import sys
import pypdfium2 as pdfium
img = pdfium.PdfDocument(sys.argv[1])[0].render(scale=2).to_pil().convert("RGB")
w, h = img.size
px = img.load()
def band(p):
    return all(abs(c - 0x15) <= 4 for c in p)
def red(p):
    return p[0] >= 0xd0 and p[1] <= 0x30 and p[2] <= 0x30
rows = [y for y in range(h // 3) if sum(band(px[x, y]) for x in range(0, w, 2)) > w * 0.3]
if not rows:
    print("no #151515 band in the top third of page 1")
    sys.exit(1)
bottom = rows[-1]
xs = [x for x in range(w) if band(px[x, (rows[0] + bottom) // 2])]
left, right = xs[0], xs[-1]
hits = [y for y in range(bottom + 1, min(h, bottom + 20))
        if sum(red(px[x, y]) for x in range(left, right + 1)) > (right - left) * 0.9]
print(f"red rows {hits[0]}-{hits[-1]} under the band ending at {bottom}" if hits else
      f"no red rule under the band ending at row {bottom}")
sys.exit(0 if hits else 1)
PY
}

pdfname=$(cd "$guide" && uv run --quiet tools/guide/guidecfg.py get slug)-$(cd "$guide" && uv run --quiet tools/guide/guidecfg.py get baseline.captured)
if make -C "$guide" pdf >"$log" 2>&1 && [[ -f "$guide/dist/$pdfname.pdf" ]]; then
  # The stock print sets body text and block titles in a serif (Noto Serif, falling back
  # to Times); the neutral print must embed the vendored (Type3) fonts and no serif.
  # Chromium embeds each variable font instance as unnamed Type3 fonts, so families
  # cannot be told apart here: the check asks for at least three Type3 programs and no
  # other font but the Helvetica of the page-number footer and the admonition labels.
  # The browser probe above proves that all three families load.
  fonts=$(pdf_type3_and_others "$guide/dist/$pdfname.pdf")
  if [[ $(head -1 <<<"$fonts") -ge 3 ]] && ! tail -n +2 <<<"$fonts" | grep -vq 'Helvetica'; then
    pass "neutral PDF: $(head -1 <<<"$fonts") Type3 font programs (at least 3), no other font but Helvetica"
  else
    failed "neutral PDF fonts"; echo "$fonts"
  fi
  if msg=$(pdf_red_rule "$guide/dist/$pdfname.pdf"); then
    pass "neutral PDF title band has the red rule ($msg)"
  else
    failed "neutral PDF: $msg"
  fi
  # FR-019: a vendored face that does not load stops the print and names the face.
  cp "$guide/build/branding/shareable/ui/font/RedHatMono-VF.woff2" "$tmp/mono.bak"
  head -c 5000 "$tmp/mono.bak" > "$guide/build/branding/shareable/ui/font/RedHatMono-VF.woff2"
  if make -C "$guide" print-pdf >"$log" 2>&1; then
    failed "print-pdf passed with a truncated RedHatMono-VF.woff2"
  elif grep -q "vendored fonts failed to load: Red Hat Mono normal (RedHatMono-VF.woff2)" "$log"; then
    pass "print-pdf stops on a font that does not load and names it"
  else
    failed "print-pdf failed, but not with the font message"; tail -10 "$log"
  fi
  cp "$tmp/mono.bak" "$guide/build/branding/shareable/ui/font/RedHatMono-VF.woff2"
else
  failed "make pdf (neutral)"; tail -30 "$log"
fi

# --- US5: an existing branded guide adopts the theme after the refresh ---------------------
adopt=$tmp/branded
if [[ -f "$adopt/tools/guide/branding/fonts/fonts.yaml" ]]; then
  set_branding "branding:
  logo_text: Agent Starter Kits
  theme: neutral
  footer:
    text: Agent Starter Kits on GitHub
    url: https://github.com/red-hat-data-services/agentic-starter-kits" "$adopt"
  if make -C "$adopt" check >"$log" 2>&1 \
     && check_neutral_site "$adopt/build/site" "Red Hat Agent Starter Kits" hat >"$tmp/adopt.check" 2>&1; then
    pass "refreshed branded guide adopts theme: neutral with one line ($(tail -1 "$tmp/adopt.check"))"
  else
    failed "adoption of theme: neutral"; tail -20 "$log"; cat "$tmp/adopt.check" 2>/dev/null
  fi
else
  failed "no refreshed branded fixture to adopt the theme (US3 section failed?)"
fi

finish
