#!/usr/bin/env bash
# Build the mini-project fixture as a git repository with three commits.
#   usage: make-mini-repo.sh <dest>
# Prints FIRST=, SECOND=, and THIRD= lines with the full commit SHAs.
#   FIRST:  the mini-project as checked in (README says port 8080, config says 9090)
#   SECOND: changes config/defaults.yaml (timeout 30 -> 60)
#   THIRD:  renames docs/setup.md to docs/install.md and deletes the Makefile
# Author, committer, and dates are fixed, so the SHAs are the same on every machine.
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: make-mini-repo.sh <dest>" >&2
  exit 2
fi
dest=$1
src=$(cd "$(dirname "$0")/mini-project" && pwd)

if [[ -e "$dest" && -n "$(ls -A "$dest" 2>/dev/null)" ]]; then
  echo "destination is not empty: $dest" >&2
  exit 2
fi

export GIT_AUTHOR_NAME="Fixture Author" GIT_AUTHOR_EMAIL="fixture@example.com"
export GIT_COMMITTER_NAME="Fixture Author" GIT_COMMITTER_EMAIL="fixture@example.com"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1

g() { git -C "$dest" -c commit.gpgsign=false -c core.hooksPath=/dev/null -c core.autocrlf=false "$@"; }
commit() { # commit <date> <message>
  GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" g commit --quiet -m "$2"
}

mkdir -p "$dest"
git init --quiet -b main "$dest"
cp -R "$src/." "$dest/"
chmod 644 "$dest/README.md" "$dest/Makefile" "$dest/config/defaults.yaml" "$dest/docs/setup.md"
g add -A
commit "2026-01-05T10:00:00+00:00" "Initial minisvc"
echo "FIRST=$(g rev-parse HEAD)"

cat > "$dest/config/defaults.yaml" <<'EOF'
# Default configuration for minisvc.
server:
  port: 9090
  bind: 127.0.0.1
timeout: 60
admin:
  enabled: false
EOF
g add -A
commit "2026-02-10T10:00:00+00:00" "Raise the default timeout"
echo "SECOND=$(g rev-parse HEAD)"

g mv docs/setup.md docs/install.md
g rm --quiet Makefile
commit "2026-03-15T10:00:00+00:00" "Rename the setup doc and drop the Makefile"
echo "THIRD=$(g rev-parse HEAD)"
