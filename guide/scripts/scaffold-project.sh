#!/usr/bin/env bash
# Scaffold a guide project from an adapter, or refresh its vendored toolkit.
#   usage: scaffold-project.sh --format antora|mkdocs|gfm --title TITLE DIR
#          scaffold-project.sh --format FORMAT --toolkit-only DIR
# Copies guide/adapters/<format>/scaffold/ into DIR (never overwriting existing
# files), renders {{TITLE}}, and installs the toolkit as DIR/tools/guide/:
# the toolkit scripts with VERSION, the adapter descriptor (adapter.yaml), the
# templates the toolkit renders (templates/), the validate allowlist
# (readonly.yaml), and the adapter's branding assets (guide/adapters/<format>/branding/
# as tools/guide/branding/, when the adapter has them: the logo template and the UI
# bundle contract that tools/guide/branding.py reads). --toolkit-only refreshes only
# tools/guide/ (used by evolve).
set -euo pipefail

usage() { echo "usage: scaffold-project.sh --format antora|mkdocs|gfm (--title TITLE | --toolkit-only) DIR" >&2; exit 2; }

format="" title="" toolkit_only=0 dir=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --format) [[ $# -ge 2 ]] || usage; format=$2; shift 2 ;;
    --title) [[ $# -ge 2 ]] || usage; title=$2; shift 2 ;;
    --toolkit-only) toolkit_only=1; shift ;;
    -*) usage ;;
    *) [[ -z "$dir" ]] || usage; dir=$1; shift ;;
  esac
done
[[ -n "$format" && -n "$dir" ]] || usage
[[ $toolkit_only -eq 1 || -n "$title" ]] || usage

plugin=$(cd "$(dirname "$0")/.." && pwd)
adapter="$plugin/adapters/$format"
[[ -f "$adapter/adapter.yaml" ]] || { echo "unknown format: $format (no $adapter/adapter.yaml)" >&2; exit 2; }

mkdir -p "$dir"

if [[ $toolkit_only -eq 0 ]]; then
  # Copy the scaffold without overwriting anything that already exists.
  (cd "$adapter/scaffold" && find . -type f) | while read -r rel; do
    rel=${rel#./}
    target="$dir/$rel"
    if [[ -e "$target" ]]; then
      echo "kept existing $rel"
      continue
    fi
    mkdir -p "$(dirname "$target")"
    cp "$adapter/scaffold/$rel" "$target"
  done
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
  rsync -a --exclude '__pycache__' "$adapter/branding/" "$tools/branding/"
fi

echo "toolkit $(cat "$tools/VERSION" 2>/dev/null || echo unknown) installed in $tools"
