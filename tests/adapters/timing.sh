#!/usr/bin/env bash
# Timing checks on the 25-page fixture guide (T064).
#   usage: timing.sh [antora|mkdocs|gfm]...   (default: all three)
# For each format: seconds from `make preview` to a served page (SC-008, under 60),
# `make pdf` (SC-011, under 180), and `drift.py --check` (plan goal, under 120).
# For antora also `make site pdf` and preview from a linked worktree under
# .claude/worktrees/ (FR-016a). Prints one result line per measurement.
set -uo pipefail

REPO=$(cd "$(dirname "$0")/../.." && pwd)
formats=("$@")
[[ ${#formats[@]} -gt 0 ]] || formats=(antora mkdocs gfm)
work=$(mktemp -d)
trap 'kill $(jobs -p) 2>/dev/null; rm -rf "$work"' EXIT
fail=0

now() { python3 -c 'import time; print(time.time())'; }
since() { python3 -c "import sys; print(f'{float(sys.argv[2]) - float(sys.argv[1]):.1f}')" "$1" "$(now)"; }
free_port() { python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()'; }
result() { # result <label> <seconds> <limit>
  if python3 -c "import sys; sys.exit(0 if float(sys.argv[1]) < float(sys.argv[2]) else 1)" "$2" "$3"; then
    echo "PASS $1: ${2}s (limit ${3}s)"
  else
    echo "FAIL $1: ${2}s (limit ${3}s)"; fail=1
  fi
}

stop_preview() { # stop_preview <make pid> <port>: the server runs as a grandchild (uvx, npx)
  kill "$1" 2>/dev/null
  lsof -ti "tcp:$2" -sTCP:LISTEN 2>/dev/null | xargs kill 2>/dev/null
  sleep 0.5
  lsof -ti "tcp:$2" -sTCP:LISTEN 2>/dev/null | xargs kill -9 2>/dev/null
  wait "$1" 2>/dev/null
}

preview_time() { # preview_time <label> <guide dir> <url path>
  local label=$1 dir=$2 path=$3 port start pid
  port=$(free_port)
  start=$(now)
  make -C "$dir" --no-print-directory preview OPEN=0 PORT="$port" > "$work/preview-$label.log" 2>&1 &
  pid=$!
  for _ in $(seq 1 240); do
    if curl -fsS -o /dev/null "http://127.0.0.1:$port$path" 2>/dev/null; then
      result "$label preview reachable" "$(since "$start")" 60
      stop_preview "$pid" "$port"
      return
    fi
    sleep 0.5
  done
  echo "FAIL $label preview: not reachable after 120s (see log below)"; tail -5 "$work/preview-$label.log"; fail=1
  stop_preview "$pid" "$port"
}

uv run --quiet "$REPO/tests/fixtures/make-large-guide.py" "$REPO/tests/fixtures/sample-guide" "$work/large" >/dev/null

for format in "${formats[@]}"; do
  dir="$work/$format/guide"
  mkdir -p "$work/$format"
  if ! bash "$REPO/tests/adapters/scaffold.sh" "$format" "$dir" "$work/large" > "$work/scaffold-$format.log" 2>&1; then
    echo "FAIL $format: scaffold"; tail -5 "$work/scaffold-$format.log"; fail=1; continue
  fi
  pages=$(find "$dir" -path "$dir/node_modules" -prune -o -path "$dir/tools" -prune -o \( -name '*.adoc' -o -name '*.md' \) -print | grep -c -E '/(pages|docs|internal)/')
  echo "INFO $format: $pages page files"

  case "$format" in
    antora) url=/guide/index.html ;;
    mkdocs) url=/ ;;
    gfm) url=/ ;;
  esac
  preview_time "$format" "$dir" "$url"

  start=$(now)
  if make -C "$dir" --no-print-directory pdf > "$work/pdf-$format.log" 2>&1; then
    result "$format make pdf" "$(since "$start")" 180
  else
    echo "FAIL $format make pdf"; tail -5 "$work/pdf-$format.log"; fail=1
  fi

  start=$(now)
  (cd "$dir" && uv run --quiet tools/guide/drift.py --check > /dev/null 2>&1); status=$?
  if [[ $status -eq 0 || $status -eq 10 ]]; then
    result "$format drift check (exit $status)" "$(since "$start")" 120
  else
    echo "FAIL $format drift check: exit $status"; fail=1
  fi

  if [[ "$format" == antora ]]; then
    git -C "$dir" add -A >/dev/null && git -C "$dir" -c user.name=t -c user.email=t@example.com -c commit.gpgsign=false commit -qm "large fixture" >/dev/null
    wt="$dir/.claude/worktrees/001-timing"
    git -C "$dir" worktree add -q -b 001-timing "$wt" >/dev/null 2>&1
    ln -s "$dir/node_modules" "$wt/node_modules"
    start=$(now)
    if make -C "$wt" --no-print-directory site pdf > "$work/worktree.log" 2>&1; then
      result "antora linked worktree: make site pdf" "$(since "$start")" 180
    else
      echo "FAIL antora linked worktree: make site pdf"; tail -8 "$work/worktree.log"; fail=1
    fi
    preview_time "antora-worktree" "$wt" /guide/index.html
  fi
done

exit $fail
