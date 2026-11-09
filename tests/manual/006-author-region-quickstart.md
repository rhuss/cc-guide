# Manual run: author-owned front page region (specs/006, quickstart sections 2 and 3)

**Status: run (automated scratch fixtures) on 2026-11-09.** The scenarios were driven end to end with the real CLIs (`publish.py`, `embed.py front-page-status`, `check.py --structure`) on scratch fixtures built with the same helpers the pytest suite uses (`tests/toolkit/conftest.py`), not through an interactive `/guide:create` session. Quickstart 1 is `make test` (980 passed at the final run). Scenarios 4 and 5 are covered below.

## Scenario 2: publish into an author-owned README

Scratch gfm guide with `publish: {page: docs/intro.md, target: ../README.md}` and a README carrying author text above and below the markers:

| Expectation | Result |
|---|---|
| `publish --write` splices the rendered page between the markers, links rebased | pass; author prefix and suffix byte-identical, placeholder gone |
| `publish --check` exits 0 when up to date | pass |
| Author edit above the markers: `--check` still exits 0 | pass |
| Region edit: exit 1 with a diff (`README.md (region)` vs `docs/intro.md (rendered)`) | pass |
| Markers deleted: `--write` exits 1 with the missing-markers error and writes nothing | pass |

## Scenario 3: embedded front page with an author region

Mini-host fixture with an embedded guide whose front page carries the markers, the region ownership comment first in the region, author text above and below:

| Expectation | Result |
|---|---|
| `front-page-status --record` then `front-page-status`: unchanged | pass |
| Author edits above and below the markers: still unchanged | pass |
| Region edit: exit 10 (`edited`), diff shows the region line only | pass |
| `check.py --structure`: region rules, structure, whole-file links pass | pass; the only output is fingerprint warnings (the fixture baseline pins no fingerprints), no violations |

## Scenario 4: embedded create keeps landing material

The apply mechanics are covered by `tests/toolkit/test_embed.py` (`test_apply_keeps_landing_sections_as_author_region`, `test_apply_author_region_markers_below_last_retained_section`): the landing section stays byte-identical above the markers, instructional sections are registered as `self:` input at the revision, developer sections move, and `region.splice` fills the region afterwards. The interactive `/guide:create` run (intake, classification table, approval) still needs a live session; record it here when it happens.

## Scenario 5: advisory contradiction

Pure skill markdown (`page-review-guide.md` check 9, `page-procedure.md` step 3, `front-page-contract.md` review additions): the reviewer reads the author region and flags contradictions as non-blocking findings. Nothing is executable without a review session; `make check` passing over contradicting author text is covered by `tests/toolkit/test_check.py` (author text is never checked, FR-013).

## Deviations

None in the toolchain. The scratch fixtures stand in for a `/guide:create` session; the session-dependent parts are named above.
