---

description: "Task list for multi-harness support (Codex, OpenCode)"
---

# Tasks: Multi-harness support (Codex, OpenCode)

**Input**: Design documents from `/specs/004-multi-harness-support/`

**Prerequisites**: plan.md, spec.md, research.md (D1-D9), data-model.md, contracts/ (harness-entry-points.md, capability-detection.md), quickstart.md

**Tests**: Included. FR-014 and SC-007 require a per-harness adapter test dimension and toolkit tests for the vendored scripts, so test tasks are part of the feature, not optional extras.

**Organization**: Grouped by user story. US1 (Codex, P1) is the MVP. US2 (Claude no-regression, P2) is a constraint verified by tests. US3 (OpenCode, P3) rides the same adapter.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- Paths are repository-relative. The plugin lives in `guide/`; shared behavior in `guide/skills/`; the format-neutral toolkit in `guide/toolkit/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Shared artifacts that later phases build on.

- [x] T001 [P] Vendor the three superpowers SDD helper scripts into `guide/toolkit/sdd/` (`sdd-workspace`, `task-brief`, `review-package`), preserving executable bits and adding a one-line provenance header naming the upstream superpowers version they were copied from (D3, FR-006).
- [x] T002 [P] Update `guide/compat.yaml` to express the superpowers compatibility expectation as a single recorded minimum/known-good version threshold used only for an advisory warning, and remove the `required_scripts` semantics that pointed into the superpowers install path (the scripts are now vendored per T001) (D6, FR-016).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The shared dependency-decoupling and detection layer that every command and every harness goes through. These change behavior on Claude Code too, so they must preserve the current Claude output (FR-012) while making it harness-portable.

**⚠️ CRITICAL**: No user story phase can be validated until this phase is complete.

- [x] T003 [US-shared] Decouple `create` and `evolve` from the superpowers install path: call the vendored `tools/guide/sdd/` scripts (resolved toolkit-relative, as other toolkit scripts are) and invoke superpowers skills (brainstorming, writing-plans, subagent-driven-development, requesting-code-review) by name only; remove every use of the superpowers `installPath`/`SP` variable. Files: `guide/skills/create/SKILL.md`, `guide/skills/evolve/SKILL.md` (D3, FR-005, FR-006).
- [x] T004 Implement the capability-detection contract from `contracts/capability-detection.md`: define, for each signal (`superpowers`, `prose`, `excalidraw`, `multi_agent`), that presence is decided by in-session capability exposure (the controller reads its own exposed skills/tools), not by reading a registry; reduce `guide/scripts/deps.sh` to emit the JSON record with the Claude-only `excalidraw_allowed`/`excalidraw_allowed_in` fields computed only when `harness == claude`, plus the additive `harness`, `superpowers_version`, `multi_agent` fields. Files: `guide/scripts/deps.sh`, `guide/skills/preflight/SKILL.md` (D4, FR-007).
- [x] T005 Rework `guide/scripts/superpowers-probe.sh` to stop reading `~/.claude/plugins/installed_plugins.json`: presence is "superpowers skills exposed in the session", version is read best-effort and compared to `compat.yaml` for an advisory warning only (never block), and `installPath` is removed from the output and all callers. File: `guide/scripts/superpowers-probe.sh` (D6, FR-016).
- [x] T006 Make `guide/skills/preflight/SKILL.md` harness-aware: run the `.claude/settings*.json` Excalidraw permission detection and the offer-to-add-entry flow only when `harness == claude`; on other harnesses report `excalidraw` from capability exposure and skip the settings wiring without error; keep the superpowers-absent stop (FR-011) and add a multi-agent-absent stop for create/evolve with a harness-appropriate prerequisite message (FR-017, FR-010). File: `guide/skills/preflight/SKILL.md`.

**Checkpoint**: Detection and orchestration are harness-portable; Claude behavior is unchanged.

---

## Phase 3: User Story 1 - Full command set on Codex (Priority: P1) 🎯 MVP

**Goal**: An author installs cc-guide on Codex and runs create/evolve/preview/export/validate/upstream with behavior equivalent to Claude Code.

**Independent Test**: Install on Codex, run create end to end on a small source repo, then preview/export/evolve --check/validate/upstream; each completes with Claude-equivalent output.

- [x] T007 [P] [US1] Add `guide/.codex-plugin/plugin.json` mirroring `guide/.claude-plugin/plugin.json` (same name/version/description/author/license) with `"skills": "./skills/"`; the version string MUST equal the `.claude-plugin` version. File: `guide/.codex-plugin/plugin.json` (D1, contracts/harness-entry-points.md, FR-001).
- [x] T008 [US1] Audit `create`, `evolve`, `preview`, `export`, `validate`, `upstream` skills so each self-runs `guide:preflight` when its result is not already present and carries no Claude-command-only assumption, so Codex (skills discovered directly, no command wrapper) runs them correctly. Files: `guide/skills/*/SKILL.md` (D1, FR-004).
- [x] T009 [P] [US1] Adapter test: assert the Codex manifest is valid JSON, its version matches `.claude-plugin`, and the six commands are discoverable as skills. File: `tests/adapters/` (new per-harness check) (FR-014, SC-007).
- [x] T010 [US1] Document Codex installation in `README.md` plus the known degradations on Codex (cc-prose -> built-in style rules, Excalidraw -> placeholder diagrams) and the multi-agent prerequisite. File: `README.md` (FR-015).

**Checkpoint**: Codex authors can produce and maintain guides. MVP complete.

---

## Phase 4: User Story 2 - Claude Code unchanged (Priority: P2)

**Goal**: No regression on Claude Code after the foundational refactor.

**Independent Test**: Existing toolkit + adapter assertions pass unchanged; a before/after create-preview-export pass yields equivalent output.

- [x] T011 [US2] Verify `deps.sh` on Claude Code still emits the existing fields (`superpowers`, `prose`, `excalidraw`, `excalidraw_allowed`, `excalidraw_allowed_in`) with the same values as before; the new fields are additive only. Add a focused test. Files: `tests/toolkit/`, `guide/scripts/deps.sh` (FR-012, SC-003).
- [x] T012 [P] [US2] Add Claude Code to the per-harness adapter test dimension and confirm the existing per-format adapter assertions still pass without modification. File: `tests/adapters/` (SC-003, SC-007).
- [x] T013 [US2] Run `make validate` and confirm the Claude `.claude-plugin` manifest and `guide/commands/*.md` wrappers are unchanged in behavior. (FR-012).

**Checkpoint**: Claude Code parity confirmed by tests.

---

## Phase 5: User Story 3 - OpenCode support (Priority: P3)

**Goal**: Install and run the guide commands on OpenCode through the shared adapter (best-effort per FR-019).

**Independent Test**: Run `install.sh`, confirm the commands are present and launch, run create end to end.

- [x] T014 [P] [US3] Add the six OpenCode command shims under `guide/opencode/command/` (`create.md`, `evolve.md`, `preview.md`, `export.md`, `validate.md`, `upstream.md`); each shim only invokes `guide:preflight` then `guide:<name>` with the passed arguments and duplicates no skill logic. Files: `guide/opencode/command/*.md` (D2, contracts/harness-entry-points.md, FR-002, FR-018).
- [x] T015 [US3] Add `guide/opencode/install.sh [--project-dir <path>]` that copies the shims into `<project-dir>/.opencode/plugins/guide/command/`, modeled on `cc-review/review/opencode/install.sh` (without the `.core-path` pointer). File: `guide/opencode/install.sh` (D2, FR-002).
- [x] T016 [P] [US3] Adapter test for OpenCode: run `install.sh --project-dir <tmp>` and assert the six shims land under `.opencode/plugins/guide/command/`. File: `tests/adapters/` (FR-014, SC-007, SC-008).
- [x] T017 [US3] Document OpenCode installation in `README.md` with the same degradation notes. File: `README.md` (FR-015).

**Checkpoint**: All three harnesses discover and launch the commands.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T018 [P] Add a repo-root `AGENTS.md` modeled on cc-review's (session-completion guidance; harness-neutral); do not hand-author any spex-managed Codex block. File: `AGENTS.md` (D7, FR-013).
- [x] T019 [P] Add toolkit tests for the vendored SDD scripts asserting their usage/exit-code contract (no args -> exit 2 with a `usage:` line). File: `tests/toolkit/` (D8).
- [x] T020 Review `guide/scripts/scaffold-project.sh`: confirm whether a guide project gains Codex/OpenCode workspace paths (for example an in-project `.opencode/`); add them to the scaffold `.gitignore` only if evidence shows they appear. File: `guide/scripts/scaffold-project.sh` (D9).
- [x] T021 Execute the `quickstart.md` scenarios A-F as the acceptance pass and record results in the run notes. (SC-001..SC-008).
- [x] T022 [P] Update `README.md` intro and the `make test-adapters` note to state the supported harness set and that the harness checks are additive to the per-format matrix. File: `README.md` (FR-015, FR-019).

---

## Dependencies & Execution Order

- **Setup (Phase 1)**: T001, T002 independent, run first ([P]).
- **Foundational (Phase 2)**: T003 depends on T001 (vendored scripts must exist). T004, T005, T006 all touch detection/preflight; T006 depends on T004 (consumes the detection record). T005 is independent of T004 but both precede any story validation. Foundational BLOCKS all user stories.
- **US1 (Phase 3)**: after Foundational. T007 independent; T008 depends on T003/T006 (skills now harness-portable); T009 depends on T007; T010 after T007/T008.
- **US2 (Phase 4)**: after Foundational. Independent of US1/US3; verifies the refactor did not regress Claude.
- **US3 (Phase 5)**: after Foundational. T015 depends on T014; T016 depends on T015.
- **Polish (Phase 6)**: after the stories it documents/tests; T018, T019, T022 are [P].

## Parallel Opportunities

- T001 and T002 together.
- Within US1: T009 needs T007's file, so T009 starts after T007 and can then run in parallel with T010.
- US1, US2, US3 can proceed in parallel after Foundational (different files).
- T018, T019, T022 together in Polish.

## Implementation Strategy

### MVP first (US1 only)

1. Phase 1 Setup -> Phase 2 Foundational -> Phase 3 US1.
2. STOP and validate: create a guide end to end on Codex (quickstart Scenario B).

### Incremental delivery

1. Foundation ready -> US1 (Codex MVP) -> US2 (Claude regression gate) -> US3 (OpenCode).
2. Each story is independently testable and does not break the others.

## Notes

- [P] = different files, no incomplete-task dependency.
- Keep one shared `skills/`/`toolkit/`; no per-harness behavior fork (FR-018).
- No em/en dashes in any file; `uv` not pip; podman not Docker; never commit `.mcp.json`; scripts use `git -C` for `.guide/cache/`.
- Commit after each task or logical group; commit messages end with `Assisted-By: 🤖 Claude Code`.
