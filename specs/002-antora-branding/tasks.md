# Tasks: Antora branding for guides

**Input**: Design documents from `specs/002-antora-branding/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Requested by the plan. The toolkit is developed test-first with pytest (`make test`); the Antora build, PDF, preview, and bundle contract get shell smoke tests under `tests/adapters/` (`make test-adapters`).

**Organization**: One phase per user story in priority order (US1 and US2 are both P1; US3 and US4 P2; US5 to US7 P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1 to US7)

## Path Conventions

- Plugin: `guide/` (toolkit in `guide/toolkit/`, Antora adapter in `guide/adapters/antora/`, scripts in `guide/scripts/`, skills in `guide/skills/`)
- Tests: `tests/toolkit/` (pytest, `pythonpath = guide/toolkit`), `tests/adapters/` (shell smoke tests, fixture guide via `tests/adapters/scaffold.sh`)

## Global Constraints

- No em dash or en dash characters in any file; tests that need one build it with `chr(0x2014)` / `chr(0x2013)`.
- The toolkit imports nothing from outside its own directory; `branding.py` reads its templates and contract from `tools/guide/branding/` (vendored by `scaffold-project.sh`). Asset lookup follows the pattern of `runs.py` and `upstream.py`: first `Path(__file__).resolve().parent / "branding"` (a guide project), then `Path(__file__).resolve().parent.parent / "adapters" / "antora" / "branding"` (the plugin source tree, where pytest imports `guide/toolkit/branding.py`).
- `guidecfg.py` imports `branding.py`, never the other way round. `branding.py` reads `guide.yaml` and `tools/guide/adapter.yaml` itself with PyYAML.
- No new dependencies: Python scripts use PyYAML only (PEP 723), Node scripts use the packages already in the scaffold `package.json`.
- Unbranded guides without `ui/supplemental/` keep today's behavior byte for byte (SC-002): `playbook.py path` prints the committed playbook and creates nothing.
- No scaffold file (Makefile, `site.yml`, `site-internal.yml`) changes; every runtime change lives in the toolkit.
- Author text is escaped for its target (XML in SVG, HTML plus `{` `}` entities in partials, JSON in the helper) (FR-017).
- Use `uv` (PEP 723 scripts with `uv run`), never pip. Commits end with `Assisted-By: 🤖 Claude Code`.
- The pinned bundle URL is `https://github.com/rhpds/rhdp_showroom_theme/releases/download/v2.0.3/ui-bundle.zip`; never fork, patch, or replace it.

## Interfaces

Names and types shared across tasks. A task that consumes one of these uses exactly this name and shape.

```python
# guide/toolkit/branding.py
KEYS = ("logo_text", "logo", "logo_alt", "footer", "favicon", "color")
DEFAULT_KEYS = {"antora": list(KEYS)}          # used when tools/guide/adapter.yaml is missing; other formats: []

def asset_dir() -> Path                        # tools/guide/branding/ or guide/adapters/antora/branding/ (see Global Constraints)
def check(root: Path, raw: Any, fmt: str, adapter_keys: list[str]
          ) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]
    # (problems, warnings) as (location, message) pairs; location is the full prefix of the
    # contract line, for example "guide.yaml:branding.logo_text", "guide.yaml:branding",
    # "ui/supplemental:css/x.css", "site.yml:ui.supplemental_files",
    # "ui/supplemental/partials/footer-content.hbs". A problem prints as f"{loc}: {msg}",
    # a warning as f"{loc}: warning: {msg}". Overlay and playbook checks run for fmt == "antora" only.
def check_guide(root: Path) -> tuple[list[str], list[str]]
    # reads guide.yaml (missing file: no block, no problems), fmt from its `format`
    # (default "antora"), adapter keys from tools/guide/adapter.yaml `branding`
    # (missing file: DEFAULT_KEYS; file without the list: []), runs check(), returns formatted lines
@dataclass
class Resolved:
    logo_text: str | None; logo: Path | None; alt: str
    footer: str | dict          # "rhdp", "none", or {"text": str, "url": str | None}
    favicon: Path | None; color: str | None; hover: str | None
def resolve(root: Path, raw: Any) -> Resolved | None   # None without a branding block
def hover_shade(color: str) -> str      # each channel int(c * 0.75 + 0.5); "#0066cc" -> "#004d99"
def logo_svg(text: str) -> str
def render(root: Path, view: str) -> Path   # view "shareable" | "internal"; returns build/branding/<view>/ui
def check_bundle(bundle: Path, contract: Path) -> list[str]   # failing contract lines, empty when all hold

# build/branding/<view>/branding.json (branded guides only)
{"logo": "<abs path of build/branding/<view>/ui/img/logo-guide.svg>", "alt": str, "footer": str,
 "generated": [rel paths], "shadowed": [rel paths]}

# guide/toolkit/guidecfg.py
Guide.branding: dict | None             # raw block, stored by load_guide without the full checks
Adapter.branding: list[str]             # default []
def validate(root: Path) -> tuple[list[str], list[str]]   # (problems, warnings)

# guide/toolkit/check.py
def check_branded_site(root: Path, guide: guidecfg.Guide) -> list[Violation]   # rule "branding", line 0
```

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Adapter descriptors, the vendored branding directory, and its distribution

- [X] T001 Add a `branding:` capability list to guide/adapters/antora/adapter.yaml (`[logo_text, logo, logo_alt, footer, favicon, color]`) and `branding: []` to guide/adapters/mkdocs/adapter.yaml and guide/adapters/gfm/adapter.yaml, each with a one-line comment pointing at data-model.md's adapter capability
- [X] T002 [P] Create guide/adapters/antora/branding/NOTICE.md stating that logo-text.svg.tmpl is derived from `img/logo-demo-platform.svg` of rhpds/rhdp_showroom_theme v2.0.3 under MPL-2.0, with the MPL-2.0 Exhibit A notice and the upstream URL
- [X] T003 [P] Create guide/adapters/antora/branding/logo-text.svg.tmpl: download the pinned bundle into a scratch directory, copy `img/logo-demo-platform.svg`, keep the Red Hat wordmark paths, the hat, and the divider unchanged, replace the viewBox width with `{{VIEWBOX_WIDTH}}`; the stock string "Demo Platform" occurs twice in the `<text>` element (its `data-name` attribute and the content of its `<tspan x="0" y="0">` child), so replace both with `{{TEXT}}` and add `textLength="{{TEXT_LENGTH}}" lengthAdjust="spacingAndGlyphs"` to the `<text>` element (Chromium honors it with the tspan child); keep `transform="translate(308 149)"`, `fill="#fff"`, `font-size="82"`, `font-weight="700"`, and the font-family list; add the MPL-2.0 notice as an XML comment after the `<svg>` start tag; confirm with `rg -c "Demo Platform"` that the template no longer contains the stock text (research.md R4)
- [X] T004 [P] Create guide/adapters/antora/branding/contract.yaml per contracts/bundle-contract.md, deriving every string, regex, `equals` value, and the `accent_selectors` / `accent_hover_selectors` lists from the unpacked pinned bundle (`css/site.css`, partials, helpers); `equals` compares after stripping leading and trailing whitespace (the stock `partials/head-icons.hbs` starts with four spaces); confirm by hand with `rg` that every rule holds against the bundle
- [X] T005 Update guide/scripts/scaffold-project.sh to copy `guide/adapters/<format>/branding/` (when present) to `<dir>/tools/guide/branding/` after the toolkit rsync, in both the full scaffold and `--toolkit-only` mode (the rsync `--delete` removes the old copy first), and mention it in the header comment (research.md R10); extend tests/toolkit/test_scaffold_project.py: an antora full scaffold has `tools/guide/branding/contract.yaml` and `tools/guide/branding/logo-text.svg.tmpl`, a `--toolkit-only` refresh restores a deleted `tools/guide/branding/` and picks up a changed `contract.yaml` from the plugin copy, and a gfm scaffold has no `tools/guide/branding/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The branding schema and its validation, shared by every user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 [P] Write failing tests in tests/toolkit/test_branding.py for `branding.check(root, raw, fmt, adapter_keys)` and `branding.check_guide(root)` (see Interfaces) covering every row of contracts/branding-config.md: both or neither logo key; `logo_text` empty, whitespace only, with a line break, 41 characters (40 passes); `logo` without `logo_alt`; missing logo and favicon files; paths that are absolute, contain `..`, or are symlinks resolving outside the project; `logo` not `.svg`; favicon not `.ico`/`.png`/`.svg`; footer as `rhdp`, `none`, `{text}`, `{text, url}`, a mapping without `text`, an unknown footer string, `url` with `ftp://` or a relative URL; color `#3e8635` passes, `3e8635`, `#fff`, `#gggggg` fail; unknown branding key; every key rejected (and an empty block rejected) for an adapter list `[]` with the format named; `site.yml` or `site-internal.yml` with `ui.supplemental_files` while a branding block or `ui/supplemental/` exists; `ui/supplemental` as a file; a file in `ui/supplemental/` that is a symlink outside the project; overlay and playbook checks are skipped for `fmt` mkdocs and gfm; `check_guide` on a directory without guide.yaml returns no problems, and without tools/guide/adapter.yaml uses `DEFAULT_KEYS`. Each case asserts the exact location and message prefix from contracts/branding-config.md
- [X] T007 [P] Write failing tests in tests/toolkit/test_branding.py for `branding.resolve(root, raw)`: alt default `Red Hat <logo_text>`, explicit alt kept, footer default `none` when omitted, footer mapping normalized, `hover_shade("#0066cc") == "#004d99"` (each channel times 0.75, rounded half up with `int(c * 0.75 + 0.5)`; Python's `round(76.5)` gives 76 and would yield `#004c99`), `hover_shade("#3e8635") == "#2f6528"`, `None` when there is no branding block
- [X] T008 [P] Write failing tests in tests/toolkit/test_guidecfg.py: a guide.yaml with a valid branding block validates for an Antora guide; the same block fails for MkDocs and gfm guides naming each key and the format; `Adapter.branding` is read from tools/guide/adapter.yaml and defaults to `[]` when the list is missing; `load_guide` succeeds for an invalid branding block (`guidecfg.py get internal.enabled` still prints the value) and fails only when `branding` is not a mapping; `guidecfg.py validate` prints branding problems in `guide.yaml:branding.<key>: message` form with exit 1, prints an overlay problem as `ui/supplemental:<rel path>: <reason>` (no `guide.yaml:` prefix), and prints a shadowing warning line `ui/supplemental/<rel path>: warning: ...` while still exiting 0
- [X] T009 Implement guide/toolkit/branding.py (PEP 723 header with pyyaml, module docstring with usage): constants (`KEYS`, `DEFAULT_KEYS`, limits, extensions, mime types), `asset_dir()`, `check(root, raw, fmt, adapter_keys)` including the overlay and playbook-conflict checks (antora only), `check_guide(root)`, `hover_shade(color)`, `resolve(root, raw) -> Resolved | None`, and the CLI `validate [--root DIR]` (prints `check_guide` lines, exit 1 on problems), all as in the Interfaces section; no import of guidecfg; make T006 and T007 pass
- [X] T010 Update guide/toolkit/guidecfg.py: add `branding` to `GUIDE_KEYS`; add `branding: list[str] = field(default_factory=list)` to the `Adapter` dataclass; in `load_guide` only check that `branding` is a mapping when present (`branding: must be a mapping`) and store it raw on `Guide.branding`, without the full branding checks, so `guidecfg.py get` keeps working for an invalid block (the scaffold Makefile reads `get internal.enabled` in `site-internal` and `print-pdf` and would otherwise skip the internal view with exit 0 instead of reaching `playbook.py`, which stops the build, FR-010); change `validate(root)` to return `(problems, warnings)`, appending the lines of `branding.check_guide(root)` to the problems and its warnings to the warnings; `main` prints problems, then warnings, and sets the exit status from problems only; update the module docstring; make T008 pass
- [X] T041 [P] Stop MkDocs and gfm builds on branding problems (FR-009, FR-010; these builds never call `playbook.py`): in guide/toolkit/mkdocs_macros.py `define_env`, call `branding.check_guide(root)` and raise `ValueError` with the problem lines (mkdocs-macros aborts `mkdocs build`, which `make site`, `make site-internal`, `make check`, and the preview all run); in guide/toolkit/attrs.py `regions` (run first by the gfm `site` and `site-internal` targets), print the problem lines to stderr and exit 1 before rewriting any region; tests in tests/toolkit/test_mkdocs_macros.py (`define_env` raises naming `guide.yaml:branding.logo_text: not supported by the mkdocs adapter`) and tests/toolkit/test_attrs.py (`attrs.py regions --write` exits 1 for a gfm guide with a branding block and leaves the pages unchanged); depends on T009

**Checkpoint**: `make test` passes; branding blocks validate per adapter

---

## Phase 3: User Story 1, brand an Antora guide from its configuration (Priority: P1) 🎯 MVP

**Goal**: A branding block with logo text, alt text, and footer changes the header logo, alt text, and footer of both views at build time, without touching tracked files.

**Independent Test**: Scaffold the fixture guide, add the agentic-starter-kits branding block, run `make check`, and inspect both built views; `git status --porcelain` stays empty.

### Tests for User Story 1

- [X] T011 [P] [US1] Write failing tests in tests/toolkit/test_branding.py for rendering: `logo_svg` escapes `& < > " '`, keeps the MPL notice comment, sets `textLength` equal to the estimate and `lengthAdjust="spacingAndGlyphs"`, uses viewBox width 780 for "Summit" (the width of the stock `logo-summit.svg`) and `ceil(308 + width + 24)` for a 40-character text, the estimate grows monotonically with added characters, a `logo_text` of `{{TEXT_LENGTH}}` appears literally in the output, and the output never contains "Demo Platform"; the alt helper is valid JavaScript whose exported function returns the exact alt string (check with `node -e` when node is available, otherwise parse the JSON literal) including quotes and `</script>`; the footer partial for `none` is `<footer class="footer"></footer>`, for `{text, url}` contains the escaped text and URL with `target="_blank" rel="noopener"`, for `{text}` has no link, and `{{x}}` in the text becomes `&#123;&#123;x&#125;&#125;`; an own `logo` is copied byte for byte to `img/logo-guide.svg`
- [X] T012 [P] [US1] Write failing tests in tests/toolkit/test_branding.py for `render(root, view)`: writes `build/branding/<view>/ui/` with `img/logo-guide.svg`, `helpers/navbar-logo-alt.js`, and `partials/footer-content.hbs` (absent for `footer: rhdp`), plus `build/branding/<view>/branding.json` with the logo path and alt; files from `ui/supplemental/` are copied last and win, and appear in `branding.json` `shadowed`; a second render replaces the first directory completely (a stale file disappears) and leaves no `*.tmp-*` or `*.old-*` directory; `branding.json` `logo` is the absolute path inside the final `build/branding/<view>/ui/`, not the temporary directory; an overlay-only guide (no block) gets only its overlay files (plus `partials/head-meta.hbs` when the overlay has `css/extra.css`) and no `branding.json`; nothing outside `build/` changes; rendering a block with every key takes under one second (`time.perf_counter`, the plan's performance goal)
- [X] T013 [P] [US1] Write failing tests in tests/toolkit/test_playbook.py: a branded guide in a main checkout gets `build/playbook.yml` with `ui.supplemental_files` equal to the absolute `build/branding/shareable/ui` and `site.keys.navbar_logo: guide` (the UI sees it as `site.keys.navbarLogo`), other `site.keys` entries kept, every `url: .` content source replaced by the absolute guide root (branches unchanged), and `output.dir`, a relative bundle URL, and relative extensions made absolute (Antora resolves `.` and `./` paths against the playbook's own directory, which is now `build/`); `--internal` gives `build/playbook-internal.yml` pointing at `build/branding/internal/ui`; an overlay-only guide gets `supplemental_files` and no `navbarLogo`; a branded linked worktree gets both the worktree rewrites and the branding keys; an invalid branding block exits 1, prints nothing on stdout, and prints the contract lines on stderr; the existing tests (repositories without guide.yaml) keep passing unchanged

### Implementation for User Story 1

- [X] T014 [US1] Implement rendering in guide/toolkit/branding.py: the Helvetica-Bold advance width table for printable ASCII (Adobe Core 14 AFM) with 611 for other characters, `logo_svg(text)` from `asset_dir() / "logo-text.svg.tmpl"` (research.md R4) with the viewBox width `max(780, ceil(308 + width + 24))` and all placeholders filled in one pass (`re.sub(r"\{\{(\w+)\}\}", ...)`, so author text containing a placeholder name stays literal), the alt helper, the footer partial, `render(root, view) -> Path` with the merge order (generated, then overlay) written to `build/branding/<view>.tmp-<pid>/`, then swapped in (rename an existing `build/branding/<view>/` to `<view>.old-<pid>` first, because POSIX `rename` cannot replace a non-empty directory, rename the new one into place, delete the old one), `branding.json`, and the CLI `render --view shareable|internal`; make T011 and T012 pass
- [X] T015 [US1] Update guide/toolkit/playbook.py: before choosing the playbook, run `branding.check_guide(root)` (problems and warnings to stderr; exit 1 on problems), render the view's overlay for branded or overlaid guides, and generate `build/playbook.yml` / `build/playbook-internal.yml` with `ui.supplemental_files` and (when branded) `site.keys.navbar_logo: guide` (the UI sees it as `site.keys.navbarLogo`); in a main checkout the generated playbook also replaces every `url: .` content source with the absolute guide root and makes `output.dir`, a relative bundle URL, and relative extensions absolute with the existing `_absolute` helper (the playbook now lives in `build/`); in a linked worktree combine this with the existing worktree rewrites; keep printing the committed playbook unchanged when neither branding nor an overlay applies (a missing guide.yaml counts as no branding block); update the module docstring; make T013 pass
- [X] T016 [US1] Create tests/adapters/test_antora_branding.sh (same structure and env handling as tests/adapters/test_antora.sh): scaffold the fixture guide with tests/adapters/scaffold.sh, add the SC-008 branding block (`logo_text: Agent Starter Kits`, footer text "Agent Starter Kits on GitHub" linking https://github.com/red-hat-data-services/agentic-starter-kits; five lines, SC-001), commit it in the fixture guide, run `make check`; assert for `build/site` and `build/site-internal` that every page's `navbar-logo-img` references `img/logo-guide.svg` with alt "Red Hat Agent Starter Kits", the built `_/img/logo-guide.svg` contains "Agent Starter Kits" and no "Demo Platform", the footer contains the link and no `demo.redhat.com`, and `git status --porcelain` is empty; then set both `logo_text` and `logo`, remove `build/site`, and assert `make site` exits non-zero, prints a `guide.yaml:branding` line, and leaves no `build/site` behind (Antora never ran)

**Checkpoint**: US1 works end to end; the guide header and footer are branded in both views

---

## Phase 4: User Story 2, keep unbranded guides unchanged (Priority: P1)

**Goal**: Guides without a branding block and without `ui/supplemental/` build exactly as before the feature.

**Independent Test**: Build the unbranded fixture with the toolkit from before the feature and with the new toolkit; compare the site output and the PDF title page.

- [X] T017 [P] [US2] Add tests to tests/toolkit/test_playbook.py and tests/toolkit/test_guidecfg.py: an unbranded guide without overlay in a main checkout gets the committed `site.yml` / `site-internal.yml` path and no `build/branding/` or `build/playbook*.yml` is created; a guide.yaml without `branding` validates with the same output as before
- [X] T018 [US2] Extend tests/adapters/test_antora_branding.sh with the SC-002 comparison: export the repository as of `BASELINE_REF` (default `161d92f`, the last commit that changed `guide/` or `tests/` before this feature, overridable by env) with `git -C "$REPO" archive "$BASELINE_REF" guide tests | tar -x -C "$base"`, failing with a clear message when `git cat-file -e "$BASELINE_REF^{commit}"` fails (for example in a shallow clone); scaffold the unbranded fixture with the archived `"$base/tests/adapters/scaffold.sh" antora "$guide"` (it uses the archived plugin, because it locates the plugin relative to itself; the current `tests/adapters/scaffold.sh` would install the new toolkit and make the comparison vacuous), run `make pdf`, and move `build/site`, `build/site-internal`, and `dist/*.pdf` aside; refresh the toolkit with the current `"$REPO/guide/scripts/scaffold-project.sh" --format antora --toolkit-only "$guide"`, run `make clean` (so no stale file can mask a missing one) and `make pdf`; assert `diff -r` finds no difference in both site trees, `build/branding/` and `build/playbook*.yml` do not exist, and the PDF's first page has the same text (pypdf `extract_text`) and the same content stream bytes (pypdf `pages[0].get_contents().get_data()`; Chromium writes identical page content for identical input, only the metadata differs)

**Checkpoint**: Unbranded guides proven unchanged

---

## Phase 5: User Story 3, branded PDF title page (Priority: P2)

**Goal**: The PDF title page of a branded guide starts with the logo on a dark band, embedded, for both views.

**Independent Test**: `make pdf` for the branded fixture; page 1 has an embedded image and the title.

- [X] T019 [US3] Extend tests/adapters/test_antora_branding.sh: for the branded fixture run `make pdf` and `make pdf VIEW=internal`; assert with a small `uv run --with pypdf` snippet that the extracted text of page 1 of each PDF contains "Agent Starter Kits" before the guide title, and that no page of either PDF contains "Demo Platform" (SC-008). Chromium draws an SVG `<img>` as vector content in the page content stream, so the PDF has no image XObject to look for; the logo text comes out of `extract_text` (verified with a `textLength`-adjusted text). Then switch the fixture to `logo: branding/own-logo.svg` (a test SVG whose `<text>` reads "OwnLogoMarker", plus `logo_alt`), run `make pdf`, assert page 1 contains "OwnLogoMarker" (US3 scenario 2), and restore the SC-008 block; finally delete `build/branding/shareable/branding.json` and assert `make print-pdf` fails with "branding output missing for the shareable view"
- [X] T020 [US3] Update guide/toolkit/print-pdf.mjs: when `guide.yaml` has a `branding` block, read `build/branding/<view>/branding.json` (view `shareable` or `internal`) and the logo file in `main`, pass `{src: "data:image/svg+xml;base64,...", alt}` to `transformDocument` as `meta.brand`, and there insert `<div class="guide-brand-band"><img src="..." alt="<escaped alt>"></div>` as the first child of the title page (the title page is created inside `transformDocument`); add the band CSS to `PRINT_CSS` (background `#151515`, full width, padding, `print-color-adjust: exact`, and `.guide-brand-band img { height: 14mm !important; width: auto !important; }`: the existing `img { max-width: 100% !important; height: auto !important; }` rule otherwise wins and stretches the logo to the full page width, verified in Chromium); fail with `branding output missing for the <view> view; run make check` when the JSON or the logo is missing; leave the title page untouched without a branding block; update the header comment

**Checkpoint**: Branded PDFs carry the logo; unbranded PDFs unchanged (T018)

---

## Phase 6: User Story 4, choose branding while creating a guide (Priority: P2)

**Goal**: The create intake asks Antora authors for branding and scaffolds the guide branded.

**Independent Test**: Read the create skill: an Antora run asks the branding question, MkDocs and gfm runs do not; the setup writes the block, copies own files to `branding/`, and validates.

- [X] T021 [US4] Update guide/skills/create/SKILL.md: in section 4 add an Antora-only intake item "Branding" (default: stock RHDP look; custom: `logo_text` or an own SVG logo, alt text (required for an own logo), footer `none` / text and link / `rhdp`, optional favicon) with the note that `logo_text` renders the Red Hat logo and is meant for guides about Red Hat products (FR-030); in section 5 step 3 write the answers into the `branding` block of guide.yaml, copy an own logo or favicon into `GUIDE/branding/` (the block points at the copy; the original is never moved), and rely on step 7 validation; mention that color and `ui/supplemental/` are later edits documented in docs/branding.md
- [X] T022 [P] [US4] Update guide/templates/guide.yaml with the commented `branding` example from contracts/branding-config.md, the note that it applies to the antora format only, and the Red Hat logo note

**Checkpoint**: New Antora guides can be branded from the intake

---

## Phase 7: User Story 5, adopt branding in an existing guide (Priority: P3)

**Goal**: An existing guide gets branding through the evolve toolkit refresh plus a branding block, with no other file edits.

**Independent Test**: Scaffold with the pre-feature plugin, add a branding block (rejected), refresh the toolkit, build (branded), and confirm the Makefile and playbooks are unchanged.

- [X] T023 [P] [US5] Bump guide/toolkit/VERSION and the `version` in guide/.claude-plugin/plugin.json to `0.2.0` (and the plugin entry in .claude-plugin/marketplace.json if it carries a version)
- [X] T024 [US5] Update guide/skills/evolve/SKILL.md step "Toolkit version": after the refresh, Antora guides can use the `branding` block and `ui/supplemental/` (see docs/branding.md); a branding block added before the refresh is rejected as an unknown key
- [X] T025 [US5] Extend tests/adapters/test_antora_branding.sh: scaffold the fixture with the `BASELINE_REF` plugin (T018), add the branding block and assert `guidecfg.py validate` fails with `guide.yaml:branding: unknown key`; run the current `scaffold-project.sh --format antora --toolkit-only`; assert `tools/guide/branding/` exists, `make check` builds a branded header, and `git diff --quiet -- Makefile site.yml site-internal.yml` holds

**Checkpoint**: Existing guides adopt branding with one refresh and one config change (SC-006)

---

## Phase 8: User Story 6, fine-tune the look (Priority: P3)

**Goal**: Favicon, accent color, and the overlay directory (static files, partials, `css/extra.css`) work, and the preview rebuilds on branding changes.

**Independent Test**: Build the fixture with favicon, color `#3e8635`, and `ui/supplemental/css/extra.css`; inspect the head links and CSS; change `logo_text` during preview.

### Tests for User Story 6

- [X] T026 [P] [US6] Write failing tests in tests/toolkit/test_branding.py: favicon `.ico`, `.png`, `.svg` render `img/favicon-guide.<ext>` and `head-icons.hbs` / `head-meta.hbs` links with `image/x-icon`, `image/png`, `image/svg+xml`; `color` renders `css/branding.css` with one rule per `accent_selectors` entry from contract.yaml using the color and one per `accent_hover_selectors` entry using the hover shade, and no `#06c` or `#004d99`; `head-meta.hbs` links `css/branding.css` then `css/extra.css` (only when present) after the favicon link and is not generated when neither color, favicon, nor `css/extra.css` applies; an overlay file at `partials/footer-content.hbs` while `footer` is set produces the shadowing warning for `branding.footer`

### Implementation for User Story 6

- [X] T027 [US6] Implement favicon, `css/branding.css` (selectors read from tools/guide/branding/contract.yaml), `head-meta.hbs`, `head-icons.hbs`, the `css/extra.css` link, and the shadow warnings in guide/toolkit/branding.py; make T026 pass
- [X] T028 [US6] Update guide/toolkit/preview-watch.mjs: also watch `ui/` and `branding/` (when present) and the `logo` and `favicon` paths from guide.yaml (read with js-yaml), and add newly named paths with `watcher.add` when guide.yaml changes (research.md R11)
- [X] T029 [US6] Extend tests/adapters/test_antora_branding.sh: add `favicon: branding/favicon.png`, `color: "#3e8635"`, and `ui/supplemental/css/extra.css` to the fixture; assert a built page links `css/site.css`, then `css/branding.css`, then `css/extra.css`, links `img/favicon-guide.png` with `image/png`, and that the built `_/css/branding.css` contains `#3e8635`; add an overlay `partials/footer-content.hbs` and assert the build prints the shadowing warning and uses the author's footer; then remove the branding block and `ui/supplemental/`, rebuild with `make check`, and assert `uv run tools/guide/playbook.py path` prints the committed `site.yml` and the pages show `logo-demo-platform.svg` and the stock `demo.redhat.com` footer again (edge case: removing the block returns to the stock look)
- [X] T030 [US6] Extend tests/adapters/test_preview_antora.sh: with a branding block, start the preview, change `logo_text`, and assert the served `_/img/logo-guide.svg` contains the new text within the existing timeout (FR-023)

**Checkpoint**: All branding keys and the overlay directory work in builds and the preview

---

## Phase 9: User Story 7, notice when the UI bundle stops fitting (Priority: P3)

**Goal**: The plugin's tests fail when the pinned bundle drops a relied-upon part, and a guide's `make check` fails when its own build shows no branding.

**Independent Test**: Run the contract checker against the pinned bundle (pass) and a copy without the logo lookup (fail); run `make check` on a branded guide whose overlay is ignored (fail).

### Tests for User Story 7

- [X] T031 [P] [US7] Write failing tests in tests/toolkit/test_branding.py for `check_bundle(bundle, contract)`: a synthetic bundle directory built in the test from contract.yaml's own expectations passes; for every rule and every accent selector a copy with that part removed or changed fails with exactly that rule id; a `.zip` of the synthetic bundle works like the directory; the CLI `contract` exits 0 and 1 accordingly
- [X] T032 [P] [US7] Write failing tests in tests/toolkit/test_check.py for `check.check_branded_site(root, guide)`: built HTML fixtures where the header shows `img/logo-guide.svg` with the right alt pass; the stock `logo-demo-platform.svg` or a wrong alt fails with `[branding] header does not show the branded logo`; a built view where no page has a `navbar-logo-img` at all (a replaced bundle with a different header) fails with `[branding] no page shows the branded logo`; pages under `_exports/` are ignored; a footer element containing `demo.redhat.com` fails when `footer` is `none` or a mapping and passes when it is `rhdp`; "Demo Platform" in page content outside the footer passes; an unbranded guide skips the check; a missing built view is skipped

### Implementation for User Story 7

- [X] T033 [US7] Implement `check_bundle` and the CLI `contract --bundle <zip|dir> [--contract FILE]` in guide/toolkit/branding.py (contracts/bundle-contract.md); make T031 pass
- [X] T034 [US7] Implement `check_branded_site(root, guide)` in guide/toolkit/check.py (contracts/branding-build.md, section Check), returning `Violation(<view>/<page>, 0, "branding", message)` entries, called from `check_pages` when `guide.branding` is set (alt text from `branding.resolve`), and list it in the module docstring; make T032 pass
- [X] T035 [US7] Extend tests/adapters/test_antora_branding.sh: download the bundle URL from guide/adapters/antora/branding/contract.yaml, run `branding.py contract` (exit 0), unpack a copy, delete `partials/header-content.hbs`, rerun (exit 1, output names `logo-lookup`) (SC-007)

**Checkpoint**: Bundle drift and silently ignored branding are caught

---

## Phase 10: Polish & Cross-Cutting Concerns

- [X] T036 [P] Write guide/docs/branding.md: the `branding` keys with defaults and limits, the overlay directory (static files, partials, `css/extra.css`, precedence and warnings), the Red Hat logo note (FR-030), what the PDF shows, how the bundle contract and the `make check` branding check behave, and adoption through `/guide:evolve`
- [X] T037 [P] Update guide/docs/adapters.md (a branding row: Antora supports the six keys, MkDocs and gfm none) and the layout bullet for `guide/adapters/<format>/` in CLAUDE.md (optional `branding/` directory vendored to `tools/guide/branding/`)
- [X] T038 Create tests/adapters/measure_logo.mjs (Playwright Chromium from the fixture's node_modules): open a built page at 1280 x 800, assert the `.navbar-logo-img` right edge is left of the `.site-title` left edge; open the built `logo-guide.svg` directly and assert the text element's `getBBox()` lies inside the viewBox; call it from tests/adapters/test_antora_branding.sh with a 40-character `logo_text`, and also run `make pdf` for that build and assert that the extracted text of PDF page 1 contains the complete 40-character text (the band image keeps its aspect ratio inside the content width, so the whole text is drawn) (SC-004)
- [X] T039 Run `make test`, `make test-adapters`, and `make validate`; fix every failure; run `rg` with `chr(0x2014)` and `chr(0x2013)` patterns over the changed files and remove any hit
- [X] T040 Run quickstart.md sections 1 to 4 and record the outcome (pass, or the failing step with output) in tests/manual/002-antora-branding.md, following the format of tests/manual/us2-evolve.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies; T003 and T004 need the pinned bundle downloaded once
- **Foundational (Phase 2)**: depends on T001 (adapter lists); blocks every user story; T041 depends on T009 and can run in parallel with T010
- **US1 (Phase 3)**: depends on Phase 2 and T003, T005
- **US2 (Phase 4)**: depends on US1's `playbook.py` change (T015)
- **US3 (Phase 5)**: depends on US1 (`branding.json` from T014)
- **US4 (Phase 6)**: depends on Phase 2 only (documentation of the block); can run in parallel with US1
- **US5 (Phase 7)**: depends on US1 and T005; T025 reuses T018's baseline export
- **US6 (Phase 8)**: depends on US1 (render) and T004 (contract selectors)
- **US7 (Phase 9)**: depends on T004; T034 depends on US1 output
- **Polish (Phase 10)**: after all stories

### Within Each Phase

- Tests marked as failing first are written and run before the implementation task that makes them pass.
- `branding.py` tasks (T009, T014, T027, T033) touch the same file and run in order.

### Parallel Opportunities

- T002, T003, T004 in parallel (different files)
- T006, T007, T008 in parallel (T006/T007 share test_branding.py; write them in one sitting or sequentially)
- T011, T012, T013 in parallel with each other's files (T011/T012 share test_branding.py)
- US4 (T021, T022) in parallel with US1
- T026, T031, T032 (tests) in parallel once Phase 2 is done (T026 and T031 share test_branding.py; write them sequentially)
- `tests/adapters/test_antora_branding.sh` tasks (T016, T018, T019, T025, T029, T035, T038) touch the same script and run in order
- T036, T037 in parallel

## Parallel Example: User Story 1

```text
Task: "T013 [US1] playbook tests in tests/toolkit/test_playbook.py"
Task: "T011/T012 [US1] rendering tests in tests/toolkit/test_branding.py"
Then: "T014 rendering in guide/toolkit/branding.py" -> "T015 playbook.py" -> "T016 smoke test"
```

## Implementation Strategy

### MVP first (User Story 1, with US2 as its guard)

1. Phase 1 and Phase 2.
2. Phase 3 (US1): a branded header and footer in both views.
3. Phase 4 (US2): prove unbranded guides are unchanged.
4. Stop and validate: the agentic-starter-kits guide can be created with branding (the paused `/guide:create` run needs only US1 and US4).

### Incremental delivery

5. US3 (PDF), US4 (create intake), then US5 to US7, then polish.
