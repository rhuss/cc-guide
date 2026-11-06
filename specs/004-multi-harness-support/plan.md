# Implementation Plan: Multi-harness support (Codex, OpenCode)

**Branch**: `004-multi-harness-support` | **Date**: 2026-11-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/004-multi-harness-support/spec.md`

## Summary

Make the `guide` plugin installable and runnable on Codex (primary) and OpenCode (secondary) in addition to Claude Code, from one plugin directory, by copying the packaging model the sibling cc-review plugin and superpowers already use. The orchestration (superpowers) is already multi-harness, and the toolkit (`guide/toolkit/`) is already format-neutral, so the work is: add per-harness entry points, stop reaching into superpowers' install path (vendor its three portable SDD helper scripts and invoke superpowers skills by name), switch dependency detection from reading `~/.claude/...` to in-session capability exposure, make preflight harness-aware, add an `AGENTS.md`, document per-harness install and known degradations, and add a per-harness dimension to the adapter smoke tests. Claude Code behavior must not regress; cc-prose (built-in `style-rules.md` fallback) and Excalidraw (placeholder-diagram fallback) stay degraded on non-Claude harnesses by design.

## Technical Context

**Language/Version**: Bash (POSIX/bash) for scripts and entry points; Python via PEP 723 (`uv run`) and Node 20+ (`.mjs`) in `guide/toolkit/`; Markdown with YAML frontmatter for skills, commands, and manifests. No new languages introduced.

**Primary Dependencies**: superpowers (already multi-harness; required for create/evolve, detected by skill exposure); optional cc-prose (`prose:*` skills) and Excalidraw MCP (`mcp__excalidraw__*` tools), both detected by exposure with built-in fallbacks.

**Storage**: Files only (plugin manifests, skills, scripts, vendored toolkit). No datastore.

**Testing**: pytest for the toolkit (`make test`); shell smoke tests per adapter (`make test-adapters`), to be extended with a per-harness dimension; `claude plugin validate` (`make validate`) for the Claude manifest.

**Target Platform**: Three agent harnesses: Claude Code, Codex (App + CLI), OpenCode. Codex needs multi-agent features enabled for create/evolve (per superpowers' codex-tools reference).

**Project Type**: Multi-harness agent plugin (one plugin directory, thin per-harness entry points over shared skills + a vendored, format-neutral toolkit).

**Performance Goals**: N/A (interactive author tooling; no throughput targets).

**Constraints**: No behavior fork per harness (FR-018); no secrets or raw inputs written anywhere; no em/en dashes; scripts never `cd` into `.guide/cache/` and only use `git -C` there; never commit `.mcp.json`. Claude Code output and behavior must match the pre-feature baseline (FR-012).

**Scale/Scope**: Six commands (create, evolve, preview, export, validate, upstream) plus the preflight and diagrams skills, across three harnesses. v1 harness set is fixed (FR-019).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is an unfilled template (all placeholders), so there are no ratified numbered principles to gate against. The binding project rules are in the repository `CLAUDE.md`: no em/en dashes; `uv` not pip, podman not Docker; no secrets or raw inputs in guide projects, fixtures, or run records; every outward action shown and approved; subagents dispatched without a model override; git commits end with `Assisted-By: 🤖 Claude Code`; scripts never `cd` into `.guide/cache/`; never commit `.mcp.json`. This feature complies: it adds packaging and detection logic only, introduces no outward actions by itself, and the vendored scripts keep using `git -C`. No violations; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/004-multi-harness-support/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (entities: entry points, capability signals, vendored scripts)
├── quickstart.md        # Phase 1 output (per-harness install + run validation)
├── contracts/           # Phase 1 output (entry-point and detection contracts)
│   ├── harness-entry-points.md
│   └── capability-detection.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
guide/
├── .claude-plugin/
│   └── plugin.json              # existing Claude manifest (unchanged except possibly keywords)
├── .codex-plugin/
│   └── plugin.json              # NEW: Codex manifest, "skills": "./skills/" (mirrors cc-review/superpowers)
├── opencode/
│   ├── command/
│   │   ├── create.md            # NEW: OpenCode command shims (6), each mirrors the Claude command wrapper
│   │   ├── evolve.md
│   │   ├── preview.md
│   │   ├── export.md
│   │   ├── validate.md
│   │   └── upstream.md
│   └── install.sh               # NEW: copies command shims into <project>/.opencode/plugins/guide/
├── commands/                    # existing Claude slash-command wrappers (unchanged)
├── skills/                      # shared across all harnesses (behavior lives here)
│   ├── preflight/               # MODIFY: harness-aware; Claude-only settings/permission wiring guarded
│   ├── create/                  # MODIFY: call vendored SDD scripts; invoke superpowers skills by name
│   ├── evolve/                  # MODIFY: same as create
│   ├── diagrams/                # (unchanged; already has placeholder fallback)
│   ├── page-task/               # (unchanged)
│   ├── preview|export|validate|upstream/   # (unchanged; already toolkit-driven and neutral)
├── scripts/
│   ├── deps.sh                  # MODIFY: capability-exposure detection, harness-aware
│   ├── superpowers-probe.sh     # MODIFY/REPLACE: presence by skill exposure, version advisory only, no Claude registry read
│   └── scaffold-project.sh      # (review: vendor SDD scripts into tools/guide/; scaffold .gitignore entries)
└── toolkit/
    ├── sdd/                     # NEW: vendored portable SDD helpers
    │   ├── sdd-workspace
    │   ├── task-brief
    │   └── review-package
    └── ... (existing toolkit unchanged)

AGENTS.md                        # NEW: repo-root agent instructions for AGENTS.md-based harnesses
compat.yaml  (guide/compat.yaml) # MODIFY: version intent only; detection no longer needs installPath
README.md                        # MODIFY: per-harness install + known degradations
tests/
├── adapters/                    # MODIFY: add per-harness dimension (discovery + launch per harness)
└── toolkit/                     # ADD: tests for vendored SDD scripts + detection logic
```

**Structure Decision**: One plugin directory (`guide/`) with three thin per-harness entry points over a single shared `skills/` directory and the shared `toolkit/`. Codex reads `guide/.codex-plugin/plugin.json` (skills discovered directly; cc-guide skills already self-run preflight when invoked without a command wrapper). OpenCode installs via `guide/opencode/install.sh`, which copies the six command shims that mirror the Claude command wrappers (preflight then the matching skill). Claude Code keeps `guide/.claude-plugin/` and `guide/commands/` unchanged. Harness differences are confined to these entry points and to capability-presence branches in `preflight`, `create`, and `evolve`; there is no behavior fork in the shared skills or toolkit (FR-018).

## Complexity Tracking

No constitution violations; no entries.

## Phases

- **Phase 0 (research.md)**: resolve the open design points, principally the capability-detection signals per harness (superpowers, cc-prose, Excalidraw, and the multi-agent capability of FR-017), the OpenCode command-shim + install mechanism, the fate of `superpowers-probe.sh` and `compat.yaml` once the Claude registry read is removed, and how preflight branches on harness. Record decisions, rationale, alternatives.
- **Phase 1 (data-model.md, contracts/, quickstart.md)**: define the entities (harness entry point, capability signal, vendored SDD script, AGENTS.md), the entry-point and detection contracts, and a per-harness install-and-run validation guide.
- **Phase 2 (tasks.md)**: produced by `/speckit-tasks`, not here.
