# Tasks: Discover guide projects in nested directories

**Input**: Design documents from `specs/007-nested-guide-discovery/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/discover-cli.md, quickstart.md

**Tests**: Requested by the spec (FR-012). The implementation (Phase 2) lands first; each story phase then adds the tests that prove it and ends with a checkpoint run.

**Format**: `- [ ] [ID] [P?] [Story] Description`

All test tasks edit `tests/toolkit/test_guidecfg.py`, section `# --- discover (FR-031) ---`. Build layouts in `tmp_path`; a minimal standalone configuration is enough because discovery only checks that `guide.yaml` exists as a regular file (write a small helper `make_guide(dir)` that creates `dir/guide.yaml` with `schema: 1` and returns `dir`). Use the existing module-level `discover(path)` subprocess helper for CLI assertions and `guidecfg.discover` for the Python API. Whenever a test needs `get embedded.front_page` to succeed, copy the `render_fixture_guide` fixture (a fully valid guide) instead of using `make_guide`, because a `schema: 1`-only file fails `get` with `format: required`.

## Phase 1: Setup

- [X] T001 Run `make test` once in the worktree root and record the baseline (all tests pass before any change), so later failures can be attributed to this change

## Phase 2: Foundational (blocking)

- [X] T002 Add the `make_guide(dir: Path) -> Path` helper next to the existing `discover()` helper in tests/toolkit/test_guidecfg.py (creates parent directories, writes `guide.yaml` containing `schema: 1\n`, returns the directory)
- [X] T003 Rewrite `discover()` in guide/toolkit/guidecfg.py per plan.md "Algorithm": module constants `DISCOVER_MAX_DEPTH = 3` and `DISCOVER_PRUNED = frozenset({"node_modules", "build", "dist", "target"})`; rule 1 unchanged (`(directory / "guide.yaml").is_file()` returns `directory`); `directory` not a directory raises `DiscoverError(4, [])`; level-by-level scan with `os.scandir` wrapped in `try/except OSError` (skip unreadable parents); accept an entry only when `entry.is_dir(follow_symlinks=False)` is true, its name does not start with `.`, and it is not in `DISCOVER_PRUNED`; an accepted entry whose `guide.yaml` is a regular file (`Path.is_file()`, symlink to a file allowed, a directory named `guide.yaml` does not count) is a candidate and is not descended into; otherwise it joins the next level; after each level return the single candidate, or raise `DiscoverError(3, candidates)` with candidates sorted once, here, by `str(path.resolve())`; after depth 3 raise `DiscoverError(4, [])`. Do not read the YAML in `discover` any more. Update the docstring to describe the bounded search (no "immediate subdirectory" wording)
- [X] T004 Update the `DiscoverError` message in guide/toolkit/guidecfg.py to `"several guide projects"` for code 3 (code 4 stays `"no guide project found"`)
- [X] T005 Update the `discover` CLI branch in `main()` of guide/toolkit/guidecfg.py: exit 3 stderr line `several guide projects found; name one with --dir:` and candidates printed as resolved paths, one per line, on stdout, in the order `discover()` returns them (already sorted); exit 4 stderr line `no guide project in {args.dir} or the directories below it (up to 3 levels)`
- [X] T006 Update the module usage text for `discover` at the top of guide/toolkit/guidecfg.py: "prints the guide root: DIR when it holds guide.yaml, otherwise the one guide project found in the shallowest of the directories up to three levels below DIR (hidden, node_modules, build, dist, target, and symlinked directories are skipped); exit 3 when several are equally shallow (they are listed), exit 4 when there is none"

**Checkpoint**: `uv run guide/toolkit/guidecfg.py discover --dir <tmp>` behaves per contracts/discover-cli.md.

## Phase 3: User Story 1, nested standalone guide found from the root (P1)

**Goal**: A standalone guide at `docs/guide/` (or depth 3) is found without `--dir` and reported as not embedded.

**Independent Test**: `make_guide(tmp/docs/guide)`; discover on `tmp` prints that path, exit 0; `get embedded.front_page --root` that path prints an empty line.

- [X] T007 [P] [US1] Add `test_discover_nested_standalone_guide` in tests/toolkit/test_guidecfg.py: `make_guide(tmp_path/"repo"/"docs"/"guide")`; CLI exit 0 and stdout resolves to that directory; `guidecfg.discover(tmp_path/"repo")` returns it; `run_cli(found, "get", "embedded.front_page")` prints an empty line (preflight reports `embedded=no`, FR-008). Build `docs/guide` by copying the `render_fixture_guide` fixture there (`shutil.copytree`), not with `make_guide`, so `get` succeeds
- [X] T008 [P] [US1] Add `test_discover_depth_three` in tests/toolkit/test_guidecfg.py: `make_guide(tmp_path/"repo"/"docs"/"user"/"guide")` is found from `tmp_path/"repo"`
- [X] T009 [P] [US1] Add `test_discover_self_wins_over_nested` in tests/toolkit/test_guidecfg.py: `make_guide(root)` and `make_guide(root/"docs"/"guide")`; discover on `root` returns `root`
- [X] T010 [US1] Checkpoint: `uv run pytest tests/toolkit/test_guidecfg.py -k discover` passes with T007 to T009

## Phase 4: User Story 2, several guides never resolve silently (P1)

**Goal**: Shallowest depth wins; ties at that depth exit 3 with sorted absolute paths and no deeper candidates.

**Independent Test**: tie layout exits 3 listing both; mixed-depth layout returns the shallower one.

- [X] T011 [P] [US2] Add `test_discover_shallower_wins` in tests/toolkit/test_guidecfg.py: `make_guide(root/"guide")` and `make_guide(root/"docs"/"guide")`; discover returns `root/"guide"`
- [X] T012 [P] [US2] Add `test_discover_tie_exits_3_sorted` in tests/toolkit/test_guidecfg.py: `make_guide(root/"site"/"guide")`, `make_guide(root/"docs"/"guide")`, and a deeper `make_guide(root/"a"/"b"/"guide")`; CLI exit 3; stdout lines equal `sorted([str(p.resolve()) for p in (docs/guide, site/guide)])` exactly (deeper candidate absent); stderr contains `several guide projects`; Python API raises `DiscoverError` with code 3 and the two candidates
- [X] T013 [US2] Checkpoint: `uv run pytest tests/toolkit/test_guidecfg.py -k discover` passes, including the existing `test_discover_several_exits_3` (it checks names in combined output, so it needs no change)

## Phase 5: User Story 3, existing embedded guides keep working (P2)

**Goal**: Embedded guide in an immediate subdirectory still found and reported embedded; a standalone guide at depth 1 is now found.

**Independent Test**: existing embedded discover tests pass; the flipped assertion passes.

- [X] T014 [US3] In `test_discover_none_exits_4` in tests/toolkit/test_guidecfg.py, remove the final assertion block ("a subdirectory with a non-embedded guide.yaml is not an embedded guide"); keep the missing and empty directory cases
- [X] T015 [US3] Add `test_discover_standalone_immediate_subdirectory` in tests/toolkit/test_guidecfg.py: take the `embedded` fixture, drop its `embedded` block with `edit(embedded / "guide.yaml", lambda d: d.pop("embedded"))`, discover on `embedded.parent` returns `embedded` with exit 0, and `run_cli(embedded, "get", "embedded.front_page")` prints an empty line; also assert the unmodified fixture case still reports a non-empty `embedded.front_page` (FR-008)
- [X] T016 [US3] Add `test_discover_embedded_at_depth_two` in tests/toolkit/test_guidecfg.py: copy the `embedded` fixture directory to `tmp_path/"repo"/"docs"/"guide"` (`shutil.copytree`); discover on `tmp_path/"repo"` returns it with exit 0 (embedded guides deeper than depth 1 are found; their embedded status comes from the configuration, spec edge case). Then checkpoint: `uv run pytest tests/toolkit/test_guidecfg.py -k discover` passes (includes `test_discover_current_dir`, `test_discover_one_embedded_subdirectory`, `test_discover_empty_directory_means_a_new_separate_guide`)

## Phase 6: User Story 4, fast search that ignores non-guide material (P2)

**Goal**: Pruned directories are never candidates nor searched; nothing below a guide; depth 4 not found; unreadable directories skipped.

**Independent Test**: each pruned layout reports exit 4 or the real guide.

- [X] T017 [P] [US4] Add parametrized `test_discover_pruned_inside` in tests/toolkit/test_guidecfg.py over `.guide/cache/x`, `.git/x`, `node_modules/x`, `build/x`, `dist/x`, `target/x`, `docs/node_modules/x`: a guide only there gives exit 4. Add `test_discover_pruning_is_exact` with `make_guide(root/"Build")` found (exit 0) and, in a separate root, `make_guide(root/"node_modules_old")` found (exit 0)
- [X] T018 [P] [US4] Add `test_discover_pruned_dirs_are_not_candidates` in tests/toolkit/test_guidecfg.py: `make_guide(root/".docs")`, `make_guide(root/"build")`, and a directory symlink `root/"shared"` pointing to `make_guide(tmp_path/"elsewhere"/"g")`; exit 4. Also `make_guide(tmp_path/"outside"/"guide")` with a symlink `root/"link"` to `tmp_path/"outside"`: exit 4 (symlinked directory not entered)
- [X] T019 [P] [US4] Add `test_discover_not_below_a_guide` in tests/toolkit/test_guidecfg.py: `make_guide(root/"docs"/"guide")` and `make_guide(root/"docs"/"guide"/"examples")`; exit 0 with `docs/guide` (a depth 3 guide below a depth 2 guide is never reported)
- [X] T020 [P] [US4] Add `test_discover_depth_four_not_found` in tests/toolkit/test_guidecfg.py: `make_guide(root/"a"/"b"/"c"/"guide")`; exit 4, stdout empty, and stderr contains `or the directories below it (up to 3 levels)` (FR-009)
- [X] T021 [P] [US4] Add `test_discover_guide_yaml_entry_kinds` in tests/toolkit/test_guidecfg.py: a directory named `guide.yaml` at `root/"x"/"guide.yaml"` makes no candidate (exit 4); a symlink `root/"y"/"guide.yaml"` to a regular file makes `root/"y"` the result; a `root/"z"/"guide.yaml"` holding invalid YAML (`"a: ["`) makes `root/"z"` the result (discovery does not parse the file; separate roots per case)
- [X] T022 [P] [US4] Add `test_discover_unreadable_directory_skipped` in tests/toolkit/test_guidecfg.py (skip with `pytest.mark.skipif(os.geteuid() == 0, ...)`): `make_guide(root/"docs"/"guide")` plus `root/"locked"` with mode `0o000`; exit 0 with `docs/guide`; restore mode in a `finally` block
- [X] T023 [P] [US4] Add `test_discover_does_not_list_pruned_trees` in tests/toolkit/test_guidecfg.py (SC-004, same root skip): `make_guide(root/"docs"/"guide")` plus `root/"node_modules"` with mode `0o000`; call `guidecfg.discover(root)` directly in the test process (not the subprocess helper, which a monkeypatch cannot reach) and monkeypatch `os.scandir` via `monkeypatch.setattr(guidecfg.os, "scandir", wrapper)` to record every listed path and assert no recorded path is inside `node_modules`; restore mode in `finally`
- [X] T024 [US4] Checkpoint: `uv run pytest tests/toolkit/test_guidecfg.py -k discover` passes with T017 to T023

## Phase 7: Polish and cross-cutting (documents and skills)

- [X] T025 [P] Amend FR-031 in specs/005-embedded-guide/spec.md: replace the "immediate subdirectories" wording with the bounded search (depth 1 to 3, shallowest wins, ties stop and ask, standalone guides accepted, pruned hidden, `node_modules`, `build`, `dist`, `target`, symlinked directories, not below a guide) and append "(Amended by spec 007-nested-guide-discovery.)"; add the same amendment note to the clarification bullet at line 17 of that file
- [X] T026 [P] Update the `discover` row in specs/005-embedded-guide/contracts/toolkit-cli.md to match specs/007-nested-guide-discovery/contracts/discover-cli.md (one row, same wording style), and add an amendment note to the `discover` decision in specs/005-embedded-guide/research.md
- [X] T027 [P] Update guide/skills/preflight/SKILL.md: the `GUIDE` bullet (line 15), exit table rows 0, 3, and 4 (lines 30 to 32), and the stop message (line 35) to describe the search below `DIR` (up to three levels, embedded or standalone guides; exit 3: "Several guide projects found: <list>. Run the command again with --dir <one of them>."); keep the embedded `yes`/`no` rule based on `get embedded.front_page`, and add: when that `get` exits non-zero (invalid configuration), report `embedded=no` and leave the error to the command's own validation
- [X] T028 [P] Update guide/skills/create/SKILL.md section 3: exit 0 bullet mentions a guide found below the target; exit 3 bullet reads "several guide projects equally close below the target"
- [X] T029 [P] Update guide/skills/evolve/SKILL.md: the "Resolve the guide" bullet (line 85) to "from the host root it finds the one guide project in the directories below it (up to three levels)", and the `--dir` row (line 21) that says automatic discovery works only "from the root of a repository with an embedded guide" so it covers any guide found below the current directory
- [X] T030 Run `rg -n "immediate subdirector|several embedded|embedded guide subdirector|repository with an embedded guide|embedded guide in one of" guide/` and fix any match that describes discovery (FR-011); then run the dash check over the changed files: `git diff --name-only main | xargs python3 -c 'import sys; bad=[f for f in sys.argv[1:] if any(chr(c) in open(f, encoding="utf-8").read() for c in (0x2014, 0x2013))]; print(bad); sys.exit(bool(bad))'`
- [X] T031 Run `make test` and `make validate`; walk through specs/007-nested-guide-discovery/quickstart.md steps 1 to 5 and confirm the expected exits

## Dependencies

- T001 before everything. T002 before all test tasks. T003 to T006 (same file, sequential) before T010, T013, T016, T024.
- US1 (Phase 3) and US2 (Phase 4) depend only on Phase 2. US3 and US4 depend only on Phase 2. Phase 7 depends on Phase 2 for wording, and T031 runs last.

## Parallel Opportunities

- Test-writing tasks marked [P] touch the same test file; parallel only if done by one writer in one edit pass. Treat them as independent units of work, not concurrent edits.
- T025 to T029 touch different files and can run in parallel.

## Implementation Strategy

MVP is Phase 2 plus US1 (the reported cc-review problem). US2 to US4 harden the behavior; Phase 7 aligns specs and skills. Everything ships in one change.
