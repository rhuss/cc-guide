#!/usr/bin/env bash
# Branding smoke test for the Antora adapter (specs/002-antora-branding): scaffold the
# fixture guide, add the agentic-starter-kits branding block, build both views, and
# check the header logo, alt text, footer, and a clean git status; an invalid block
# stops `make site` before Antora runs.
#   usage: bash tests/adapters/test_antora_branding.sh
# It also proves that an unbranded guide builds byte for byte as before the feature
# (SC-002): the fixture is scaffolded with the plugin as of BASELINE_REF, built, then
# refreshed to the current toolkit and built again.
# Env: CC_GUIDE_NODE_MODULES=<dir> reuses a prepared node_modules (see scaffold.sh);
#      BASELINE_REF=<commit> the plugin before the feature (default 161d92f, the last
#      commit that changed guide/ or tests/ before it; needs a full clone);
#      KEEP=1 keeps the temporary guide projects for inspection.
set -uo pipefail

REPO=$(cd "$(dirname "$0")/../.." && pwd)
BASELINE_REF=${BASELINE_REF:-161d92f}
tmp=$(mktemp -d "${TMPDIR:-/tmp}/cc-guide-branding.XXXXXX")
guide=$tmp/guide
log=$tmp/make.log
fail=0

pass() { echo "PASS antora branding: $1"; }
failed() { echo "FAIL antora branding: $1"; fail=1; }
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

# check_site <site dir> <alt> <footer url or -> <logo text or -> [<footer link text>]:
# header logo, alt, footer (the link and its text). Pages without a header (the root
# redirect page) are skipped; at least one must have one.
check_site() {
  uv run --quiet --no-project python - "$@" <<'EOF'
import re
import sys
from pathlib import Path
site, alt, url, text = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
link_text = sys.argv[5] if len(sys.argv) > 5 else None
problems = []
pages = [p for p in site.rglob("*.html") if "_exports" not in p.parts]
headed = 0
for page in pages:
    html = page.read_text()
    rel = page.relative_to(site)
    img = re.search(r'<img [^>]*class="navbar-logo-img"[^>]*>', html)
    if not img:
        continue
    headed += 1
    src = re.search(r'src="([^"]*)"', img.group(0)).group(1)
    got_alt = re.search(r'alt="([^"]*)"', img.group(0)).group(1)
    if not src.endswith("img/logo-guide.svg"):
        problems.append(f"{rel}: header logo is {src}")
    if got_alt != alt:
        problems.append(f"{rel}: alt is {got_alt!r}")
    footer = re.search(r'<footer class="footer">([\s\S]*?)</footer>', html)
    body = footer.group(1) if footer else ""
    if "demo.redhat.com" in body or "Demo Platform" in body:
        problems.append(f"{rel}: footer still shows the Red Hat Demo Platform notice")
    if url != "-" and f'href="{url}"' not in body:
        problems.append(f"{rel}: footer lacks the link {url}")
    if link_text and not re.search(r'<a href="' + re.escape(url) + r'"[^>]*>' + re.escape(link_text) + "</a>", body):
        problems.append(f"{rel}: footer link text is not {link_text!r}")
logo = site / "_" / "img" / "logo-guide.svg"
if not logo.is_file():
    problems.append(f"{logo} missing")
else:
    svg = logo.read_text()
    if text != "-" and text not in svg:
        problems.append(f"{logo.name} lacks {text!r}")
    if "Demo Platform" in svg:
        problems.append(f"{logo.name} still says Demo Platform")
if not headed:
    problems.append(f"no page in {site} has a navbar-logo-img header")
for p in problems[:20]:
    print(p)
print(f"{headed} pages with a header checked, {len(problems)} problem(s)")
sys.exit(1 if problems else 0)
EOF
}

if ! bash "$REPO/tests/adapters/scaffold.sh" antora "$guide" >"$tmp/scaffold.log" 2>&1; then
  failed "scaffold"; tail -20 "$tmp/scaffold.log"; finish
fi
pass "scaffold"

# SC-001, SC-008: five lines of guide.yaml brand the guide.
KITS_URL=https://github.com/red-hat-data-services/agentic-starter-kits
SC008="branding:
  logo_text: Agent Starter Kits
  footer:
    text: Agent Starter Kits on GitHub
    url: $KITS_URL"
set_branding "$SC008"
# Setup files (a node_modules symlink from CC_GUIDE_NODE_MODULES, npm's package-lock.json)
# are excluded or committed here, so the status check below sees only what builds write.
mkdir -p "$guide/.git/info" && echo node_modules >> "$guide/.git/info/exclude"
g add -A && g commit --quiet -m "Brand the fixture guide"

if make -C "$guide" check >"$log" 2>&1; then
  pass "make check (branded)"
else
  failed "make check (branded)"; tail -30 "$log"; finish
fi
for view in site site-internal; do
  if check_site "$guide/build/$view" "Red Hat Agent Starter Kits" "$KITS_URL" "Agent Starter Kits" "Agent Starter Kits on GitHub" >"$tmp/$view.check" 2>&1; then
    pass "build/$view: branded logo, alt text, and footer ($(tail -1 "$tmp/$view.check"))"
  else
    failed "build/$view: branding"; cat "$tmp/$view.check"
  fi
done
if [[ -z "$(g status --porcelain)" ]]; then
  pass "git status clean after the branded build (FR-021, SC-005)"
else
  failed "git status not clean after the build"; g status --porcelain
fi

# FR-010: an invalid block stops make site before Antora runs.
cp "$guide/guide.yaml" "$tmp/guide.yaml.sc008"
mkdir -p "$guide/branding"
printf '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"/>\n' > "$guide/branding/own-logo.svg"
set_branding "branding:
  logo_text: Agent Starter Kits
  logo: branding/own-logo.svg
  logo_alt: Own logo"
rm -rf "$guide/build/site"
if make -C "$guide" site >"$log" 2>&1; then
  failed "make site passed with both logo_text and logo"
elif grep -q '^guide.yaml:branding' "$log" && [[ ! -e "$guide/build/site" ]]; then
  pass "invalid branding block stops make site before Antora (FR-010)"
else
  failed "make site failed, but not as expected"; tail -20 "$log"
fi
cp "$tmp/guide.yaml.sc008" "$guide/guide.yaml"
rm -rf "$guide/branding"

# --- US3: the PDF title page starts with the logo (FR-025, FR-026, SC-008) ----------
# pdf_logo <pdf> <logo text> <title>: page 1 shows the logo text before the title, and
# no page mentions the Demo Platform. Chromium draws an SVG <img> as vector content, so
# the logo text comes out of the page text (there is no image XObject to look for).
pdf_logo() {
  uv run --quiet --no-project --with pypdf python - "$@" <<'PY'
import re
import sys
from pypdf import PdfReader
pdf, logo, title = sys.argv[1:4]
texts = [re.sub(r"\s+", " ", p.extract_text() or "") for p in PdfReader(pdf).pages]
first = texts[0] if texts else ""
at = first.find(logo)
problems = []
if at < 0:
    problems.append(f"page 1 lacks {logo!r}: {first[:200]!r}")
elif first.find(title, at + len(logo)) < 0:
    problems.append(f"page 1 has no {title!r} after {logo!r}")
hits = [i + 1 for i, text in enumerate(texts) if "Demo Platform" in text]
if hits:
    problems.append(f"Demo Platform on pages {hits}")
print("; ".join(problems) or "ok")
sys.exit(1 if problems else 0)
PY
}

# pdf_band <pdf>: page 1 starts with a band in the site header color (#151515) across
# most of the page width, and the light logo pixels lie inside it, clear of its edges
# (FR-025: a logo made for the dark header stays legible; SC-004: nothing is cut off).
pdf_band() {
  uv run --quiet --no-project --with pypdfium2 --with pillow python - "$1" <<'PY'
import sys
import pypdfium2 as pdfium
img = pdfium.PdfDocument(sys.argv[1])[0].render(scale=2).to_pil().convert("RGB")
w, h = img.size
px = img.load()
def band(p):
    return all(abs(c - 0x15) <= 4 for c in p)
rows = [y for y in range(h // 3) if sum(band(px[x, y]) for x in range(0, w, 2)) > w * 0.3]
if not rows:
    print("no #151515 band in the top third of page 1")
    sys.exit(1)
top, bottom = rows[0], rows[-1]
mid = (top + bottom) // 2
xs = [x for x in range(w) if band(px[x, mid])]
left, right = xs[0], xs[-1]
light = [(x, y) for y in range(top, bottom + 1) for x in range(left, right + 1) if min(px[x, y]) > 200]
problems = []
if bottom - top < 40:
    problems.append(f"band only {bottom - top} px high")
if not light:
    problems.append("no light logo pixels on the band")
else:
    lx0, lx1 = min(x for x, _ in light), max(x for x, _ in light)
    ly0, ly1 = min(y for _, y in light), max(y for _, y in light)
    if lx0 <= left + 2 or lx1 >= right - 2 or ly0 <= top + 2 or ly1 >= bottom - 2:
        problems.append(f"logo pixels ({lx0},{ly0})-({lx1},{ly1}) touch the band edges ({left},{top})-({right},{bottom})")
print("; ".join(problems) or f"band ({left},{top})-({right},{bottom}), logo inside")
sys.exit(1 if problems else 0)
PY
}

title=$(cd "$guide" && uv run --quiet tools/guide/guidecfg.py get title)
pdfname=$(cd "$guide" && uv run --quiet tools/guide/guidecfg.py get slug)-$(cd "$guide" && uv run --quiet tools/guide/guidecfg.py get baseline.captured)
for view in shareable internal; do
  out=$guide/dist/$pdfname.pdf
  [[ $view == internal ]] && out=$guide/dist/$pdfname-INTERNAL.pdf
  if make -C "$guide" pdf VIEW=$view >"$log" 2>&1 && [[ -f "$out" ]]; then
    if msg=$(pdf_logo "$out" "Agent Starter Kits" "$title"); then
      pass "PDF ($view): title page starts with the branded logo, no Demo Platform"
    else
      failed "PDF ($view): $msg"
    fi
    if msg=$(pdf_band "$out"); then
      pass "PDF ($view): the logo sits on a #151515 band ($msg)"
    else
      failed "PDF ($view): $msg"
    fi
  else
    failed "make pdf VIEW=$view (branded)"; tail -30 "$log"
  fi
done

# US3 scenario 2: an own logo shows on the title page. It carries a script, an onload
# handler, and an image whose onerror handler would rewrite the title: shown as an image
# (FR-012, FR-026), none of them runs, which the inline-markup alternative would not ensure.
mkdir -p "$guide/branding"
cat > "$guide/branding/own-logo.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 80" onload="document.querySelectorAll('h1').forEach((h) => { h.textContent = 'ScriptRanMarker'; })"><script>document.querySelectorAll('h1').forEach((h) => { h.textContent = 'ScriptRanMarker'; });</script><image href="missing-image.png" width="1" height="1" onerror="document.querySelectorAll('h1').forEach((h) => { h.textContent = 'ScriptRanMarker'; })"/><text x="10" y="60" font-family="Helvetica, Arial, sans-serif" font-size="56" fill="#fff">OwnLogoMarker</text></svg>
SVG
set_branding "branding:
  logo: branding/own-logo.svg
  logo_alt: Own product logo
  footer: none"
if make -C "$guide" pdf >"$log" 2>&1; then
  if msg=$(pdf_logo "$guide/dist/$pdfname.pdf" "OwnLogoMarker" "$title"); then
    pass "PDF: an own logo shows on the title page"
  else
    failed "PDF with an own logo: $msg"
  fi
  if msg=$(pdf_band "$guide/dist/$pdfname.pdf"); then
    pass "PDF: the own logo sits on a #151515 band ($msg)"
  else
    failed "PDF with an own logo: $msg"
  fi
  if uv run --quiet --no-project --with pypdf python -c 'import sys; from pypdf import PdfReader; sys.exit(any("ScriptRanMarker" in (p.extract_text() or "") for p in PdfReader(sys.argv[1]).pages))' "$guide/dist/$pdfname.pdf"; then
    pass "PDF: no script or handler of the own SVG logo ran"
  else
    failed "PDF: a script or handler of the own SVG logo ran"
  fi
  if cmp -s "$guide/branding/own-logo.svg" "$guide/build/site/_/img/logo-guide.svg" \
     && check_site "$guide/build/site" "Own product logo" "-" "-" >"$tmp/own.check" 2>&1; then
    pass "site: the own logo is copied unchanged and shown as <img> with its alt text"
  else
    failed "site with an own logo"; cat "$tmp/own.check"
  fi
else
  failed "make pdf with an own logo"; tail -30 "$log"
fi
cp "$tmp/guide.yaml.sc008" "$guide/guide.yaml"
rm -rf "$guide/branding"

# A branded guide without its rendered branding output cannot print.
if make -C "$guide" check >"$log" 2>&1; then
  rm -f "$guide/build/branding/shareable/branding.json"
  if make -C "$guide" print-pdf >"$log" 2>&1; then
    failed "make print-pdf passed without build/branding/shareable/branding.json"
  elif grep -q "branding output missing for the shareable view" "$log"; then
    pass "print-pdf stops when the branding output is missing"
  else
    failed "print-pdf failed, but not for the missing branding output"; tail -10 "$log"
  fi
else
  failed "make check before the missing-output test"; tail -30 "$log"
fi

# --- US6: favicon, accent color, and the overlay directory (FR-015, FR-016, FR-019) ---
mkdir -p "$guide/branding" "$guide/ui/supplemental/css"
uv run --quiet --no-project python - "$guide/branding/favicon.png" <<'PY'
import struct
import sys
import zlib
def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(b"\x00\x3e\x86\x35")) + chunk(b"IEND", b""))
open(sys.argv[1], "wb").write(png)
PY
printf '.doc { font-size: 1.05em; } /* ExtraCssMarker */\n' > "$guide/ui/supplemental/css/extra.css"
set_branding "$SC008
  favicon: branding/favicon.png
  color: \"#3e8635\""
if make -C "$guide" check >"$log" 2>&1; then
  pass "make check with favicon, color, and ui/supplemental/css/extra.css"
  if uv run --quiet --no-project python - "$guide/build/site" >"$tmp/us6.check" 2>&1 <<'PY'
import re
import sys
from pathlib import Path
site = Path(sys.argv[1])
problems = []
headed = 0
for page in sorted(p for p in site.rglob("*.html") if "_exports" not in p.parts):
    html = page.read_text()
    if 'class="navbar-logo-img"' not in html:
        continue
    headed += 1
    rel = page.relative_to(site)
    order = [html.find(name) for name in ("/css/site.css", "/css/branding.css", "/css/extra.css")]
    if -1 in order or order != sorted(order):
        problems.append(f"{rel}: stylesheets not linked as site.css, branding.css, extra.css: {order}")
    if not re.search(r'<link rel="icon" href="[^"]*img/favicon-guide\.png" type="image/png">', html):
        problems.append(f"{rel}: no favicon-guide.png link with image/png")
    if "img/favicon.ico" in html:
        problems.append(f"{rel}: the stock favicon.ico is still linked")
if not headed:
    problems.append("no page with a header")
if not (site / "_" / "img" / "favicon-guide.png").is_file():
    problems.append("_/img/favicon-guide.png missing")
# US6-2: links, the hovered and active TOC entries, the focus outline, the skip link, and
# the search field take the accent; note admonitions keep the stock blue (site.css still
# colors them and branding.css, which loads later, never names them).
css = (site / "_" / "css" / "branding.css").read_text()
for rule in (".doc a { color: #3e8635; }", ".doc a:hover { color: #2f6528; }",
             ".toc .toc-menu a:hover { color: #3e8635; }",
             ".toc .toc-menu a.is-active { border-left-color: #3e8635; }",
             ":focus-visible { outline-color: #3e8635; }", ".skip-link { color: #3e8635; }",
             "#search-input:focus { border-color: #3e8635; }"):
    if rule not in css:
        problems.append(f"_/css/branding.css lacks {rule!r}")
if "admonition" in css:
    problems.append("_/css/branding.css touches admonitions")
if ".doc .admonitionblock.note .icon{background-color:#06c" not in (site / "_" / "css" / "site.css").read_text():
    problems.append("_/css/site.css no longer colors note admonitions #06c")
if "ExtraCssMarker" not in (site / "_" / "css" / "extra.css").read_text():
    problems.append("_/css/extra.css is not the overlay file")
print("; ".join(problems[:10]) or f"ok ({headed} pages)")
sys.exit(1 if problems else 0)
PY
  then
    pass "every page links site.css, branding.css, extra.css in order and favicon-guide.png; accent rules, note admonitions keep #06c ($(cat "$tmp/us6.check"))"
  else
    failed "favicon, color, or extra.css: $(cat "$tmp/us6.check")"
  fi
else
  failed "make check with favicon, color, and extra.css"; tail -30 "$log"
fi

# FR-020: an overlay partial wins over the generated one, with a warning.
mkdir -p "$guide/ui/supplemental/partials"
printf '<footer class="footer"><p>AuthorFooterMarker</p></footer>\n' > "$guide/ui/supplemental/partials/footer-content.hbs"
if make -C "$guide" check >"$log" 2>&1; then
  if grep -q 'ui/supplemental/partials/footer-content.hbs: warning: shadows the file generated for branding.footer' "$log"; then
    pass "an overlay partial that shadows the generated footer is reported"
  else
    failed "no shadowing warning for the overlay footer"; tail -20 "$log"
  fi
  if grep -q AuthorFooterMarker "$guide/build/site/guide/index.html" \
     && ! grep -q 'Agent Starter Kits on GitHub' "$guide/build/site/guide/index.html"; then
    pass "the author's footer partial wins over the generated one"
  else
    failed "the built footer is not the author's partial"
  fi
else
  failed "make check with an overlay footer partial"; tail -30 "$log"
fi

# Removing the block and the overlay returns the guide to the stock look.
set_branding ""
rm -rf "$guide/ui" "$guide/branding"
if make -C "$guide" check >"$log" 2>&1; then
  committed=$(cd "$guide" && pwd -P)/site.yml
  if [[ "$(cd "$guide" && uv run --quiet tools/guide/playbook.py path)" == "$committed" ]]; then
    pass "without branding and overlay the committed site.yml is used again"
  else
    failed "playbook.py path does not print the committed site.yml"
  fi
  page=$guide/build/site/guide/index.html
  if grep -q 'img/logo-demo-platform.svg' "$page" && grep -q 'demo.redhat.com' "$page"; then
    pass "the stock logo and footer are back after removing the branding"
  else
    failed "the stock look did not come back"
  fi
else
  failed "make check after removing the branding"; tail -30 "$log"
fi
cp "$tmp/guide.yaml.sc008" "$guide/guide.yaml"

# --- SC-002: an unbranded guide builds exactly as before the feature ---------------
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

old=$tmp/unbranded
# The html-single export prints "Last updated <build time>"; one SOURCE_DATE_EPOCH for
# both builds makes that line (and only that line) reproducible.
epoch=$(date +%s)
if baseline_plugin; then
  # The archived scaffold.sh locates the plugin relative to itself, so the fixture gets
  # the toolkit as of BASELINE_REF (the current scaffold.sh would install the new one).
  if ! bash "$tmp/baseline/tests/adapters/scaffold.sh" antora "$old" >"$tmp/scaffold-old.log" 2>&1; then
    failed "scaffold with the $BASELINE_REF plugin"; tail -20 "$tmp/scaffold-old.log"
  elif ! SOURCE_DATE_EPOCH=$epoch make -C "$old" pdf >"$log" 2>&1; then
    failed "make pdf with the $BASELINE_REF toolkit"; tail -30 "$log"
  else
    mkdir -p "$tmp/before"
    mv "$old/build/site" "$old/build/site-internal" "$tmp/before/"
    mv "$old"/dist/*.pdf "$tmp/before/before.pdf"
    bash "$REPO/guide/scripts/scaffold-project.sh" --format antora --toolkit-only "$old" >/dev/null
    if make -C "$old" clean >/dev/null 2>&1 && SOURCE_DATE_EPOCH=$epoch make -C "$old" pdf >"$log" 2>&1; then
      pass "unbranded fixture builds with the refreshed toolkit"
      for view in site site-internal; do
        if diff -r "$tmp/before/$view" "$old/build/$view" >"$tmp/$view.diff" 2>&1; then
          pass "build/$view identical before and after the feature (SC-002)"
        else
          failed "build/$view differs after the feature"; head -20 "$tmp/$view.diff"
        fi
      done
      if [[ -e "$old/build/branding" ]] || ls "$old"/build/playbook*.yml >/dev/null 2>&1; then
        failed "the unbranded build wrote build/branding/ or build/playbook*.yml"
      else
        pass "no build/branding/ and no generated playbook for the unbranded guide"
      fi
      if [[ "$(pdf_page1 "$tmp/before/before.pdf")" == "$(pdf_page1 "$old"/dist/*.pdf)" ]]; then
        pass "PDF title page has the same text and content stream (SC-002, FR-027)"
      else
        failed "PDF title page differs after the feature"
        diff <(pdf_page1 "$tmp/before/before.pdf") <(pdf_page1 "$old"/dist/*.pdf) | head -20
      fi
    else
      failed "make pdf after the toolkit refresh"; tail -30 "$log"
    fi
  fi
fi

# --- US5: an existing guide adopts branding with one refresh (FR-029, SC-006) ----------
adopt=$tmp/adopt
if baseline_plugin; then
  if ! bash "$tmp/baseline/tests/adapters/scaffold.sh" antora "$adopt" >"$tmp/scaffold-adopt.log" 2>&1; then
    failed "scaffold with the $BASELINE_REF plugin (adoption)"; tail -20 "$tmp/scaffold-adopt.log"
  else
    set_branding "$SC008" "$adopt"
    if (cd "$adopt" && uv run --quiet tools/guide/guidecfg.py validate) >"$log" 2>&1; then
      failed "the $BASELINE_REF toolkit accepted a branding block"
    elif grep -q '^guide.yaml:branding: unknown key' "$log"; then
      pass "the toolkit before the feature rejects the branding block as an unknown key"
    else
      failed "the old toolkit failed, but not with guide.yaml:branding: unknown key"; cat "$log"
    fi
    bash "$REPO/guide/scripts/scaffold-project.sh" --format antora --toolkit-only "$adopt" >/dev/null
    if [[ -f "$adopt/tools/guide/branding/contract.yaml" && -f "$adopt/tools/guide/branding/logo-text.svg.tmpl" ]]; then
      pass "the toolkit refresh vendors tools/guide/branding/"
    else
      failed "tools/guide/branding/ missing after the toolkit refresh"
    fi
    if make -C "$adopt" check >"$log" 2>&1; then
      if check_site "$adopt/build/site" "Red Hat Agent Starter Kits" "$KITS_URL" "Agent Starter Kits" >"$tmp/adopt.check" 2>&1; then
        pass "after the refresh the guide builds branded ($(tail -1 "$tmp/adopt.check"))"
      else
        failed "refreshed guide is not branded"; cat "$tmp/adopt.check"
      fi
    else
      failed "make check after the toolkit refresh"; tail -30 "$log"
    fi
    if git -C "$adopt" diff --quiet -- Makefile site.yml site-internal.yml; then
      pass "Makefile, site.yml, and site-internal.yml unchanged (FR-029)"
    else
      failed "adopting branding changed a build file"; git -C "$adopt" diff --stat -- Makefile site.yml site-internal.yml
    fi
  fi
fi

# --- US7: the pinned UI bundle still fits the branding (FR-031, SC-007) ----------------
CONTRACT=$REPO/guide/adapters/antora/branding/contract.yaml
bundle_url=$(uv run --quiet --no-project --with pyyaml python -c 'import sys, yaml; print(yaml.safe_load(open(sys.argv[1]))["bundle"])' "$CONTRACT")
mkdir -p "$tmp/bundle" "$tmp/bundle-copy"
if curl -fsSL -o "$tmp/bundle/ui-bundle.zip" "$bundle_url"; then
  if uv run --quiet "$REPO/guide/toolkit/branding.py" contract --bundle "$tmp/bundle/ui-bundle.zip" --contract "$CONTRACT" >"$log" 2>&1; then
    pass "the pinned bundle satisfies the branding contract"
  else
    failed "the pinned bundle breaks the branding contract"; cat "$log"
  fi
  unzip -q "$tmp/bundle/ui-bundle.zip" -d "$tmp/bundle-copy"
  rm -f "$tmp/bundle-copy/partials/header-content.hbs"
  if uv run --quiet "$REPO/guide/toolkit/branding.py" contract --bundle "$tmp/bundle-copy" --contract "$CONTRACT" >"$log" 2>&1; then
    failed "a bundle without partials/header-content.hbs passed the contract"
  elif grep -q '^contract: logo-lookup: partials/header-content.hbs: missing file' "$log"; then
    pass "a bundle without the logo lookup fails the contract and names logo-lookup"
  else
    failed "the contract failed, but did not name logo-lookup"; cat "$log"
  fi
  # SC-007: removing any one relied-upon part of the real bundle (every string, pattern,
  # recorded content, and accent rule of the contract) fails the rule that names it.
  if uv run --quiet --no-project --with pyyaml python - "$REPO/guide/toolkit" "$tmp/bundle/ui-bundle.zip" "$CONTRACT" "$tmp/mutants" >"$tmp/mutants.log" 2>&1 <<'PY'
import re
import shutil
import sys
import zipfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import branding  # noqa: E402
bundle, contract, work = Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
data = branding.load_contract(contract)
pristine = work / "pristine"
zipfile.ZipFile(bundle).extractall(pristine)
assert branding.check_bundle(pristine, contract) == []

def mutant(rel, change):
    copy = work / "copy"
    shutil.rmtree(copy, ignore_errors=True)
    shutil.copytree(pristine, copy)
    path = copy / rel
    if change is None:
        path.unlink()
        return copy
    text = path.read_text()
    new = change(text)
    assert new != text, f"mutation of {rel} changed nothing"
    path.write_text(new)
    return copy

def recolor(selector, value):
    def change(css):
        def rule(m):
            if selector in [" ".join(s.split()) for s in m.group(1).split(",")]:
                return m.group(1) + "{" + re.sub(re.escape(value) + r"(?![0-9a-fA-F])", "#123456", m.group(2), flags=re.I) + "}"
            return m.group(0)
        return branding.CSS_RULE_RE.sub(rule, css)
    return change

cases = []
for rule in data["rules"]:
    for needle in rule.get("contains") or []:
        cases.append((rule["id"], rule["file"], lambda t, n=needle: t.replace(n, "")))
    for regex in rule.get("matches") or []:
        cases.append((rule["id"], rule["file"], lambda t, r=regex: re.sub(r, "", t)))
    if "equals" in rule:
        cases.append((rule["id"], rule["file"], lambda t: t + "\n<!-- changed -->\n"))
    if not (rule.get("contains") or rule.get("matches") or "equals" in rule):
        cases.append((rule["id"], rule["file"], None))           # a rule that checks only the file
for key, prefix, value_of in (("accent_selectors", "accent", lambda e: data["accent_color"]),
                              ("accent_hover_selectors", "accent", lambda e: data["accent_hover_color"]),
                              ("accent_restore_selectors", "restore", lambda e: e["value"])):
    for entry in data[key]:
        cases.append((f"{prefix}:{entry['selector']}", "css/site.css", recolor(entry["selector"], str(value_of(entry)))))
bad = []
for rid, rel, change in cases:
    lines = branding.check_bundle(mutant(rel, change), contract)
    if not any(line.startswith(f"contract: {rid}: ") for line in lines):
        bad.append(f"{rid} ({rel}): {lines}")
print("\n".join(bad) or f"{len(cases)} mutations, each fails its rule")
sys.exit(1 if bad else 0)
PY
  then
    pass "every relied-upon part removed from the real bundle fails its contract rule ($(tail -1 "$tmp/mutants.log"))"
  else
    failed "a mutated real bundle passed the contract"; cat "$tmp/mutants.log"
  fi
else
  failed "download $bundle_url"
fi

# --- SC-004: a 40-character logo_text shows completely in the header and the PDF --------
LONG="Agent Starter Kits for OpenShift AI Labs"
[[ ${#LONG} -eq 40 ]] || failed "the SC-004 logo text is ${#LONG} characters, not 40"
set_branding "branding:
  logo_text: $LONG"
if make -C "$guide" pdf >"$log" 2>&1; then
  if node "$REPO/tests/adapters/measure_logo.mjs" "$guide" "$guide/build/site" >"$tmp/measure.log" 2>&1; then
    pass "40-character logo in Chromium at 1280 px: no overlap with the title, text inside the viewBox (SC-004)"
  else
    failed "40-character logo measurement"; cat "$tmp/measure.log"
  fi
  if msg=$(pdf_logo "$guide/dist/$pdfname.pdf" "$LONG" "$title"); then
    pass "PDF title page shows the whole 40-character logo text (SC-004)"
  else
    failed "PDF with a 40-character logo: $msg"
  fi
  if msg=$(pdf_band "$guide/dist/$pdfname.pdf"); then
    pass "PDF: the 40-character logo fits inside its band (SC-004, $msg)"
  else
    failed "PDF with a 40-character logo: $msg"
  fi
else
  failed "make pdf with a 40-character logo_text"; tail -30 "$log"
fi
cp "$tmp/guide.yaml.sc008" "$guide/guide.yaml"

finish
