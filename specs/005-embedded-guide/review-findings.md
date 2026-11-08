# Deep Review Findings

**Date:** 2026-11-07
**Branch:** 005-embedded-guide
**Rounds:** 2
**Gate Outcome:** PASS after the author's decision on FINDING-11 (read the recorded front page from history, fixed in bedf18d); no Critical or Important finding remains open. The review itself ended with FAIL because FINDING-11 needed that decision.
**Invocation:** quality-gate (speckit-spex-ship, review-code stage)

Stage 1 spec compliance: 96% (2 partial deviations, FR-026 and FR-006, both fixed in round 1).
cc-review was not detected, so the built-in review ran: five internal agents (goal alignment skipped, no pull request exists) and no external tools.

## Summary

| Severity | Found | Fixed | Remaining |
|----------|-------|-------|-----------|
| Critical | 0 | 0 | 0 |
| Important | 11 | 11 | 0 |
| Minor | 21 | 8 | 13 |
| Notable | 3 | - | 3 |
| **Total** | **35** | **19** | **16** |

Findings reported by several agents were merged: the developer_readme validation was reported by three agents, and the snapshot export issues by the production readiness agent (three findings in one function).

**Agents completed:** 5/6 (goal alignment skipped: no pull request). External tools: not run (simplified review without cc-review).
**Agents failed:** none

## Findings

### FINDING-1
- **Severity:** Important
- **File:** guide/toolkit/drift.py (pr_report)
- **Category:** correctness (FR-026)
- **Source:** stage 1 spec compliance
- **Resolution:** fixed (round 1, c440b21)

**What is wrong:** The pull request check compared the base branch tip (`pull_request.base.sha`) with the head.

**Why this matters:** Cited files that changed on the base branch after the pull request branched off counted as the pull request's own changes. Unrelated pull requests then failed.

**How it was resolved:** The check now compares from `git merge-base base head`, the way GitHub's own pull request diff does. The `before` baseline entry is read at the merge base as well. Regression test: `test_pr_ignores_cited_changes_that_reached_the_base_later`.

### FINDING-2
- **Severity:** Important
- **File:** guide/toolkit/guidecfg.py (load_inputs), guide/toolkit/drift.py (evaluate_inputs)
- **Category:** correctness (FR-006)
- **Source:** stage 1 spec compliance
- **Resolution:** fixed (round 1, c440b21)

**What is wrong:** A `local:<id>` input raised a ConfigError whenever `confidential.local.yaml` was absent.

**Why this matters:** That file is git-ignored by design. In a fresh clone or in the scheduled drift workflow, the drift check therefore stopped with exit 2.

**How it was resolved:** When the file is absent, the input now loads unresolved and drift reports it as `skipped`. A file that exists but lacks the id is still an error. Tests were added in test_guidecfg and test_drift.

### FINDING-3
- **Severity:** Important
- **File:** guide/toolkit/embed.py (check_plan, apply)
- **Category:** correctness / security
- **Source:** correctness, security, and test-quality agents
- **Resolution:** fixed (round 1, 1eb01b9)

**What is wrong:** `check_plan` never validated the move plan's `developer_readme`. `apply` could therefore write outside the host, inside the guide subdirectory, into the front page, or append to a build file.

**Why this matters:** Each of those cases changes files that FR-003 protects, and they happen after other files have already been written.

**How it was resolved:** `check_plan` now refuses the plan unless the path is inside the host, outside the guide and `.git/`, a `.md` file, not a README or the front page, and not a file that the plan changes. Parametrized tests compare a byte snapshot of the host before and after.

### FINDING-4
- **Severity:** Important
- **File:** guide/toolkit/embed.py (apply)
- **Category:** correctness (FR-021)
- **Source:** correctness agent
- **Resolution:** fixed (round 1, 1eb01b9)

**What is wrong:** The plan could name developer sections that overlap, for example a parent and its subsection, or the same section twice.

**Why this matters:** For a trimmed file this crashed with a TypeError traceback. For the root README the subsection text was moved twice.

**How it was resolved:** A new `section_span` lets `check_plan` refuse overlapping developer sections. `apply` now raises `Refused` instead of unpacking None.

### FINDING-5
- **Severity:** Important
- **File:** guide/toolkit/fetch.py (export_snapshot)
- **Category:** production readiness
- **Source:** production readiness agent
- **Resolution:** fixed (round 1, 1eb01b9)

**What is wrong:** The `self` snapshot was built with `git archive`. Paths marked `export-ignore` were dropped from it, which makes the snapshot that page tasks read incomplete. The whole tar was also held in memory, and the tar `data` filter aborted on symlinks pointing outside the tree. That abort left a temporary directory behind.

**How it was resolved:** The snapshot is now written straight to disk with a temporary `GIT_INDEX_FILE`, using `read-tree` and then `checkout-index --all --prefix`. On failure the temporary directory and the index are removed and a FetchError is raised. The re-review confirmed that the host's real index and work tree stay untouched. Tests were added for export-ignore, absolute symlinks, and cleanup after a failure.

### FINDING-6
- **Severity:** Important
- **File:** guide/toolkit/embed.py (stage)
- **Category:** production readiness / security
- **Source:** production readiness and security agents
- **Resolution:** fixed (round 1, 1eb01b9)

**What is wrong:** `stage --out` ran `rmtree(<out>/docs)` without any guard. `--out .` deleted the guide's pages, and `--out ..` deleted the host's `docs/`.

**How it was resolved:** `stage` now refuses any output whose `docs` equals the docs tree, contains it, lies inside it, or lies outside the guide root. Test: `test_stage_refuses_an_output_that_overlaps_docs`.

### FINDING-7
- **Severity:** Important
- **File:** guide/toolkit/guidecfg.py (load_inputs)
- **Category:** security (FR-006)
- **Source:** security agent
- **Resolution:** fixed (round 1, 1eb01b9)

**What is wrong:** An embedded guide accepted a confidential input that had a real location in the committed `inputs.yaml`.

**How it was resolved:** Validation now requires `local:<id>` for confidential inputs of embedded guides. Separate guides are unchanged.

### FINDING-8
- **Severity:** Important
- **File:** guide/toolkit/check.py (_relative_links)
- **Category:** architecture / spec (FR-024, SC-002)
- **Source:** architecture agent
- **Resolution:** fixed (round 1, 1eb01b9; refined in round 2)

**What is wrong:** `apply` rewrites reference definitions and `src=` attributes when it moves developer text, but the developer README check did not look at those link forms.

**How it was resolved:** `_relative_links` now also checks reference definitions and `src` attributes.

### FINDING-9
- **Severity:** Important
- **File:** guide/toolkit/check.py, guide/toolkit/embed.py (REFDEF_RE, SRC_ATTR_RE)
- **Category:** correctness (FR-021, FR-024)
- **Source:** round 1 re-review
- **Resolution:** fixed (round 2)

**What is wrong:** The reference-definition regexes also matched footnote definitions (`[^1]: See ...`). That gave false broken-link reports, and `relink` rewrote the first word of a footnote as if it were a path. The `src=` regex also matched inside code spans and `data-src`.

**How it was resolved:** Labels starting with `^` are excluded, code spans are stripped before matching `src=`, and `data-src` is not matched. A keep-in-place community file is now accepted as the developer README. Tests were added.

### FINDING-10
- **Severity:** Important
- **File:** tests/toolkit/test_embed.py
- **Category:** test quality
- **Source:** test-quality agent
- **Resolution:** fixed (round 1, 1eb01b9)

**What is wrong:** No tests covered the data-protecting refusals of `check_plan`: a stale plan, relocate onto an existing file, relocate without `to`, unknown keys, and section removal.

**How it was resolved:** Parametrized cases with byte snapshots were added, plus `test_apply_refuses_a_stale_plan`.

### FINDING-11
- **Severity:** Important
- **File:** guide/toolkit/fetch.py (store_front_page_blob), guide/toolkit/embed.py (front_page_status)
- **Category:** production readiness (FR-009a)
- **Source:** production readiness agent
- **Resolution:** fixed after the author's decision (read from history)

**What is wrong:** The baseline front page is stored as an unreferenced loose object (`git hash-object -w`). It is never pushed, so other clones and CI do not have it, and `git gc` prunes it after about two weeks.

**Why this matters:** Hand edits are still detected, because the comparison uses the blob id. However, the diff that evolve shows the author becomes "(no diff available)".

**Recommendation:** Keep the normalized front page reachable. One option is a committed copy in the guide subdirectory. Another is to derive the old version from the commit that last changed `baseline.yaml`. Either changes the data model (data-model.md `front_page_blob`), so it is left to the author.

**How it was resolved:** The author chose to read the recorded text from history. `front_page_status` takes the front page from the commit that last changed `baseline.yaml` and accepts it only when its normalized blob id equals `front_page_blob`; the loose object is the fallback before that commit exists. A front page committed separately from its baseline reports that no diff is available. Tests: `test_front_page_diff_survives_gc_from_history`, `test_front_page_committed_separately_has_no_diff`.

## Minor findings

Fixed in round 1:
- sources.py `_gitdir`: dead `self` branch reverted.
- upstream.py `draft`: dead `.guide/cache/self.git` fallback replaced with `_bare`.
- embed.py `register_inputs`: dead `header` assignment removed.
- drift.py: a shallow checkout is now named as such instead of as a squash merge (scheduled workflow, `fetch-depth: 1`).
- guide-pr-check.yml: added `timeout-minutes: 10` and a concurrency group per pull request.
- guide/docs/embedded.md: `self` drift is described as comparing with the checked-out commit.
- create and evolve skills: `retarget` takes paths relative to the host root, with an example.
- fetch.py docstring: `pin` (not `rebaseline`) records `ref` and `web`.

Remaining, not auto-fixed:
- embed.py `embedded_keys_text` writes paths unquoted into guide.yaml (YAML injection through odd host file names).
- runs.py `mask_local` masks full locations only, not basenames.
- embed.py `stage`: host images map to `/blob/` (not `/raw/`), and linked logos are mangled when there is no `web` URL (FR-010a, export).
- embed.py: stubs are always Markdown, so `stub: true` on `.rst` or `.adoc` files yields a stub with no working link.
- embed.py `apply`: there is no rollback or OSError handling on partial failure.
- fetch.py: snapshot exports under `~/.cache/cc-guide/self/` are never pruned.
- Per-citation git subprocesses in check.py, drift.py, and sources.py (performance on large guides).
- Duplicated link and fence regexes and fence masks across embed.py, check.py, and sources.py; `STUB_MARKER` and `REGION_RE` are defined in several modules.
- `front_page_blob` has two writers (`fetch.rebaseline` and `embed.py front-page-status --record`).
- Duplicated host-path and tracked-head helpers across fetch, sources, drift, and embed.
- Dead parameters in embed.py: `allow_stubs`, `Plan.raw`, `Plan.absolute_links`, `stub_text(label)`, `_input_id(existing)`. Input ids can also collide (`docs/a-b.md` and `docs/a/b.md`).
- The Makefile `preview` for embedded guides watches the whole host tree.
- Test gaps: inventory branches (changelog, `doc/`, Sphinx, Docusaurus, `package.json`, `Cargo.toml`), shallow-clone drift, squash of a cited change, HTML logo front page, `absolute_links` front page, a host without a README, a kept input reported as changed, persona links on the front page (SC-001), and exit-code-only assertions.

## Notable Observations

### NOTABLE-1
- **File:** guide/templates/guide-pr-check.yml
- **Category:** security
- **Description:** The pull request check runs the head's own toolkit and baseline, so the verdict is advisory against a hostile contributor.
- **Rationale:** Running the base revision's `drift.py`, CODEOWNERS on `<guide>/tools/` and `.github/workflows/`, and pinning actions by SHA would harden it.

### NOTABLE-2
- **File:** guide/toolkit/guidecfg.py
- **Category:** architecture
- **Description:** Nothing reads `embedded.pr_check` or the `get embedded.developer_readme` and `get embedded.stubs` keys, and nothing checks that `pr_check` agrees with the workflow file.

### NOTABLE-3
- **File:** guide/toolkit/embed.py, fetch.py, runs.py
- **Category:** architecture
- **Description:** Private helpers (`guidecfg._norm`, `_embedded_raw`, `_local_inputs`, `fetch._read_raw` and `_write_raw`) are used across modules as the de facto embedded API. `fetch.host_toplevel` shadows `guidecfg.host_toplevel` but has a different failure contract.

## Post-Fix Spec Coverage

No requirement code was removed. The only deletions were dead code and the `git archive` export, which was replaced. All FR-001 to FR-032 implementations remain in place.

## Test Suite Results

| Round | Test Command | Exit Code | Failures | Status |
|-------|-------------|-----------|----------|--------|
| 0 (before fixes) | make test | 0 | 0 | 889 passed |
| 1 | make test | 0 | 0 | 907 passed |
| 1 | tests/adapters/test_gfm_embedded.sh | 0 | 0 | passed |
| 2 | make test | 0 | 0 | 908 passed |
