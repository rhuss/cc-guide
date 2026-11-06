# Agent Instructions

Repository-level guidance for any agent harness working in this repository (Claude Code, Codex, OpenCode). It complements the project rules in `CLAUDE.md`; where they overlap, `CLAUDE.md` wins.

## Session completion

Before ending a work session:

1. Commit the work in logical commits. Every commit message ends with the trailer `Assisted-By: 🤖 Claude Code`.
2. Run the quality gates for anything you changed: `make validate` (manifests), `make test` (toolkit), and `make test-adapters` (per-format and per-harness smoke tests).
3. Show every outward action (creating a remote repository, pushing, filing an issue or pull request, changing a cluster) in full and run it only after explicit approval. Never push or file anything on your own initiative.
4. Leave the tree clean: no stray files, no `.mcp.json`, no secrets or raw inputs committed.
5. Hand off: state what changed, what is left, and any decisions that still need follow-up.

## Working rules

- No em dash or en dash characters in any file. Rephrase, or use commas, parentheses, or separate sentences.
- Use `uv` (not pip) and podman (not Docker) in any instruction you write.
- The shared skills in `guide/skills/` and the format-neutral toolkit in `guide/toolkit/` carry no per-harness behavior fork. Harness differences live only in the thin per-harness entry points (`guide/.claude-plugin/`, `guide/commands/`, `guide/.codex-plugin/`, `guide/opencode/`) and in capability-presence branches (Claude-only wiring and the optional-dependency fallbacks).
- Dependency presence is decided by in-session capability exposure, never by reading a plugin registry or settings file.
