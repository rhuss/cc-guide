---
runbook_version: 1
feature: 004-multi-harness-support
status: drafted
mode: light
steps_total: 5
step_results: pending,pending,pending,pending,pending
drafted_at: 4803f8c
drafted_fingerprint: b7ee14ebf410ee0579016e771b6b08b53f5154eb8fba196bc4792f9d2e73ab20
tested_at:
tested_fingerprint:
updated: 2026-11-06
---

# Try it: Multi-harness support (Codex, OpenCode)

<!-- runbook-status -->
> **Status:** drafted · 0 of 5 steps · Mode: light · Drafted at 4803f8c · 2026-11-06
<!-- /runbook-status -->

## What you're testing

That the plugin now carries working entry points for Codex and OpenCode beside Claude Code, that dependency detection and the vendored SDD scripts work, and that Claude Code did not regress. The journey runs the local, no-network checks in order: toolkit tests, Claude manifest validation, the Codex manifest, the three per-harness discovery checks, and the vendored SDD script contract. Live end-to-end runs on real Codex and OpenCode sessions are listed under "Not covered here".

## Test environment

No fixtures. Every step is a local command run from the worktree root; no services are started. Requires `uv`, `git`, Node 20+, `jq`, and (for `make test-adapters` style checks) `npx`, `pandoc`, and Playwright Chromium already installed, as the repository README documents.

## Steps

### Step 1 of 5: Toolkit tests pass, including detection and SDD tests (US2)

**Why this step:** The toolkit suite is the no-regression gate (FR-012) and now also covers the new capability detection (`test_deps.py`) and the vendored SDD scripts (`test_sdd_scripts.py`), so one run exercises both the old behavior and the new code.

**Needs:** nothing.

**Run:**

```
make test
```

**What you should see:** the suite passes with exit code 0 (about 739 tests passing), including the detection and SDD-script tests.

**If you see something else:** a failure in `test_deps.py` points at the detection refactor; a failure in an existing toolkit test points at a regression that must be fixed before shipping.

**Result:**

### Step 2 of 5: Claude plugin still validates (US2)

**Why this step:** Confirms the Claude Code manifest and command wrappers are still valid after the refactor, which is the core no-regression promise for the primary existing user base.

**Needs:** nothing.

**Run:**

```
make validate
```

**What you should see:** validation passes. A single pre-existing, unrelated `ICON_MISSING` warning is expected and does not fail the run.

**If you see something else:** a new validation error naming `guide/.claude-plugin/` or `guide/commands/` means the Claude entry point changed and must be restored.

### Step 3 of 5: Codex manifest is valid and version-matched (US1)

**Why this step:** Codex is the primary new harness. Its manifest must point at the shared skills and carry the same version as the Claude manifest, or the two entry points drift.

**Needs:** nothing.

**Run:**

```
jq -e '.skills == "./skills/"' guide/.codex-plugin/plugin.json && test "$(jq -r .version guide/.codex-plugin/plugin.json)" = "$(jq -r .version guide/.claude-plugin/plugin.json)" && echo VERSIONS_MATCH
```

**What you should see:** `true` printed by `jq -e`, then `VERSIONS_MATCH`.

**If you see something else:** no output or a non-zero exit means either the `skills` pointer is wrong or the Codex and Claude versions differ; align them.

### Step 4 of 5: All three harnesses discover and launch the commands (US1, US2, US3)

**Why this step:** This is the per-harness adapter dimension (FR-014, SC-007): each check asserts its harness can discover and launch the six guide commands. Running all three proves the one plugin directory serves every supported harness.

**Needs:** Steps 2 and 3 (the manifests they check must be valid).

**Run:**

```
bash tests/adapters/test_harness_claude.sh && bash tests/adapters/test_harness_codex.sh && bash tests/adapters/test_harness_opencode.sh
```

**What you should see:** each script prints its pass tally (Claude 14/0, Codex 17/0, OpenCode 8/0) and the combined command exits 0.

**If you see something else:** a non-zero exit names the harness that can no longer discover or launch the commands; read that script's failing assertion.

### Step 5 of 5: Vendored SDD scripts enforce their usage contract (US1)

**Why this step:** create and evolve now call the vendored `guide/toolkit/sdd/` scripts instead of reaching into the superpowers install path (FR-006). Their usage/exit-code contract confirms the vendored copies are present and executable.

**Needs:** nothing.

**Run:**

```
bash guide/toolkit/sdd/task-brief; echo "exit=$?"
```

**What you should see:** a line beginning `usage:` on stderr and `exit=2` (the no-argument usage contract).

**If you see something else:** a missing-file error means the vendoring (T001) did not land; a different exit code means the script was altered away from its upstream contract.

**Result:**

## Not covered here

These need a real Codex or OpenCode session with superpowers installed, which this environment does not have:

- Live Codex end-to-end `create` and the other commands on a small source repo (quickstart Scenario B, SC-001, SC-002).
- Codex degradations: `create` without cc-prose (built-in style rules) and without the Excalidraw tools (placeholder diagrams) (Scenario C, SC-005).
- The superpowers-absent and multi-agent-absent stop gates on a real non-Claude session (Scenario D, SC-006, FR-011, FR-017).
- Live OpenCode run after `install.sh` (Scenario E, SC-008), including the open question of whether OpenCode resolves the `guide:*` skills the shims invoke (filed to the idea inbox).

## Coverage

- **US1 (Codex)**: partially covered here. The Codex manifest, cross-harness discovery, detection, and the vendored SDD scripts are verified locally; a live Codex create/evolve run is deferred (see above).
- **US2 (Claude no-regression)**: fully covered by Steps 1, 2, and 4.
- **US3 (OpenCode)**: partially covered. The installer and shim presence are verified by Step 4; a live OpenCode run and skill-resolution check are deferred.

## Results
