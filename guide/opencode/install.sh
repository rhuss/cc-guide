#!/usr/bin/env bash
set -euo pipefail

# Install cc-guide commands for OpenCode.
# Copies the command shims into .opencode/plugins/guide/command/ in the target
# project. The shims only chain guide:preflight and the matching guide:<name>
# skill; all behavior lives in the shared guide/skills/ (FR-002, FR-018).
# Usage: ./install.sh [--project-dir <path>]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="."

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-dir) PROJECT_DIR="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

TARGET="$PROJECT_DIR/.opencode/plugins/guide"
mkdir -p "$TARGET/command"

for cmd in "$SCRIPT_DIR/command"/*.md; do
  [ -f "$cmd" ] || continue
  cp "$cmd" "$TARGET/command/"
done

echo "cc-guide commands installed for OpenCode at $TARGET/command"
