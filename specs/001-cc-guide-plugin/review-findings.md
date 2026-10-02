# Deep Review Findings

**Date:** 2026-10-01
**Branch:** 001-cc-guide-plugin
**Rounds:** 2
**Gate Outcome:** PASS
**Invocation:** quality-gate (after_implement hook, spec compliance 98%)

## Summary

| Severity | Found | Fixed | Remaining |
|----------|-------|-------|-----------|
| Critical | 0 | 0 | 0 |
| Important | 9 | 9 | 0 |
| Minor | 13 | 13 | 0 |
| Notable | 6 | 2 | 4 (captured to brainstorm/idea-inbox.md) |
| **Total** | **28** | **24** | **4** |

**Agents completed:** 5/5 internal agents (Goal Alignment skipped: no pull request for the branch), plus two scoped re-reviews.
**External tools:** CodeRabbit failed (the CLI requires a workspace SSO session; also this CLI version has no `--files` option, so the review ran as `--committed --base main`); Codex failed (usage limit until 2026-10-17); Copilot skipped (disabled in config).
**Execution note:** spex-teams is not enabled, so the five agents ran sequentially. Each fix round was re-reviewed by one scoped agent that applied all five perspectives to that round's diff.

Earlier in the same gate, a three-part spec compliance review (FR-001 to FR-042, edge cases, success criteria, data model) found 14 deviations and gaps; they were fixed before the deep review (commit 42da9c9 and f39d92c). The one open item is FR-003 (see Remaining Findings).

## Findings

### FINDING-1
- **Severity:** Important
- **Confidence:** 85
- **File:** guide/toolkit/upstream.py:339-344
- **Category:** correctness
- **Source:** correctness-agent
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:** `sanitize` compared `text.splitlines()` with `classify.redact(text).splitlines()` through `zip`. The private-key pattern collapses a multi-line PEM block into one line, so the two lists misalign.

**Why this matters:** after a PEM block, innocent lines were reported and a real token near the end of a draft could be skipped, letting a credential pass the gate in front of a public issue (FR-035).

**How it was resolved:** each line is redacted on its own and reported; when only the whole text differs (a multi-line secret), one problem is still reported. Test `test_sanitize_flags_token_after_private_key_block`.

### FINDING-2
- **Severity:** Important
- **Confidence:** 92
- **File:** guide/toolkit/upstream.py:55, 132-133
- **Category:** architecture
- **Source:** architecture-agent
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:** upstream.py had its own copy of `GIT_ENV` and the git helper from fetch.py, already diverging (no error mode).

**Why this matters:** later hardening of the shared helper (timeouts, environment) would miss upstream.py.

**How it was resolved:** upstream.py calls `fetch._git(..., check=False)`; the copy is gone, so the timeout from FINDING-6 applies here too.

### FINDING-3
- **Severity:** Important
- **Confidence:** 88
- **File:** guide/toolkit/drift.py:41-44, guide/toolkit/check.py:55-57
- **Category:** architecture
- **Source:** architecture-agent
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:** check.py and drift.py defined their own link regexes with different syntax support (angle-bracket links in one, href attributes in the other).

**Why this matters:** a link the leak and broken-link checks see could be invisible to the drift impact set, or the reverse, so evolve could miss a page that links to a changed page (FR-026).

**How it was resolved:** `XREF_RE`, `MD_LINK_RE`, `SCHEME_RE`, and `link_targets()` live in sources.py and both modules use them.

### FINDING-4
- **Severity:** Important
- **Confidence:** 88
- **File:** guide/toolkit/fetch.py:72-84, 120, 144; guide/toolkit/upstream.py:152
- **Category:** security
- **Source:** security-agent
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:** a `repo` value starting with `-` (for example `--upload-pack=...`) reached `git clone` and `git ls-remote` as an option.

**Why this matters:** adoption (FR-028) reads foreign `baseline.yaml` files; a crafted value could run a program through git.

**How it was resolved:** every clone and ls-remote passes `--` before the URL, and `guidecfg.load_baseline` rejects repo values that start with `-`.

### FINDING-5
- **Severity:** Important
- **Confidence:** 90
- **File:** guide/toolkit/preview-watch.mjs (was antora-watch.mjs):70-79, 174-179
- **Category:** production-readiness
- **Source:** production-readiness-agent
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:** stopping the preview did not stop a running build; uv, npx, Antora, or MkDocs kept running as orphans.

**Why this matters:** Ctrl-C during a long build left CPU-bound processes behind (FR-030 preview loop).

**How it was resolved:** builds run in their own process group (`detached: true`), and the stop handler kills the group before exiting. Both preview smoke tests pass and no process remains afterwards.

### FINDING-6
- **Severity:** Important
- **Confidence:** 88
- **File:** guide/toolkit/fetch.py:105-115
- **Category:** production-readiness
- **Source:** production-readiness-agent
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:** `baseline.yaml` was written in place; an interruption could leave it truncated.

**Why this matters:** the baseline is the single source of truth for every pin; losing it breaks every later build and drift check.

**How it was resolved:** fetch.py and upstream.py write to a temporary file and `os.replace` it. Together with this, every git call got a timeout (`GUIDE_GIT_TIMEOUT`, default 600 s) and every gh call one (`GUIDE_GH_TIMEOUT`, default 60 s), from Minor finding 15.

### FINDING-7
- **Severity:** Important
- **Confidence:** 92
- **File:** guide/toolkit/mkdocs_macros.py:31-74
- **Category:** test-quality
- **Source:** test-quality-agent
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:** the MkDocs macros (baseline values, experimental labels, baseline note) had no tests.

**Why this matters:** they are the only path for baseline values and experimental labels into MkDocs pages (FR-015, FR-018).

**How it was resolved:** `tests/toolkit/test_mkdocs_macros.py` covers `attr` (values and the unknown-name failure), both tiers, an unknown tier, GitHub links, and local repositories without links.

### FINDING-8
- **Severity:** Important
- **Confidence:** 78
- **File:** eval.yaml:82-95
- **Category:** test-quality
- **Source:** test-quality-agent
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:** the `review_catches_planted` judge accepted generic keywords (`admin`, `enabled`) anywhere in the Critical/Important text.

**Why this matters:** a review that missed a planted false fact could still pass the eval (SC-002).

**How it was resolved:** the judge splits the section into finding entries and requires all keywords of one planted fact in a single entry; annotations use specific keywords with alternatives. A sample review that misses the admin UI fact now fails.

### FINDING-9
- **Severity:** Important
- **Confidence:** 78
- **File:** guide/templates/guide-drift.yml:23-36
- **Category:** security
- **Source:** fix round 1 re-review
- **Round found:** 2
- **Resolution:** fixed (round 2)

**What is wrong:** after round 1 moved the source token into a global `extraheader`, `actions/checkout` still persisted its own header, so git commands run from the checkout could send two Authorization headers.

**Why this matters:** private sources could fail to authenticate in the scheduled drift check (FR-025b).

**How it was resolved:** `persist-credentials: false` on the checkout step; the second re-review confirmed every later step still works.

### Minor findings (all fixed)

| # | File | Finding | Resolution |
|---|---|---|---|
| 10 | guide/toolkit/check.py:300-314 | Closing code fence did not need as many markers as the opening one | Full marker stored and length compared; regression-sensitive test with an unbalanced inner fence (round 2) |
| 11 | guide/adapters/gfm/scaffold/pandoc/print.sh:29 | Trap did not remove the `.nav` temp file | Trap removes both files |
| 12 | guide/toolkit/antora-watch.mjs | Name no longer matched (also serves MkDocs) | Renamed to `preview-watch.mjs`, all references updated |
| 13 | guide/toolkit/upstream.py:459 | `approved -> rejected` and `drafted -> drafted` not in data-model.md | Kept (withdrawing an approval and redrafting are valid); data-model.md documents both |
| 14 | guide/toolkit/classify.py (awk) | `awk -f file` classified as a query although the program file is not inspected | `-f` and `--file` deny awk as a query; test |
| 15 | fetch, drift, upstream, sources | git and gh calls without timeouts | Timeouts with clear errors (see FINDING-6) |
| 16 | guide/toolkit/leakcheck.py:100-108 | Confidential terms and patterns in href/src values not scanned | Link targets are scanned; test with a term and a ticket key in URLs |
| 17 | guide/templates/guide-drift.yml:31-33 | Token embedded in a rewritten URL could reach logs | Token sent as a masked `extraheader` |
| 18 | guide/adapters/gfm/scaffold/Makefile:17-20 | Browser-open loop polled for up to 120 s after the server stopped | At most 30 s |
| 19 | guide/templates/guide-drift.yml | Drift step without `timeout-minutes` | 15 minutes |
| 20 | tests/toolkit/test_leakcheck.py | No test for confidential patterns in PDF text | `test_pdf_ticket_pattern` |
| 21 | guide/scripts/scaffold-project.sh | `--toolkit-only` refresh untested | `tests/toolkit/test_scaffold_project.py` (refresh, stale file removed, content untouched, kept files, unknown format) |
| 22 | tests/toolkit/test_check.py | Fence-length fix not protected by a test | Covered by the round 2 test (see 10) |

## Notable Observations

### NOTABLE-1 (resolved)
- **File:** guide/toolkit/guidecfg.py:44, playbook.py:27, sources.py:35
- **Category:** architecture
- **Description:** `URL_RE` defined three times. playbook.py now uses `guidecfg.URL_RE`; the stricter variant in sources.py stays for full-reference validation.

### NOTABLE-2 (resolved)
- **File:** guide/toolkit/upstream.py:95-98
- **Category:** production-readiness
- **Description:** findings were written in place; now written atomically with the baseline fix.

### NOTABLE-3
- **File:** guide/toolkit/drift.py:460
- **Category:** architecture
- **Description:** `--check` is accepted but drift.py has no other mode. Kept because the contract and the scheduled workflow call `drift.py --check`; captured for a future decision.

### NOTABLE-4
- **File:** guide/toolkit/print-pdf.mjs:315-320
- **Category:** security
- **Description:** remote images still load while printing (fonts, scripts, and styles are blocked). Blocking them would make PDFs of guides with remote images fail; the comment now states the behavior. Captured for a decision on an offline-only mode.

### NOTABLE-5
- **File:** guide/toolkit/print-pdf.mjs, preview-watch.mjs, shoot.mjs
- **Category:** test-quality
- **Description:** the Node scripts are covered only by the shell smoke tests (happy paths plus the planted failure); no unit tests for title page, TOC grouping, or landscape handling.

### NOTABLE-6
- **File:** guide/toolkit/check.py:55-57
- **Category:** architecture
- **Description:** the shared `MD_LINK_RE` matches any `](path)`, slightly looser than check.py's old pattern; image links inside links are now checked too. Accepted; revisit if false broken-link reports appear.

## Goal Alignment

Skipped: no pull request exists for the branch, so no declared goals beyond the spec. Spec compliance was checked separately (98%).

## Post-Fix Spec Coverage

The fix loop removed duplicate helpers, old regexes, and a Makefile helper, so coverage was verified: the implementing functions for every toolkit-backed requirement still exist (29 of 29 checked: fetch pin/fetch/rebaseline, drift report, check pages and structure, leak checks, classifier, upstream operations including status recording, run summaries and resume, source resolution, regions, playbooks, diagram and ledger checks, adoption, doctor, MkDocs macros, the preview watcher, and the PDF printer), and the suites that exercise them pass. All spec requirements verified after the fix loop.

## Test Suite Results

| Round | Test Command | Exit Code | Failures | Status |
|-------|-------------|-----------|----------|--------|
| 1 | make test | 0 | 0 | passed (462) |
| 1 | make test-adapters | 0 | 0 | passed (58 checks) |
| 2 | make test | 0 | 0 | passed (463) |

Test suite passed in all fix rounds.

## Remaining Findings

None at Critical or Important severity.

Resolved by author decision (2026-10-01): keep the hard dependency on superpowers in `plugin.json`; FR-003, SC-009, and the companion-plugin edge case in spec.md now describe that the plugin does not load without superpowers.
