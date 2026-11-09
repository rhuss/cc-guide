# Tasks: Author-owned region on the generated front page

**Input**: Design documents from `/specs/006-author-owned-front-page-region/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/ (region-markers.md, publish-cli.md, move-plan-destination.md), quickstart.md

**Tests**: Included. The spec's success criteria are fixture-verifiable and the repo's convention is pytest per module (`make test`); every story carries its test tasks first.

**Organization**: Tasks grouped by user story (spec.md stories 1 to 4) so each story is independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1 (publish into author-owned README), US2 (embedded front page region), US3 (create move-plan destination), US4 (advisory contradiction findings)
- File paths are repository-relative from `guide/` and `tests/toolkit/`

## Path Conventions

Toolkit scripts: `guide/toolkit/` (copied into guide projects as `tools/guide/`). Tests: `tests/toolkit/`. Skill markdown: `guide/skills/`. Adapter scaffold: `guide/adapters/gfm/`.

## Global Constraints

Inherited by every task, copied from the repo rules and spec constraints:

- No em dash or en dash characters in any file; rephrase or build them from code points in tests.
- Use `uv` instead of pip; toolkit scripts are PEP 723 (`uv run`) with `requires-python >= 3.11`.
- Toolkit modules import nothing from outside `guide/toolkit/` (self-contained when copied to `tools/guide/`).
- Never write secrets, tokens, kubeconfig content, or raw inputs into fixtures.
- Scripts never `cd` into `.guide/cache/` and run git there only through `git -C <cache path>`.
- Git commits end with the trailer `Assisted-By: 🤖 Claude Code`.
- The mechanism is gfm-adapter only in v1 (FR-016); other adapters must not gain publish support.

## Interfaces

Cross-task contracts; a task's implementer sees only their own task, so consuming tasks reference these names exactly:

- `guide/toolkit/region.py` (T002):
  - `parse(text: str) -> Region` where `Region` has fields `author_prefix: str`, `content: str`, `author_suffix: str`, `begin_line: int`, `end_line: int`; raises `RegionError(msg, rule)` with rule `"region-unbalanced"` or `"region-duplicate"`.
  - `splice(text: str, new_content: str) -> str` (replaces content between markers, byte-preserving prefix and suffix).
  - `normalized(text: str) -> str` (region content with `guide:attr` values emptied; whole file when no markers).
- `guide/toolkit/guidecfg.py` (T004): `Publish` dataclass with `page: Path` and `target: Path` (resolved absolute), exposed as `guide.publish: Publish | None` on the loaded guide; `ConfigError` on invalid blocks.
- `guide/toolkit/publish.py` (T008): CLI `uv run tools/guide/publish.py [--root DIR] [--write | --check]`, exit 0 clean/no-op, 1 error or difference.
- `guide/toolkit/check.py` (T009, T015): rule names `region-unbalanced`, `region-duplicate` through the existing `Violation(path, line, rule, message)`.
- `guide/toolkit/embed.py` (T020): `DESTINATIONS` gains `"author-region"`; `apply(root, plan_path, dry_run=False)` unchanged signature.

---

## Phase 1: Setup

**Purpose**: Confirm the baseline before any change.

- [x] T001 Run `make test` in the repository root and confirm the full toolkit suite passes unchanged (baseline for the feature; record the count for the final phase)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The region parser and the publish declaration every story depends on.

- [x] T002 Implement `guide/toolkit/region.py`: `parse(text)` returning the Region view (author_prefix, content, author_suffix, begin_line, end_line), `splice(text, new_content)`, `normalized(text)`; fence-masked marker scanning (reuse the approach of `embed.py:_fence_mask`); errors `region-unbalanced` and `region-duplicate` naming file and line per contracts/region-markers.md
- [x] T003 Write `tests/toolkit/test_region.py`: parse (balanced, prefix/suffix/content split), splice byte-preservation of author text, unbalanced and duplicate marker errors, markers inside fenced code blocks treated as text, empty region
- [x] T004 Implement the `publish` block in `guide/toolkit/guidecfg.py`: `Publish` dataclass (`page`, `target`), parsing and validation per data-model.md (both keys required, no unknown keys, page inside content root and existing, target outside content root, one block, gfm adapter only), `ConfigError` messages with file and line
- [x] T005 Add publish-block parsing cases to `tests/toolkit/test_guidecfg.py`: valid block, missing keys, unknown keys, page outside content root, target inside content root, non-gfm adapter rejection

**Checkpoint**: region.py and guidecfg publish parsing exist and are tested; stories can proceed.

---

## Phase 3: User Story 1 - Publish a guide page into an author-owned README region (Priority: P1) MVP

**Goal**: A gfm guide declares `publish: {page, target}` in guide.yaml; the writer splices the rendered page into the target's region; the check compares the region only.

**Independent Test**: quickstart.md scenario 2 (write, check, author-edit tolerance, region-edit failure, missing-markers error).

### Tests for User Story 1

- [x] T006 [P] [US1] Write `tests/toolkit/test_publish.py` writer cases: splice writes only the region (author text byte-identical before and after), link rebasing from page dir to target dir (inline links, reference definitions, angle brackets, images; absolute URLs and fragments untouched), sources block and guide:attr regions included, missing markers error writes nothing, no publish block is a no-op exit 0
- [x] T007 [P] [US1] Write `tests/toolkit/test_publish.py` check cases: identical region passes, edited region fails with diff, edited author text passes, missing source page fails naming the page

### Implementation for User Story 1

- [x] T008 [US1] Implement `guide/toolkit/publish.py` per contracts/publish-cli.md: `--write` and `--check` modes over the guidecfg publish declaration, rendering via `embed.rewrite_links` rebase, splice via `region.splice`, exit codes 0/1, human-readable output
- [x] T009 [US1] Extend `guide/toolkit/check.py`: add the publish target to the whole-file link check file set (FR-008) and run the region validity parse on it (rules `region-unbalanced`, `region-duplicate`)
- [x] T010 [P] [US1] Add `publish` and `check-publish` targets to `guide/adapters/gfm/scaffold/Makefile` (check-publish wired into `check`, no-op notice without a publish block) and document the publish block and markers in `guide/adapters/gfm/adapter.yaml`
- [x] T011 [P] [US1] Add `tests/toolkit/test_check.py` cases: publish target link check covers author links into the guide (unresolvable author link fails, FR-008), region validity errors reported for the target

**Checkpoint**: `make publish` and `make check` behave per quickstart scenario 2 on a scratch gfm guide.

---

## Phase 4: User Story 2 - Author-owned region on the embedded front page (Priority: P1)

**Goal**: With markers on the embedded front page, every command operates on the region only; author text is invisible to hand-edit detection; without markers, spec 005 behavior is unchanged.

**Independent Test**: quickstart.md scenario 3 (front-page-status unchanged for author edits, edited for region edits, make check passes).

### Tests for User Story 2

- [x] T012 [P] [US2] Add `tests/toolkit/test_embed.py` front_page_status cases: author edit above markers leaves status `unchanged`, region edit reports `edited` with a region-only diff, whole-file front page without markers keeps today's behavior (FR-002), marker transition of an existing front page reports `edited` once then settles after re-record, `embed.stage` keeps the whole front page including author text so site and PDF exports are unchanged (FR-015)
- [x] T013 [P] [US2] Add `tests/toolkit/test_attrs.py` cases: generated-region rewriting on a front page with markers touches the region only; a `guide:attr` marker in author text is neither rewritten nor an unknown-attribute error

### Implementation for User Story 2

- [x] T014 [US2] Make `fetch.normalized_front_page` region-aware in `guide/toolkit/fetch.py` (region content only when markers present, attr values still emptied inside it) and thread it through `embed.front_page_status` and `fetch.store_front_page_blob` per research R5
- [x] T015 [US2] Extend `guide/toolkit/check.py`: `check_structure` reads section titles and persona links from the front page's region when markers are present; the ownership-comment rule accepts the comment as the first line of the region (FR-011)
- [x] T016 [US2] Make `attrs.regions` in `guide/toolkit/attrs.py` region-aware: substitution and unknown-attribute detection run on the region only (research R7)
- [x] T017 [P] [US2] Rewrite `guide/skills/page-task/front-page-contract.md` for the region model: ownership comment inside the region (stating the region is guide-owned and the rest is the author's), badges and logo as ordinary author text (rule 3 special case dissolved), region-only editing for the page task, region-only review checks, whole-file link check noted as the single exception
- [x] T018 [P] [US2] Update `guide/skills/evolve/SKILL.md` section 8: hand-edit reporting scoped to the region; author text never reported; the marker-transition note from research R5

**Checkpoint**: quickstart scenario 3 passes on a scratch embedded guide; test_embed and test_attrs additions green.

---

## Phase 5: User Story 3 - Embedded create keeps landing material as the author region (Priority: P2)

**Goal**: The move plan offers `author-region` as the default destination for landing-oriented README sections; apply writes the markers below the retained text.

**Independent Test**: quickstart.md scenario 4 (pitch stays byte-identical above the markers, instructional sections verified as input, no dropped claims from the pitch).

### Tests for User Story 3

- [x] T019 [P] [US3] Add `tests/toolkit/test_embed.py` move-plan cases: `author-region` accepted only for root-Markdown-README sections with non-null section and no stub; rejected for other paths, whole-file entries, or with `stub: true`; root-README destination constraint updated (input, developer, author-region)

### Implementation for User Story 3

- [x] T020 [US3] Extend `guide/toolkit/embed.py`: add `author-region` to `DESTINATIONS`, validator rules per contracts/move-plan-destination.md, and `apply` behavior writing the marker pair immediately below the last retained author-region section (retained text byte-identical, research R9)
- [x] T021 [P] [US3] Update `guide/skills/create/SKILL.md` classification step: landing-oriented sections (pitch, context, usage examples) default to `author-region`; instructional material keeps `input`; the front page task note says it fills the region between markers
- [x] T022 [US3] Add `tests/toolkit/test_embed.py` apply cases: apply writes markers below retained sections, retained text unchanged, front page task can then splice into the region

**Checkpoint**: quickstart scenario 4 passes on a scratch repository with a pitch-style README.

---

## Phase 6: User Story 4 - The guide notices contradictions without blocking (Priority: P3)

**Goal**: Reviewer briefs direct reading the author region and flagging contradictions as non-blocking findings.

**Independent Test**: quickstart.md scenario 5 (planted contradiction appears as advisory; all checks and gates pass).

- [x] T023 [P] [US4] Add the author-region review instruction to `guide/skills/page-task/page-review-guide.md`: read the author region when reviewing the front page or a published region's source page; flag contradictions with the guide region or sources as non-blocking findings in the run summary; never fail a check over author text (FR-014, FR-013)
- [x] T024 [P] [US4] Add the matching instruction to `guide/skills/page-task/page-procedure.md` for front-page and published-source page tasks, and to the review additions of `guide/skills/page-task/front-page-contract.md` (one sentence each, same wording)

**Checkpoint**: a review run on the quickstart scenario 5 fixture lists the contradiction as an advisory.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T025 Run `make test` and confirm the full suite passes with the recorded baseline plus the new tests; run the quickstart.md scenarios 2 and 3 end to end on scratch fixtures
- [x] T026 Sweep every file touched by this feature for em/en dash characters and repo-rule violations (no `cd` into `.guide/cache/`, no secrets in fixtures); check `guide/toolkit/` still imports nothing from outside its own directory (`make validate` if plugin-level checks apply)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1**: none.
- **Phase 2 (Foundational)**: blocks all stories (region.py and guidecfg publish parsing).
- **Phase 3 (US1)** and **Phase 4 (US2)**: after Phase 2; independent of each other.
- **Phase 5 (US3)**: after Phase 4 (apply writes markers the front page task then fills; the front-page region flow must exist).
- **Phase 6 (US4)**: after Phase 3 or 4 (briefs reference regions that exist); pure markdown.
- **Phase 7**: last.

### Within Each User Story

- Tests first (they must fail before implementation).
- Parser/config before consumers; writer before Makefile wiring; toolkit before skill markdown that references it.

### Parallel Opportunities

- T006 and T007 (two test files, same story) and T010/T011 across US1.
- T012/T013 (US2 tests), T017/T018 (US2 markdown) once T014 through T016 land.
- T019 (US3 tests) parallel with T023/T024 (US4 markdown).

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 baseline, Phase 2 foundation.
2. Phase 3 (US1) complete: publish into an author-owned README works.
3. Stop and validate (quickstart scenario 2). US1 alone already serves plain gfm guides (aprofile's migration path).

### Incremental Delivery

4. Phase 4 (US2): embedded front page region. 5. Phase 5 (US3): create move plan. 6. Phase 6 (US4): advisories. 7. Phase 7 polish.

---

## Notes

- [P] tasks touch different files with no dependency on incomplete tasks.
- Every task names its file; contracts and research entries are referenced by name so no task needs extra context.
- Commit after each task or logical group with the repo trailer `Assisted-By: 🤖 Claude Code`.
