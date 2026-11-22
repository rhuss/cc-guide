# Deep Review Findings

**Date:** 2026-11-22
**Branch:** 008-captured-visuals
**Rounds:** 1
**Gate Outcome:** PASS
**Invocation:** quality-gate (ship pipeline, ask level never)

## Summary

| Severity | Found | Fixed | Remaining |
|----------|-------|-------|-----------|
| Critical | 1 | 0 (rejected: false positive) | 0 |
| Important | 22 | 22 | 0 |
| Minor | 23 | 9 | 14 |
| Notable | 4 | - | 4 |
| **Total** | **50** | **31** | **18** |

**Agents completed:** 5/5 internal (Goal Alignment skipped: no PR for the branch) + 2 external tools (CodeRabbit, Codex). Copilot disabled in config.
**Agents failed:** none

Test suite after the fix round: `make test` 1289 passed, 1 skipped (the host emoji font test; the emoji path now runs in the podman smoke test). `bash tests/adapters/test_visuals.sh` (podman 6.2.0, linux/arm64): 36 of 36 checks pass.

## Findings

### FINDING-1 (Critical, rejected)
- **File:** guide/toolkit/capture/web.py (screenshot call)
- **Source:** codex
- **Resolution:** rejected (false positive)

**What was claimed:** Playwright rejects `full_page=True` together with `clip`, so every web capture fails.

**Why it is not a defect:** Playwright applies `clip` to the full page rectangle when both are given. The podman smoke test captures the cropped `table` visual through exactly this call, writes `table.png`, and runs two drift rounds without drift.

### FINDING-2 (Important, fixed)
- **File:** guide/toolkit/visuals.py (`ensure_image`, `cmd_drift`)
- **Source:** architecture agent (also correctness agent, CodeRabbit)

**What was wrong:** The "building the capture environment" progress line went to stdout before the report, so `drift --format json` printed text that is not JSON on every first run and after every toolkit refresh. The evolve skill parses that output.

**How it was resolved:** `Run` has a `log` callable (stderr by default) for progress. In JSON mode, `cmd_drift` sends errors and "no visuals declared" to stderr and prints an empty JSON report when no recipe exists. Tests: `test_drift_json_stdout_is_json_when_the_image_is_built`, `test_drift_json_without_recipe`.

### FINDING-3 (Important, fixed)
- **File:** guide/toolkit/visuals.py (`create_network`, `start_capture`, `start_environment`)
- **Source:** production readiness agent

**What was wrong:** A container or the network was recorded for teardown only after `podman run`/`network create` returned 0. A container that podman created but could not start, or a call cut short by an interrupt, stayed behind (SC-006).

**How it was resolved:** Names are recorded before each call, and teardown uses `rm -f`, so a missing resource does no harm. Teardown now reports which names it could not remove, and the interrupt message names them. Tests: `test_container_that_fails_to_start_is_still_removed`, `test_network_recorded_before_create_fails`.

### FINDING-4 (Important, fixed)
- **File:** guide/toolkit/visuals.py (`execute`)
- **Source:** production readiness agent (also correctness agent)

**What was wrong:** The handler that turns SIGINT/SIGTERM into `KeyboardInterrupt` stayed installed during teardown, so a second Ctrl-C or a CI cancel cut the cleanup short.

**How it was resolved:** Both signals are ignored for the duration of teardown and scratch cleanup, then the previous handlers are restored. Test: `test_teardown_ignores_a_second_interrupt` sends a real SIGINT during each `rm`.

### FINDING-5 (Important, fixed)
- **File:** guide/toolkit/visuals.py (podman calls)
- **Source:** production readiness agent

**What was wrong:** Seed steps, pulls, builds, logs, render, diff, sweep, and teardown called podman without a timeout. A blocking seed command hung the run and held the lock.

**How it was resolved:** `Run.pod()` gives every call a timeout (60 s for short calls, 300 s for render and diff, 600 s for seed steps, 900 s for pulls, 1800 s for the build) and turns a timeout into exit status 124. The existing failure paths then report the step, for example "seed step 2 ... timed out". Tests: `test_podman_timeout_fails_the_environment_not_the_run`, `test_timeouts_are_passed_to_podman`.

### FINDING-6 (Important, fixed)
- **File:** guide/toolkit/capture/web.py (`COLLECT_JS`)
- **Source:** security agent (also CodeRabbit, twice)

**What was wrong:** The page text collector walked only `document.body` with a TreeWalker. Text in open shadow roots and same-origin iframes, and the `aria-valuetext`/`aria-description` attributes, were never redacted, but the ARIA snapshot and the screenshot showed them (FR-021).

**How it was resolved:** The collector visits the document, every open shadow root, and every reachable iframe document, and collects the two extra attributes. Tests: `tests/toolkit/test_web_redaction.py`.

### FINDING-7 (Important, fixed)
- **File:** guide/toolkit/capture/web.py (`capture`)
- **Source:** security agent

**What was wrong:** Redaction ran once. Afterwards the run scrolled to highlights and the crop and measured boxes, while timers, re-renders, and lazy loading could add new text that reached the PNG unredacted.

**How it was resolved:** All scrolling now happens first, then redaction, then the measurements. A second redaction pass runs right before the screenshot, and its counts are merged into the record.

### FINDING-8 (Important, fixed)
- **File:** guide/toolkit/visuals.py (`_failure_outcome`, `DriftRun.failure`, `render_cli`)
- **Source:** security agent (also CodeRabbit)

**What was wrong:** Seed output, container log tails, and build and render errors went unredacted into the console summary, `report.md`, `report.json`, and the CI job summary.

**How it was resolved:** Every failure detail passes through the visual's effective redaction rules and masks (`Run.safe`) before an outcome or drift result is built. Test: `test_failure_details_are_redacted`.

### FINDING-9 (Important, fixed)
- **File:** guide/toolkit/visuals.py (`create_network`)
- **Source:** security agent

**What was wrong:** The run network had outbound access, so tool images and pages could reach the internet and the author's network, against FR-010.

**How it was resolved:** The network is created with `--internal`. Images are pulled on the host before the run. The podman smoke test passes on the internal network, so DNS by environment name and readiness still work. Test: `test_run_network_is_internal`.

### FINDING-10 (Important, fixed)
- **File:** guide/toolkit/check.py (Markdown link rules)
- **Source:** codex

**What was wrong:** A page embedding a placeholder visual (FR-031a) passed the `visuals` rule but failed `broken-link`, so the documented placeholder flow could not pass `make check`.

**How it was resolved:** `placeholder_images()` lists the images of placeholder sidecars, and both Markdown link checks skip them. A missing image of a captured visual stays an error. Test: `test_visuals_embedded_placeholder_is_not_a_broken_link` (three formats).

### FINDING-11 (Important, fixed)
- **File:** guide/toolkit/check.py (`check_visuals`)
- **Source:** codex

**What was wrong:** `table-dark.png` was accepted with only `visual:table` cited, so dark-variant claims were not tied to the dark sidecar (FR-023, FR-026).

**How it was resolved:** An embedded image needs a citation of its own output name, so the dark image needs `visual:table-dark`. Test: `test_visuals_dark_image_needs_dark_citation` (three formats).

### FINDING-12 (Important, fixed)
- **File:** guide/toolkit/visuals.py (`sweep`)
- **Source:** codex (also security agent)

**What was wrong:** A run killed before its cleanup left `job.json` (resolved host values) and `raw/` (unredacted CLI output) in `.guide/visuals/<run-id>/` indefinitely.

**How it was resolved:** Under the lock, `sweep_scratch()` deletes `job.json` and `raw/` of every earlier run directory and keeps the ten newest run directories. `job.json` is written with mode 0600. Tests: `test_sweep_removes_host_values_of_dead_runs_and_prunes`, `test_job_file_is_private`.

### FINDING-13 (Important, fixed)
- **File:** guide/toolkit/visuals.py (`DriftRun.compare`)
- **Source:** CodeRabbit (also correctness and test quality agents)

**What was wrong:** When the image comparison failed, `image_diff` returned `None` and the web visual was reported "unchanged" (FR-027).

**How it was resolved:** A failed comparison is reported as `recapture-failed` with "image comparison failed", which counts as drift (exit 10). Tests: `test_drift_failed_image_comparison_is_not_unchanged`, `test_drift_missing_committed_image_drifts`, `test_drift_placeholder_sidecar_drifts`.

### FINDING-14 (Important, fixed)
- **File:** guide/skills/evolve/SKILL.md (section 1)
- **Source:** CodeRabbit

**What was wrong:** On direct invocation, the skill forwarded only `--check` or `--pages` to preflight, so `--visuals` stopped on missing superpowers.

**How it was resolved:** `--visuals` is forwarded as well.

### FINDING-15 (Important, fixed)
- **File:** guide/toolkit/capture/render_cli.py (`logical_lines`)
- **Source:** CodeRabbit

**What was wrong:** A line longer than the 4096-column logical screen wrapped inside pyte, so a secret split at the wrap escaped redaction. Output beyond 20000 rows also scrolled off silently.

**How it was resolved:** A row filled to the edge is joined with its soft-wrapped rest before redaction. The screen height accounts for soft wraps, and output beyond `MAX_ROWS` fails the visual instead of losing lines. Tests: `test_soft_wrapped_secret_is_redacted`, `test_too_many_lines_fail`.

### FINDING-16 (Important, fixed)
- **File:** guide/toolkit/capture/redact.py (`api-key` rule)
- **Source:** CodeRabbit

**What was wrong:** `"password": "..."` and other quoted keys were not matched.

**How it was resolved:** The key may be closed by a quote before the separator. `token` joins the key list. Test: `test_quoted_keys_and_more_token_shapes`.

### FINDING-17 (Important, fixed)
- **File:** guide/toolkit/capture/web.py, guide/toolkit/capture/redact.py
- **Source:** CodeRabbit

**What was wrong:** A value split across inline elements (`<span>/home/</span><b>alice</b>`) was redacted node by node and never matched.

**How it was resolved:** Text nodes carry the id of their nearest block-level ancestor. Consecutive nodes of one block are redacted as one text by `redact.apply_segments`, and each replacement is mapped back to the nodes. Tests: `test_segments_*` in test_redact.py and test_web_redaction.py. The smoke test checks "Runs in /home/user/runs on example-host" from a split caption.

### FINDING-18 (Important, fixed)
- **File:** guide/toolkit/capture/web.py (highlight and crop steps)
- **Source:** CodeRabbit

**What was wrong:** A `text=` selector of a highlight or crop no longer matched once redaction changed that text, so the later scroll or snapshot timed out.

**How it was resolved:** Each step tags its element with `data-ccg-mark` and keeps a locator for the mark, not the selector.

### FINDING-19 to FINDING-23 (Important, fixed; test quality)
- **Files:** tests/adapters/test_visuals.sh, tests/adapters/fixtures/visuals/, tests/toolkit/test_visuals.py
- **Source:** test quality agent

**What was wrong:**
- Web redaction never ran against known values (SC-004).
- Token-shaped strings were missing from the capture fixture.
- The emoji path ran in no executed test.
- The pty runner had no unit test.
- No failing visual ran against real podman (US2 AS3, FR-012, FR-013).

**How it was resolved:**
- The seed page has host-value placeholders split across inline elements, in an input value, and in a token attribute.
- The CLI fixture prints `user@`, bearer, and `ghp_` strings, assembled at runtime, plus an emoji.
- The smoke test asserts the redaction counts, the absence of host values and tokens, the emoji bitmap, a byte-identical second capture (SC-002), and a failing `wait: "#missing"` visual: exit 1, the step and selector, the debug image in the run directory, no image or sidecar, and no leftovers.
- New pty tests run against `/bin/sh` (width 37, timeout).

## Remaining Findings (Minor)

| Source | File | Finding |
|--------|------|---------|
| architecture | visualcfg.py, guidecfg.py | `visual_dir` and `optional` parsed twice; the fallback table duplicates the adapter descriptors |
| architecture | visuals.py, check.py | front page region parsing duplicated with different `RegionError` handling |
| architecture | web.py, visualcfg.py, sources.py | `ROLE_RE`, the visual name grammar, and the reserved ids duplicated across modules |
| architecture | visuals.py, render_cli.py, Containerfile | dead code: `Outcome.environment_failed`, `Recipe.raw`, `screen_lines`, the unused `columns` parameter, the unused `pyyaml` pin |
| architecture | visuals.py, web.py | variant-to-stem mapping rebuilt in four places |
| architecture | visuals.py, docs | `placeholder` exit codes differ from capture and are not documented |
| correctness | check.py | an AsciiDoc image inside a table cell is skipped by the visuals scan |
| production | visuals.py | the host buffers CLI output without a byte cap (the renderer now fails beyond 20000 lines) |
| production | visuals.py | on timeout only the host `podman exec` client is killed, not the process in the container |
| security | Containerfile, guide-visuals.yml | transitive Python packages unpinned; actions referenced by tag |
| test quality | test_visuals.py | build, network, and capture container start failures and `in: capture` seed steps untested |
| test quality | test_antora.sh, test_mkdocs.sh | US1 AS4 checks only that files exist, not that pages embed them |
| test quality | test_workflows.py | no regression test pins the review guide and create plan wording (FR-025, FR-031, FR-032) |
| test quality | test_visualcfg.py | fingerprint test lacks step, script content, `disable_redaction`, and port changes |

Minor findings fixed in the same round: transitive environment references (correctness), highlight measuring after all scrolling (correctness), symlink refusal in `place` (security), OpenShift token, `token` key, private key and case-insensitive host name rules (security), `podman info` probe in doctor (architecture), CI timeout, artifact upload and stderr tail (production), teardown leftovers message (production), run directory pruning (production), byte-identical second capture check (test quality).

## Notable Observations

Captured to `brainstorm/idea-inbox.md`:
- NOTABLE-1 (architecture, visuals.py): `Run.recipe` is temporally coupled; make it a constructor argument.
- NOTABLE-2 (production, visuals.py): old capture image tags are never pruned.
- NOTABLE-3 (security, visuals.py): tool containers run with `label=disable` and full capabilities; the capture container runs as root.
- NOTABLE-4 (correctness, drift.py): affected visuals of a moved source appear under a "No drift" verdict.

## Goal Alignment

Skipped: no pull request exists for the branch.

## Post-Fix Spec Coverage

The fix round removed no requirement code: deletions replaced lines in place. All 40 functional requirements remain implemented (see the compliance matrix in REVIEW-CODE.md). The FR-008 label deviation (hashed guide path and host) is unchanged and listed as a spec evolution candidate.

## Test Suite Results

| Round | Test Command | Exit Code | Failures | Status |
|-------|-------------|-----------|----------|--------|
| 1 | make test | 0 | 0 | passed (1289 passed, 1 skipped) |
| 1 | bash tests/adapters/test_visuals.sh | 0 | 0 | passed (36 checks) |
