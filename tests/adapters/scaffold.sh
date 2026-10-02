#!/usr/bin/env bash
# Scaffold the fixture guide as a guide project in the layout /guide:create produces.
#   usage: scaffold.sh <format> <dir> [<neutral guide>]
# <format> is antora, mkdocs, or gfm; <dir> must not exist or be empty.
# The neutral guide defaults to tests/fixtures/sample-guide.
# Env: CC_GUIDE_NODE_MODULES=<dir> symlinks a prepared node_modules instead of npm install.
#      CC_GUIDE_SKIP_NPM=1 skips the node_modules step entirely.
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "usage: scaffold.sh <format> <dir> [<neutral guide>]" >&2
  exit 2
fi
format=$1
dir=$2
REPO=$(cd "$(dirname "$0")/../.." && pwd)
FIXTURES=$REPO/tests/fixtures
neutral=${3:-$FIXTURES/sample-guide}
adapter=$REPO/guide/adapters/$format

[[ -d "$adapter/scaffold" ]] || { echo "unknown format: $format" >&2; exit 2; }
if [[ -e "$dir" && -n "$(ls -A "$dir" 2>/dev/null)" ]]; then
  echo "target is not empty: $dir" >&2
  exit 2
fi
mkdir -p "$dir"
dir=$(cd "$dir" && pwd)

# Source repository: the mini-project with three deterministic commits, beside the guide.
mini=$(dirname "$dir")/$(basename "$dir")-mini-repo
rm -rf "$mini"
eval "$(bash "$FIXTURES/make-mini-repo.sh" "$mini")"

title=$(sed -n 's/^title: *//p' "$neutral/guide.yaml" | head -1 | tr -d '"')

# Scaffold, {{TITLE}}, and tools/guide/ (toolkit, VERSION, adapter.yaml, templates):
# the same script /guide:create uses.
bash "$REPO/guide/scripts/scaffold-project.sh" --format "$format" --title "$title" "$dir" >/dev/null

render() { # render <file>: fill the fixture placeholders in place
  python3 - "$1" "$title" "file://$mini" "$FIRST" "$SECOND" "$THIRD" "$FIXTURES" <<'EOF'
import sys
path, title, url, first, second, third, fixtures = sys.argv[1:]
text = open(path).read()
for key, value in {"TITLE": title, "MINI_REPO_URL": url, "MINI_FIRST_COMMIT": first,
                   "MINI_SECOND_COMMIT": second, "MINI_THIRD_COMMIT": third,
                   "FIXTURES_DIR": fixtures}.items():
    text = text.replace("{{" + key + "}}", value)
open(path, "w").write(text)
EOF
}

cp "$neutral/baseline.yaml.tmpl" "$dir/baseline.yaml"
cp "$neutral/inputs.yaml" "$dir/inputs.yaml"
render "$dir/baseline.yaml"
render "$dir/inputs.yaml"

uv run --quiet "$REPO/tests/adapters/convert.py" "$format" "$neutral" "$dir" >/dev/null
printf 'rules: []\n' > "$dir/guide-rules.yaml"

g() { git -C "$dir" -c commit.gpgsign=false -c core.hooksPath=/dev/null "$@"; }
git init --quiet -b main "$dir"
g add -A
GIT_AUTHOR_NAME="Fixture Author" GIT_AUTHOR_EMAIL="fixture@example.com" \
GIT_COMMITTER_NAME="Fixture Author" GIT_COMMITTER_EMAIL="fixture@example.com" \
  g commit --quiet -m "Scaffold fixture guide ($format)"

if [[ -f "$dir/package.json" && "${CC_GUIDE_SKIP_NPM:-0}" != 1 ]]; then
  if [[ -n "${CC_GUIDE_NODE_MODULES:-}" && -d "$CC_GUIDE_NODE_MODULES" ]]; then
    ln -s "$CC_GUIDE_NODE_MODULES" "$dir/node_modules"
  else
    (cd "$dir" && npm install --silent --no-audit --no-fund >/dev/null)
  fi
fi
echo "scaffolded $format guide in $dir (sources: $mini)"
