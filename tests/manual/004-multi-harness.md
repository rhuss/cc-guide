# Manual and end-to-end verification: multi-harness support (feature 004)

Acceptance pass for `specs/004-multi-harness-support/quickstart.md` (scenarios A to F). Automated parts ran during implementation; scenarios that need a live Codex or OpenCode session with superpowers installed and an end-to-end `create` run are recorded here as procedures and are open.

## Automated suites (2026-11-06, macOS)

| Command | Result |
|---|---|
| `make validate` | marketplace and plugin manifests pass; one pre-existing `ICON_MISSING` warning, unrelated to this feature; the Claude `.claude-plugin` manifest and `guide/commands/*.md` are unchanged vs `main` (FR-012) |
| `make test` | 732 passed (adds `test_deps.py` rework, `test_probe.py` rework, and `test_sdd_scripts.py`) |
| per-harness adapter checks | `test_harness_claude.sh`, `test_harness_codex.sh`, `test_harness_opencode.sh` all exit 0 |

## Scenario A: Claude Code unchanged (FR-012, SC-003)

| Expectation | Result |
|---|---|
| Existing toolkit assertions still pass | pass: `make test` 732 passed; the Claude-only `excalidraw_allowed` settings scan is byte-identical and `test_deps.py::test_legacy_fields_present_with_same_values_on_claude` confirms the legacy fields are unchanged with the new fields additive |
| Existing per-format adapter assertions unchanged | the per-format test files (`test_antora.sh`, `test_mkdocs.sh`, `test_gfm.sh`, `test_pdf.sh`, preview tests) are unmodified; the harness checks are additive. The full per-format run needs node, npx, Pandoc, and Playwright Chromium and is run with `make test-adapters` on a machine with that tool chain |
| `.claude-plugin` and `commands/` unchanged | `git diff --name-only main -- guide/.claude-plugin/ guide/commands/` is empty |
| create/preview/export parity before and after | open: needs an interactive Claude Code session |

## Scenario B: Codex full command set (US1, SC-001, SC-002)

Procedure, open (needs a Codex session with superpowers and multi-agent features enabled). Automated support verified here:

| Expectation | Result |
|---|---|
| Six commands discoverable on Codex | `test_harness_codex.sh`: the `.codex-plugin/plugin.json` is valid, its version equals the Claude manifest (`0.4.0`), `skills` is `./skills/`, and the six commands resolve to skills with matching `name:` frontmatter |
| Skills self-run preflight (no command layer) | each of the six skills now self-invokes `guide:preflight` when its result is absent (`guide/skills/*/SKILL.md`) |
| create end to end on Codex | open: needs a session |

## Scenario C: Codex degradations (SC-005)

| Expectation | Result |
|---|---|
| Without cc-prose, pages use built-in style rules, run completes, a note states prose is absent | preflight emits the one-line prose-absent note and records `prose: absent`; the page-task dispatch names `style-rules.md` when prose is absent (FR-008). Full run is open (needs a session) |
| Without Excalidraw, diagram tasks fall back to placeholders and the run continues | create (section 6c) and the diagrams skill (section 11) route to the placeholder path when the tools are absent; the Claude-only permission wiring is gated on `harness == claude` (FR-009, FR-010). Full run is open |

## Scenario D: superpowers / multi-agent prerequisites (SC-006, FR-017)

| Expectation | Result |
|---|---|
| No superpowers exposed: create stops with a harness-named install message, nothing written | preflight step 2 stops create/evolve when `superpowers == false` with a harness-named message (FR-011). Session verification open |
| No multi-agent dispatch: create stops with the parallel-subagent prerequisite message | preflight step 2 stops create/evolve when `multi_agent == false` (FR-017). Session verification open |

## Scenario E: OpenCode (US3, SC-008)

| Expectation | Result |
|---|---|
| `install.sh --project-dir <project>` lands the six shims | `test_harness_opencode.sh` runs the installer into a tmp project and asserts the six shims land under `.opencode/plugins/guide/command/` and each chains preflight and its skill |
| Commands launch; create end to end | open: needs an OpenCode session |

## Scenario F: detection contract (SC-004)

`guide/scripts/deps.sh` reports correct booleans from the capability signals the controller passes, with no read of `~/.claude/plugins/installed_plugins.json`:

| Harness | Result |
|---|---|
| claude | `excalidraw_allowed` computed from settings (true in this worktree, whose `.claude/settings.local.json` allows `mcp__excalidraw`); all booleans reflect the passed signals |
| codex | `excalidraw_allowed: false`, `excalidraw_allowed_in: []` (settings wiring skipped, FR-010); capability booleans reflect the passed signals |
| opencode | same as codex; `superpowers_version` omitted reports as `null` |

`rg` finds no `installed_plugins` or `.claude/plugins` reference in `deps.sh` or `superpowers-probe.sh` (SC-004). `superpowers-probe.sh` is advisory: exit 0 at or above the known-good version or when none is reported, exit 3 (warn, continue) below it.
