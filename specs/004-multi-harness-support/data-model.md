# Phase 1 Data Model: Multi-harness support

This feature has no runtime datastore. The "entities" are configuration and code artifacts and the detection record passed between preflight and the skills.

## Entity: Harness entry point

Represents how one harness discovers and launches the guide commands.

| Attribute | Values | Notes |
|---|---|---|
| harness | `claude` \| `codex` \| `opencode` | v1 set is fixed (FR-019) |
| manifest/installer path | `guide/.claude-plugin/plugin.json` \| `guide/.codex-plugin/plugin.json` \| `guide/opencode/install.sh` + `guide/opencode/command/*.md` | one per harness |
| points at | shared `guide/skills/` | no per-harness behavior |
| command exposure | slash commands (Claude), skills (Codex), copied command shims (OpenCode) | all resolve to the same skills |

Rule: each harness reads only its own entry point (FR-003). Adding a harness adds an entry point only; it must not require a skill/toolkit change (FR-018, FR-019).

## Entity: Capability signal

A boolean derived from in-session capability exposure (FR-007), produced by `deps.sh` and consumed by preflight, create, and evolve.

| Signal | Present when | Absent behavior |
|---|---|---|
| `superpowers` | superpowers skills are exposed in the session | create/evolve stop with install message (FR-011) |
| `multi_agent` | the harness exposes subagent/parallel-dispatch tools | create/evolve stop with prerequisite message (FR-017) |
| `prose` | `prose:humanizer` skill is exposed | pages use built-in `style-rules.md` (FR-008) |
| `excalidraw` | `mcp__excalidraw__*` tools are available | diagram tasks use placeholder path (FR-009) |
| `harness` | always (identifies `claude`/`codex`/`opencode`) | drives Claude-only settings wiring (FR-010) |

Detection MUST NOT read a harness-specific registry or settings file to decide presence (FR-007). The Claude-only `excalidraw_allowed`/`excalidraw_allowed_in` settings fields remain, but are computed and used only when `harness == claude`.

## Entity: Vendored SDD helper script

The three portable superpowers scripts copied into the toolkit (FR-006).

| Script | Role | Contract |
|---|---|---|
| `sdd-workspace` | resolve the per-plan workspace dir | prints the plan workspace abs path |
| `task-brief` | extract one task's text to a file | `task-brief PLAN_FILE N [OUTFILE]`; usage → exit 2 |
| `review-package` | build a review diff package | `review-package PLAN_FILE BASE HEAD [OUTFILE]`; usage → exit 2 |

Location: `guide/toolkit/sdd/`. Invoked by create/evolve via a toolkit-relative path, never via a superpowers install path. Travels into guide projects as `tools/guide/sdd/` through the existing scaffold copy.

## Entity: AGENTS.md

Repo-root agent instructions for AGENTS.md-based harnesses (FR-013). Harness-neutral content; any spex-managed Codex block is owned by `.specify/spex.json` tooling, not hand-authored here.

## State / transitions

Only the pipeline-irrelevant preflight flow has states: preflight runs, emits the capability-signal record, and either continues (create/evolve) or stops (superpowers or multi_agent absent). No persisted entity state.
