#!/usr/bin/env bash
# Scaffold a guide project from an adapter, or refresh its vendored toolkit.
#   usage: scaffold-project.sh --format antora|mkdocs|gfm --title TITLE [--embedded] DIR
#          scaffold-project.sh --format FORMAT --toolkit-only DIR
# Copies guide/adapters/<format>/scaffold/ into DIR (never overwriting existing
# files), renders {{TITLE}}, and installs the toolkit as DIR/tools/guide/:
# the toolkit scripts with VERSION, the adapter descriptor (adapter.yaml), the
# templates the toolkit renders (templates/), the validate allowlist
# (readonly.yaml), and the adapter's branding assets (guide/adapters/<format>/branding/
# as tools/guide/branding/, when the adapter has them: the logo template, the UI
# bundle contract, and the vendored fonts that tools/guide/branding.py reads; the
# maintainer script fonts/update-fonts.py stays in the plugin). --toolkit-only refreshes only
# tools/guide/ (used by evolve).
# --embedded (gfm only, specs/005-embedded-guide) scaffolds a guide subdirectory of a
# host repository: no internal/ part, the pointer page docs/README.md from
# guide/adapters/gfm/embedded/ (the host README is the front page), and
# confidential.local.yaml in the guide's .gitignore. It refuses a DIR that exists, is not
# empty, and holds neither guide.yaml nor tools/guide/adapter.yaml (it never merges into an
# unrelated directory).
set -euo pipefail

usage() { echo "usage: scaffold-project.sh --format antora|mkdocs|gfm (--title TITLE [--embedded] | --toolkit-only) DIR" >&2; exit 2; }

format="" title="" toolkit_only=0 embedded=0 dir=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --format) [[ $# -ge 2 ]] || usage; format=$2; shift 2 ;;
    --title) [[ $# -ge 2 ]] || usage; title=$2; shift 2 ;;
    --toolkit-only) toolkit_only=1; shift ;;
    --embedded) embedded=1; shift ;;
    -*) usage ;;
    *) [[ -z "$dir" ]] || usage; dir=$1; shift ;;
  esac
done
[[ -n "$format" && -n "$dir" ]] || usage
[[ $toolkit_only -eq 1 || -n "$title" ]] || usage

plugin=$(cd "$(dirname "$0")/.." && pwd)
adapter="$plugin/adapters/$format"
[[ -f "$adapter/adapter.yaml" ]] || { echo "unknown format: $format (no $adapter/adapter.yaml)" >&2; exit 2; }
overlay=""
if [[ $embedded -eq 1 && $toolkit_only -eq 0 ]]; then
  if [[ $format != gfm ]]; then
    echo "embedded guides support the gfm format only in this release (got $format)" >&2
    exit 2
  fi
  # A directory with guide.yaml or a vendored toolkit is a (partly) scaffolded guide: resume it.
  if [[ -d "$dir" && ! -f "$dir/guide.yaml" && ! -f "$dir/tools/guide/adapter.yaml" \
        && -n "$(ls -A "$dir" 2>/dev/null)" ]]; then
    echo "$dir exists, is not empty, and is not a guide project; choose another guide subdirectory" >&2
    exit 2
  fi
  overlay="$adapter/embedded"
fi

mkdir -p "$dir"

if [[ $toolkit_only -eq 0 ]]; then
  # Copy the scaffold without overwriting anything that already exists. An embedded
  # guide takes files from the embedded overlay first and has no internal part.
  { (cd "$adapter/scaffold" && find . -type f); if [[ -n "$overlay" ]]; then (cd "$overlay" && find . -type f); fi; } |
    sort -u | while read -r rel; do
    rel=${rel#./}
    if [[ -n "$overlay" && ( $rel == internal/* ) ]]; then
      continue
    fi
    src="$adapter/scaffold/$rel"
    if [[ -n "$overlay" && -f "$overlay/$rel" ]]; then
      src="$overlay/$rel"
    fi
    target="$dir/$rel"
    if [[ -e "$target" ]]; then
      echo "kept existing $rel"
      continue
    fi
    mkdir -p "$(dirname "$target")"
    cp "$src" "$target"
  done
  if [[ -n "$overlay" ]] && ! grep -qx 'confidential.local.yaml' "$dir/.gitignore" 2>/dev/null; then
    printf '%s\n' '# Confidential terms and input locations of an embedded guide (never committed)' \
      'confidential.local.yaml' >> "$dir/.gitignore"
  fi
  # Render {{TITLE}} in text files that contain it.
  TITLE="$title" python3 - "$dir" <<'PY'
import os, sys
root = sys.argv[1]
title = os.environ["TITLE"]
for base, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "tools", ".guide")]
    for name in files:
        path = os.path.join(base, name)
        try:
            text = open(path, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        if "{{TITLE}}" in text:
            open(path, "w", encoding="utf-8").write(text.replace("{{TITLE}}", title))
PY
fi

# Install or refresh the vendored toolkit.
tools="$dir/tools/guide"
mkdir -p "$tools"
rsync -a --delete --exclude '__pycache__' --exclude '.pytest_cache' "$plugin/toolkit/" "$tools/"
cp "$adapter/adapter.yaml" "$tools/adapter.yaml"
mkdir -p "$tools/templates"
for t in run-summary.md upstream-issue.md; do
  cp "$plugin/templates/$t" "$tools/templates/$t"
done
cp "$plugin/validate/readonly.yaml" "$tools/readonly.yaml" 2>/dev/null || true
# Branding assets of the adapter (Antora only). The rsync --delete above removed any
# earlier copy, so a refresh always matches the plugin.
if [[ -d "$adapter/branding" ]]; then
  rsync -a --exclude '__pycache__' --exclude 'update-fonts.py' "$adapter/branding/" "$tools/branding/"
fi

echo "toolkit $(cat "$tools/VERSION" 2>/dev/null || echo unknown) installed in $tools"
