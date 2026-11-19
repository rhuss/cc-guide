# Code Review: Discover guide projects in nested directories

**Spec:** specs/007-nested-guide-discovery/spec.md
**Date:** 2026-11-19
**Branch:** 007-nested-guide-discovery
**Reviewer:** Claude (speckit-spex-gates.review-code + spex-deep-review)
**Scope:** `git diff main` (uncommitted worktree changes), reviewed against the spec and contracts/discover-cli.md only (plan.md and tasks.md deliberately not consulted).

## Compliance Summary

**Overall Score: 100% (13/13 functional requirements, 12/12 edge cases, 5/5 success criteria).**

No `## Constants` section in the spec, so the spec-declared-constants check was skipped.

## Functional Requirements

| FR | Status | Evidence |
|----|--------|----------|
| FR-001 rule 1, DIR holding guide.yaml wins, nothing below searched | Compliant | guidecfg.py `discover()` returns `directory` before any walk; test_discover_current_dir, test_discover_self_wins_over_nested |
| FR-002 level-by-level search, depth 1 to 3, regular file or symlink to one | Compliant | `for _depth in range(DISCOVER_MAX_DEPTH)` with `(sub / "guide.yaml").is_file()` (follows symlinks, rejects directories); test_discover_depth_three, test_discover_depth_four_not_found, test_discover_guide_yaml_entry_kinds |
| FR-003 embedded or standalone both qualify | Compliant | No `_embedded_raw` filter in discover; test_discover_nested_standalone_guide, test_discover_standalone_immediate_subdirectory |
| FR-004 shallowest depth decides; exit 3 lists only that depth, resolved and sorted; exit 4 when none | Compliant | `found` per level, `sorted(..., key=str(p.resolve()))`, main prints `cand.resolve()`; test_discover_shallower_wins, test_discover_tie_exits_3_sorted, test_discover_several_exits_3 |
| FR-005 pruning: hidden, node_modules, build, dist, target, symlinked directories | Compliant | `entry.name.startswith(".")`, `DISCOVER_PRUNED`, `entry.is_dir(follow_symlinks=False)`; test_discover_pruned_inside, test_discover_pruned_dirs_are_not_candidates, test_discover_pruning_is_exact |
| FR-006 nothing below a guide project | Compliant | candidates go to `found`, never to `nxt`; test_discover_not_below_a_guide |
| FR-007 unreadable directories skipped | Compliant (after fix round 1) | `os.access(sub, R_OK or X_OK)` check plus per-entry and per-listing OSError handling; test_discover_unreadable_directory_skipped[0o000, 0o111], test_discover_unlistable_dir_exits_4 |
| FR-008 embedded status from the configuration only | Compliant (after fix round 1) | preflight SKILL.md exit 0 row; the fallback for a failing `get` now decides by the top-level `embedded` key |
| FR-009 messages and toolkit descriptions | Compliant | usage text, docstring, `DiscoverError` message, exit 3 and exit 4 stderr messages match contracts/discover-cli.md |
| FR-010 spec 005 FR-031 and toolkit-cli row amended | Compliant | specs/005-embedded-guide/spec.md FR-031 and clarification, contracts/toolkit-cli.md, research.md R13, contracts/front-page.md section 3 (fix round 1) |
| FR-011 skill text | Compliant | preflight, create, evolve SKILL.md; `rg` finds no remaining "only immediate subdirectories" or "only embedded" statements under guide/ (guide/docs/embedded.md:113 is non-exclusive and still true) |
| FR-012 test coverage list | Compliant | all 12 listed cases have a discriminating test (see Deep Review Report) |
| FR-013 toolkit self-contained, no new dependencies | Compliant | only `os` and `pathlib`, both already imported |

## Edge Cases

All 12 spec edge cases are handled: DIR missing or a file (exit 4, test_discover_none_exits_4), unreadable directory, invalid YAML candidate (test_discover_guide_yaml_entry_kinds), depth-1 guide not searched further, shallower shadows deeper, directory named guide.yaml, fixture copies are candidates (by design), deeper embedded guide reported as embedded (FR-008 text), exact pruned names (test_discover_pruning_is_exact), pruned names at every depth (`docs/node_modules`), create resumes a nested guide (create SKILL.md), no upward search.

## Success Criteria

| SC | Status | Evidence |
|----|--------|----------|
| SC-001 cc-review layout resolves without --dir | Compliant | test_discover_nested_standalone_guide |
| SC-002 prior scenarios hold except the deliberate reversal | Compliant | existing embedded tests unchanged; the old "standalone not found" assertion replaced by test_discover_standalone_immediate_subdirectory |
| SC-003 ties never resolve silently | Compliant | test_discover_tie_exits_3_sorted, test_discover_several_exits_3 |
| SC-004 pruned trees are never listed | Compliant | test_discover_does_not_list_pruned_trees (readable node_modules, scandir recorder), test_discover_unreadable_pruned_tree_changes_nothing |
| SC-005 no false candidates in pruned locations | Compliant | test_discover_pruned_inside, test_discover_pruned_dirs_are_not_candidates |

## Extra Features (Not in Spec)

None. The preflight sentence telling the agent to use the printed path quoted, as one value, is a hardening note added in fix round 1 (security finding), not new behavior.

## Project-rule checks

- No em dash or en dash characters in any changed file (checked with `rg` on code points U+2014 and U+2013).
- No `.venv` or `uv.lock` left in the worktree; nothing committed or pushed.
- `make test`: 1001 passed before the fix loop, 1004 passed after fix round 1.

## Deep Review Report

See `review-findings.md` in this directory for every finding in full (it numbers them FINDING-1 to FINDING-12; the F and R labels below are local to this summary).

**Gate: PASS (after fix round 1)**

| Agent | Found | Fixed | Remaining | Status |
|-------|-------|-------|-----------|--------|
| Correctness | 1 | 1 | 0 | completed |
| Architecture & Idioms | 2 | 2 | 0 | completed |
| Security | 3 | 1 (partial) | 3 (1 Notable spec-conflict, 1 Minor, 1 Notable) | completed |
| Production Readiness | 3 | 1 | 2 Notable | completed |
| Test Quality | 5 | 4 | 1 Minor | completed |
| Goal Alignment | 0 | 0 | 0 | skipped (no PR found) |
| CodeRabbit (external) | 1 | 1 | 0 | completed |
| Copilot (external) | 0 | 0 | 0 | skipped (disabled in config) |
| Codex (external) | 0 | 0 | 0 | completed (no actionable findings) |
| Test Suite (regression) | 0 | 0 | 0 | passed |

### Findings

Fixed in round 1:

- F1 (Important, test-quality) SC-004 test passed for the wrong reason (unreadable node_modules was skipped by the permission path, not by pruning). Now uses a readable `node_modules/pkg/guide.yaml` and asserts scandir never touches it; the unreadable variant is a separate result-only test.
- F2 (Important, test-quality) FR-007 test did not reach the listing-failure path. Parametrized over 0o000 and 0o111, plus test_discover_unlistable_dir_exits_4.
- F3 (Minor, external CodeRabbit, also implied by F2) a 0o111 directory holding guide.yaml was accepted as a candidate and could shadow a readable guide (FR-007). Added `os.access` check; a mutant without it returns the locked directory, the fixed code returns `docs/guide`.
- F4 (Minor, correctness + architecture) preflight reported `embedded=no` for any `get` failure, even with an `embedded` block present (FR-008). Text now decides by the top-level `embedded` key.
- F5 (Minor, production-readiness) one bad entry dropped all siblings of a listing. Per-entry OSError handling; a listing that breaks off keeps what was read.
- F6 (Minor, test-quality) test_discover_several_exits_3 had an always-true substring assertion. Now exact sorted stdout plus stderr text.
- F7 (Minor, test-quality) DIR as a regular file not tested; stdout and message not checked. test_discover_none_exits_4 covers all three targets.
- F8 (Notable, architecture) specs/005-embedded-guide/contracts/front-page.md section 3 still described the old rule. Amended with the spec 007 note.
- F9 (Important, security, partial) unquoted `discover --dir <dir>` examples in evolve and create. Quoted; preflight now tells the agent to use the printed path as one quoted value.

- F10 (Minor, test-quality, found by the round 1 re-review) test_discover_unreadable_pruned_tree_changes_nothing passes whether or not pruning works; docstring now states it guards against a crash only and points to the scandir-recording test.

Round 1 re-review of the modified files found no regressions (verified on Python 3.12 and 3.14, macOS APFS).

Remaining (none Critical or Important for the gate):

- R1 (Notable, security, spec conflict) vendored or submodule trees (`vendor/`, `third_party/`, nested clones) are not pruned, so a dependency that ships guide.yaml within three levels can be resolved as the guide project when no shallower guide exists. guide/toolkit/guidecfg.py:399-400 (`DISCOVER_PRUNED`). The spec fixes the pruned list (FR-005, Clarifications, Assumptions), so the code is compliant; changing it needs a spec evolution (add `vendor`, `third_party`, skip directories holding `.git`, or ask before using a nested match).
- R2 (Minor, security) directory names containing newlines or shell metacharacters are printed verbatim; a newline can fake an extra output line. guide/toolkit/guidecfg.py:1066-1077. Pre-existing for depth 1; mitigated by the quoting guidance in preflight.
- R3 (Minor, test-quality) test_discover_embedded_at_depth_two asserts only the path, not the embedded status. tests/toolkit/test_guidecfg.py:546-553. A deeper embedded copy fails spec 005 validation (front page path), which the spec defers to validation.
- R4 (Notable, security and production-readiness) discovery from `$HOME` walks three levels of private folders (macOS privacy prompts, network mounts). guide/toolkit/guidecfg.py:424-455.
- R5 (Notable, production-readiness) skipped unreadable directories leave no trace in the exit 4 message. guide/toolkit/guidecfg.py:440-446.

## Conclusion

The implementation matches the spec at 100%. The deep review gate passes after one fix round; the remaining items are Minor or Notable, and R1 is a spec-evolution candidate rather than a code defect.
