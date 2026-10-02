# Tasks: cc-guide, a plugin for source-verified guides

**Input**: Design documents from `specs/001-cc-guide-plugin/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Requested by the plan. The toolkit is developed test-first with pytest (`uv run --with pytest --with pyyaml pytest`); adapters get shell smoke tests; judgment-heavy skills get agent-eval-harness cases; full runs are manual quickstart scenarios recorded under `tests/manual/`.

**Organization**: One phase per user story in priority order. User Story 1 spans two phases: core create with the Antora adapter (MVP), then the MkDocs and GitHub Markdown adapters.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: User story from spec.md (US1 to US6)

## Path Conventions

- Plugin: `guide/` (installed); repository tooling and tests at the root.
- Toolkit sources: `guide/toolkit/` (copied into guide projects as `tools/guide/`).
- "Source block" is short for the spec's "source reference block" (FR-010, `contracts/page-conventions.md` section 1).
- All Python toolkit scripts carry PEP 723 metadata (`dependencies = ["pyyaml"]`, plus `pypdf` where noted) and run with `uv run`.

## Global Constraints

Copied from the spec and plan; every task inherits them.

- No em dash or en dash characters in any file.
- `uv` instead of pip; podman instead of Docker in any container instruction.
- No secrets, tokens, kubeconfig content, or raw inputs (transcripts, notes, ticket exports) written into a guide project (FR-005, FR-039a).
- Every outward action (remote repository, push, issue, pull request, cluster mutation) is shown in full and runs only after explicit approval (FR-005c, FR-033, FR-039).
- Subagents are dispatched without a model override.
- Git commits end with the trailer `Assisted-By: 🤖 Claude Code`.
- Scripts never `cd` into `.guide/cache/` and never run git there except through `git -C <cache path>` from the guide project root.
- Interfaces between tasks use the names defined in the task that introduces them; later tasks list them under **Interfaces**.

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Create the repository skeleton:
  - `.claude-plugin/marketplace.json`: marketplace `guide-plugin-development`, one plugin `guide`, `"source": "./guide"`, owner Roland Huss.
  - `guide/.claude-plugin/plugin.json`: name `guide`, version `0.1.0`, MIT, repository `https://github.com/rhuss/cc-guide`, keywords.
  - `CLAUDE.md`: the repository rules from Global Constraints.
  - Shape follows `~/Development/context-engineering/cc-prose/.claude-plugin/` and `cc-prose/prose/.claude-plugin/plugin.json`.
  - Dependency declaration check (research R2): try declaring `superpowers` in `plugin.json` `dependencies`. Keep it only if `claude plugin validate ./guide` accepts it and an install without superpowers reports the missing dependency. Otherwise remove it and note the result in `guide/docs/settings.md` (T061). The runtime check (T017) stays either way.
- [X] T002 Create the root `Makefile`, modeled on `cc-prose/Makefile`, with these targets:
  - `validate`: `claude plugin validate .` and `./guide`.
  - `install` and `uninstall`: idempotent marketplace add and plugin install of `guide@guide-plugin-development`.
  - `test`: `uv run --with pytest --with pyyaml --with pypdf pytest tests/toolkit`.
  - `test-adapters`: runs `tests/adapters/*.sh`.
  - `eval` and `help`.
- [X] T003 [P] Create `pyproject.toml` (pytest configuration only: testpaths `tests/toolkit`, pythonpath `guide/toolkit`). Add `tests/toolkit/conftest.py` with fixtures:
  - `tmp_guide(tmp_path)`: an empty guide project directory.
  - `fixture_repo(tmp_path)`: builds the mini-project git repository by running `tests/fixtures/make-mini-repo.sh` and returns `(path, first_commit, second_commit, third_commit)` parsed from its output.
  - `render_fixture_guide(tmp_path, fixture_repo)`: copies `tests/fixtures/sample-guide/` and renders `baseline.yaml.tmpl` into `baseline.yaml` with the repository URL and `MINI_FIRST_COMMIT`.
- [X] T004 [P] Create the fixture project `tests/fixtures/mini-project/`:
  - `README.md` claims the service listens on port 8080, while `config/defaults.yaml` sets `port: 9090` (planted drift).
  - `Makefile` with targets `install` and `status`.
  - `docs/setup.md`.
  - `tests/fixtures/make-mini-repo.sh <dest>`: creates a git repository with three commits and prints their SHAs as `FIRST=`, `SECOND=`, `THIRD=` lines.
    - The second commit changes `config/defaults.yaml`, so drift tests have a changed cited file.
    - The third commit renames `docs/setup.md` to `docs/install.md` and deletes `Makefile`, so drift tests cover renames and deletions.
    - It sets `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_NAME`, and `GIT_COMMITTER_EMAIL` to fixed values and `GIT_AUTHOR_DATE` and `GIT_COMMITTER_DATE` to fixed per-commit timestamps, so the SHAs are deterministic across machines.
  - `tests/fixtures/mini-transcript.txt`: says the admin UI is on port 7070, which no source supports (planted false claim).
  - `tests/fixtures/mini-confidential-notes.txt`: names `ACME Corp` as the first customer and gives a rollout date (confidential input).
- [X] T005 [P] Create the format-neutral fixture guide `tests/fixtures/sample-guide/`:
  - `guide.yaml`: two personas `admin` and `user`; internal part enabled; confidential term `ACME Corp`; pattern `\b[A-Z]{2,}-\d+\b`.
  - `baseline.yaml.tmpl`: one source `mini`, `repo: {{MINI_REPO_URL}}`, `commit: {{MINI_FIRST_COMMIT}}`, with an attribute `version: 1.2.3`. It is rendered by `conftest.py` (`render_fixture_guide`) and by `tests/adapters/scaffold.sh` from the output of `make-mini-repo.sh`.
  - `inputs.yaml` additionally registers `tests/fixtures/mini-confidential-notes.txt` with `confidential: true` (a note naming `ACME Corp` as the first customer), so the confidential-input rules can be tested.
  - `inputs.yaml`: references `tests/fixtures/mini-transcript.txt`.
  - `pages/`: four neutral pages (index, admin/install, user/start, internal/notes). Each page has a source block, a `Check:` step with an expectation, one experimental label, and one baseline value. Neutral page format, converted by `tests/adapters/convert.py` (T025):
    - Markdown body with an HTML-comment source block and HTML-comment expectations exactly as in `contracts/page-conventions.md`
    - admonitions as `:::note`, `:::tip`, `:::important`, `:::warning`, `:::caution` blocks closed by `:::`
    - experimental labels as `:::experimental feature="..." pr=N anchor=... tier=in-review|on-main`
    - baseline values as `{{attr:<name>}}`
    - navigation order in `pages/nav.yaml`
  - `tests/fixtures/make-large-guide.py`: generates a 25-page variant of the sample guide (repeating and renaming the four pages) for the timing checks in T064.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The toolkit core and the shared preflight that every command needs.

- [X] T006 [P] Write `tests/toolkit/test_guidecfg.py` covering:
  - a valid guide, baseline, and inputs load
  - unknown keys fail
  - a `format` without an adapter fails
  - an input `location` inside the guide project is rejected
  - a baseline `commit` that is not a 40-hex SHA fails
  - a change request referencing an unknown source fails
  - `disposable` defaults to false
- [X] T007 Implement `guide/toolkit/guidecfg.py`, which loads and validates the three files per data-model.md. Interfaces produced:
  - `load_guide(root: Path) -> Guide`
  - `load_baseline(root: Path) -> Baseline`
  - `load_inputs(root: Path) -> Inputs`
  - dataclasses `Guide`, `Persona`, `Section`, `Cluster`, `Baseline`, `Source`, `ChangeRequest`, `Inputs`, `Input`
  - exception `ConfigError(path, message)`
  - CLI `uv run guidecfg.py validate [--root DIR]`, exiting non-zero with `file:key: message` lines on failure
- [X] T008 [P] Write `tests/toolkit/test_sources.py` covering:
  - the AsciiDoc line-comment block and the HTML-comment block
  - the grammar in `contracts/page-conventions.md` section 1, including `input:<id>` references
  - blocks inside listings ignored
  - the no-sources markers
  - an unknown source id
  - a path missing at the pinned commit
  - a line range beyond the end of the file
- [X] T009 Implement `guide/toolkit/sources.py`. Interfaces produced:
  - `parse_block(text: str, style: Literal["line","html"]) -> list[Ref]`
  - `Ref(kind: "source"|"url"|"input", source_id, path, ranges, url, input_id)`
  - `resolve(ref: Ref, baseline: Baseline, cache_dir: Path) -> Resolution(ok: bool, message: str)`, reading files with `git -C <cache>/<id> show <commit>:<path>`
  - `cited_files(pages: list[Path], style) -> dict[source_id, set[path]]`
  - CLI `sources.py check PAGE...`
- [X] T010 [P] Write `tests/toolkit/test_fetch.py`, using `fixture_repo` with `file://` URLs, covering:
  - pin writes the full SHA for `repo@ref`
  - fetch creates `.guide/cache/<id>.git` and a worktree at the pinned commit
  - an unreachable source fails, or with `--allow-unverified` gets status `unverified`
  - no command changes the process working directory
- [X] T011 Implement `guide/toolkit/fetch.py`, ported from saw-guide `scripts/fetch-baseline.sh`, with three subcommands:
  - `pin --source ID=REPO[@REF]...` writes or updates `baseline.yaml`.
  - `fetch [--allow-unverified]` makes blobless bare clones plus pinned worktrees under `.guide/cache/`.
  - `rebaseline --to ID=REF...` writes new commits, `captured: today`, and the change-request states.

  Interfaces produced: `pin(root, specs) -> Baseline`, `fetch(root, allow_unverified=False) -> dict[source_id, status]`, and `rebaseline(root, targets) -> Baseline`.
- [X] T012 [P] Write `tests/toolkit/test_check.py` covering:
  - em and en dashes
  - more than one sentence per line in `.adoc` (abbreviations such as `e.g.` and version numbers are not sentence ends)
  - typed values that equal any baseline commit, short commit, or attribute value
  - a missing source block
  - `// STUB` pages under `STRICT=1`
  - rule files with `require`, `forbid`, and `require_order` per page glob
  - an `input:<id>` reference on a shareable page fails, and so does an `input:` reference to an id missing from `inputs.yaml`
  - an AsciiDoc `image::` macro whose alt text contains a comma without quotes fails (FR-019)
  - an Antora diagram image (from `diagrams/` exports) without `role=expand` fails (FR-022a)
- [X] T013 Implement `guide/toolkit/check.py`. It generalizes saw-guide `scripts/check-content.sh` into data-driven rules read from an optional `guide-rules.yaml` (per glob: `require`, `forbid`, `require_order` regex lists), plus the built-in global checks above. Interfaces produced:
  - `check_pages(root: Path, guide: Guide, baseline: Baseline, strict: bool) -> list[Violation(path, line, rule, message)]`
  - CLI `check.py [--strict]`, which exits 1 on violations
- [X] T014 [P] Write `tests/toolkit/test_leakcheck.py` covering:
  - a confidential term in built HTML
  - a ticket-key pattern match
  - a link into the internal part
  - a term inside PDF text (pypdf)
  - a clean build passes
- [X] T015 Implement `guide/toolkit/leakcheck.py`, with PEP 723 dependencies `pyyaml` and `pypdf`:
  - `scan_dir(path, guide) -> list[Leak]`
  - `scan_pdf(path, guide) -> list[Leak]`
  - CLI `leakcheck.py DIR_OR_PDF...`, which exits 1 on leaks

  Terms are matched case-insensitively and patterns as regex; internal links are detected by the adapter's `internal_root`.
- [X] T016 [P] Implement `guide/toolkit/doctor.py` with `tests/toolkit/test_doctor.py`. It reads `requires` from the adapter descriptor (copied into the guide project as `tools/guide/adapter.yaml`), checks the installed versions (`node --version`, `npx antora --version`, `mkdocs --version`, `pandoc --version`, `npx markserv --version`, Playwright Chromium), and prints one install hint per missing tool (`uv tool install`, `npm install`, `brew install`). Exit codes: 0 when everything is present, 1 when something is missing.
- [X] T017 Implement the superpowers contract probe in `guide/scripts/superpowers-probe.sh` and `guide/compat.yaml` (known-good: `6.3.0`, `6.4.1`). The probe:
  - reads `installPath` for `superpowers@*` from `~/.claude/plugins/installed_plugins.json` (honor `$HOME`; pick the `user` scope entry)
  - checks for the skills `brainstorming`, `writing-plans`, `subagent-driven-development`, and `requesting-code-review`
  - runs `bash <installPath>/skills/subagent-driven-development/scripts/{sdd-workspace,task-brief,review-package}` without arguments and expects exit 2 plus a `usage:` line
  - prints JSON `{installPath, version, known, ok, problems[]}`
  - exits 0 when ok, 3 when ok but the version is unknown, and 4 when the probe failed

  Test: `tests/toolkit/test_probe.py`, using a fake `$HOME` with fake plugin trees for the ok, unknown-version, and missing-script cases.
- [X] T018 [P] Implement `guide/scripts/deps.sh`. It prints JSON `{superpowers: bool, prose: bool, excalidraw_allowed: bool}`, where `prose` comes from `installed_plugins.json` keys starting with `prose@` and `excalidraw_allowed` from `.claude/settings.local.json` or `.claude/settings.json` in the guide project containing an `mcp__excalidraw` allow entry. Test: `tests/toolkit/test_deps.py`.
- [X] T019 Write the preflight skill `guide/skills/preflight/SKILL.md`, which implements "Shared preflight" from `contracts/commands.md`:
  - resolve the guide project (`--dir` or the current directory; `guide.yaml` required except for create)
  - run `deps.sh` and `superpowers-probe.sh` (for create and evolve without `--check`), then `make doctor` when a guide project exists
  - show the one-line notice when cc-prose is absent (FR-003a)
  - state the recommended model and effort and warn when the session model differs (FR-042)
  - stop before writing any file when a requirement fails (SC-009)

  Interfaces consumed: `superpowers-probe.sh` exit codes, `deps.sh` JSON, and `make doctor`.
- [X] T020 [P] Create the templates in `guide/templates/`:
  - `guide.yaml`, `baseline.yaml`, and `inputs.yaml` (commented, schema version 1)
  - `styleguide.md` (term list format from saw-guide `.style/styleguide.md`)
  - `run-summary.md` (sections per data-model.md "Run summary")
  - `upstream-issue.md` (provenance note text from FR-035, placeholders for summary, locations, evidence, proposal)
  - `guide-rules.yaml` (an example rule set)

**Checkpoint**: `make test` passes; the toolkit validates the fixture guide; the preflight reports the dependency states correctly.

---

## Phase 3: User Story 1, create a source-verified guide (Priority: P1) 🎯 MVP

**Goal**: `/guide:create` produces a reviewed, source-verified Antora guide with a baseline, a run summary, and collected upstream findings.

**Independent Test**: Quickstart scenarios 3 and 4 with `--format antora` on the mini-project fixture.

- [X] T021 [P] [US1] Write `tests/toolkit/test_attrs.py` covering:
  - `export --format antora` emits `--attribute <id>-commit=...`, `<id>-commit-short`, `<id>-blob`, `<id>-tree`, `<id>-<attribute>`, and `baseline-date` for every source
  - the output is stable and shell-safe
- [X] T022 [US1] Implement `guide/toolkit/attrs.py`:
  - `export(baseline, fmt) -> list[str]` and CLI `attrs.py export --format antora`
  - `values(baseline) -> dict[str, str]`, which is shared by the later adapters

  Attribute names generalize saw-guide's `saw-commit`, `saw-blob`, and so on to `<source-id>-*`.
- [X] T023 [US1] Implement `guide/toolkit/playbook.py` with `tests/toolkit/test_playbook.py` (FR-016a, research R9a):
  - `is_linked_worktree(root) -> bool` (`.git` is a file)
  - `path(root, internal: bool) -> Path`: returns `site.yml` or `site-internal.yml` in a main checkout; in a linked worktree it writes `build/playbook.yml` or `build/playbook-internal.yml` with the content source `url` set to the main repository path, `branches: <worktree branch>`, `worktrees: <worktree name>`, and an absolute `output.dir`, and returns that path
  - CLI `playbook.py path [--internal]`
  - Test: create a real linked worktree of a temp repository under `.claude/worktrees/<name>` (the spex layout) and assert the generated playbook values; the Antora smoke test runs `make site` once from such a worktree.
- [X] T024 [US1] Create the Antora adapter `guide/adapters/antora/`, ported from `~/Work/projects/saw-guide`:
  - `adapter.yaml`, per `contracts/adapter.md`
  - `scaffold/site.yml` and `scaffold/site-internal.yml` (internal component only in the internal playbook; `@antora/html-single-extension` enabled)
  - `scaffold/package.json` (`@antora/cli ~3.2.0`, `@antora/site-generator ~3.2.0`, the html-single extension, `playwright ^1.48`)
  - `scaffold/content/antora.yml`
  - `scaffold/content/modules/ROOT/nav.adoc` and `pages/index.adoc`
  - `scaffold/content/modules/ROOT/partials/{baseline-note,experimental-on-main,experimental-in-review}.adoc` (parameters `feature-name`, `feature-pr`, `feature-anchor`, unset after use)
  - `scaffold/internal/antora.yml` with `modules/internal/nav.adoc`
  - the RHDP showroom UI bundle as in saw-guide (lightbox for `role=expand` and `role=fullscreen`); the page template and procedure show diagrams as `image::<name>.svg["<alt text>",role=expand]` (FR-022a)
  - `scaffold/Makefile` with every target from `contracts/adapter.md`, where `site` passes `$(shell uv run tools/guide/attrs.py export --format antora)`, uses `--log-failure-level=warn`, sets `attribute-missing: warn`, and builds from `$(shell uv run tools/guide/playbook.py path [--internal])`, so linked worktrees work (T023)

  Interfaces consumed: `attrs.py export`, `check.py`, `leakcheck.py`, and `doctor.py`.
- [X] T025 [US1] Create `tests/adapters/convert.py` (neutral page format from T005 to `antora`; the `mkdocs` and `gfm` targets follow in T038) and `tests/adapters/scaffold.sh <format> <dir>`. The scaffold script copies `guide/adapters/<format>/scaffold/`, copies `guide/toolkit/` to `tools/guide/`, and copies `guide/adapters/<format>/adapter.yaml` to `tools/guide/adapter.yaml`, which is the same layout create produces (T033).

  Then write the smoke test `tests/adapters/test_antora.sh`. It converts `tests/fixtures/sample-guide` into an Antora project in a temp directory and runs `make doctor check dist`, asserting that both tarballs exist and the shareable one contains no `internal/` path (FR-020). It then plants `ACME Corp` in a shareable page and asserts that `make check` fails with the leak reported.
- [X] T026 [P] [US1] Create the page-task templates in `guide/skills/page-task/`, generalized from saw-guide `.superpowers/sdd/2026-09-30-saw-guide-plan/{page-procedure.md,page-review-guide.md,global-constraints.md}`:
  - `page-procedure.md`: skeleton first; source block; why-paragraph before numbered steps; `Check:` lines with expectations; adapter snippets for admonitions and experimental labels; `make check` before commit; the commit trailer.
  - `page-review-guide.md`: at least 12 factual spot-checks or all statements (FR-011); severity calibration; required output format; read-only rules; no `cd` into `.guide/cache`; flag as Important any shareable statement whose only support is an input marked confidential.
  - `global-constraints.template.md`: placeholders filled from `guide.yaml` and `baseline.yaml`.
  - `final-review-addendum.md`: cross-page consistency, persona journeys, shareable/internal boundary, adjudication of deferred minors (FR-013).
  - `style-rules.md`: the built-in style rules used when cc-prose is absent (voice descriptions for the built-in styles `concepts`, `technical`, `reference`; banned filler and inflated phrasing; sentence length; active voice; terms from the guide's `styleguide.md`).
  - `SKILL.md`: how create and evolve hand these files to superpowers dispatches, pre-seeded controller rulings (prose-check resume; re-verify disputed findings against the pinned source before applying them, FR-012; when an isolated or background session refuses a `git` command rewritten by a shell hook such as `rtk git`, call `/usr/bin/git` directly), and how the rigor profile maps to review dispatch (FR-021).
  - The cc-prose branch (FR-003a): when preflight reports `prose: true`, `page-procedure.md` has implementers write with the section's cc-prose voice profile and run the prose AI-pattern check (resuming the turn afterwards), and `page-review-guide.md` includes the check result. When `prose: false`, both use `style-rules.md`.
  - Input handling rules in `page-procedure.md`: quotes from transcripts appear only verbatim, otherwise paraphrase without quotation marks; claims from inputs enter a page only after verification against a pinned source; contradictions are recorded as findings (spec User Story 1, scenario 3); content derived from an input marked `confidential` may appear only on internal pages, cited with an `input:<id>` reference in the source reference block (spec User Story 1, scenario 4).
- [X] T027 [P] [US1] Write the diagrams skill `guide/skills/diagrams/SKILL.md` and port `guide/toolkit/shoot.mjs` from saw-guide `scripts/shoot.mjs`, with the deferred fixes (null guard when there is no `<svg>`, `opt()` erroring on a missing value). The skill implements research R9 as an ordered flow:
  1. **Canvas**: find which canvas the tools talk to through the server's `/health` endpoint (`elements_count`, `websocket_clients`); name the URL to the author; open it when `websocket_clients` is 0, because export needs a connected browser (FR-024).
  2. **Backup**: `export_scene` to `.guide/canvas-backup/<timestamp>.excalidraw`, made read-only, before `clear_canvas` or any `import_scene` with mode `replace`; restore afterwards (FR-024).
  3. **Layout plan** before any arrow: rows and columns with 80 to 100 px channels between rows and at least 40 px between boxes; boxes and labels off frame borders; frames as real Excalidraw frames or groups with their label and children (FR-022).
  4. **Arrows**: curved arrows as `arrow` elements with `roundness: {type: 2}` and at least three points, bound to box edges through `startElementId` and `endElementId`. Arrow geometry is never changed with `update_element` (it cannot set `points` or `roundness`): edit the scene JSON and re-import with `import_scene` mode `replace` after a backup, or delete and recreate the arrow with `batch_create_elements`. Labels bound to an arrow sit at the path midpoint; move them by reshaping the arrow or by making them free-standing text. On the first diagram of a run, verify that curves render (`get_element` plus an exported image) and fall back to `elbowed: true` if not.
  5. **Palette** with hex values; one entity keeps one color across diagrams; legend text `#495057`, never `#1e1e1e`.
  6. **Before export**: remove duplicate container-bound texts, then run `uv run tools/guide/diagram_check.py check <scene>`; export only at zero findings (FR-023).
  7. **Export** to `.guide/diagrams/<name>/round<N>/` (scene, SVG through `export_to_image`, 2x PNG through `shoot.mjs`, check report), so every round is kept (FR-023b); copy the accepted round's `.excalidraw` to `diagrams/` and the images to the adapter's image directory.
  8. **Controller review** (done by the controlling session, never by the drawing subagent): `diagram_check.py crops <png> --scene <scene> --out <dir>` and review every tile and finding crop at native resolution; record the verdict in the round directory (FR-023a).
  9. **Fix rounds**: at most two automated fix rounds per diagram. Then hand the diagram to the author ("open for manual edit" with the canvas URL), wait for the author's "done", export, check, and review again (FR-023b).
  10. **Permissions**: check that `mcp__excalidraw` is allowed in the guide project's `.claude/settings.local.json` and offer to add it.
  11. **Tool unavailable**: warn with the install hint and ask whether to continue with a placeholder image block that names the missing diagram; record a ruling (FR-003).
- [X] T028 [P] [US1] Write `tests/toolkit/test_diagram_check.py` with small fixture scenes under `tests/fixtures/diagrams/`:
  - a straight arrow crossing an unbound text element is reported
  - a curved arrow (`roundness` type 2, three points) whose sampled path crosses a box is reported, while the straight chord between its ends would not cross
  - arrow ends inside their bound boxes are not reported
  - a label or box crossing a frame border is reported
  - a duplicate container-bound text and an unbound arrow end are reported
  - a clean scene yields exit 0
  - `crops` writes tiles no larger than 1600 x 1200 px at native resolution plus one crop per finding
- [X] T029 [US1] Implement `guide/toolkit/diagram_check.py` (PEP 723 dependencies `pillow`). Interfaces produced:
  - `load_scene(path) -> Scene` (elements with bounding boxes, rotation applied to boxes, frames and groups, bindings, container ids)
  - `sample_arrow(element, step_px=4) -> list[Point]` (Catmull-Rom through the points for `roundness` type 2, polyline otherwise)
  - `check(scene) -> list[Finding(kind, element_ids, bbox, message)]` with kinds `arrow-crosses-text`, `arrow-crosses-box`, `crosses-frame-border`, `duplicate-bound-text`, `unbound-arrow-end`
  - `crops(png, scene, out_dir, findings) -> list[Path]`, which maps scene coordinates to PNG pixels from the exported scene bounds and scale
  - CLI `diagram_check.py check SCENE` (exit 1 with findings as text and JSON) and `diagram_check.py crops PNG --scene SCENE --out DIR`
- [X] T030 [P] [US1] Write `tests/toolkit/test_runs.py` covering:
  - a run summary assembled from a fixture superpowers ledger lists every task, verdict, fix-round count, and ruling. Create the fixture `tests/fixtures/ledger/progress.md` in this task: the superpowers identity line naming `docs/guide/plan.md`, three tasks (one complete with a clean review, one complete after one fix round, one mid fix round), two rulings, and one deferred minor, using the line formats in data-model.md "Progress ledger"
  - `findings add` validates against the schema and assigns `UF-<n>` ids
- [X] T031 [US1] Implement `guide/toolkit/runs.py`:
  - `summary(root, plan_workspace: Path, run_id: str) -> Path`, which writes `runs/<run-id>.md` from the template, reading the ledger lines defined in data-model.md
  - `findings_add(root, finding: dict) -> str`, which appends to `findings/upstream.yaml`
  - CLIs `runs.py summary` and `runs.py findings-add`
- [X] T032 [P] [US1] Port `guide/toolkit/ledger.py` from saw-guide `scripts/check_ledger.py` with `tests/toolkit/test_ledger.py`. Source ids now come from `baseline.yaml` instead of the hard-coded `saw|openshell` prefixes, and the source block is parsed only at the top of the page. Wire it into the Antora scaffold's `check` target for `STRICT=1` (FR-021 strict).
- [X] T033 [US1] Write part 1 of the create skill, `guide/skills/create/SKILL.md` sections "Preflight", "Intake", and "Project setup", implementing the first half of the create flow in `contracts/commands.md` and plan.md "How create drives superpowers":
  1. Preflight.
  2. Target directory rules (FR-005b).
  3. Intake interview: every FR-006 field, cluster connections, the drift schedule opt-in, and the remote repository and push opt-ins (FR-005c). The remote is created private by default, only after confirmation of name and visibility.
  4. Scaffold the adapter, copy the toolkit to `tools/guide/` with `VERSION`, and copy `guide/adapters/<format>/adapter.yaml` to `tools/guide/adapter.yaml` (the layout that `doctor.py` and `tests/adapters/scaffold.sh` expect).
  5. `fetch.py pin` and `fetch.py fetch`. When a source cannot be fetched, name it and ask the author whether to continue without it; on yes, use `--allow-unverified` and record the status `unverified` (spec edge case).
  6. Input registration with sha256, refusing locations inside the project (FR-005), asking per input whether it is confidential and recording `inputs[].confidential`.
  7. When diagrams are planned and the Excalidraw tools are missing: warn with the install hint and ask whether to continue with placeholders (FR-003).

  Interfaces consumed: `fetch.py pin|fetch`, `guidecfg.py validate`, and the `preflight` skill.
- [X] T034 [US1] Write part 2 of the create skill (sections "Guide spec and plan", "Execution", "Wrap-up", "Resume") and the command wrapper `guide/commands/create.md` (frontmatter `description` and `argument-hint: "[--dir PATH] [--format antora|mkdocs|gfm] [--rigor fast|standard|strict] [--source ID=REPO@REF]... [--input PATH]... [description]"`; it invokes the preflight skill and then the create skill with the arguments). Part 2 covers:
  1. Superpowers `brainstorming` with the spec location `docs/guide/spec.md` injected.
  2. `writing-plans` with the plan location `docs/guide/plan.md`, one task per page or diagram, and Global Constraints rendered from the template.
  3. The author approval gate.
  4. `subagent-driven-development` with the page-task files and the rigor switch. Diagram tasks run the diagrams skill; before a diagram task counts as complete, the controller runs `diagram_check.py` itself and reviews the crops of the export (FR-023a), applying the two-round cap and the manual hand-off (FR-023b).
  5. The final review with the addendum and one fix round.
  6. `runs.py summary`.
  7. Upstream findings through `runs.py findings-add`.
  8. The list of rulings (FR-014).

  - Push handling: when the author opted into pushes and a push fails (for example a locked SSH agent), keep committing locally, report the failure once, retry after the next completed task, and list unpushed commits in the wrap-up (spec edge case).
  - Resume (FR-013a): detect an existing superpowers ledger whose identity line names `docs/guide/plan.md`, continue at the first unfinished task, and treat `--restart` as a confirmed new run.
  - Experimental content in two tiers (FR-015) is recorded in `baseline.yaml` `change_requests`.

  Interfaces consumed: `runs.py summary|findings-add`, the `page-task` files (T026), and the `diagrams` skill (T027).
- [X] T035 [US1] Run quickstart scenarios 3 and 4 with `--format antora` on the mini-project fixture and record the outcomes in `tests/manual/us1-create.md`:
  - the false port claim is rejected by source
  - the README drift is collected as an upstream finding
  - raw inputs are absent from the repository
  - resume continues at the third task
  - SC-002: the author checks an independent sample of at least 15 factual statements against the pinned fixture sources and records the supported share (target at least 95%)
  - SC-010: a second run of the same fixture with `--rigor fast` uses at most half the review dispatches of the standard run, counted from the two run summaries
  - SC-013: the fixture plan's architecture diagram passes `diagram_check.py`, the controller's crop review is recorded in its round directory, and at least one manual hand-off is exercised by declining the automated result once

**Checkpoint**: The MVP works end to end for Antora.

---

## Phase 4: User Story 1 increment, MkDocs and GitHub Markdown adapters (Priority: P1)

**Goal**: create works in all three formats (FR-017).

**Independent Test**: `make test-adapters` passes for `mkdocs` and `gfm`; quickstart scenario 3 with `--format gfm` passes.

- [X] T036 [P] [US1] Create the MkDocs adapter `guide/adapters/mkdocs/`:
  - `adapter.yaml`
  - `scaffold/mkdocs.yml`: Material `>=9.5,<9.8`, the `glightbox` plugin for click-to-enlarge diagrams (FR-022a), the `admonition`, `pymdownx.details`, and `pymdownx.superfences` extensions, `macros` with `include_yaml: [baseline.yaml]` and module `tools/guide/mkdocs_macros.py` exposing `attrs.values()`, `print-site`, `exclude_docs: internal/`
  - `scaffold/mkdocs-internal.yml`, with `INHERIT: mkdocs.yml`, including `internal/`
  - `scaffold/docs/index.md`
  - `scaffold/docs/assets/experimental.css` for the `experimental` admonition class
  - `scaffold/requirements.txt` for `uv tool` or `uvx` (pinned)
  - `scaffold/Makefile` with every target from `contracts/adapter.md`, run through `uvx --with ... mkdocs` and never pip
  - `guide/toolkit/mkdocs_macros.py`
- [X] T037 [P] [US1] Create the GitHub Markdown adapter `guide/adapters/gfm/`:
  - `adapter.yaml`
  - `scaffold/docs/README.md` (the table of contents defines the navigation order)
  - `scaffold/docs/SUMMARY.md`
  - `scaffold/internal/README.md`
  - `scaffold/package.json` (`markserv`, `playwright`)
  - `scaffold/Makefile` with every target from `contracts/adapter.md`, where `site` runs `attrs.py regions --write docs internal` and checks run on `docs/`

  Extend `guide/toolkit/attrs.py` with `regions(root, baseline, write: bool) -> list[Change]`, which rewrites `<!-- guide:attr NAME -->VALUE<!-- /guide:attr -->`, and extend `tests/toolkit/test_attrs.py` for regions (idempotent; an unknown name fails). Admonitions use GitHub alerts; experimental labels are IMPORTANT alerts with the fixed first line from `contracts/page-conventions.md` section 4. Diagrams are written as `[![alt](path.svg)](path.svg)` so a click opens the full-size SVG (FR-022a).
- [X] T038 [US1] Add `mkdocs` and `gfm` targets to `tests/adapters/convert.py` and `tests/adapters/scaffold.sh` (including the `tools/guide/adapter.yaml` copy). Write the smoke tests `tests/adapters/test_mkdocs.sh` and `tests/adapters/test_gfm.sh` with the same assertions as `test_antora.sh` (`make doctor check dist`, tarball contents, planted leak fails). Wire all three into `make test-adapters`.
- [ ] T039 [US1] Update `guide/skills/create/SKILL.md` and `guide/skills/page-task/page-procedure.md` with the per-format snippets (source block syntax, expectation syntax, admonitions, experimental labels, attribute or region usage). Run quickstart scenario 3 with `--format gfm` and append the outcome to `tests/manual/us1-create.md`.

---

## Phase 5: User Story 2, evolve a guide when the sources change (Priority: P2)

**Goal**: drift detection, adoption of existing guides, targeted updates, and a new baseline.

**Independent Test**: Quickstart scenarios 6 and 7 (SC-004, SC-005).

- [X] T040 [P] [US2] Write `tests/toolkit/test_drift.py`, using `fixture_repo`, covering:
  - the second commit changes a cited file, so the affected pages include the citing page and the pages linking to it
  - between the second and the third commit, the renamed cited file is reported as `renamed docs/setup.md -> docs/install.md` and the deleted one as `deleted Makefile`; both mark their citing pages as affected (spec User Story 2, scenario 3)
  - a changed input checksum is reported (FR-005a)
  - an unreachable source is reported as `unchecked`
  - a pinned commit that no longer exists upstream (simulated by rewriting the fixture history) is reported as `pin-missing` with a request for a new pin, not as an error trace
  - exit codes are 0 for no drift and 10 for drift
  - `--format markdown` and `--format json`
- [X] T041 [US2] Implement `guide/toolkit/drift.py`. Per source it fetches the tracked branch head (`git -C .guide/cache/<id>.git fetch`) and diffs the pinned commit against it. Interfaces consumed: `guidecfg.load_*`, `sources.cited_files`, and `fetch.fetch`.
  - Changed files come from `git diff --name-status -M <pinned>..<head>` and are intersected with `sources.cited_files`; renames and deletions keep their status in the report, and the evolve page task must update or remove every such reference (never silently drop it).
  - Inbound links come from adapter link syntax (`xref:` for Antora, relative `.md` links for the Markdown adapters).
  - Change requests are re-read with `gh api repos/<repo>/pulls/<n>` for state, head SHA, and merged.
  - Input checksums are compared.

  Interfaces produced: `report(root) -> DriftReport(sources, changed_files, affected_pages, change_requests, inputs)` and CLI `drift.py --check [--format markdown|json]`.
- [X] T042 [P] [US2] Write `tests/fixtures/saw-baseline.yaml` (a copy of saw-guide's `baseline.yaml`) and `tests/toolkit/test_adopt.py`. With `guide/templates/adopt-map.example.yaml`, which maps the SAW keys `saw.commit`, `openshell.deployed.commit`, and `saw.open_prs[]` onto `sources[]` and `change_requests[]`, the migration produces a valid cc-guide baseline. Pages without source blocks are listed.
- [X] T043 [US2] Implement `guide/toolkit/adopt.py`:
  - `migrate(root, mapping: Path) -> Baseline`
  - `missing_blocks(root) -> list[Path]`
  - CLI `adopt.py migrate --map FILE` and `adopt.py report`
- [X] T044 [US2] Write the evolve skill `guide/skills/evolve/SKILL.md` and the command wrapper `guide/commands/evolve.md`:
  - `--check` runs `make drift` only, with no superpowers dependency.
  - `--adopt` copies the toolkit, migrates the baseline, writes `guide.yaml` and `inputs.yaml` through the intake subset, and adds source blocks page by page through superpowers execution with reviews (FR-028).
  - The normal flow:
    1. Drift report.
    2. Change-request re-evaluation (FR-027).
    3. Registration and verification of new inputs.
    4. A `writing-plans` plan limited to the impact set (FR-026).
    5. Execution with the page-task files and the rigor switch.
    6. `make check`.
    7. `fetch.py rebaseline` written last (FR-029).
    8. Upstream findings found during the run collected through `runs.py findings-add` (FR-031).
    9. The run summary.
  - Resume works as in create.
- [X] T045 [US2] Create the drift workflow template `guide/templates/guide-drift.yml`:
  - a weekly cron plus `workflow_dispatch`
  - `astral-sh/setup-uv`
  - `make drift`
  - on exit 10, create or update one issue labelled `guide-drift` through `gh`
  - token `GUIDE_SOURCES_TOKEN` for private sources
  - unreadable sources reported as unchecked (FR-025b)

  Add the opt-in step to the create skill that installs it as `.github/workflows/guide-drift.yml` and sets `drift.schedule` in `guide.yaml`.
- [ ] T046 [US2] Run quickstart scenarios 6 and 7 (scenario 7 on a copy of `~/Work/projects/saw-guide`) and record the results in `tests/manual/us2-evolve.md`:
  - only affected pages change
  - the PR 56 notice is updated
  - the baseline is written last
  - `make check` passes

---

## Phase 6: User Story 3, preview the guide (Priority: P3)

**Goal**: live local preview for every format.

**Independent Test**: Quickstart scenario 5 in an Antora guide and a gfm guide.

- [X] T047 [US3] Implement `guide/toolkit/antora-watch.mjs`, using `chokidar` and `browser-sync` (added to the Antora scaffold `package.json`), per research R9a and FR-030:
  - the playbook comes from `playbook.py path [--internal]` (works in linked worktrees)
  - changes are debounced (300 ms); changes arriving during a build are queued and trigger exactly one follow-up build
  - a failed build keeps serving the last good site and prints the error; a successful build swaps the site in and reloads the browser
  - browser-sync serves the HTML with `Content-Type: text/html` (its client is injected only for requests that accept `text/html`)
  - smoke test `tests/adapters/test_preview_antora.sh`: start the watcher on a scaffolded fixture, change a page and assert a rebuild, break a page and assert the last good site is still served, fix it and assert recovery

  Then fill in the `preview` targets:
  - Antora: `node tools/guide/antora-watch.mjs [--internal]`.
  - MkDocs: `uvx ... mkdocs serve [-f mkdocs-internal.yml]`.
  - gfm: `npx markserv docs` or `internal`.
- [X] T048 [US3] Write the preview skill `guide/skills/preview/SKILL.md` and the command wrapper `guide/commands/preview.md`. The skill runs `make preview [VIEW=internal]` in the background, waits for the port, opens the browser with `open`, and reports the URL and how to stop it (FR-030, SC-008).

---

## Phase 7: User Story 4, export the full guide as a PDF (Priority: P4)

**Goal**: one PDF of the whole guide per view, from the same content (FR-030a to FR-030f).

**Independent Test**: Quickstart scenario 2 (PDF part) for all three formats.

- [X] T049 [P] [US4] Write `tests/adapters/test_pdf.sh`. For each format it runs `make pdf` and checks with `pdftotext` (via pypdf in `tests/adapters/pdftext.py`):
  - the title page shows the title, baseline date, and source commits
  - every page title appears in navigation order
  - no confidential term appears
  - `make pdf VIEW=internal` puts `INTERNAL` in every page footer and in the file name
  - a planted check failure writes no PDF
- [X] T050 [US4] Implement `guide/toolkit/print-pdf.mjs`. Inputs: the print HTML path, `guide.yaml`, `baseline.yaml`, and `--view shareable|internal`. It:
  - injects the title page and a linked TOC from the document headings
  - rewrites inter-page links to in-document anchors with unique ids
  - applies print CSS (wrapped `pre`, tables at 100% width, landscape named pages for `.guide-wide`, admonition and experimental styling)
  - calls `page.pdf()` with `displayHeaderFooter` (page numbers; the `INTERNAL` marker for the internal view)
  - writes `dist/<slug>-<baseline-date>[-INTERNAL].pdf`

  Interfaces consumed: none from Python; it reads YAML with `js-yaml`.
- [X] T051 [US4] Produce the print HTML per adapter and wire `make pdf` (`make check`, then the print HTML, then `print-pdf.mjs`, then `leakcheck.py` on the PDF for the shareable view, deleting the PDF on a leak):
  - Antora: verify `@antora/html-single-extension` on saw-guide content first. If it falls short, implement `guide/toolkit/assemble.py`, which concatenates the built pages in `nav.adoc` order, and record a ruling.
  - MkDocs: the `print-site` page.
  - gfm: `pandoc --standalone` over `docs/SUMMARY.md` order with GitHub CSS.
- [X] T052 [US4] Write the export skill `guide/skills/export/SKILL.md` and the command wrapper `guide/commands/export.md`. `--internal` warns that the file must stay inside the internal audience; `--out` sets the path; on failure no file remains and the cause is named (FR-030f).

---

## Phase 8: User Story 5, report problems found in the sources (Priority: P5)

**Goal**: approval-gated upstream issues and optional change proposals (FR-031 to FR-036).

**Independent Test**: Quickstart scenario 8.

- [X] T053 [P] [US5] Write `tests/toolkit/test_upstream.py` covering:
  - a finding whose `locations[].quote` is gone at the newer fixture commit gets `needs-review`
  - an unchanged one gets `reverified`
  - `sanitize` rejects drafts containing confidential terms, ticket patterns, internal links, or private-repo URLs
  - `draft` includes the provenance note
  - `dedupe` merges findings with the same source and overlapping locations
- [X] T054 [US5] Implement `guide/toolkit/upstream.py` and extend the finding schema in `guidecfg.py` with `locations[].quote` (the text at the pinned commit, already defined in `data-model.md`).
  - `reverify(root, finding_id) -> status` fetches the default-branch head into `.guide/cache/<id>.git` and searches for the quote, tolerating moved lines.
  - `draft(root, finding_id) -> Path` renders `templates/upstream-issue.md` into `.guide/runs/<run-id>/drafts/`.
  - `sanitize(text, guide) -> list[Problem]`.
  - `dedupe(root) -> list[Merge]`.
  - `existing(finding) -> list[url]` uses `gh search issues` (FR-036).

  The same four operations are exposed as CLI subcommands.
- [X] T055 [US5] Write the upstream skill `guide/skills/upstream/SKILL.md` and the command wrapper `guide/commands/upstream.md`:
  - re-verify all findings mechanically, then semantically, dropping stale ones with a note (FR-032)
  - dedupe and show existing issues
  - show every draft in full, with `naming-ux` drafts as issue-only proposals
  - post only approved drafts with `gh issue create`
  - `--pr` for mechanical fixes: fork, branch, commit with the trailer, show the diff, and run `gh pr create` only after approval
  - record URLs and statuses in `findings/upstream.yaml` and link them from the internal part (FR-033 to FR-036)
- [ ] T056 [US5] Run quickstart scenario 8 against a throwaway GitHub repository you own and record the results in `tests/manual/us5-upstream.md`.

---

## Phase 9: User Story 6, validate recipes against a live cluster (Priority: P6)

**Goal**: opt-in, two-tier validation with redaction (FR-037 to FR-040).

**Independent Test**: Quickstart scenario 9.

- [X] T057 [P] [US6] Write `tests/toolkit/test_classify.py` covering:
  - every allowlist entry in `contracts/page-conventions.md` section 3
  - pipelines where every segment must be a query
  - `oc debug`, `oc exec`, any `make`, redirection, and `tee` are mutating
  - the `curl` method and data flags
  - the matcher grammar (`exit`, `contains`, `not-contains`, `matches`, `lines`, `and`)
  - a check step without an expectation yields `not-evaluable`
  - an `extra_queries` pattern matching `oc debug` does not make it a query
  - redaction of bearer tokens, `token:` and `client-key-data:` values, and Authorization headers
- [X] T058 [US6] Implement `guide/validate/readonly.yaml` (the default allowlist) and `guide/toolkit/classify.py`:
  - `classify(cmd: str, allow: Allowlist) -> "query"|"mutating"`
  - `match(matcher: str, stdout: str, exit_code: int) -> bool`
  - `redact(text: str) -> str`
  - `extract(pages, style) -> list[CheckStep(page, line, commands, expectation)]`

  Also a CLI. Guide-level additions come from `validate.extra_queries` in `guide.yaml` and can only add query patterns; they cannot reclassify a command on the explicit mutating list.
- [X] T059 [US6] Write the validate skill `guide/skills/validate/SKILL.md` and the command wrapper `guide/commands/validate.md`:
  - the connection comes from `guide.yaml` (`KUBECONFIG` set only for the child process)
  - the read-only tier runs queries only and marks others skipped
  - the full tier requires `disposable: true` and confirms each mutating command
  - results are written redacted to `.guide/runs/<run-id>/validation.md`
  - mismatches become review findings in the run summary (FR-040)
  - a mismatch caused by the upstream project (for example a documented default that differs from the deployed behavior) is also collected through `runs.py findings-add` (FR-031)
  - nothing secret is written to the project (FR-039a)
- [ ] T060 [US6] Run quickstart scenario 9 (read-only against an existing cluster with a read-only kubeconfig; full tier on a kind cluster using the podman provider marked disposable) and record the results in `tests/manual/us6-validate.md`.

---

## Phase 10: Polish & Cross-Cutting Concerns

- [X] T061 [P] Write the plugin documentation:
  - `guide/docs/learnings.md`: already seeded during planning (process, diagram, review, canvas, rendering, and preview lessons); add the lessons learned while building the plugin itself and keep the requirement cross-references current.
  - `guide/docs/settings.md`: recommended model and effort; a permission allowlist example for a guide project's `.claude/settings.local.json` covering `gh`, `make`, `node`, `npx`, `uv`, and `mcp__excalidraw`; why not to bypass all permissions.
  - `guide/docs/adapters.md`: adapter capabilities, pins, and the MkDocs Material maintenance-mode note.
- [X] T062 [P] Create the eval suite: `eval.yaml` (agent-eval-harness format as in cc-prose) plus `eval/cases/`. The cases are:
  - `review-planted-false-fact` (a page with three planted false statements and the fixture sources; the review must flag all three)
  - `upstream-stale-finding` (one finding already fixed on the default branch; it must be dropped)
  - `classify-mutating` (ten commands; all mutating ones are classified as mutating)

  Covers SC-002.
- [X] T063 Write the full `README.md`: commands, install, dependencies (superpowers required, Excalidraw MCP for diagrams, cc-prose optional), rigor profiles, quick start, and links to `guide/docs/`. Prepare the marketplace entry for `~/Development/context-engineering/cc-rhuss-marketplace/.claude-plugin/marketplace.json` (`git-subdir` source, path `guide`) and its README section, committed locally there; pushing that repository waits for the author's approval.
- [ ] T064 Run `make validate test test-adapters` and quickstart scenarios 1, 2, 5, and 10; record the results in `tests/manual/README.md` and fix any failures found. Timing checks on the 25-page guide from `tests/fixtures/make-large-guide.py`, per format, recorded with `time`:
  - preview reachable within 60 seconds of `make preview` (SC-008)
  - `make pdf` under 180 seconds (SC-011)
  - `make drift` over the fixture's sources under 120 seconds (plan performance goal)
  - `make site preview pdf` from a linked worktree under `.claude/worktrees/` for the Antora fixture (FR-016a)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Setup; blocks every user story.
- **US1 core (Phase 3)**: depends on Foundational. This is the MVP.
- **US1 increment (Phase 4)**: depends on Phase 3 (`attrs.py`, the page-task templates, the create skill).
- **US2 (Phase 5)**: depends on Phase 3 (a created guide, the toolkit, the page-task templates). Phase 4 is only needed for evolving Markdown guides.
- **US3 (Phase 6)**: depends on Phase 3 for Antora and on Phase 4 for the Markdown formats.
- **US4 (Phase 7)**: depends on Phase 3 (and Phase 4 for all formats).
- **US5 (Phase 8)**: depends on Phase 3 (findings collected by create, T031).
- **US6 (Phase 9)**: depends on Foundational (page conventions, `guidecfg.py`); independent of the other stories.
- **Polish (Phase 10)**: after the desired stories are complete.

### Within Each Phase

- Tests marked [P] come before the implementation they cover and must fail first.
- Toolkit modules come before the skills that call them; skills come before their command wrappers; manual quickstart runs come last.

### Parallel Opportunities

- Phase 1: T003, T004, and T005 together.
- Phase 2: the test files T006, T008, T010, T012, and T014 together; T016, T018, and T020 alongside the core modules.
- Phase 3: T021, T026, T027, T028, T030, and T032 together once Phase 2 is done.
- Phase 4: T036 and T037 together.
- After Phase 3: US5 (Phase 8) and US6 (Phase 9) can proceed in parallel with US2 to US4.
- Phase 10: T061 and T062 together.

## Parallel Example: User Story 1

```text
Together after Phase 2:
  T021 tests for attrs.py
  T026 page-task templates
  T027 diagrams skill and shoot.mjs
  T028 tests for diagram_check.py
  T030 tests for runs.py
  T032 strict ledger port
Then in order: T022 → T023 → T024 → T025 → T029 → T031 → T033 → T034 → T035
(T034 also needs T026, T027, and T029.)
```

## Implementation Strategy

### MVP first (User Story 1 with Antora)

1. Phases 1 and 2 (toolkit core, preflight).
2. Phase 3 (create with Antora).
3. **Stop and validate**: quickstart scenarios 3 and 4 on the fixture.

### Incremental delivery

1. MVP, then Phase 4 (all three formats).
2. Phase 5 (evolve; SC-005 on the SAW guide), which is the second reason the plugin exists.
3. Phases 6 and 7 (preview and PDF).
4. Phases 8 and 9 (upstream and validate), in either order.
5. Phase 10 (docs, evals, marketplace listing).

### Notes

- Each task ends with its tests passing and a commit carrying the trailer.
- Manual quickstart records under `tests/manual/` are evidence for the final verification gate.
