#!/usr/bin/env bash
# Build the eval scene: a source repository whose default branch already fixed one
# of two collected findings, and a guide project pinned to the older commit.
#   requires: CC_GUIDE_PLUGIN pointing at the plugin directory (guide/ in cc-guide)
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
: "${CC_GUIDE_PLUGIN:?set CC_GUIDE_PLUGIN to the guide plugin directory}"

src="$here/upstream-src"
guide="$here/guide-project"
rm -rf "$src" "$guide"
mkdir -p "$src/docs" "$src/config"

export GIT_AUTHOR_NAME="Fixture Author" GIT_AUTHOR_EMAIL="fixture@example.com"
export GIT_COMMITTER_NAME="Fixture Author" GIT_COMMITTER_EMAIL="fixture@example.com"
g() { git -C "$src" -c commit.gpgsign=false -c core.hooksPath=/dev/null "$@"; }

git init --quiet -b main "$src"
printf '# minisvc\n\nThe service listens on port 8080 by default.\n' > "$src/README.md"
printf 'server:\n  port: 9090\n' > "$src/config/defaults.yaml"
printf '# Setup\n\n1. Run `make install`.\n2. Run `make check-status` and expect `ok`.\n' > "$src/docs/setup.md"
printf 'install:\n\t@echo installing\n\nstatus:\n\t@echo ok\n' > "$src/Makefile"
g add -A
GIT_AUTHOR_DATE=2026-01-05T10:00:00Z GIT_COMMITTER_DATE=2026-01-05T10:00:00Z g commit --quiet -m "Initial"
pinned=$(g rev-parse HEAD)

# The default branch fixes the stale target name; the README port drift remains.
printf '# Setup\n\n1. Run `make install`.\n2. Run `make status` and expect `ok`.\n' > "$src/docs/setup.md"
g add -A
GIT_AUTHOR_DATE=2026-02-05T10:00:00Z GIT_COMMITTER_DATE=2026-02-05T10:00:00Z g commit --quiet -m "Fix the status target name in the setup doc"

mkdir -p "$guide/findings"
cat > "$guide/guide.yaml" <<EOF
schema: 1
title: minisvc guide
format: antora
personas:
  - id: admin
    title: Administrator
    start: index
EOF
cat > "$guide/baseline.yaml" <<EOF
captured: "2026-01-06"
sources:
  - id: mini
    repo: $src
    ref: main
    commit: $pinned
EOF
cat > "$guide/findings/upstream.yaml" <<'EOF'
findings:
  - id: UF-1
    source: mini
    kind: doc-drift
    locations:
      - ref: README.md:3
        quote: The service listens on port 8080 by default.
      - ref: config/defaults.yaml:2
        quote: "port: 9090"
    summary: The README states port 8080, but the default configuration uses 9090.
    evidence: config/defaults.yaml sets server.port to 9090; README.md says 8080.
    status: collected
  - id: UF-2
    source: mini
    kind: stale-reference
    locations:
      - ref: docs/setup.md:4
        quote: Run `make check-status` and expect `ok`.
    summary: The setup doc names a make target check-status that does not exist.
    evidence: The Makefile defines status, not check-status.
    status: collected
EOF
git init --quiet -b main "$guide"
bash "$CC_GUIDE_PLUGIN/scripts/scaffold-project.sh" --format antora --toolkit-only "$guide" >/dev/null
echo "scene ready: source $src (pinned ${pinned:0:7}), guide project $guide"
