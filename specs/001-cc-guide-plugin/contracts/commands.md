# Contract: Commands

The plugin `guide` exposes six slash commands. Each command file in `guide/commands/` is a thin wrapper that runs the shared preflight and then delegates to the skill of the same name in `guide/skills/`. Arguments use `--flag value`; anything else is free text passed to the skill.

## Shared preflight (every command, FR-003, FR-003a, FR-004, FR-042)

Runs before any file is written; stops with an actionable message on failure (SC-009).

1. Resolve the guide project: the current directory, or the directory given with `--dir`. Commands other than `create` require a `guide.yaml` there.
2. Dependency check from `~/.claude/plugins/installed_plugins.json`:
   - `superpowers@*`: required for `create` and `evolve` (except `--check`). Read `installPath`; run the contract probe (see "Superpowers contract probe" below).
   - `prose@*`: optional; record `prose: present|absent` and show the one-line notice when absent.
   - Excalidraw MCP tools: needed only when the run plans diagram tasks; checked by the presence of `mcp__excalidraw__*` tools in the session. When missing, warn with the install hint and ask whether to continue with diagram placeholders (FR-003).
   - Adapter tool chain: `make doctor` in the guide project (runs `tools/guide/doctor.py`, see `adapter.md`).
3. Print the recommended session settings (model, effort) and warn without blocking when the session model is not the recommended one.

### Superpowers contract probe (FR-004)

- Required skills: `brainstorming`, `writing-plans`, `subagent-driven-development`, `requesting-code-review`.
- Required scripts under `skills/subagent-driven-development/scripts/`: `sdd-workspace`, `task-brief`, `review-package`, always invoked as `bash <script>`.
- Probe: each script run with no arguments must exit with status 2 and print a line starting with `usage:`; the `wrote <path>:` output format is checked on a dry fixture during plugin tests.
- Known-good versions are listed in `guide/compat.yaml`. Unknown versions that pass the probe run with a warning; a failed probe stops the command and names the missing or changed piece.

## `/guide:create`

| Argument | Meaning |
|---|---|
| `--dir <path>` | Target directory (FR-005b). Default: current directory, which must be empty. |
| `--format antora\|mkdocs\|gfm` | Adapter; asked if missing. |
| `--rigor fast\|standard\|strict` | Default `standard`. |
| `--source <id>=<repo>[@<ref>]` | Repeatable. Source repository to pin; `<id>` is the source id used in source blocks. |
| `--input <path-or-url>` | Repeatable. Input to register (never copied). |
| free text | Description of the guide's subject and audience. |

Flow: preflight → intake interview (FR-006: audience, personas, scope, sections and voices, rigor, internal part, confidential terms and patterns, optional cluster connections, drift schedule opt-in, remote repository and push opt-ins) → scaffold with the adapter → pin sources (`baseline.yaml`) and register inputs (`inputs.yaml`) → guide spec through superpowers brainstorming → plan through writing-plans with guide templates → author approval → subagent-driven execution with per-task reviews (rigor-dependent) → whole-guide review and one fix round → run summary, rulings, upstream findings collected.

Resume (FR-013a): rerunning `/guide:create` in a project with an unfinished ledger continues at the first unfinished task; with `--restart` it asks for confirmation and starts a new run.

## `/guide:evolve`

| Argument | Meaning |
|---|---|
| `--check` | Check-only mode (FR-025a): report drift, change nothing, no AI-dependent steps. Equivalent to `make drift` in the guide project (runs `tools/guide/drift.py --check`). |
| `--input <path-or-url>` | Repeatable. New inputs to register. |
| `--to <source-id>=<ref>` | Repeatable. Target revision per source; default is each source's tracked branch head. |
| `--rigor ...` | As in create. |
| `--adopt` | Adoption step for guides without a cc-guide baseline or source blocks (FR-028). |

Flow: preflight → drift report → change-request re-evaluation → impact set (changed cited files, pages citing them, pages linking to those) → update plan for author approval → execution with the same reviews → new baseline only after checks pass (FR-029) → run summary.

## `/guide:preview`

| Argument | Meaning |
|---|---|
| `--internal` | Serve the internal view (FR-030). Default: shareable. |
| `--port <n>` | Default per adapter. |

Builds with the adapter, serves with live reload, opens the browser (macOS `open`). Usable during a run.

## `/guide:export`

| Argument | Meaning |
|---|---|
| `--internal` | Include the internal part (FR-030e); file name gets `-INTERNAL`, footer marks every page, warning shown. |
| `--out <path>` | Default `dist/<guide-slug>-<baseline-date>[-INTERNAL].pdf`. |

Fails without writing a file when content checks fail or the PDF tool chain is missing (FR-030f).

## `/guide:upstream`

| Argument | Meaning |
|---|---|
| `--finding <id>` | Repeatable; limit to these findings. Default: all `collected` and `reverified`. |
| `--pr` | Offer change proposals for mechanical fixes (FR-034). |

Flow: re-verify each finding on the default branch of its repository (FR-032) → dedupe and check for existing issues (FR-036) → draft each report with the provenance note (FR-035) → show every draft in full → post only approved drafts (FR-033) → record URLs in `findings/upstream.yaml` and link them from the internal part.

## `/guide:validate`

| Argument | Meaning |
|---|---|
| `--cluster <name>` | Required (FR-037); a connection from `guide.yaml`. |
| `--tier read-only\|full` | Default `read-only`. `full` refuses unless the connection is `disposable: true` (FR-039). |
| `--page <path>` | Repeatable; limit to pages. |

Each mutating command in the full tier is shown and needs confirmation. Output is redacted before it is recorded (FR-039a). Mismatches become review findings (FR-040).
