# Quickstart: validate multi-harness support

Validation scenarios that prove the feature works. Run from a checkout of cc-guide. These are run/validation guides, not implementation.

## Prerequisites

- `uv`, `git`, Node 20+, Playwright Chromium (for export/preview checks).
- superpowers installed for the harness under test.
- For Codex: multi-agent features enabled (`multi_agent = true` in `~/.codex/config.toml`).

## Scenario A: Claude Code unchanged (FR-012, SC-003)

1. On `main` (pre-feature), run `make test` and `make test-adapters`; record results.
2. On this branch, run `make validate`, `make test`, `make test-adapters`.
3. Expect: existing assertions still pass; only the new additive per-harness checks are added. A create/preview/export pass on a sample guide yields equivalent output to the baseline.

## Scenario B: Codex full command set (US1, SC-001, SC-002)

1. Install the plugin on Codex via its plugin mechanism (README steps), pointing at this checkout.
2. Confirm the six guide commands/skills are discoverable on Codex.
3. Run create end to end on a small source repo (for example a single-service repo pinned to a tag) with a short description.
4. Run preview, export, `evolve --check`, validate (read-only), upstream.
5. Expect: each runs to completion; create produced a guide with per-page source verification; no Claude-specific setup step was required.

## Scenario C: Codex degradations (SC-005)

1. On Codex without cc-prose: run create; expect pages written via `style-rules.md`, run completes, a note states prose is absent.
2. On Codex without the Excalidraw tools: run a guide that plans diagrams; expect diagram tasks fall back to placeholders and the run continues naming the missing diagrams.

## Scenario D: superpowers / multi-agent prerequisites (SC-006, FR-017)

1. On a harness without superpowers exposed: run create; expect an immediate stop with a harness-named install message and no guide content written.
2. On a harness without multi-agent dispatch: run create; expect a stop with the parallel-subagent prerequisite message.

## Scenario E: OpenCode (US3, SC-008)

1. Run `guide/opencode/install.sh --project-dir <project>`.
2. Confirm the guide commands are present under `<project>/.opencode/plugins/guide/command/` and launch.
3. Run create end to end on a small source repo.

## Scenario F: detection contract (SC-004)

1. Run `guide/scripts/deps.sh` on each harness; confirm the JSON record reports correct booleans from capability exposure with no read of `~/.claude/plugins/installed_plugins.json` (verify by running with that file absent/renamed on a non-Claude harness).

## Adapter test dimension (SC-007)

`make test-adapters` fails if any supported harness can no longer discover or launch the commands (manifest validity for Claude/Codex, shim install + presence for OpenCode).
