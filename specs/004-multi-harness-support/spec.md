# Feature Specification: Multi-harness support (Codex, OpenCode)

**Feature Branch**: `004-multi-harness-support`

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "Support the full cc-guide command set on Codex (primary) and OpenCode (secondary), the way the sibling cc-review plugin already supports Claude Code, Codex, and OpenCode from one plugin directory. Reuse superpowers (already multi-harness) for orchestration, vendor the portable SDD helper scripts, detect dependencies by capability exposure rather than by reading a Claude plugin registry, and fall back to built-in behavior for the two optional Claude-bound capabilities (cc-prose voice profiles and Excalidraw diagrams)."

## Clarifications

### Session 2026-11-06

- Q: Which harnesses must v1 support? → A: Exactly Claude Code, Codex, and OpenCode. Other harnesses that superpowers supports (Cursor, Devin, Gemini, etc.) are out of scope for v1, though the packaging should not preclude adding them later.
- Q: What level of OpenCode support does v1 require? → A: Best-effort on the same shared adapter as Codex (install path plus command discovery and launch); no separate hardening or dedicated test matrix beyond what the shared adapter provides.
- Q: How is the superpowers version contract enforced without the Claude plugin registry? → A: Presence is required (create/evolve stop if superpowers is absent); the known-good and minimum version check is advisory only (warn on an unknown or below-known-good version, do not block).
- Q: When the active harness lacks the parallel subagent (multi-agent) capability that per-page writing and review need, what do create/evolve do? → A: Stop with a prerequisite message. There is no sequential single-agent fallback in v1.
- Q: Does "behavior equivalent to Claude Code" on Codex include diagram and prose-polish parity? → A: No. Prose polish (cc-prose) and Excalidraw diagrams fall back to built-in style rules and placeholder diagrams respectively on non-Claude harnesses; equivalence covers the authoring and verification flow, not these two optional capabilities.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Author runs the full guide command set on Codex (Priority: P1)

An author working inside Codex installs cc-guide through Codex's own plugin mechanism and runs the complete set of guide commands (`create`, `evolve`, `preview`, `export`, `validate`, `upstream`) against their source repositories and notes. A guide is created, previewed, exported, validated, and kept current, with the same page-by-page writing and per-page source verification an author gets on Claude Code.

**Why this priority**: This is the whole point of the feature and the primary harness the user asked for. Delivering only this story already lets Codex authors produce and maintain guides, which is a complete, valuable slice on its own.

**Independent Test**: Install cc-guide on Codex, run `create` end to end on a small source repository, then run `preview`, `export`, `evolve --check`, `validate` (read-only), and `upstream` and confirm each produces the same class of output it produces on Claude Code.

**Acceptance Scenarios**:

1. **Given** cc-guide installed on Codex and superpowers installed on Codex, **When** the author runs the create command with sources and a guide description, **Then** the command interviews, scaffolds, plans, writes pages with per-page source verification, runs the final review, and produces a guide project, without the author taking any Claude-Code-specific setup step.
2. **Given** a guide project created on Codex, **When** the author runs preview, export, validate (read-only), evolve, and upstream, **Then** each command runs to completion with output equivalent to Claude Code.
3. **Given** cc-guide installed on Codex, **When** the author lists or invokes the guide commands, **Then** the same command names available on Claude Code are available and launch the same behavior.

---

### User Story 2 - Existing Claude Code behavior is unchanged (Priority: P2)

An author who already uses cc-guide on Claude Code upgrades to the version that adds multi-harness support and sees no change: every command behaves exactly as before, including the superpowers-driven orchestration, cc-prose voice profiles when installed, the Excalidraw diagram flow, and the preflight permission wiring.

**Why this priority**: The current user base is on Claude Code. Adding harnesses must not regress the existing, working experience. It is P2 because it is a constraint on the P1 work rather than new user value, but a regression here would be unacceptable.

**Independent Test**: On Claude Code, run the existing adapter and toolkit test suites plus a create/preview/export pass on a sample guide before and after the change and confirm identical behavior and output.

**Acceptance Scenarios**:

1. **Given** cc-guide on Claude Code with superpowers, cc-prose, and the Excalidraw server all present, **When** the author runs any guide command, **Then** behavior and output match the pre-feature baseline.
2. **Given** cc-guide on Claude Code, **When** preflight runs, **Then** it still performs the Claude settings and permission checks exactly as before.

---

### User Story 3 - Author runs the guide command set on OpenCode (Priority: P3)

An author working in OpenCode installs cc-guide using the OpenCode install path and runs the guide commands, getting the same guide-authoring behavior through the shared adapter.

**Why this priority**: OpenCode is the secondary harness the user named as less important. It rides on the same adapter as Codex, so it is valuable but lower priority and acceptable to deliver as best-effort in v1.

**Independent Test**: Install cc-guide on OpenCode, confirm the guide commands are discoverable and launch, and run create end to end on a small source repository.

**Acceptance Scenarios**:

1. **Given** cc-guide installed on OpenCode and superpowers installed on OpenCode, **When** the author invokes a guide command, **Then** the command launches and runs through the shared skill logic without per-harness behavior forks.

---

### Edge Cases

- **superpowers missing on the active harness**: create and evolve stop before writing anything and tell the author how to install superpowers for that specific harness; preview, export, and validate (which do not need superpowers) still run.
- **cc-prose absent (for example on Codex today)**: pages are written with the built-in style rules; no error, and the degradation is stated to the author.
- **Excalidraw tools absent**: diagram tasks fall back to the existing placeholder path; the run continues and names the missing diagrams.
- **Harness without parallel subagent support available/enabled**: because per-page writing and review rely on the harness's multi-agent dispatch, create/evolve detect the missing capability and stop with a clear prerequisite message rather than silently producing an unreviewed guide.
- **Wrong manifest read by a harness**: each harness reads only its own entry point; the presence of other harnesses' manifests in the same plugin directory never changes behavior.
- **A command that touches Claude-only settings on a non-Claude harness**: the Claude-only permission wiring is skipped without error, and no `.claude/settings*.json` file is required to exist.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The plugin MUST be installable on Codex through Codex's own plugin mechanism and expose the same `/guide:*` command set available on Claude Code.
- **FR-002**: The plugin MUST be installable on OpenCode through OpenCode's own mechanism and expose the same command set.
- **FR-003**: A single plugin directory MUST serve all supported harnesses; each harness MUST read only its own manifest or entry point and ignore the others.
- **FR-004**: On Codex, all six commands (create, evolve, preview, export, validate, upstream) MUST run to completion with behavior equivalent to Claude Code, except for the documented degradations of optional capabilities (cc-prose and Excalidraw).
- **FR-005**: The create and evolve flows MUST obtain orchestration by invoking superpowers skills by name and MUST NOT depend on reading a Claude plugin registry or a fixed filesystem install path to locate superpowers.
- **FR-006**: cc-guide MUST provide its own copies of the subagent-driven-development helper scripts (workspace resolution, task brief extraction, review package generation) so create/evolve never read or execute files inside another plugin's install directory.
- **FR-007**: Presence of each dependency MUST be detected by capability exposure in the current session: superpowers by the availability of its skills, cc-prose by the availability of its `prose:humanizer` skill, and Excalidraw by the availability of its `mcp__excalidraw__*` tools; detection MUST NOT rely on reading harness-specific registry or settings files.
- **FR-008**: When cc-prose is not available on the active harness, pages MUST be written using cc-guide's built-in style rules, preserving today's prose-absent behavior.
- **FR-009**: When the Excalidraw tools are not available on the active harness, diagram tasks MUST use the existing placeholder path and the run MUST continue.
- **FR-010**: Preflight MUST run on every supported harness and MUST perform Claude-only settings and permission wiring only on Claude Code, skipping it on other harnesses without error.
- **FR-011**: When superpowers is not available on the active harness, create and evolve MUST stop before writing guide content and MUST present a harness-appropriate message explaining how to install superpowers for that harness.
- **FR-012**: Claude Code behavior MUST remain unchanged across all commands relative to the pre-feature baseline (no regression).
- **FR-013**: The repository MUST provide an `AGENTS.md` with agent instructions for AGENTS.md-based harnesses.
- **FR-014**: The automated adapter test suite MUST verify, for each supported harness, that the guide commands are discoverable and can launch, as a harness dimension alongside the existing per-format adapter smoke tests.
- **FR-015**: Installation and usage documentation MUST describe how to install cc-guide on each supported harness and MUST state the known degradations on non-Claude harnesses (cc-prose and Excalidraw fall back).
- **FR-016**: The superpowers compatibility expectation MUST be expressed so that it works without the Claude plugin registry. Presence is a hard requirement (create/evolve stop when superpowers is absent, per FR-011); the recorded minimum (known-good) version check is advisory only (it warns when superpowers reports an unknown version or a version below that recorded threshold, and never blocks), with consistent messaging across harnesses.
- **FR-017**: create and evolve MUST detect the absence of the harness's parallel subagent (multi-agent) capability that per-page writing and review require, and MUST stop with a clear prerequisite message rather than produce an unreviewed guide. Detection MUST follow the same capability-exposure approach as FR-007: the capability is considered present when the active session exposes the harness's multi-agent dispatch tools (for example the subagent/Agent dispatch tool on Claude Code, or the multi-agent spawn/wait tools on Codex), not by reading a harness-specific config or registry file.
- **FR-018**: No behavior fork per harness may exist in the shared skills or toolkit; harness differences MUST be confined to the thin per-harness entry points and to capability-presence branches (Claude-only wiring, optional-dependency fallbacks).
- **FR-019**: The supported harness set for v1 MUST be exactly Claude Code, Codex, and OpenCode. Additional harnesses are out of scope for v1, and the packaging MUST NOT be structured in a way that precludes adding them later. OpenCode is delivered as best-effort on the shared adapter (install, command discovery, and launch) without a dedicated hardening pass beyond Codex parity.

### Key Entities *(include if feature involves data)*

- **Harness entry point**: the per-harness manifest or installer (Claude Code, Codex, OpenCode) that makes the shared commands discoverable on that harness. Each points at the same shared skills; none changes behavior.
- **Capability signal**: an observed, in-session indicator that a dependency is present (a superpowers skill is available, the `prose:humanizer` skill is available, the `mcp__excalidraw__*` tools are available). Replaces registry/path lookups.
- **Vendored SDD helper scripts**: cc-guide's own copies of the workspace, task-brief, and review-package scripts, invoked by create/evolve in place of another plugin's installed scripts.
- **AGENTS.md**: repository-level agent instructions consumed by AGENTS.md-based harnesses.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An author can create a guide end to end on Codex without performing any Claude-Code-specific setup step.
- **SC-002**: All six guide commands run to completion on Codex on a representative sample guide, with output of the same kind and structure as on Claude Code.
- **SC-003**: The existing Claude Code behavior is unchanged: the current toolkit and adapter test suite assertions still pass unchanged (the new per-harness checks from FR-014 are additive), and a before/after create-preview-export pass on a sample guide yields equivalent results.
- **SC-004**: Dependency detection returns the correct present/absent result for superpowers, cc-prose, and Excalidraw on every supported harness without reading any harness-specific registry or settings file.
- **SC-005**: With cc-prose absent, a guide is still produced using built-in style rules; with Excalidraw absent, a guide is still produced with placeholder diagrams; neither absence aborts the run.
- **SC-006**: When superpowers is absent on the active harness, create and evolve stop and emit an install message naming that harness, and leave no partial guide content behind.
- **SC-007**: The adapter test suite exercises every supported harness and fails if any harness can no longer discover or launch the guide commands.
- **SC-008**: An author can install cc-guide on OpenCode and launch the guide commands through the shared adapter.

## Assumptions

- **Orchestration is reused, not reimplemented**: superpowers is already multi-harness (it ships Codex and OpenCode entry points and harness tool references), so create/evolve rely on it being installed for the active harness rather than cc-guide re-creating brainstorming, planning, and subagent-driven development.
- **cc-prose port is out of scope here**: cc-prose remains Claude Code only for now; its multi-harness port is tracked separately in the cc-prose repository. On other harnesses cc-guide uses the built-in style-rules fallback. Prose polish (named voice profiles, the AI-pattern gate) is therefore degraded on Codex until that separate port lands.
- **Excalidraw permission wiring for Codex is out of scope here**: diagrams rely on the existing placeholder fallback on non-Claude harnesses; wiring the Excalidraw MCP permission model for Codex is a separate follow-up. Diagram authoring is therefore degraded on Codex until that follow-up lands.
- **Codex is primary, OpenCode is secondary**: OpenCode is delivered on the same shared adapter and is acceptable as best-effort in v1 (install path plus command discovery and launch), without separate hardening beyond what the shared adapter provides.
- **Parallel subagent support is a prerequisite on non-Claude harnesses**: per-page writing and review require the harness's multi-agent dispatch (for example Codex with multi-agent features enabled), consistent with how superpowers documents Codex subagent dispatch. cc-guide documents this prerequisite and detects its absence.
- **Capability detection is the uniform contract**: consumers and preflight decide dependency presence from in-session capability exposure, the same method the sibling cc-review plugin uses, rather than from a Claude plugin registry.
- **No new output formats or guide behaviors**: this feature changes packaging, dependency resolution, and preflight portability only; the guide-authoring behavior and output formats are unchanged.
- **Reference implementations exist**: the sibling cc-review plugin and superpowers provide the packaging templates (per-harness manifests, OpenCode installer, AGENTS.md) this feature follows.
