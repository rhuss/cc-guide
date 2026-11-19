# Deep Review Findings

**Date:** 2026-11-19
**Branch:** 007-nested-guide-discovery
**Rounds:** 1
**Gate Outcome:** PASS
**Invocation:** quality-gate (ship pipeline)

## Summary

| Severity | Found | Fixed | Remaining |
|----------|-------|-------|-----------|
| Critical | 0 | 0 | 0 |
| Important | 4 | 3 (+1 reclassified) | 0 |
| Minor | 8 | 6 | 2 |
| Notable | 4 | 1 | 3 |
| **Total** | **16** | **10** | **5** |

The Important security finding on vendored trees (FINDING-11) was reclassified as Notable with a spec-conflict note: its fix would change the pruned list that FR-005, the Clarifications, and the Assumptions fix for this release. Its partial companion (FINDING-12, unquoted paths) was fixed in the skills; the rest of it remains as Minor.

**Agents completed:** 5/6 (Goal Alignment skipped, no PR found) + 2 external tools (CodeRabbit, Codex). Copilot disabled in config.
**Agents failed:** none.

## Findings

### FINDING-1
- **Severity:** Important
- **Confidence:** 90
- **File:** tests/toolkit/test_guidecfg.py:671-690
- **Category:** test-quality
- **Source:** test-quality-agent
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:** The SC-004 test used a node_modules at mode 0o000. On Python 3.12, `is_file()` on it raises and discovery skipped it via the permission path, so the test passed even with `node_modules` removed from `DISCOVER_PRUNED` (confirmed by mutant).

**Why this matters:** SC-004 (pruned trees add no work) had no discriminating test.

**How it was resolved:** The test now uses a readable `node_modules/pkg/guide.yaml` and asserts that `os.scandir` never touches `node_modules`; broken pruning would also cause a depth-2 tie. The unreadable case moved to a separate result-only test.

### FINDING-2
- **Severity:** Important
- **Confidence:** 85
- **File:** tests/toolkit/test_guidecfg.py:636-669
- **Category:** test-quality
- **Source:** test-quality-agent
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:** The FR-007 test only used mode 0o000, which never reaches the `os.scandir` failure handler.

**Why this matters:** A searchable but unlistable directory (0o111) is realistic and its handler had no coverage.

**How it was resolved:** Parametrized over 0o000 and 0o111 with a guide.yaml inside the locked directory, plus `test_discover_unlistable_dir_exits_4` (DIR at 0o111 exits 4 without a traceback).

### FINDING-3
- **Severity:** Minor
- **Confidence:** 75
- **File:** guide/toolkit/guidecfg.py:442-446
- **Category:** external
- **Source:** coderabbit (related to FINDING-2)
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:** A 0o111 directory permits looking up `guide.yaml` but not listing, so it was accepted as a candidate although unreadable, and could shadow a readable guide deeper in the tree.

**Why this matters:** FR-007 and the edge case require unreadable directories to be skipped.

**How it was resolved:** `os.access(sub, os.R_OK | os.X_OK)` is checked before a subdirectory is examined. A mutant without the check returns the locked directory; the fixed code returns `docs/guide`.

**External tool analysis (CodeRabbit):**
> For a non-root user, a directory with mode 0o111 permits metadata lookup for a known filename but does not permit directory listing. Thus, locked/guide.yaml can pass this check even though locked is unreadable. If a readable guide exists at docs/guide, discovery returns locked instead of skipping it and finding the readable guide. Check candidate-directory readability before adding it to found. Add a regression case with 0o111.

### FINDING-4
- **Severity:** Minor
- **Confidence:** 72
- **File:** guide/skills/preflight/SKILL.md:30
- **Category:** correctness
- **Source:** correctness-agent (also reported by: architecture-agent)
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:** The new fallback said to report `embedded=no` whenever `get embedded.front_page` exits non-zero. `get` runs the full validation, so an embedded guide with any unrelated configuration error (for example one found at depth 2 whose front page path no longer resolves) was reported as not embedded.

**Why this matters:** FR-008 bases the embedded status on the presence of the embedded block only.

**How it was resolved:** On a failing `get`, `embedded` is `yes` when guide.yaml parses as YAML with a top-level `embedded` key and `no` otherwise; the error stays with the command's validation.

### FINDING-5
- **Severity:** Minor
- **Confidence:** 70
- **File:** guide/toolkit/guidecfg.py:427-441
- **Category:** production-readiness
- **Source:** production-readiness-agent
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:** The whole listing of a parent sat in one `try`; an `OSError` from one `DirEntry.is_dir` call (possible on NFS, FUSE, CIFS) or a listing that broke off discarded every sibling.

**Why this matters:** One bad entry could hide the real guide, producing a wrong exit 4 or a silently deeper match (FR-007).

**How it was resolved:** Per-entry `try/except OSError`; a listing that fails partway keeps the entries already read.

### FINDING-6
- **Severity:** Minor
- **Confidence:** 90
- **File:** tests/toolkit/test_guidecfg.py:466-471
- **Category:** test-quality
- **Source:** test-quality-agent
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:** `str(embedded.name) in out` was always true ("guide" is a substring of "guide2" and of the stderr text), and stdout and stderr were mixed.

**Why this matters:** US2 AS3 ("lists both") was not verified.

**How it was resolved:** Asserts exact sorted resolved paths on stdout and the stderr message.

### FINDING-7
- **Severity:** Minor
- **Confidence:** 75
- **File:** tests/toolkit/test_guidecfg.py:707-718
- **Category:** test-quality
- **Source:** test-quality-agent
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:** The edge case "DIR is not a directory" was not tested, and the exit 4 test checked only the exit code.

**Why this matters:** A regression to a traceback on a file argument would go unnoticed.

**How it was resolved:** `test_discover_none_exits_4` covers a missing path, an empty directory, and a regular file, and asserts empty stdout and the exit 4 message.

### FINDING-8
- **Severity:** Notable
- **Confidence:** 80
- **File:** specs/005-embedded-guide/contracts/front-page.md:20
- **Category:** architecture
- **Source:** architecture-agent
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:** The create contract still said "One embedded guide found: resume it", contradicting the amended FR-031.

**How it was resolved:** Amended to the new rule with the spec 007 note, like the other amendments.

### FINDING-9
- **Severity:** Minor
- **Confidence:** 80
- **File:** tests/toolkit/test_guidecfg.py:696-705
- **Category:** test-quality
- **Source:** re-review (round 1)
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:** `test_discover_unreadable_pruned_tree_changes_nothing` passes whether or not pruning works (the `os.access` check skips the unreadable directory either way).

**How it was resolved:** The docstring states it guards against a crash only and points to the scandir-recording test, which covers pruning.

### FINDING-10
- **Severity:** Minor (remaining part of an Important finding)
- **Confidence:** 70
- **File:** guide/toolkit/guidecfg.py:1066-1077; guide/skills/evolve/SKILL.md:85; guide/skills/create/SKILL.md:50
- **Category:** security
- **Source:** security-agent
- **Round found:** 1
- **Resolution:** partially fixed (round 1); remainder open

**What is wrong:** Directory names are printed verbatim; a name containing a newline produces an extra output line that reads like a second path, and names with `$(...)` or backticks are dangerous if an agent pastes the path into a double-quoted shell argument. The evolve and create examples passed `--dir <dir>` unquoted.

**Why this matters:** Discovery now walks three levels of names that third-party content can control.

**How it was resolved:** The evolve and create examples are quoted, and preflight tells the agent to use the printed path as one quoted value (exactly one line). Rejecting such names in `discover()` remains open; it is pre-existing behavior for depth 1 and would add a pruning rule the spec does not list.

### FINDING-11
- **Severity:** Notable (reported as Important; reclassified, spec conflict)
- **Confidence:** 75
- **File:** guide/toolkit/guidecfg.py:399-400 (`DISCOVER_PRUNED`)
- **Category:** security
- **Source:** security-agent
- **Round found:** 1
- **Resolution:** remaining (spec evolution candidate)

**What is wrong:** Vendored and submodule trees (`vendor/<org>/<pkg>`, `third_party/x`, nested clones) are not pruned. A repository whose only guide.yaml within three levels belongs to a dependency resolves to that dependency, and commands then run its Makefile and tools.

**Why this matters:** User Story 4 says a dependency package is never picked up; that holds only for the pruned names.

**What needs to happen:** The pruned list is fixed by FR-005, the Clarifications ("the pruning list stays as in the issue"), and the Assumptions. Options for a spec evolution: add `vendor` and `third_party`, skip directories that hold a `.git` entry, or have preflight confirm a nested match with the author before any command runs scripts in it.

### FINDING-12
- **Severity:** Minor
- **Confidence:** 80
- **File:** tests/toolkit/test_guidecfg.py:546-553
- **Category:** test-quality
- **Source:** test-quality-agent
- **Round found:** 1
- **Resolution:** remaining

**What is wrong:** `test_discover_embedded_at_depth_two` asserts only the discovered path; its docstring mentions the embedded status, which is not checked. A deeper copy of the embedded fixture fails spec 005 validation (front page path), so `get embedded.front_page` cannot confirm the status there.

**What needs to happen:** Either check the status with a parser that does not validate (the preflight fallback now reads the top-level `embedded` key), or reword the docstring.

## Notable Observations

### NOTABLE-1
- **File:** guide/toolkit/guidecfg.py:424-455
- **Category:** security, production-readiness
- **Source:** security-agent, production-readiness-agent
- **Description:** Running a guide command from `$HOME` or `/` walks three levels of private folders (macOS privacy prompts for Documents, Desktop, Library/Containers; slow network or cloud-sync mounts).
- **Rationale:** The old code stopped at depth 1. A guard (exit 4 for the home directory or filesystem root, or descend only inside a git work tree) would need a spec decision.

### NOTABLE-2
- **File:** guide/toolkit/guidecfg.py:440-446
- **Category:** production-readiness
- **Source:** production-readiness-agent
- **Description:** Skipped unreadable directories leave no trace; exit 4 looks the same whether or not part of the tree was skipped.
- **Rationale:** A guide behind wrong permissions shows up as "no guide project" with no hint. A stderr count of skipped directories would keep the stdout contract.

(FINDING-11 is also listed in the idea inbox as a Notable spec-evolution candidate.)

## Post-Fix Spec Coverage

The fix round removed no behavior (it replaced a list comprehension with a loop and added a readability check). All FR-001 to FR-013 remain implemented: discover() rule 1, depth loop, pruning, `found`/`nxt` split, exit codes and messages in main(), skill text, spec 005 amendments, and the test list. All spec requirements verified after the fix loop.

## Test Suite Results

| Round | Test Command | Exit Code | Failures | Status |
|-------|-------------|-----------|----------|--------|
| baseline | make test | 0 | 0 | 1001 passed |
| 1 | make test | 0 | 0 | 1004 passed |
| 1 (docstring edit) | pytest -k discover | 0 | 0 | 29 passed |

Test suite passed in all fix rounds.

## Remaining Findings

No Critical or Important findings remain. Open Minor items: FINDING-10 (name sanitizing in discover) and FINDING-12 (embedded status at depth 2 untested). Open Notable items: FINDING-11 (vendored trees, needs spec evolution), NOTABLE-1, NOTABLE-2.
