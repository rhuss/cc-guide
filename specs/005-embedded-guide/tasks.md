# Tasks: Embedded guide with the README as front page

**Input**: Design documents from `specs/005-embedded-guide/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (toolkit-cli.md, workflows.md, front-page.md), quickstart.md

**Tests**: Included. The spec's success criteria are verified by toolkit unit tests (`make test`) and an adapter smoke test (`make test-adapters`). Write each test task before the implementation task it covers and confirm it fails first.

**Repository rules for every task**: no em or en dash characters in any file (tests build them with `chr(0x2014)` / `chr(0x2013)`); toolkit modules import nothing outside `guide/toolkit/`; scripts never `cd` into `.guide/cache/`; commits end with `Assisted-By: 🤖 Claude Code`.

## Interfaces shared across tasks

Declared here so tasks agree on names (all in `guide/toolkit/`):
- `guidecfg.Embedded` dataclass: `front_page: Path`, `developer_readme: Path | None`, `stubs: list[Path]`, `pr_check: bool` (paths resolved against the guide root); `Guide.embedded: Embedded | None`.
- `guidecfg.host_toplevel(root) -> Path | None`: `git -C <root> rev-parse --show-toplevel`, None outside a repository.
- `guidecfg.embedded_front_page(root) -> Path | None`: reads only the `embedded.front_page` key and tolerates a missing `guide.yaml`; `pages(root, adapter, view)` calls it, so its eight callers need no change.
- `guidecfg.is_guide_owned(root, host_path) -> bool`: true for paths inside the guide subdirectory, the front page, the developer README, and stubs (used by check and embed).
- `guidecfg.Source` gains `web: str`, `fingerprints: dict[str, str]`, `front_page_blob: str`; `guidecfg.Input` gains `revision: str`, `blob: str`; `Input.path()` returns None for `self:` and resolves `local:` through `confidential.local.yaml`.
- Helper paths are made relative with `os.path.relpath(path.resolve(), root.resolve())`, so a front page prints as `../README.md`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1 to US5 from spec.md

---

## Phase 1: Setup

- [X] T001 Create the host repository fixture `tests/fixtures/mini-host/` (committed as plain files, turned into a git repo by a helper): `README.md` with a `# Mini Host` title, a badge line, user sections (`## Install`, `## Usage`) and developer sections (`## Building from source`, `## Running tests`) containing a relative link `docs/install.md` and `CONTRIBUTING.md`; `CONTRIBUTING.md`; `LICENSE`; `docs/install.md`; `USAGE.md`; `src/cli.py`; `config/defaults.yaml`; `Makefile`; `pyproject.toml` with `readme = "README.md"`.
- [X] T002 Add a `build_mini_host` helper and `mini_host` fixture to `tests/toolkit/conftest.py` that copies `tests/fixtures/mini-host/` into a temp dir, runs `git init -b main`, and commits with fixed author and dates (same approach as `build_mini_repo`), returning the host path and commit SHA.

---

## Phase 2: Foundational (blocks all user stories)

**Purpose**: configuration, discovery, the `self` source, and the front page as a page.

### Tests

- [X] T003 [P] Add embedded configuration tests to `tests/toolkit/test_guidecfg.py`: a valid `embedded` block loads; unknown keys under `embedded` fail; `embedded` with `format: mkdocs`, with `internal.enabled: true`, or with non-empty `internal.confidential_terms` fails (FR-004); `front_page` inside the guide root, outside the host toplevel, or not ending in `.md` fails; missing front page fails `validate` but passes with `--allow-missing-front-page`; `developer_readme` and `stubs` entries must resolve inside the host toplevel and outside the guide root.
- [X] T004 [P] Add `discover` tests to `tests/toolkit/test_guidecfg.py`: current dir with `guide.yaml` returns it; one embedded subdirectory returns it; two embedded subdirectories exit 3 listing both; none exits 4; a subdirectory with a non-embedded `guide.yaml` is ignored.
- [X] T005 [P] Add `confidential.local.yaml` tests to `tests/toolkit/test_guidecfg.py`: terms and patterns merge into `Guide.confidential_terms/patterns`; missing file means none; bad regex in the local file is a config error naming the file; `local:<id>` input locations resolve through the file's `inputs` map and fail with a clear message when the id is missing.
- [X] T006 [P] Add baseline and inputs schema tests to `tests/toolkit/test_guidecfg.py`: `self` allowed only when `embedded` is set and at most once; `fingerprints` allowed only on `self`, values 40 hex; `front_page_blob` 40 hex; `web` optional; inputs with `location: self:<path>` require `revision` (40 hex) and `blob` (40 hex) and are not refused as "inside the guide project"; `Input.path()` returns None for them; `local:` inputs are accepted only in embedded guides.
- [X] T007 [P] Add `pages()` and `_rel` tests: in `tests/toolkit/test_guidecfg.py`, `pages()` includes the front page in embedded mode and not otherwise; in `tests/toolkit/test_drift.py`, a report over an embedded guide lists the front page as exactly `../README.md` (regression for `drift._rel`, which raised before).
- [X] T008 [P] Add `self` fetch tests to `tests/toolkit/test_fetch.py` using `mini_host` with a guide subdirectory: `pin --source self=..` writes `repo: ..`, the host branch as `ref`, the HEAD commit, `web` from a GitHub `origin` (and none for a non-GitHub origin), and `fingerprints` for every `self:` path cited by pages; `fetch` exports the snapshot under `$XDG_CACHE_HOME/cc-guide/self/<hash>/<commit>/` (set `XDG_CACHE_HOME` to a temp dir) and creates nothing under `.guide/cache/self`; `where self` prints that path; `where <other>` prints the cache worktree; `where self --commit <sha>` exports and prints a snapshot of that commit (used by evolve for the target revision); `where` with an unknown id exits 2; with a working branch checked out, `pin` still records the host's default branch (`origin/HEAD`, else `main`, else `master`) as `ref` while pinning the working branch HEAD commit; uncommitted changes in the host are not visible in the snapshot; after `_rewrite_history` plus `git gc --prune=now` (or a fresh clone) makes the pinned commit unavailable, `fetch` exports the snapshot from the tracked head when all fingerprints match, and reports "pin unavailable" without failing when they do not; `rebaseline` recomputes fingerprints and writes `front_page_blob` (stored with `git hash-object -w`).

### Implementation

- [X] T009 Implement the `embedded` block in `guide/toolkit/guidecfg.py`: add `embedded` to `GUIDE_KEYS`; parse `front_page` (default `../README.md`), `developer_readme` (default none), `stubs` (list, default empty), `pr_check` (`off`|`on`, default `off`) into a new `Embedded` dataclass on `Guide`; validate per data-model.md ("`embedded` present requires `format: gfm`, `internal.enabled: false`, empty `internal.confidential_terms` and `internal.confidential_patterns`"; paths must resolve inside the host toplevel from `git -C <root> rev-parse --show-toplevel` and outside the guide root); add the `--allow-missing-front-page` flag to `validate`; add `embedded.*` keys to `GET_KEYS`. Makes T003 pass.
- [X] T010 Implement `discover` in `guide/toolkit/guidecfg.py` per contracts/toolkit-cli.md (exit 3 for several, exit 4 for none). Makes T004 pass.
- [X] T011 Implement `confidential.local.yaml` loading in `guide/toolkit/guidecfg.py` (`load_guide` merges `confidential_terms`, `confidential_patterns`; `load_inputs` resolves `local:<id>` locations from its `inputs` map). Makes T005 pass.
- [X] T012 Extend `load_baseline` and `load_inputs` in `guide/toolkit/guidecfg.py` for the `self` entry (`web`, `fingerprints`, `front_page_blob`) and for `self:`/`local:` input locations with `revision` and `blob`. Makes T006 pass.
- [X] T013 Make `guidecfg.pages()` append the front page when embedded, and make `drift._rel` in `guide/toolkit/drift.py` and `check._rel` in `guide/toolkit/check.py` use `os.path.relpath(path.resolve(), root.resolve())` so a front page prints as `../README.md`. Add `host_toplevel`, `embedded_front_page`, and `is_guide_owned` per the Interfaces section. Makes T007 pass.
- [X] T014 Implement the `self` source in `guide/toolkit/fetch.py`: resolve `repo: ..` to the host toplevel; `pin` reads refs with `git -C <toplevel>` (default `ref`: the host's default branch from `origin/HEAD`, else `main`, else `master`; default commit: the committed HEAD of the current branch), derives `web` from a GitHub `origin`, and computes `fingerprints` with `git -C <toplevel> rev-parse <commit>:<path>` for all `self` paths cited by pages (use `sources.cited_files`); `fetch` exports `git archive <commit>` into the XDG cache path and never creates `.guide/cache/self`; add the `where <id> [--commit <sha>]` subcommand (exit 2 for an unknown id); `rebaseline` recomputes fingerprints; when the pinned commit is missing, fall back on content per research R5 (snapshot from the tracked head when all fingerprints match). Point `sources._gitdir` in `guide/toolkit/sources.py` at the host git dir for `self` so `resolve` works. Makes T008 pass.
- [X] T015 Add `--embedded` to `guide/scripts/scaffold-project.sh` (gfm only, refuse other formats): skip `internal/`, copy the pointer page from a new `guide/adapters/gfm/embedded/docs/README.md` (one line linking `../../README.md`, with `<!-- guide: no-sources -->`), append `confidential.local.yaml` to the guide's `.gitignore`; refuse a target directory that exists, is not empty, and holds no `guide.yaml` (never merge into an unrelated directory). Add a test case to `tests/toolkit/test_scaffold_project.py` (no `internal/`, pointer page present, ignore entry present, mkdocs refused, non-empty unrelated directory refused, standalone scaffold output unchanged).

**Checkpoint**: `make test` passes; an embedded guide project can be scaffolded, configured, and pinned against its host.

---

## Phase 3: User Story 1, Turn an existing README into a verified front page (P1) 🎯 MVP

**Goal**: embedded create consolidates the existing docs after an approved move plan and produces a front page that builds, checks, and prints.

**Independent Test**: quickstart.md section 2, steps 1 to 3, first two expectation bullets, plus the self-citation failure.

### Tests

- [X] T016 [P] [US1] Add `tests/toolkit/test_embed.py` inventory tests: on `mini_host`, `embed.py inventory --format json` lists `README.md` (kind `readme`, with its headings), `CONTRIBUTING.md` (`community`), `LICENSE` (`license`), `docs/install.md` (`doc-file`) and `docs/` (`doc-dir`), `USAGE.md` (`doc-file`), flags `pyproject.toml` as publishing the README; a `.github/README.md` is listed as `github-readme`; a directory with `mkdocs.yml` is `doc-site`; nothing under the guide subdirectory is listed.
- [X] T017 [P] [US1] Add `apply` tests to `tests/toolkit/test_embed.py`: with a move plan moving `Building from source` and `Running tests` to `DEVELOPMENT.md`, the sections are moved with text unchanged except heading levels and relative links rewritten to resolve from the new path; an existing `DEVELOPMENT.md` gets the sections appended under `## Moved from the README`; `self:` inputs are registered with `revision` and `blob`; `.github/README.md` relocation works; an uncommitted guide subdirectory does not count as dirty, while uncommitted changes outside it are refused; a plan path that does not exist at `self_revision`, a plan that removes `LICENSE`, a section heading that is not found, `stub: true` on `.github/README*`, and `stub: true` on a root README are refused with exit 2 and change nothing; a non-Markdown root README (`README.rst`) accepts only `input` plus removal or `relocate`; `--dry-run` changes nothing.
- [X] T018 [P] [US1] Add front page checks to `tests/toolkit/test_check.py`: in embedded mode the front page is checked (missing sources block fails, broken link fails, dash character built with `chr(0x2014)` fails, confidential term from `confidential.local.yaml` fails); `--structure` reads section titles from the front page, not `docs/README.md`; a source entry citing `self:guide/docs/x.md`, `self:README.md`, `self:DEVELOPMENT.md`, or a stub path fails (FR-012); a `self` citation without a fingerprint reports the rebaseline hint; in a guide whose only source is `self` (no `.guide/cache/`), a citation of a missing path or out-of-range lines fails; with the pinned commit unavailable (fresh clone after a simulated squash), citations resolve from fingerprint blobs and `make check` style checking passes, and a citation whose blob is gone resolves against the head with a warning instead of an error; a front page whose first line is not the ownership comment fails; with `--structure`, a section title present in `docs/SUMMARY.md` but missing from the front page fails; `DEVELOPMENT.md` broken relative link fails, but missing sources block and dash rules do not apply to it.
- [X] T019 [P] [US1] Add staging tests to `tests/toolkit/test_embed.py`: `embed.py stage --out build/stage` writes `build/stage/docs/README.md` equal to the front page with `guide/docs/x.md` links rewritten to `x.md`, image paths rewritten, links to host files (`DEVELOPMENT.md`, `LICENSE`) rewritten to `<web>/blob/<ref>/<path>` when `web` is set; links in staged guide pages that point at the front page (for example `../../README.md` from `docs/admin/x.md`, and the pointer page's link) are rewritten to the staged `README.md`; non-embedded guides exit 2.
- [X] T020 [P] [US1] Add attrs tests to `tests/toolkit/test_attrs.py`: regions in the front page are rewritten; `self-blob`/`self-tree` use `<web>/blob/<ref>/` and `<web>/tree/<ref>/` and are absent when `web` is missing.

### Implementation

- [X] T021 [US1] Create `guide/toolkit/embed.py` (PEP 723 header, `pyyaml`, `--root`) with `inventory` per contracts/toolkit-cli.md and research R12 detection rules (root README any format, `.github/README*`, `docs/README*`, `CONTRIBUTING*`, `CODE_OF_CONDUCT*`, `SECURITY*`, `SUPPORT*`, `INSTALL*`, `USAGE*`, `CHANGELOG*`, `LICENSE*`, `docs/`, `doc/`, `documentation/`, directories containing `mkdocs.yml`, `antora.yml`, `conf.py`, or `docusaurus.config.*`; manifests `pyproject.toml` `project.readme`, `package.json`, `Cargo.toml` `readme`). Read from the host at HEAD with `git -C <toplevel> ls-files` so ignored files and the guide subdirectory are skipped. Makes T016 pass.
- [X] T022 [US1] Implement `embed.py apply --plan FILE [--dry-run]` (dirty check only outside the guide subdirectory: `git status --porcelain -- . ':!<guide dir>'`) per data-model.md move plan rules ("every `path` exists at `self_revision`"; "`remove` and `stub: true` entries are documentation files only (never `LICENSE*`, never files outside the inventory)"; the root README only `input` plus `developer` sections; non-Markdown README `input` plus removal or `relocate`). Section extraction by heading (to the next heading of the same or higher level), heading level adjustment, relative link rewriting, append under `## Moved from the README` for an existing developer README, `self:` input registration in `inputs.yaml`, relocation, and update of `embedded.developer_readme`. Stub writing is added in US3 (T040); until then `apply` refuses `stub: true` entries with a "stubs not implemented yet" error. Makes T017 pass.
- [X] T023 [US1] Implement embedded checks in `guide/toolkit/check.py`: front page as a page (via `pages()`), dash check on the front page, `check_structure` reads the front page when embedded, the FR-012 self-citation ban (via `is_guide_owned`), missing-fingerprint hint, resolution of `self` citations whenever `self` is in the baseline (not only when `.guide/cache/` exists, check.py:534), section titles read from the front page only in embedded mode, the ownership comment as the first front page line, developer README link check without page rules. Makes T018 pass.
- [X] T024 [US1] Implement `embed.py stage --out DIR` per research R3, including the rewrite of staged links that point at the front page. Makes T019 pass.
- [X] T025 [US1] Update `guide/toolkit/attrs.py`: region rewriting covers the front page when embedded; `self` web links use the tracked branch (`web`, `ref`). Makes T020 pass.
- [X] T026 [US1] Give `guide/adapters/gfm/scaffold/pandoc/render.sh` and `print.sh` a docs directory parameter (default `docs`, so standalone output is unchanged) and update `guide/adapters/gfm/scaffold/Makefile`: when `uv run tools/guide/guidecfg.py get embedded.front_page` is non-empty, `site`, `check`, and `print-pdf` run `embed.py stage --out build/stage` first and render from `build/stage/docs`; `regions` includes the front page; `preview` serves the host toplevel with markserv and opens `README.md`. Update the comment in `guide/adapters/gfm/adapter.yaml`.
- [X] T027 [P] [US1] Make `upstream._own_remotes` in `guide/toolkit/upstream.py` use the git toplevel of the guide root and make `upstream._bare` (upstream.py:137-147, 263) read `self` from the host git directory; replace `.guide/cache/<id>` reading paths in `guide/skills/upstream/SKILL.md` (line 26) with `fetch.py where <id>`; and make `guide/toolkit/ledger.py` default the strict claim ledger to `ledger/claims.md` in the guide root when embedded; add tests to `tests/toolkit/test_upstream.py` (own remotes and a `self` finding re-verified from the host) and `tests/toolkit/test_ledger.py`.
- [X] T028 [P] [US1] Write `guide/skills/page-task/front-page-contract.md` from contracts/front-page.md (nine rules) and register it in `guide/skills/page-task/SKILL.md` (files table, setup copy, dispatch additions for the front page task), `guide/skills/page-task/global-constraints.template.md`, the gfm snippet in `guide/skills/page-task/page-procedure.md`, and check 7 in `guide/skills/page-task/page-review-guide.md`. In the same files, replace every hard-coded `.guide/cache/<id>` reading path (page-procedure.md:14, page-review-guide.md:14, 32, 36, page-task/SKILL.md:37) with the path printed by `fetch.py where <id>`.
- [X] T029 [US1] Update `guide/skills/preflight/SKILL.md`: resolve `GUIDE` with `guidecfg.py discover` (from `$PLUGIN/toolkit/` when the guide has no toolkit yet), handle exit 3 and 4 per FR-031, and add `embedded=yes|no` to the result line.
- [X] T030 [US1] Add the embedded target, intake, and setup to `guide/skills/create/SKILL.md` (sections 3 to 5) per contracts/front-page.md: target detection with `discover` and the `--embedded` argument; refusal of an existing non-empty non-guide subdirectory; clean tree (outside the guide subdirectory) and default-branch preconditions; embedded intake (subdirectory, developer README path, gfm only, no internal part, no remote, confidential terms to `confidential.local.yaml`, confidential inputs registered as `local:<id>` with the real location only in that file); setup without `git init` using `scaffold-project.sh --embedded`, `fetch.py pin --source self=..`, host-root session files in `.git/info/exclude`. Replace hard-coded `.guide/cache/<id>/` reading paths in the create skill with `fetch.py where <id>`.
- [X] T030a [US1] Add section 5a Consolidation to `guide/skills/create/SKILL.md`: `embed.py inventory`; classification rules (user-facing to input, development to developer README, `LICENSE*` and community health files kept where GitHub detects them, changelog kept, documentation sites kept with pages as input by default, a host without README gets a new front page and no developer README unless there is development material); the move plan table with removals and flagged manifests; author edits; approval; `embed.py apply`; decline path (stop, offer to remove the uncommitted guide subdirectory).
- [X] T030b [US1] Add the embedded execution and wrap-up to `guide/skills/create/SKILL.md` (sections 6 to 9): front page as start page in the guide spec and plan; front page task with the contract; final review with `check.py --structure`; final `fetch.py rebaseline` (fingerprints) and `embed.py front-page-status --record` after the last check; run summary with dropped claims and upstream candidates only for kept material, never naming `local:` input locations. Make `guide/toolkit/runs.py` `summary` and `findings-add` print only the id for `local:` inputs, with a test in `tests/toolkit/test_runs.py` that a run summary never contains a `local:` location.
- [X] T031 [P] [US1] Update `guide/skills/preview/SKILL.md` to open `README.md` in embedded mode, and add the commented `embedded` block to `guide/templates/guide.yaml`, a `guide/templates/confidential.local.yaml` example, and a "Dropped claims" section to `guide/templates/run-summary.md`.
- [X] T032 [US1] Create `tests/adapters/test_gfm_embedded.sh` (reuse `tests/adapters/scaffold.sh` helpers and `CC_GUIDE_NODE_MODULES`): build the host from `tests/fixtures/mini-host/`, scaffold `--embedded` into `host/guide`, pin `self`, apply a fixture move plan, install fixture pages and a fixture front page citing `self`, run `make -C host/guide check dist print-pdf`; assert the front page title is in `build/site`, the first content page of the PDF is the front page (`pdftext.py`), before `apply`, `git status --porcelain -- . ':!guide'` is empty; after the run it lists exactly the allowed paths (front page, `DEVELOPMENT.md`, files named in the plan); host `Makefile` and `pyproject.toml` are unchanged (`cmp`), `LICENSE` is at the root, `DEVELOPMENT.md` links resolve, and a page citing `self:guide/docs/x.md` makes `make check` fail. The fixture move plan in this phase has no `stub: true` entries (stubs arrive in T042).

**Checkpoint**: US1 independently testable with `make test` and `tests/adapters/test_gfm_embedded.sh`.

---

## Phase 4: User Story 2, Keep the README front page current with evolve (P1)

**Goal**: drift and evolve treat the front page like any page, with squash-safe `self` drift and hand-edit detection.

**Independent Test**: quickstart.md section 2, the drift, squash, and front-page-status bullets.

### Tests

- [X] T033 [P] [US2] Add fingerprint drift tests to `tests/toolkit/test_drift.py` with `mini_host`: a commit touching only guide files gives exit 0; a change to a file cited by the front page gives exit 10 with `../README.md` in `affected_pages`; deleting a cited file reports `deleted`; after `_rewrite_history` makes the pin unreachable, unchanged cited files give exit 0 with `mode: fingerprint` and no `pin-missing`, changed ones give exit 10; `self:` inputs report `recorded`; `local:` inputs show only the id in markdown and JSON output; an external `file://` source next to `self` keeps commit mode and reports its own drift as today (FR-015).
- [X] T034 [P] [US2] Add `front-page-status` tests to `tests/toolkit/test_embed.py`: unchanged front page prints `unchanged` exit 0; a hand edit after `--record` prints `edited` with a unified diff exit 10; a `make regions` style rewrite of a generated region after `--record` still prints `unchanged` (regions are normalized before comparing).

### Implementation

- [X] T035 [US2] Implement fingerprint mode for `self` in `guide/toolkit/drift.py` (`_source_state` and `report`): compare `fingerprints` with blob ids at the tracked branch head, skip `_pin_reachable` for `self`, add commit log and renames only when the pin is reachable, report `mode`; `recorded` status for `self:` inputs; mask `local:` locations in `to_markdown` and JSON. Makes T033 pass.
- [X] T036 [US2] Implement `embed.py front-page-status [--record]`: `--record` stores the front page blob (`git hash-object -w`, after normalizing generated `guide:attr` regions) as `front_page_blob` on the `self` baseline entry; without it, compare and report. Makes T034 pass.
- [X] T037 [US2] Update `guide/skills/evolve/SKILL.md` per contracts/front-page.md "evolve skill: embedded additions": resolve with `discover`; run `embed.py front-page-status` before planning and ask before overwriting hand edits; include the front page in the impact set; never create, move, or remove files outside the guide subdirectory; for `self`, the target revision is the committed HEAD of the current branch and the target snapshot comes from `fetch.py where self --commit <sha>` (no `-next` worktree under `.guide/cache/`); rebaseline recomputes fingerprints, then `embed.py front-page-status --record` runs after the final `make check`; read sources through `fetch.py where <id>`.
- [X] T038 [US2] Extend `tests/adapters/test_gfm_embedded.sh`: commit a guide-only change and assert `drift.py --check` exits 0; change a cited file and assert exit 10 listing `../README.md`.

**Checkpoint**: US1 and US2 together form the complete P1 slice.

---

## Phase 5: User Story 3, Old documentation links keep working (P2)

**Goal**: removed documentation paths keep stubs that checks accept and evolve keeps pointing at the right page.

**Independent Test**: quickstart.md section 2, the stub bullet.

### Tests

- [X] T039 [P] [US3] Add stub tests: in `tests/toolkit/test_embed.py`, `apply` with `stub: true` on `docs/install.md` and `USAGE.md` writes stubs with exactly `<!-- guide: moved -->`, one heading (the old title), and one link to the front page, adds them to `embedded.stubs`, and registers the originals as `self:` inputs; `retarget docs/install.md=guide/docs/admin/install.md` rewrites only that stub's link relative to the stub; a removed file with no destination keeps the front page link; `stub: true` on `.github/README*` or a root README is refused (FR-023 exemption). In `tests/toolkit/test_check.py`, stubs with a resolving link pass without a sources block; a stub with a broken link, two links, or a missing marker fails; the `STUB` unfinished-page marker logic is unaffected.

### Implementation

- [X] T040 [US3] Implement stub writing in `embed.py apply` (remove the T022 refusal) and `embed.py retarget OLD=NEW ...` in `guide/toolkit/embed.py`; implement stub checks in `guide/toolkit/check.py`. Makes T039 pass.
- [X] T041 [US3] Wire stubs into the skills: in `guide/skills/create/SKILL.md` the guide plan maps every stubbed path to its covering page and the run calls `embed.py retarget` after the last page task; in `guide/skills/evolve/SKILL.md` renamed or removed pages trigger `embed.py retarget` for affected stubs and front page links.
- [X] T042 [US3] Extend `tests/adapters/test_gfm_embedded.sh`: the fixture plan stubs `docs/install.md`; assert the stub exists, links to the guide page, and `make check` passes.

---

## Phase 6: User Story 4, Optional drift check on every pull request (P2)

**Goal**: an opt-in workflow fails pull requests that change cited files without re-verifying the guide.

**Independent Test**: quickstart.md section 2, the PR mode bullet, plus workflow template rendering tests.

### Tests

- [X] T043 [P] [US4] Add PR mode tests to `tests/toolkit/test_drift.py` with `mini_host` branches: no cited change gives exit 0; cited change without a `self` baseline change gives exit 10 naming the file and affected pages; cited change with a changed `self` entry whose fingerprints match head gives exit 0; a further push changing a cited file after rebaseline gives exit 10; `GUIDE_SKIP=1` gives exit 0 with "skipped by request"; external source drift is ignored; `--format json` matches the data-model.md PR shape; `--check --source self` limits the report; a base commit without `<guide dir>/baseline.yaml` (the pull request that introduces the guide) counts as "baseline changed"; a cited file at head without a fingerprint counts as a mismatch (fail); a cited file deleted in the pull request is reported as changed; a base SHA missing from the checkout exits 2.
- [X] T044 [P] [US4] Add template rendering tests to `tests/toolkit/test_scaffold_project.py` (or a new `tests/toolkit/test_workflows.py`): `guide-drift.yml` with `{{GUIDE_DIR}}` rendered to `.` is equivalent to the current template's behavior (same jobs and steps, working directory `.`); rendered to `guide` sets `defaults.run.working-directory: guide`; `guide-pr-check.yml` parses as YAML, has `permissions: contents: read` only, `fetch-depth: 0`, the `guide-skip` label condition, and the `--pr --base --head` call.

### Implementation

- [X] T045 [US4] Implement `--pr --base <sha> [--head <sha>]` and `--source <id>` in `guide/toolkit/drift.py` per research R7 and contracts/toolkit-cli.md (read the base baseline with `git -C <toplevel> show <base>:<guide dir>/baseline.yaml`; cited files from pages at head). Makes T043 pass.
- [X] T046 [US4] Add `{{GUIDE_DIR}}` to `guide/templates/guide-drift.yml` (`defaults.run.working-directory`) and create `guide/templates/guide-pr-check.yml` per contracts/workflows.md. Makes T044 pass.
- [X] T047 [US4] Update `guide/skills/create/SKILL.md`: offer the PR check (default no) in embedded intake, record `embedded.pr_check`, render `{{GUIDE_DIR}}` for both workflows (`.` for separate guides), install into the host's `.github/workflows/` only on opt-in, stop before overwriting an existing file, and mention the `guide-skip` label in the closing summary.
- [X] T048 [US4] Extend `tests/adapters/test_gfm_embedded.sh`: on a branch, change a cited file; assert `drift.py --pr --base main` exits 10, and exits 0 with `GUIDE_SKIP=1`; assert the PR check finishes in under 60 seconds and `embed.py stage` in under 1 second on the fixture (plan Performance Goals).

---

## Phase 7: User Story 5, Separate guides keep working unchanged (P3)

**Goal**: no regression for standalone guides and other formats.

**Independent Test**: full existing test suites plus the create flow on an empty directory.

- [X] T049 [US5] Run `make test` and `make test-adapters` and fix any regression in standalone gfm, mkdocs, and antora output; confirm `tests/adapters/test_gfm.sh` still finds `build/site/README.html` and `tests/adapters/test_pdf.sh` format detection is unchanged.
- [X] T050 [US5] Verify in `guide/skills/create/SKILL.md` and `guide/skills/preflight/SKILL.md` that an empty target directory never offers embedded mode and keeps the remote offer, and that `--embedded` with `--format antora|mkdocs` explains the gfm-only rule; add a `tests/toolkit/test_guidecfg.py` case that `discover` on an empty directory exits 4 (create then follows the standalone flow).

---

## Phase 8: Polish and cross-cutting

- [X] T051 [P] Write `guide/docs/embedded.md` (author documentation: when to choose embedded mode, layout, consolidation and move plan, stubs, developer README, `self` source and fingerprints, PR check and `guide-skip`, confidential terms in `confidential.local.yaml`, limits: gfm only, no internal part, no monorepo subdirectories) and link it from `README.md` and `guide/docs/adapters.md`.
- [X] T052 [P] Update `specs/001-cc-guide-plugin/contracts/adapter.md`, `commands.md` (discovery, create target rules, evolve), and `page-conventions.md` (self-citation ban, front page links) to reference embedded mode.
- [X] T053 Run the dash check over all changed files (`rg "[\x{2013}\x{2014}]"` must find nothing outside tests that build the characters with `chr()`), `make validate`, `make test`, and `make test-adapters`.
- [X] T054 Record a manual embedded run per quickstart.md section 3 as `tests/manual/embedded-quickstart.md` (steps, observations, deviations); if a live Claude Code run is not possible in this session, write the procedure with an explicit "not yet run" status.

---

## Dependencies and execution order

- Phase 1 then Phase 2 block everything.
- US1 (Phase 3) depends on Phase 2. US2 (Phase 4) depends on Phase 2 and on T021/T022/T024 only for the shared adapter test file; its toolkit work (T033, T035) can start right after Phase 2.
- US3 (Phase 5) depends on T022 (apply) and T023 (checks).
- US4 (Phase 6) depends on T035 (fingerprint mode) for the PR comparison.
- US5 (Phase 7) runs after all stories.
- Polish last.

Within a story: tests first (confirm they fail), then implementation, then the smoke test extension.

## Parallel opportunities

- Phase 2 tests T003 to T008 are all [P] (different test files or independent cases); implementation T009 to T013 touch `guidecfg.py` and must run in order; T014 and T015 can run in parallel with each other after T012.
- US1 tests T016 to T020 are [P]; T027, T028, T031 are [P] with the toolkit work.
- US2 T033/T034 [P]; US4 T043/T044 [P].

## Implementation strategy

MVP is Phase 1, Phase 2, US1, and US2 (both P1): an embedded guide that can be created from an existing repository and kept current. US3 (stubs) and US4 (PR check) follow as independent increments; US5 is the regression gate before merge.
