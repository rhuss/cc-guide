# Phase 0 Research: Multi-harness support (Codex, OpenCode)

All decisions below reuse the packaging and detection patterns already proven in the sibling cc-review plugin and in superpowers 7.0.0. No NEEDS CLARIFICATION remain.

## D1: Codex entry point

**Decision**: Add `guide/.codex-plugin/plugin.json` mirroring cc-review's, with `"skills": "./skills/"` plus name/version/description/author/license. Codex discovers the skills directly. No Codex-specific command layer is added: cc-guide's `create`/`evolve`/etc. skills already invoke `guide:preflight` themselves when their result is not already in the conversation (observed in `guide/skills/create/SKILL.md`), so invoking the skill directly on Codex runs preflight first exactly as the Claude command wrapper would.

**Rationale**: Smallest possible surface; identical to how cc-review and superpowers expose skills to Codex. One shared `skills/` directory, no fork.

**Alternatives considered**: A Codex-specific command wrapper layer (rejected: Codex consumes skills, not Claude slash commands; the skills are already self-sufficient).

## D2: OpenCode entry point

**Decision**: Add `guide/opencode/command/*.md` (six shims: create, evolve, preview, export, validate, upstream) and `guide/opencode/install.sh`, modeled on `cc-review/review/opencode/`. Each shim mirrors the matching Claude command wrapper: "invoke the `guide:preflight` skill with these args and stop if it stops, then invoke the `guide:<name>` skill with the same args." `install.sh` copies the shims into `<project>/.opencode/plugins/guide/command/`.

**Rationale**: cc-review's install.sh pattern is the established template. cc-guide needs no `.core-path` pointer (unlike cc-review) because cc-guide's logic lives in the skills, not a separate `core/`; the shims only chain preflight + skill.

**Alternatives considered**: Duplicating skill logic into OpenCode command files (rejected: violates FR-018, creates drift). Pointer-to-core like cc-review (rejected: cc-guide has no `core/`).

## D3: Vendoring the SDD helper scripts

**Decision**: Copy the three portable superpowers scripts (`sdd-workspace`, `task-brief`, `review-package`) into `guide/toolkit/sdd/`. Change `create` and `evolve` to call these vendored copies (resolved relative to the plugin/toolkit, as the other toolkit scripts are) and to invoke superpowers skills (brainstorming, writing-plans, subagent-driven-development, requesting-code-review) by name only. Remove all use of the superpowers `installPath`.

**Rationale**: The scripts are plain bash doing git/file plumbing with no Claude-specific logic (verified), so vendoring is safe and removes the only hard dependency on a Claude-registry-resolved path. The scaffold already copies `guide/toolkit/` into guide projects as `tools/guide/`, so the vendored scripts travel with the project for CI too.

**Alternatives considered**: Teaching the probe each harness's plugin layout to locate superpowers' scripts in place (rejected in the brainstorm as brittle and cross-plugin). Keeping the scripts only in superpowers and shelling to a resolved skill path (rejected: no stable cross-harness path).

**Sync obligation**: Record the upstream superpowers version the scripts were copied from; add a maintainer note so they can be refreshed if superpowers changes them. (Surface in tasks.)

## D4: Capability detection (FR-007, FR-017)

**Decision**: Replace registry/settings reads with in-session capability exposure:
- **superpowers present**: its skills are available in the session (for example the brainstorming / subagent-driven-development skills appear in the skill list).
- **cc-prose present**: the `prose:humanizer` skill is available (the method cc-review uses).
- **Excalidraw present**: `mcp__excalidraw__*` tools are available.
- **multi-agent capability (FR-017)**: the harness exposes its subagent/parallel-dispatch tools (Claude Code Agent/Task tool; Codex multi-agent spawn/wait tools).

`deps.sh` emits a JSON record of these booleans. The controller/skills read the booleans; they no longer read `~/.claude/plugins/installed_plugins.json`.

**Rationale**: Capability exposure is the only signal available uniformly across harnesses and is already the cc-review approach. It is also correct: a dependency that is installed but not exposed in the session cannot be used anyway.

**Alternatives considered**: Per-harness registry/config parsing (rejected: brittle, N implementations, and installed-but-not-exposed false positives).

## D5: Preflight harness-awareness (FR-010)

**Decision**: `preflight` detects the active harness and runs the Claude-only `.claude/settings*.json` permission wiring (the Excalidraw allow-entry detection and the offer to add it) only on Claude Code. On Codex/OpenCode it reports Excalidraw tool presence/absence from capability exposure and skips the settings wiring without error; if Excalidraw is absent, diagram tasks use the placeholder path (FR-009). Preflight still blocks create/evolve when superpowers is absent (FR-011) and when the multi-agent capability is absent (FR-017), with harness-appropriate messages.

**Rationale**: The settings/permission model is Claude-specific; other harnesses manage permissions differently and need no file wiring for v1 (Excalidraw-on-Codex permission wiring is an explicit out-of-scope follow-up per the spec).

**Harness detection**: derive from capability exposure and environment rather than a brittle single signal; record the chosen method in the contract. (Detail deferred to implementation; the branch points are: "is this Claude Code" gating the settings wiring.)

## D6: superpowers-probe.sh and compat.yaml (FR-016)

**Decision**: `superpowers-probe.sh` stops reading the Claude plugin registry. Presence becomes "are superpowers skills exposed" (hard requirement). `compat.yaml` keeps a single recorded minimum/known-good version threshold used only for an **advisory** warning (unknown version, or a version below the recorded threshold); it never blocks. `installPath` is removed from the probe output and from create/evolve (they call vendored scripts and invoke skills by name).

**Rationale**: Matches FR-005, FR-007, FR-016. Keeps a useful compatibility warning without a Claude-only mechanism.

**Open implementation detail**: where the harness/superpowers version string comes from when no registry is read (may be best-effort or omitted on harnesses that do not expose it); advisory-only means a missing version simply skips the warning.

## D7: AGENTS.md (FR-013)

**Decision**: Add a repo-root `AGENTS.md` modeled on cc-review's: session-completion guidance and any cc-guide-specific agent notes. Keep it generic and harness-neutral; do not include a spex-managed Codex block unless spex manages this repo (it does here, but the block is managed by `.specify/spex.json`, so leave that to the spex tooling rather than hand-authoring it).

**Rationale**: AGENTS.md-based harnesses read it; cc-review is the template.

## D8: Adapter tests (FR-014, SC-007)

**Decision**: Extend `tests/adapters/` with a per-harness dimension that asserts each supported harness can discover the commands and launch them (manifest validity for Claude and Codex, shim install + presence for OpenCode). Add toolkit tests for the vendored SDD scripts (usage/exit-code contract) and for the detection logic in `deps.sh`.

**Rationale**: SC-007 requires the suite to fail if any harness loses discovery/launch. The existing per-format matrix gains a harness axis; the new checks are additive (SC-003).

## D9: Scaffold and .gitignore (open question from spec)

**Decision**: The guide-project scaffold continues to ignore `.guide/`, `.superpowers/`, `node_modules/`, `build/`, `dist/`. Add Codex/OpenCode workspace entries only if those harnesses write workspace state into the guide project (for example an `.opencode/` plugins dir created by install.sh inside a guide project). Confirm during implementation whether any such paths appear in a guide project; if yes, add them to the scaffold `.gitignore`.

**Rationale**: Keep `.gitignore` minimal and evidence-based; do not add speculative entries.
