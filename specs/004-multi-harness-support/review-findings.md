# Deep Review Findings

**Date:** 2026-11-06
**Branch:** 004-multi-harness-support
**Rounds:** 1
**Gate Outcome:** PASS
**Invocation:** ship pipeline (review-code, stage 7/8)

## Summary

| Severity | Found | Fixed | Remaining |
|----------|-------|-------|-----------|
| Critical | 0 | 0 | 0 |
| Important | 3 | 1 | 2 (both ambiguous, OpenCode) |
| Minor | 6 | 4 | 2 |
| Notable | 6 | 3 | 3 (informational) |
| **Total** | **15** | **8** | **7** |

**Review agents completed:** 5/6 internal (Goal Alignment skipped, no PR) + 2 external (CodeRabbit, Codex). Copilot disabled in config.
**Test suite:** full toolkit suite passed (exit 0); 39 feature tests pass; all three harness checks pass (Claude 14/0, Codex 17/0, OpenCode 8/0).

## Findings

### FINDING-1 (deps.sh argument-parse hang)
- **Severity:** Minor
- **Confidence:** 84
- **File:** guide/scripts/deps.sh:50-54
- **Category:** correctness
- **Source:** correctness-agent (also reported by: coderabbit)
- **Resolution:** fixed (round 1)

**What is wrong:** The five value-taking flags (`--superpowers`, `--superpowers-version`, `--multi-agent`, `--prose`, `--excalidraw`) read their value with `${2:-}` then unconditionally `shift 2`. When such a flag is the last token, only one positional remains, `shift 2` fails without shifting (no `set -e`), and the `while [[ $# -gt 0 ]]` loop reprocesses the same `$1` forever (confirmed empirically: exit 124 on a trailing bare flag).

**Why this matters:** A direct or scripted invocation with a trailing bare flag hangs with no diagnostic, inconsistent with the sibling flags `--dir`, `--session-dir`, `--harness` which use `${2:?...}`.

**How it was resolved:** Each of the five flags now assigns `${2:?<flag> requires a value}` in the parent shell (so a missing value exits cleanly) before normalizing with `bool`. Verified: a trailing bare `--superpowers` now exits 1 with a clear message; jq and python3 fallbacks still emit identical JSON; all 39 tests pass.

### FINDING-2 (settings.md stale superpowers version)
- **Severity:** Minor
- **Confidence:** 86
- **File:** guide/docs/settings.md:80
- **Category:** architecture (doc consistency, FR-016)
- **Source:** architecture-agent
- **Resolution:** fixed (round 1)

**What is wrong:** The companion-plugins table still listed "superpowers 6.3.0 or later" after the feature replaced the `minimum_version: 6.3.0` / `known_good` list in compat.yaml with a single advisory `known_good_version: 7.0.0`, contradicting README and compat.yaml.

**How it was resolved:** Updated to "superpowers (validated against 7.0.0; an older version warns, never blocks)".

### FINDING-3 (stale probe description)
- **Severity:** Minor
- **Confidence:** 80
- **File:** guide/docs/settings.md:97, guide/docs/learnings.md:77
- **Category:** architecture (doc accuracy)
- **Source:** architecture-agent
- **Resolution:** fixed (round 1)

**What is wrong:** Both docs described superpowers-probe.sh as a "runtime contract probe" that "does not check versions or the scripts cc-guide calls". After the feature the probe does exactly one thing: an advisory version comparison. It no longer reads a registry, verifies presence, or checks `required_scripts` (that key was removed). The "scripts cc-guide calls" phrase was a dead reference to the removed concept.

**How it was resolved:** Reworded both to describe the probe as an advisory version-only warning (never a block) that no longer verifies scripts or presence; presence is decided by capability exposure.

### FINDING-4 (Codex launch path untested)
- **Severity:** Important
- **Confidence:** 74
- **File:** tests/adapters/test_harness_codex.sh
- **Category:** test-quality (FR-010, FR-014, SC-007)
- **Source:** test-quality-agent
- **Resolution:** fixed (round 1)

**What is wrong:** The Codex harness test verified discovery (manifest, version, skills path, name frontmatter) but not launch. Codex has no command layer, so preflight runs on Codex only via each skill's "self-invoke when invoked directly" guard. No test asserted that guard, so deleting it would let Codex run create/evolve with no preflight (no capability detection, no superpowers/multi_agent gate) while all three harness tests still passed. Codex is the primary harness, so its unique launch path was the one left unverified.

**How it was resolved:** Added assertions to test_harness_codex.sh that each of the six command skills self-invokes `guide:preflight`, and that preflight retains the superpowers-absent (FR-011) and multi_agent-absent (FR-017) stop gates. All eight new assertions pass.

### FINDING-5 (python3 heredoc import path)
- **Severity:** Notable
- **Confidence:** 72
- **File:** guide/scripts/deps.sh (python3 fallbacks), guide/scripts/superpowers-probe.sh
- **Category:** security (defense in depth)
- **Source:** security-agent
- **Resolution:** fixed (round 1)

**What is wrong:** The jq-absent fallbacks ran `python3 - <<'PY'` (program from stdin), so `sys.path[0]` was the current working directory and a planted `json.py` could shadow the stdlib. Low exploitability (cwd is the author's own project root), but these scripts read `~/.claude/settings.json`, so the mitigation is worth taking.

**How it was resolved:** All three fallbacks now invoke `python3 -I -` (isolated mode drops cwd and env from the import path). Safe because the scripts use only stdlib json/sys. Both fallbacks still emit correct JSON.

### FINDING-6 (jq/python3 not declared)
- **Severity:** Notable
- **Confidence:** 72
- **File:** guide/scripts/deps.sh, guide/scripts/superpowers-probe.sh, README.md
- **Category:** production-readiness
- **Source:** production-readiness-agent
- **Resolution:** fixed (round 1)

**What is wrong:** The capability-detection scripts need jq (preferred) or python3 (fallback), but neither was declared in the README requirements. If both are absent the scripts emit no JSON and exit non-zero, which preflight would consume as an undiagnosed empty record.

**How it was resolved:** Added jq/python3 to the README "Requirements (every harness)" section, stating jq is preferred, python3 is the fallback, and at least one must be on PATH.

### FINDING-7 (probe exit-3 conflation)
- **Severity:** Notable
- **Confidence:** 72
- **File:** guide/scripts/superpowers-probe.sh:10-13
- **Category:** correctness / doc accuracy
- **Source:** correctness-agent (also reported by: architecture-agent)
- **Resolution:** fixed (round 1, comment only)

**What is wrong:** Exit 3 was documented only as "version below threshold", but the script also exits 3 when compat.yaml is missing (a different condition pushed into the same `problems[]` path). Consumer (preflight) treats exit 3 as an advisory warning either way, so behavior is correct; only the header comment was inaccurate.

**How it was resolved:** Broadened the header comment to state exit 3 means an advisory problem was recorded (version below threshold, or compat.yaml not found). Left the single exit code as is since preflight's handling is correct.

### FINDING-8 (OpenCode command discovery path)
- **Severity:** Important
- **Confidence:** 75 (external)
- **File:** guide/opencode/install.sh:20
- **Category:** external (Codex CLI)
- **Source:** codex
- **Resolution:** not fixed (ambiguous, flagged for live-OpenCode acceptance)

**What is wrong (as reported):** install.sh writes command shims to `<project>/.opencode/plugins/guide/command/`; Codex claims OpenCode discovers project commands under `<project>/.opencode/command/`, so the commands would not be found.

**Why this was not auto-fixed:** The install path is the documented design decision (research.md DECISION R-opencode) and is byte-for-byte the same pattern the spec-designated reference plugin uses: cc-review installs to `.opencode/plugins/cc-review/command/`. The claim contradicts that working reference and cannot be confirmed without a live OpenCode session. OpenCode is explicitly best-effort for v1 (clarification Q2, FR-019) and the live-OpenCode launch acceptance (User Story 3 independent test) is recorded as open in tests/manual/004-multi-harness.md. Relocating away from the reference on an unverified claim risks a regression. Flagged for the open live-OpenCode acceptance.

### FINDING-9 (OpenCode skill discoverability)
- **Severity:** Important
- **Confidence:** 75 (external)
- **File:** guide/opencode/install.sh:23-25, README.md (OpenCode section)
- **Category:** external (Codex CLI)
- **Source:** codex
- **Resolution:** not fixed (ambiguous, flagged for live-OpenCode acceptance)

**What is wrong (as reported):** install.sh copies only command shims. Each shim invokes `guide:preflight` and a `guide:*` skill by name, which requires the guide plugin's skills to be discoverable to OpenCode; the installer does not establish that.

**Why this was not auto-fixed:** Per the spec model (FR-001, FR-002, Assumptions), the plugin is installed through the harness's own plugin mechanism (which registers its skills), with install.sh adding the command shims. The README OpenCode section under-documents the plugin-registration step relative to the Codex section, which is a best-effort doc-completeness nuance within OpenCode's explicitly deferred hardening scope. Verifying the actual OpenCode skill-resolution behavior needs a live session (User Story 3 acceptance, open). Writing authoritative OpenCode internals here without that session risks inaccurate docs. Flagged for the open live-OpenCode acceptance.

## Notable Observations

### NOTABLE-1 (vendored task-brief path input)
- **File:** guide/toolkit/sdd/task-brief:28,31-37
- **Category:** security
- **Source:** security-agent
- **Description:** `task-brief` interpolates the caller-supplied TASK_NUMBER into its default output path with no numeric validation; a value like `../../x` would create/truncate a file outside the workspace.
- **Rationale:** The task number comes from the trusted controller, not an external boundary, and the file is vendored verbatim from superpowers 7.0.0 (changing it would break the verbatim-copy contract of FR-006). Captured for the vendoring note / upstream rather than patched here.

### NOTABLE-2 (Claude hard dependency vs spec edge case)
- **File:** guide/.claude-plugin/plugin.json (dependencies), cross-ref spec.md:70
- **Category:** architecture
- **Source:** architecture-agent
- **Description:** The Claude manifest hard-declares `dependencies: [superpowers@...]`, so on Claude Code the whole plugin fails to load without superpowers, making preview/export/upstream/validate/evolve --check unavailable too. spec.md:70 states those commands "still run" when superpowers is missing. On Codex/OpenCode (no manifest hard dependency) they do run, so superpowers-absent behavior now differs by harness.
- **Rationale:** Pre-existing, documented Claude behavior protected by FR-012 (no regression). Informational; parity with the spec edge case would require making the Claude dependency soft (capability-gated).

## Remaining Findings (not fixed)

| # | Severity (report taxonomy) | File | Note |
|---|---|---|---|
| FINDING-8 | ambiguous | guide/opencode/install.sh:20 | OpenCode command discovery path; matches reference + research.md decision; needs live-OpenCode acceptance |
| FINDING-9 | ambiguous | guide/opencode/install.sh:23-25, README | OpenCode skill discoverability; best-effort scope; needs live-OpenCode acceptance |
| NOTABLE-2 | ambiguous | guide/.claude-plugin/plugin.json | Claude hard-dependency vs spec.md:70 edge case; pre-existing, FR-012-protected |
| A | unambiguous-minor | guide/opencode/command/*.md | Byte-identical to guide/commands/*.md, maintained by hand, no parity test (deliberate per-harness layout) |
| B | unambiguous-minor | tests/toolkit/test_probe.py:27-30 | ge() version compare exercised only on the leading component |
| C | unambiguous-minor | tests/toolkit/test_deps.py:197-211 | Legacy-field value assertion partly vacuous; FR-012 is genuinely covered by the excalidraw-wiring tests |

## Test Suite Results

| Round | Test Command | Exit Code | Status |
|-------|-------------|-----------|--------|
| 1 (post-fix) | pytest tests/toolkit (feature files) | 0 | passed (39) |
| 1 (post-fix) | full toolkit suite | 0 | passed |
| 1 (post-fix) | test_harness_claude/codex/opencode.sh | 0/0/0 | passed (14/17/8) |

Test suite passed after the fix round. No regressions introduced by the fixes.
