#!/usr/bin/env bash
# Smoke test for embedded gfm guides (specs/005-embedded-guide, T032, T038, T042, T048):
# build a host repository from tests/fixtures/mini-host, scaffold an embedded guide into
# host/guide, pin self, apply a move plan, install a front page and pages, then build,
# check, and print; drift, stubs, and the pull request mode follow.
#   usage: bash tests/adapters/test_gfm_embedded.sh
# Env: CC_GUIDE_NODE_MODULES=<dir> reuses a prepared node_modules (see scaffold.sh);
#      KEEP=1 keeps the temporary host repository for inspection.
set -uo pipefail

REPO=$(cd "$(dirname "$0")/../.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/cc-guide-embedded.XXXXXX")
host=$tmp/host
guide=$host/guide
log=$tmp/make.log
fail=0
export XDG_CACHE_HOME=$tmp/xdg
export GIT_AUTHOR_NAME="Fixture Author" GIT_AUTHOR_EMAIL="fixture@example.com"
export GIT_COMMITTER_NAME="Fixture Author" GIT_COMMITTER_EMAIL="fixture@example.com"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1

pass() { echo "PASS gfm-embedded: $1"; }
failed() { echo "FAIL gfm-embedded: $1"; fail=1; }
finish() {
  if [[ $fail -ne 0 || "${KEEP:-0}" == 1 ]]; then
    echo "host repository kept in $host"
  else
    rm -rf "$tmp"
  fi
  exit $fail
}
g() { git -C "$host" -c commit.gpgsign=false -c core.hooksPath=/dev/null "$@"; }
tk() { (cd "$guide" && uv run --quiet tools/guide/"$@"); }

# --- host repository and embedded scaffold ---------------------------------------------
cp -R "$REPO/tests/fixtures/mini-host" "$host"
git init --quiet -b main "$host"
g add -A && g commit --quiet -m "Initial Mini Host"
base_sha=$(g rev-parse HEAD)
cp "$host/Makefile" "$tmp/Makefile.orig"
cp "$host/pyproject.toml" "$tmp/pyproject.toml.orig"

if bash "$REPO/guide/scripts/scaffold-project.sh" --format gfm --title "Mini Host" --embedded "$guide" >"$tmp/scaffold.log" 2>&1; then
  pass "scaffold --embedded"
else
  failed "scaffold --embedded"; cat "$tmp/scaffold.log"; finish
fi
[[ ! -e "$guide/internal" ]] && pass "no internal/ part" || failed "internal/ scaffolded"

cat > "$guide/guide.yaml" <<'YAML'
schema: 1
title: "Mini Host"
format: gfm
personas:
  - id: admin
    title: Administrator
    start: admin/install
sections:
  - id: overview
    title: Overview
    voice: concepts
  - id: admin
    title: Admin guide
    voice: technical
rigor: standard
internal:
  enabled: false
  confidential_terms: []
  confidential_patterns: []
embedded:
  front_page: ../README.md
  stubs: []
  pr_check: off
YAML
printf 'rules: []\n' > "$guide/guide-rules.yaml"

if [[ -n "${CC_GUIDE_NODE_MODULES:-}" && -d "$CC_GUIDE_NODE_MODULES" ]]; then
  ln -s "$CC_GUIDE_NODE_MODULES" "$guide/node_modules"
else
  (cd "$guide" && npm install --silent --no-audit --no-fund >/dev/null 2>&1) || { failed "npm install"; finish; }
fi

# --- pin self, apply a move plan ---------------------------------------------------
tk fetch.py pin --source self=.. >"$tmp/pin.log" 2>&1 && pass "pin self" || { failed "pin self"; cat "$tmp/pin.log"; finish; }
if [[ -z "$(g status --porcelain -- . ':(exclude)guide')" ]]; then
  pass "nothing outside guide/ changed before apply"
else
  failed "files outside guide/ changed before apply"; g status --porcelain
fi
mkdir -p "$guide/.guide/runs/r1"
cat > "$guide/.guide/runs/r1/move-plan.yaml" <<YAML
self_revision: $base_sha
developer_readme: ../DEVELOPMENT.md
developer_readme_exists: false
entries:
  - {path: ../README.md, section: null, destination: input}
  - {path: ../README.md, section: Building from source, destination: developer}
  - {path: ../README.md, section: Running tests, destination: developer}
  - {path: ../CONTRIBUTING.md, destination: keep}
  - {path: ../LICENSE, destination: keep}
  - {path: ../docs/install.md, destination: input, stub: true}
manifests:
  - {path: ../pyproject.toml, publishes_readme: true}
absolute_links: false
YAML
if tk embed.py apply --plan .guide/runs/r1/move-plan.yaml >"$tmp/apply.log" 2>&1; then
  pass "embed.py apply"
else
  failed "embed.py apply"; cat "$tmp/apply.log"; finish
fi

# --- pages and the front page ---------------------------------------------------------
mkdir -p "$guide/docs/admin"
cat > "$guide/docs/admin/install.md" <<'MD'
# Install Mini Host

<!-- Sources:
self:config/defaults.yaml:1-3
self:src/cli.py:4-4
-->

The greeting comes from `config/defaults.yaml`. Back to the [front page](../../../README.md).
MD
cat > "$guide/docs/SUMMARY.md" <<'MD'
# Summary

<!-- guide: no-sources -->

## Overview

- [Mini Host](README.md)

## Admin guide

- [Install Mini Host](admin/install.md)
MD
cat > "$host/README.md" <<'MD'
<!-- guide: front page. This file is generated and maintained by cc-guide; change it with /guide:evolve. -->
# Mini Host Front Page

[![CI](https://img.shields.io/badge/ci-passing-brightgreen.svg)](https://example.com/ci)

<!-- Sources:
self:src/cli.py:1-12
self:pyproject.toml
-->

Mini Host prints a greeting.

## Overview

Mini Host is a small command line tool.

## Admin guide

- [Install Mini Host](guide/docs/admin/install.md)

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md), [CONTRIBUTING.md](CONTRIBUTING.md), and the [license](LICENSE).
MD
tk embed.py retarget docs/install.md=guide/docs/admin/install.md >"$tmp/retarget.log" 2>&1 \
  && pass "retarget the stub to its guide page" || { failed "retarget"; cat "$tmp/retarget.log"; }
tk fetch.py rebaseline --to self=HEAD >"$tmp/rebaseline.log" 2>&1 || { failed "rebaseline"; cat "$tmp/rebaseline.log"; }

# --- build, check, and print ------------------------------------------------------------
if make -C "$guide" check dist >"$log" 2>&1; then
  pass "make check dist"
else
  failed "make check dist"; tail -40 "$log"; finish
fi
if grep -q "Mini Host Front Page" "$guide/build/site/README.html" 2>/dev/null; then
  pass "front page rendered as build/site/README.html"
else
  failed "front page title missing from build/site/README.html"
fi
pdf=$(ls "$guide"/dist/*.pdf 2>/dev/null | head -1)
if [[ -n "$pdf" ]]; then
  first=$(uv run --quiet "$REPO/tests/adapters/pdftext.py" text "$pdf" | awk '/^== page/{n++} n>=1' | grep -m1 -E "Mini Host Front Page|Install Mini Host")
  if [[ "$first" == *"Mini Host Front Page"* ]]; then
    pass "the PDF starts with the front page"
  else
    failed "the PDF does not start with the front page (first title: $first)"
  fi
else
  failed "no PDF in dist/"
fi
changed=$(g status --porcelain --untracked-files=all -- . ':(exclude)guide' | awk '{print $2}' | LC_ALL=C sort | tr '\n' ' ')
if [[ "$changed" == "DEVELOPMENT.md README.md docs/install.md " ]]; then
  pass "outside guide/ only README.md, DEVELOPMENT.md, and the stub changed"
else
  failed "unexpected changes outside guide/: $changed"
fi
cmp -s "$host/Makefile" "$tmp/Makefile.orig" && pass "host Makefile unchanged" || failed "host Makefile changed"
cmp -s "$host/pyproject.toml" "$tmp/pyproject.toml.orig" && pass "host pyproject.toml unchanged" || failed "host pyproject.toml changed"
[[ -f "$host/LICENSE" ]] && pass "LICENSE at the root" || failed "LICENSE missing"
grep -q "## Building from source" "$host/DEVELOPMENT.md" && pass "DEVELOPMENT.md holds the developer sections" \
  || failed "DEVELOPMENT.md lacks the developer sections"

# the stub (US3, T042)
if head -1 "$host/docs/install.md" | grep -qx '<!-- guide: moved -->' \
    && grep -q '](../guide/docs/admin/install.md)' "$host/docs/install.md"; then
  pass "docs/install.md is a stub linking to the guide page"
else
  failed "docs/install.md is not a retargeted stub"; cat "$host/docs/install.md"
fi
grep -q 'stubs:' "$guide/guide.yaml" && grep -q '../docs/install.md' "$guide/guide.yaml" \
  && pass "the stub is listed in guide.yaml" || failed "the stub is not listed in guide.yaml"

# a page citing guide material fails the check
cat > "$guide/docs/admin/bad.md" <<'MD'
# Bad

<!-- Sources:
self:guide/docs/admin/install.md
-->

Circular.
MD
if (cd "$guide" && uv run --quiet tools/guide/check.py) >"$tmp/bad.log" 2>&1; then
  failed "a self-citation of guide material passed the check"
else
  grep -q "self-citation" "$tmp/bad.log" && pass "self-citation of guide material fails the check" \
    || { failed "check failed without a self-citation violation"; cat "$tmp/bad.log"; }
fi
rm -f "$guide/docs/admin/bad.md"

# --- drift (US2, T038) -------------------------------------------------------------
g add -A && g commit --quiet -m "Embedded guide"
echo "More words." >> "$guide/docs/admin/install.md"
g add -A && g commit --quiet -m "guide-only change"
if tk drift.py --check >"$tmp/drift0.log" 2>&1; then
  pass "a guide-only commit is no drift"
else
  failed "a guide-only commit reported drift"; cat "$tmp/drift0.log"
fi
sed -i.bak 's/hello/hi/' "$host/src/cli.py" && rm -f "$host/src/cli.py.bak"
g add -A && g commit --quiet -m "change a cited file"
tk drift.py --check >"$tmp/drift1.log" 2>&1
status=$?
if [[ $status -eq 10 ]] && grep -q '`../README.md`' "$tmp/drift1.log"; then
  pass "a cited change is drift and lists ../README.md"
else
  failed "a cited change: exit $status"; cat "$tmp/drift1.log"
fi

# --- pull request mode and timing (US4, T048) ---------------------------------------
g switch --quiet -c pr
sed -i.bak 's/hi/hey/' "$host/src/cli.py" && rm -f "$host/src/cli.py.bak"
g add -A && g commit --quiet -m "pr: change a cited file"
start=$(python3 -c 'import time; print(time.time())')
tk drift.py --pr --base main >"$tmp/pr.log" 2>&1
status=$?
elapsed=$(python3 -c "import time; print(round(time.time() - $start, 2))")
if [[ $status -eq 10 ]] && grep -q 'src/cli.py' "$tmp/pr.log"; then
  pass "drift.py --pr fails for a cited change without a guide update"
else
  failed "drift.py --pr: exit $status"; cat "$tmp/pr.log"
fi
python3 -c "import sys; sys.exit(0 if $elapsed < 60 else 1)" && pass "the pull request check took ${elapsed}s (< 60s)" \
  || failed "the pull request check took ${elapsed}s"
if (cd "$guide" && GUIDE_SKIP=1 uv run --quiet tools/guide/drift.py --pr --base main) >"$tmp/pr-skip.log" 2>&1 \
    && grep -q 'skipped by request' "$tmp/pr-skip.log"; then
  pass "GUIDE_SKIP=1 passes with a note"
else
  failed "GUIDE_SKIP=1 did not pass"; cat "$tmp/pr-skip.log"
fi
# the staging step itself, measured inside one interpreter (uv start-up is not part of it)
stage_time=$(cd "$guide" && uv run --quiet --no-project --with pyyaml python3 - <<'PY'
import sys, time
from pathlib import Path
sys.path.insert(0, "tools/guide")
import embed
start = time.time()
embed.stage(Path("."), Path("build/stage-timing"))
print(round(time.time() - start, 2))
PY
)
python3 -c "import sys; sys.exit(0 if $stage_time < 1 else 1)" && pass "embed.py stage took ${stage_time}s (< 1s)" \
  || failed "embed.py stage took ${stage_time}s"

finish
