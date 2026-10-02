#!/usr/bin/env bash
# PDF export smoke test (T049): for each format, scaffold the fixture guide and check
# `make pdf` and `make pdf VIEW=internal` with tests/adapters/pdftext.py.
#   usage: bash tests/adapters/test_pdf.sh [format...]
# Without arguments it tests every adapter whose Makefile prints with print-pdf.mjs.
# Env: TIMING=1 also times `make pdf` on the 25-page fixture (SC-011: under 180 s);
#      KEEP=1 keeps the temporary guide projects.
set -uo pipefail

REPO=$(cd "$(dirname "$0")/../.." && pwd)
FIXTURES=$REPO/tests/fixtures
PDFTEXT=$REPO/tests/adapters/pdftext.py
tmp=$(mktemp -d "${TMPDIR:-/tmp}/cc-guide-pdf.XXXXXX")
fail=0

formats=("$@")
if [[ ${#formats[@]} -eq 0 ]]; then
  for dir in "$REPO"/guide/adapters/*/; do
    f=$(basename "$dir")
    grep -q 'print-pdf.mjs' "$dir/scaffold/Makefile" 2>/dev/null && formats+=("$f")
  done
fi

finish() {
  if [[ $fail -ne 0 || "${KEEP:-0}" == 1 ]]; then echo "guide projects kept in $tmp"; else rm -rf "$tmp"; fi
  exit $fail
}

# Page titles of the neutral fixture in navigation order (shareable, then internal).
titles() { # titles <neutral guide> shareable|all
  uv run --quiet --no-project --with pyyaml python - "$1" "$2" <<'EOF'
import re, sys, yaml
from pathlib import Path
root, which = Path(sys.argv[1]), sys.argv[2]
nav = yaml.safe_load((root / "pages" / "nav.yaml").read_text())
groups = nav["shareable"] + (nav.get("internal", []) if which == "all" else [])
for group in groups:
    for page in group["pages"]:
        text = (root / "pages" / f"{page}.md").read_text()
        print(re.search(r"^# (.+)$", text, re.M).group(1))
EOF
}

check_pdf() { # check_pdf <label> <pdf> <neutral guide> <guide> shareable|internal
  local label=$1 pdf=$2 neutral=$3 guide=$4 view=$5 args=() t
  local title date
  title=$(cd "$guide" && uv run --quiet tools/guide/guidecfg.py get title)
  date=$(cd "$guide" && uv run --quiet tools/guide/guidecfg.py get baseline.captured)
  args+=(--title "$title" --date "$date")
  for t in $(sed -n 's/^ *commit: *//p' "$guide/baseline.yaml"); do args+=(--commit "$t"); done
  while IFS= read -r t; do args+=(--page-title "$t"); done < <(titles "$neutral" "$([[ $view == internal ]] && echo all || echo shareable)")
  if [[ $view == internal ]]; then
    args+=(--footer INTERNAL)
  else
    args+=(--forbid "ACME Corp" --forbid "Internal notes" --forbid "do not share outside")
  fi
  if uv run --quiet "$PDFTEXT" check "$pdf" "${args[@]}" > "$tmp/$label.check" 2>&1; then
    echo "PASS $label: PDF content ($(grep -c '^PASS' "$tmp/$label.check") checks)"
  else
    echo "FAIL $label: PDF content"; grep -v '^PASS' "$tmp/$label.check"; fail=1
  fi
}

for format in "${formats[@]}"; do
  guide=$tmp/$format
  log=$tmp/$format.log
  if ! bash "$REPO/tests/adapters/scaffold.sh" "$format" "$guide" > "$log" 2>&1; then
    echo "FAIL $format: scaffold"; tail -20 "$log"; fail=1; continue
  fi
  name=$(cd "$guide" && uv run --quiet tools/guide/guidecfg.py get slug)-$(cd "$guide" && uv run --quiet tools/guide/guidecfg.py get baseline.captured)

  if make -C "$guide" pdf > "$log" 2>&1 && [[ -f "$guide/dist/$name.pdf" ]]; then
    echo "PASS $format: make pdf wrote dist/$name.pdf"
    check_pdf "$format-shareable" "$guide/dist/$name.pdf" "$FIXTURES/sample-guide" "$guide" shareable
  else
    echo "FAIL $format: make pdf"; tail -30 "$log"; fail=1
  fi

  if make -C "$guide" pdf VIEW=internal > "$log" 2>&1 && [[ -f "$guide/dist/$name-INTERNAL.pdf" ]]; then
    echo "PASS $format: make pdf VIEW=internal wrote dist/$name-INTERNAL.pdf"
    check_pdf "$format-internal" "$guide/dist/$name-INTERNAL.pdf" "$FIXTURES/sample-guide" "$guide" internal
  else
    echo "FAIL $format: make pdf VIEW=internal"; tail -30 "$log"; fail=1
  fi

  # A planted check failure (an em dash, written as its UTF-8 bytes) must leave no PDF.
  page=$(cd "$guide" && uv run --quiet --no-project --with pyyaml python -c "
import sys; sys.path.insert(0, 'tools/guide'); import guidecfg
a = guidecfg.load_adapter('.'); print(next(p for p in guidecfg.pages('.', a, 'shareable') if 'start' in p.name))")
  cp "$guide/$page" "$tmp/page.bak"
  printf '\nA dash \xe2\x80\x94 planted by the test.\n' >> "$guide/$page"
  if make -C "$guide" pdf > "$log" 2>&1; then
    echo "FAIL $format: make pdf passed with a planted em dash"; fail=1
  elif [[ -e "$guide/dist/$name.pdf" ]]; then
    echo "FAIL $format: make pdf failed but left dist/$name.pdf"; fail=1
  else
    echo "PASS $format: planted check failure writes no PDF"
  fi
  cp "$tmp/page.bak" "$guide/$page"

  if [[ "${TIMING:-0}" == 1 ]]; then
    large=$tmp/$format-large-neutral
    uv run --quiet "$FIXTURES/make-large-guide.py" "$FIXTURES/sample-guide" "$large" > /dev/null
    lguide=$tmp/$format-large
    modules=""
    [[ -d "$guide/node_modules" ]] && modules=$(cd "$guide/node_modules" && pwd -P)
    if CC_GUIDE_NODE_MODULES=$modules bash "$REPO/tests/adapters/scaffold.sh" "$format" "$lguide" "$large" > "$log" 2>&1; then
      start=$(date +%s)
      if make -C "$lguide" pdf > "$log" 2>&1; then
        secs=$(( $(date +%s) - start ))
        if [[ $secs -lt 180 ]]; then echo "PASS $format: 25-page make pdf in ${secs}s (SC-011 < 180 s)"; else echo "FAIL $format: 25-page make pdf took ${secs}s"; fail=1; fi
      else
        echo "FAIL $format: 25-page make pdf"; tail -20 "$log"; fail=1
      fi
    else
      echo "FAIL $format: scaffold of the 25-page guide"; tail -20 "$log"; fail=1
    fi
  fi
done

[[ ${#formats[@]} -gt 0 ]] || { echo "FAIL: no adapter with a pdf target"; fail=1; }
finish
