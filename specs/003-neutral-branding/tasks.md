# Tasks: Neutral Red Hat inspired branding for new guides

**Input**: Design documents from `specs/003-neutral-branding/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Requested (test-first per phase, as in spec 002). The toolkit is developed with pytest (`make test`); the Antora build, PDF, and browser behavior get shell plus Playwright smoke tests under `tests/adapters/` (`make test-adapters`).

**Organization**: One phase per user story in priority order (US1 to US3 are P1, US4 P2, US5 P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1 to US5)

## Path Conventions

- Plugin: `guide/` (toolkit in `guide/toolkit/`, Antora adapter in `guide/adapters/antora/`, scripts in `guide/scripts/`, skills in `guide/skills/`)
- Tests: `tests/toolkit/` (pytest; this feature's branding tests live in `tests/toolkit/test_branding_neutral.py`, next to the spec 002 `test_branding.py`, `pythonpath = guide/toolkit`), `tests/adapters/` (shell smoke tests, fixture guide via `tests/adapters/scaffold.sh`), golden files in `tests/fixtures/branding/`

## Global Constraints

- No em dash or en dash characters in any file; tests that need one build it with `chr(0x2014)` / `chr(0x2013)`. Tests that need CJK input build it with `chr(0x6F22)` and similar, so test files stay ASCII where practical.
- The toolkit imports nothing from outside its own directory. Fonts and the manifest live in `guide/adapters/antora/branding/fonts/` and reach guides as `tools/guide/branding/fonts/` through the existing `scaffold-project.sh` copy of the adapter's `branding/` directory; `branding.asset_dir()` already resolves both locations.
- fontTools is imported only inside the outline functions (`from fontTools... import ...` in the function body), never at module level. Only `branding.py` and `playbook.py` declare it, as `fonttools[woff]==4.67.0`, in their PEP 723 headers. `guidecfg.py`, `check.py`, `attrs.py`, and `mkdocs_macros.py` keep `dependencies = ["pyyaml"]` (research R4). The pytest environment provides fontTools through `--with 'fonttools[woff]==4.67.0'` in the Makefile `test` target (T019).
- Guides without `theme` (or with `theme: stock`) and without `wordmark` produce byte-identical build output to commit `b0db967` (the last commit on `main` before this feature) (SC-004, research R9). Do not refactor the stock code paths of `logo_svg`, `head_meta`, or `_render_into`; branch off them.
- Outline rendering is deterministic: same text, font, and toolkit version give the same bytes (FR-009). Numbers are formatted with at most two decimals, trailing zeros and a trailing dot stripped, and `-0` written as `0`.
- No network access at build or print time. The only download is `update-fonts.py`, run once by hand in T003; its output is committed.
- The pinned bundle URL stays `https://github.com/rhpds/rhdp_showroom_theme/releases/download/v2.0.3/ui-bundle.zip`; never fork, patch, or replace it.
- Use `uv` (PEP 723 scripts with `uv run`), never pip. Commits end with `Assisted-By: 🤖 Claude Code`.

## Interfaces

Names and types shared across tasks. A task that consumes one of these uses exactly this name and shape.

```python
# guide/toolkit/branding.py (additions and changes)
KEYS = ("logo_text", "wordmark", "logo", "logo_alt", "footer", "favicon", "color", "theme")
THEMES = ("neutral", "stock")
WORDMARK_WEIGHT = 500
LOGO_TEXT_WEIGHT = 700                  # the template's font-weight
THEME_CSS = "css/theme-neutral.css"
FONT_DIR = "font"                       # in the overlay: font/<file>, font/OFL.txt

def fonts_dir() -> Path                 # asset_dir() / "fonts"
def load_manifest(path: Path | None = None) -> dict          # fonts.yaml of fonts_dir() unless path is given
def missing_glyphs(text: str, manifest: dict | None = None) -> list[str]
    # characters of text (in order, without repeats) outside manifest["display_coverage"]
def check_fonts(root: Path, manifest: dict | None = None) -> list[tuple[str, str]]
    # (location, message) per missing or mismatching file of the manifest plus OFL.txt;
    # location is the path relative to root when inside root, else relative to the plugin
    # repository root (guide/adapters/antora/branding/fonts/<file>)
def outline(text: str, weight: int) -> tuple[list[str], float]
    # SVG path data, one string per glyph that draws something (spaces draw nothing), in
    # logo units at font size 82 with the baseline at y 0 and the first glyph at x 0;
    # and the total advance width in the same units
def wordmark_svg(text: str) -> str      # contracts/theme-build.md "Logo"
def logo_svg(text: str, theme: str = "stock") -> str
    # "stock": unchanged spec 002 output; "neutral": template with outlined text
def theme_css(manifest: dict | None = None) -> str            # contracts/theme-build.md
def head_meta(favicon_link: str, color: bool, extra_css: bool, theme: bool = False) -> str

@dataclass
class Resolved:                         # adds two fields after the spec 002 ones
    ...; wordmark: str | None = None; theme: str = "stock"

# build/branding/<view>/branding.json (branded guides) adds:
{"theme": "neutral" | "stock", "fonts": "<abs build/branding/<view>/ui/font>" | null}

# guide/toolkit/check.py
def check_neutral_theme(root: Path, guide: guidecfg.Guide) -> list[Violation]   # rule "branding", line 0
```

Validation messages are exactly those in data-model.md.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Vendored fonts and manifest, their distribution, the stock golden files, and the adapter and contract additions

- [X] T001 Capture the stock golden files before any `branding.py` change: from the worktree at commit `b0db967`, run `uv run --with pyyaml python -c` importing `guide/toolkit/branding.py` and write `logo_svg("Agent Starter Kits")`, `logo_svg("Summit")`, `logo_svg("Agent & <Starter> \"Kits\"")`, and `head_meta(STOCK_FAVICON, True, True)` to tests/fixtures/branding/stock-logo-agent-starter-kits.svg, stock-logo-summit.svg, stock-logo-escaped.svg, and stock-head-meta-color-extra.hbs; add tests in tests/toolkit/test_branding_neutral.py that compare the current functions against these files byte for byte (they pass now and guard SC-004 for every later task)
- [X] T002 [P] Create guide/adapters/antora/branding/fonts/update-fonts.py (PEP 723: `fonttools[woff]==4.67.0`, `pyyaml`; maintainer tool, never vendored): `--release <tag>` (default `5.0.0`) downloads the six files listed in research.md R2 and `OFL.txt` from `https://raw.githubusercontent.com/RedHatOfficial/RedHatFont/<tag>/<upstream path>` into its own directory, computes each sha256, reads the `wght` axis range from `fvar`, derives `family` (from the file name: Red Hat Display, Red Hat Text, Red Hat Mono) and `style` (`italic` for `-Italic-`), computes `display_coverage` as sorted, merged inclusive code point ranges of `RedHatDisplay-VF.woff2`'s best cmap, and writes `fonts.yaml` in the shape of data-model.md with a header comment naming the script; it prints a summary and changes nothing else
- [X] T003 Run `uv run guide/adapters/antora/branding/fonts/update-fonts.py --release 5.0.0`; confirm the six checksums equal research.md R2 and the axis ranges are 300 to 900 (Display) and 300 to 700 (Text, Mono); commit the fonts, `OFL.txt`, and `fonts.yaml`
- [X] T004 [P] Update guide/adapters/antora/branding/NOTICE.md: a section for the Red Hat fonts (release 5.0.0, https://github.com/RedHatOfficial/RedHatFont, SIL Open Font License 1.1, the file list, `OFL.txt` next to them) stating that logos with outlined text are a rendering of Red Hat Display, and that the built site publishes `OFL.txt` with the fonts (FR-029)
- [X] T005 Update guide/scripts/scaffold-project.sh to exclude `fonts/update-fonts.py` from the branding copy (add `--exclude 'update-fonts.py'` to the existing rsync); extend tests/toolkit/test_scaffold_project.py: a full antora scaffold and a `--toolkit-only` refresh both have `tools/guide/branding/fonts/fonts.yaml`, `OFL.txt`, and the six `.woff2` files byte-identical to the plugin copies, and no `update-fonts.py`
- [X] T006 [P] Add `wordmark` and `theme` to the `branding:` list in guide/adapters/antora/adapter.yaml (MkDocs and gfm keep `[]`)
- [X] T007 [P] Add the rules `font-stacks`, `navbar-rule`, and `navbar-css` from contracts/bundle-contract.md to guide/adapters/antora/branding/contract.yaml; run `uv run guide/toolkit/branding.py contract --bundle <pinned bundle zip>` and confirm exit 0; confirm the parametrized synthetic-bundle tests in tests/toolkit/test_branding.py (section "bundle contract") pass for the new rules and each new rule fails when its string is removed (FR-028)

**Checkpoint**: fonts vendored and verified; stock golden files guard every later change

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Keys, validation, manifest reading, and resolved values, shared by every user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T008 [P] Write failing tests in tests/toolkit/test_branding_neutral.py for `check()` and `check_guide()` with the new keys: exactly one of `logo_text`, `wordmark`, `logo` (none, two, three: `guide.yaml:branding: set exactly one of logo_text, wordmark, or logo`); `wordmark` empty, whitespace only, with a line break, 41 characters (40 passes, message `must be one line of 1 to 40 characters (got 41)`); `theme` values `neutral` and `stock` pass, `dark`, `""`, `1`, and `null` fail with `guide.yaml:branding.theme: must be neutral or stock (got <value>)`; `wordmark` containing `chr(0x6F22)` fails with `no glyph for "<char>" (U+6F22) in Red Hat Display`; `logo_text` with that character passes under `stock` and fails under `neutral`; each missing glyph is reported once, in text order; `wordmark` and `theme` rejected for adapter lists `[]` naming the format (FR-005); font checks (below) run only when `theme: neutral` or `wordmark` is set
- [X] T009 [P] Write failing tests in tests/toolkit/test_branding_neutral.py for the manifest: `load_manifest()` returns six `files` entries with the keys of data-model.md; every listed file and `OFL.txt` exists in `fonts_dir()` and its sha256 matches; `display_coverage` contains `0x20` to `0x7E` and `0xE9`, not `0x6F22`; `missing_glyphs("Agent & Kits")` is `[]`; `check_fonts(root)` reports `<location>: missing; refresh the toolkit (scaffold-project.sh --toolkit-only)` for a deleted file and `<location>: checksum mismatch; refresh the toolkit (scaffold-project.sh --toolkit-only)` for a changed one (copy `fonts_dir()` into `tmp_path` and monkeypatch `branding.fonts_dir`), with the location relative to the guide root when the fonts are inside it
- [X] T010 [P] Write failing tests in tests/toolkit/test_branding_neutral.py for `resolve()`: `wordmark` trimmed, alt default is the wordmark (no prefix), explicit `logo_alt` wins; a wordmark `Agent & <Kits> "x"` becomes that exact alt string and `alt_helper()` returns it unchanged (Handlebars escapes it in the attribute, as in spec 002); `theme` defaults to `stock`; `logo_text` alt default unchanged (`Red Hat <logo_text>`)
- [X] T011 Implement in guide/toolkit/branding.py: `KEYS`, `THEMES`, weights and path constants from Interfaces; `fonts_dir()`, `load_manifest()`, `missing_glyphs()`, `check_fonts()`; extend `_check_block` for the exclusivity rule (replace the two-key check), `wordmark` rules (reuse the `logo_text` length check), `theme` values, glyph coverage, and font checks; extend `Resolved` and `resolve()`; update `generated_files()` so the logo comes from `branding.wordmark` when set; update the module docstring's example block; make T008 to T010 pass and keep T001 green
- [X] T012 Add a test to tests/toolkit/test_guidecfg.py: `guidecfg.py validate` on an Antora guide with `wordmark` and `theme: neutral` exits 0; with `theme: dark` prints the theme line and exits 1; confirm `guidecfg.py` still runs with only pyyaml (run it through `uv run` in the test with its own header, not the pytest environment)

**Checkpoint**: `make test` passes; new keys validate; no rendering yet

---

## Phase 3: User Story 1, neutral look for a non-Red Hat guide (Priority: P1) 🎯 MVP

**Goal**: A guide with `wordmark`, `theme: neutral`, and `footer: none` shows an outlined wordmark, the vendored Red Hat fonts, and the red navbar rule, and `/guide:create` writes that block.

**Independent Test**: Scaffold the fixture guide with the User Story 1 block, run `make check`, and probe the built page in Chromium (font loaded, navbar shadow, navbar height, logo without `<text>`).

### Tests for User Story 1

- [X] T013 [P] [US1] Write failing tests in tests/toolkit/test_branding_neutral.py for `outline()` and `wordmark_svg()`: `outline("OpenClaw on OpenShift", 500)` returns 19 path strings (21 characters, two spaces) and an advance of about 897.4 (tolerance 0.5); two calls return identical results; heavier weight gives a different path for the same glyph; `wordmark_svg` has no `<text`, no `<style`, and no `font-` attribute (so no browser font choice can change it, SC-003), at least one `<path` per non-space character, `viewBox="0 0 <ceil(advance)> 178.739"`, a `<g transform="translate(0 149)" fill="#fff">`, the font and license comment, no `-0` number, and no number with more than two decimals; output equals the golden file tests/fixtures/branding/wordmark-openclaw.svg (create it from the first passing implementation and review it in a browser before committing); `wordmark_svg("A  B")` keeps the double space (its advance equals the sum of the glyph advances of `A`, two spaces, and `B`); `wordmark_svg` of 40 characters renders in under 0.5 s
- [X] T014 [P] [US1] Write failing tests in tests/toolkit/test_branding_neutral.py for the neutral overlay from `render(root, view)`: with `wordmark` and `theme: neutral`, `ui/font/` holds the six fonts and `OFL.txt` byte-identical to `fonts_dir()`; `ui/css/theme-neutral.css` equals `theme_css()`, which has the generated-file comment, one `@font-face` per manifest entry in manifest order (family, `url("../font/<file>") format("woff2")`, `font-weight: <min> <max>`, `font-style`, `font-display: swap`), and `.navbar { box-shadow: inset 0 -3px 0 #e00; }`, and nothing that sets a link, admonition, or code color; `ui/partials/head-styles.hbs` is `NEUTRAL_HEAD_STYLES`, the stock partial (contract rule `head-styles-stock`) minus its three Google Fonts links (research R11); `ui/partials/head-meta.hbs` links `theme-neutral.css`, and with `color` and `ui/supplemental/css/extra.css` the order is `branding.css`, `theme-neutral.css`, `extra.css`; `branding.json` has `"theme": "neutral"`, `"fonts"` pointing at the final `ui/font` directory, and `"font_faces"` listing one `{family, file, weight, style}` per manifest entry in manifest order; `theme: neutral` with an own `logo` copies the logo byte for byte and still adds the fonts and theme CSS; an author file `ui/supplemental/css/theme-neutral.css` wins and triggers the shadow warning `shadows the file generated for branding.theme`; `wordmark` with `theme: stock` renders the outlined logo but no fonts, no theme CSS, and `"fonts": null` and `"font_faces": []`
- [X] T015 [P] [US1] Write failing tests in tests/toolkit/test_check.py for `check_neutral_theme(root, guide)`: a built view where one page lacks the `theme-neutral.css` link reports `[branding] page does not load the neutral theme` for that page; a view without `_/font/OFL.txt` reports `neutral theme font missing: OFL.txt`; a page that still links fonts.googleapis.com reports `page still loads Google Fonts`; pages under `_exports/` are skipped; the internal view is checked only while the internal part is enabled; `theme: stock` or no block returns `[]`; the existing branded-site check accepts a `wordmark` guide whose pages show `img/logo-guide.svg` with the wordmark as alt (FR-027)
- [X] T016 [P] [US1] Write a failing test in tests/toolkit/test_playbook.py: `uv run guide/toolkit/playbook.py path` (subprocess, the script's own PEP 723 environment) for a guide with `wordmark` and `theme: neutral` exits 0 and the overlay it renders contains `img/logo-guide.svg` without `<text` and `css/theme-neutral.css`

### Implementation for User Story 1

- [X] T017 [US1] Implement `outline()` and `wordmark_svg()` in guide/toolkit/branding.py per research R3 and R8 (lazy fontTools imports; `TTFont(fonts_dir() / "RedHatDisplay-VF.woff2")`, `instantiateVariableFont(font, {"wght": weight}, inplace=False)`, `SVGPathPen` through `TransformPen((s, 0, 0, -s, x, 0))`, `s = 82 / unitsPerEm`, number formatting from Global Constraints); cache the instanced font per weight within one process; make T013 pass
- [X] T018 [US1] Implement the neutral overlay in guide/toolkit/branding.py: `theme_css()`, the `theme` parameter of `head_meta()` (stock call path unchanged), `_render_into` writes the wordmark logo for `wordmark`, and for `theme: neutral` the fonts, `OFL.txt`, `theme-neutral.css`, and `head-meta.hbs`; `generated_files()` maps `css/theme-neutral.css`, `font/<file>`, and `font/OFL.txt` to `branding.theme`; `branding.json` gains `theme`, `fonts`, and `font_faces`; make T014 pass and keep T001 green
- [X] T019 [US1] Add `fonttools[woff]==4.67.0` to the PEP 723 headers of guide/toolkit/branding.py and guide/toolkit/playbook.py and to the pytest environment by adding `--with 'fonttools[woff]==4.67.0'` to the `test` target in the Makefile; make T016 pass
- [X] T020 [US1] Implement `check_neutral_theme()` in guide/toolkit/check.py and call it wherever `check_branded_site()` is called; make T015 pass
- [X] T021 [US1] Create tests/adapters/measure_neutral.mjs (Playwright Chromium from the fixture's node_modules, same loading pattern as tests/adapters/measure_logo.mjs): open a built page at 1280 x 800, wait for `document.fonts.ready`, and print JSON with `document.fonts.check('16px "Red Hat Text"')`, `document.fonts.check('16px "Red Hat Display"')`, the computed `box-shadow` and `height` of `.navbar`, and the computed `font-family` of `body`; exit 1 when the page fails to load
- [X] T022 [US1] Create tests/adapters/test_antora_neutral.sh (structure and env handling of tests/adapters/test_antora_branding.sh): scaffold the fixture guide, add `branding: {wordmark: OpenClaw on OpenShift, theme: neutral, footer: none}`, commit it in the fixture, run `make check`; assert every page in `build/site` (and `build/site-internal`) shows `img/logo-guide.svg` with alt "OpenClaw on OpenShift", the built logo has no `<text`, `_/font/` has the six fonts and `OFL.txt`, no footer contains `demo.redhat.com`; run measure_neutral.mjs and assert, with Google Fonts requests blocked and counted, that the vendored Red Hat Text and Display faces loaded and no Google Fonts request was made (SC-007), the box shadow is `rgb(238, 0, 0) 0px -3px 0px 0px inset`, and the navbar height equals the height measured on a stock build of the same fixture; assert `git status --porcelain` is empty; finally delete `build/site/_/font/OFL.txt`, run only `uv run tools/guide/check.py`, and assert it reports `neutral theme font missing: OFL.txt`
- [X] T023 [US1] Rewrite step 5 of guide/skills/create/SKILL.md per research R10 and contracts/branding-config.md: Antora only; ask "Is this guide about a Red Hat product?"; yes leads to `logo_text` (short product name, 1 to 40 characters); no leads to `wordmark`, proposing the guide title when it has at most 40 characters and otherwise asking for a shorter text; then offer the follow-ups (own SVG logo instead, with required alt text; footer text with optional link; favicon); always write `theme: neutral` and `footer: none` unless a follow-up set the footer; do not offer the RHDP look, and point to `$PLUGIN/docs/branding.md` for it; update step 5.3 (project setup) so the branding block is written for every Antora guide (FR-021 to FR-023)
- [X] T024 [P] [US1] Update the commented branding example in guide/templates/guide.yaml: show `wordmark` as the alternative to `logo_text` (with the note that `logo_text` renders the Red Hat logo and is meant for Red Hat products), and `theme: neutral` with a one-line explanation (FR-024)

**Checkpoint**: US1 works end to end; a new non-Red Hat guide has no Red Hat logo and no Demo Platform notice

---

## Phase 4: User Story 2, hat variant with outlined text (Priority: P1)

**Goal**: `logo_text` with `theme: neutral` keeps the Red Hat hat and renders the product name as Red Hat Display Bold outlines.

**Independent Test**: Build the fixture with `logo_text: OpenShift AI` and `theme: neutral`; inspect the logo SVG and the alt text.

- [X] T025 [P] [US2] Write failing tests in tests/toolkit/test_branding_neutral.py for `logo_svg(text, "neutral")`: no `<text`; every `<path` of the template outside the `<text>` element and the MPL-2.0 comment appear unchanged; a `<g transform="translate(308 149)" fill="#fff">` holds one path per non-space character drawn at weight 700; the viewBox width is `max(780, ceil(308 + advance + 24))`; output equals tests/fixtures/branding/logo-text-neutral-openshift-ai.svg (created from the first passing implementation and reviewed in a browser); `logo_svg(text)` and `logo_svg(text, "stock")` still equal the T001 golden files
- [X] T026 [US2] Implement the `theme` parameter of `logo_svg()` in guide/toolkit/branding.py: for `neutral`, read the template, replace the whole `<text ...>...</text>` element with the outlined group (match the element with one regular expression anchored on `<text ` and `</text>`; fail loudly if it does not match exactly once), and fill `{{VIEWBOX_WIDTH}}` with the new width; `_render_into` passes `brand.theme`; make T025 pass
- [X] T027 [US2] Extend tests/adapters/test_antora_neutral.sh: switch the fixture block to `logo_text: OpenShift AI` with `theme: neutral`, rebuild, assert the logo contains the hat paths and the MPL-2.0 comment and no `<text`, and every page's alt text is "Red Hat OpenShift AI"

**Checkpoint**: Both create answers produce a neutral guide

---

## Phase 5: User Story 3, existing guides do not change (Priority: P1)

**Goal**: Guides without a block, and branded guides without `theme`, build byte-identical to commit `b0db967`.

**Independent Test**: Build both fixture kinds with the plugin at `b0db967` and with this branch; compare site trees and the PDF's first page.

- [X] T028 [P] [US3] Add tests to tests/toolkit/test_branding_neutral.py and tests/toolkit/test_playbook.py: a `logo_text` block without `theme` renders exactly the spec 002 file set (no `font/`, no `theme-neutral.css`), its `head-meta.hbs` for `color` plus `extra.css` equals the T001 golden file, and `branding.json` differs from the spec 002 shape only by `"theme": "stock"` and `"fonts": null`; an unbranded guide still gets the committed playbook path and no `build/branding/`
- [X] T029 [US3] Extend tests/adapters/test_antora_neutral.sh with the SC-004 comparison, reusing the baseline export pattern of tests/adapters/test_antora_branding.sh (T018 of spec 002) with `BASELINE_REF=${BASELINE_REF:-b0db967}`: for two fixtures (no block; `logo_text: Agent Starter Kits` with a footer text and no `theme`), scaffold with the archived plugin, run `make pdf`, move `build/site`, `build/site-internal`, and the PDF aside, refresh the toolkit from this branch with `scaffold-project.sh --toolkit-only`, `make clean`, `make pdf`, and assert `diff -r` finds no difference in both site trees and the PDF's first page has the same text and content stream bytes

**Checkpoint**: Existing guides proven unchanged

---

## Phase 6: User Story 4, PDF matches the neutral site (Priority: P2)

**Goal**: The PDF of a neutral guide uses the Red Hat fonts and shows the red rule under the title band.

**Independent Test**: `make pdf` for the US1 fixture; list the PDF's fonts and render page 1.

- [X] T030 [US4] Update guide/toolkit/print-pdf.mjs per contracts/theme-build.md "PDF typography": read `theme`, `fonts`, and `font_faces` from `branding.json` (the printer reads no other branding file); for `neutral`, fail with `branding output missing for the <view> view; run make check` when the `fonts` directory or a listed file is missing, and inject one `@font-face` rule per `font_faces` entry with `pathToFileURL(<fonts>/<file>).href`, its family, weight range, and style, plus the typography overrides (body Red Hat Text; `h1` to `h6`, `.guide-title-page`, `.guide-toc` Red Hat Display; `pre`, `code` Red Hat Mono); add `border-bottom: 3px solid #e00` to `.guide-brand-band` for `neutral` only; without `neutral` the injected CSS is unchanged; update the header comment
- [X] T031 [US4] Extend tests/adapters/test_antora_neutral.sh: run `make pdf` for a neutral fixture (the printer blocks remote fonts itself); list the PDF's embedded fonts with pypdf (each page's `/Resources /Font` subtype and `/BaseFont`) and assert Type3 fonts are present (Chromium embeds the vendored variable fonts as unnamed Type3 fonts, so names cannot be checked) and no serif fallback (Times, Noto Serif, DejaVu Serif, Georgia) is embedded; render page 1 with pypdfium2 and assert a row of red pixels (`#e00` within tolerance) directly under the dark band

**Checkpoint**: Neutral PDF matches the site

---

## Phase 7: User Story 5, adopt the theme in an existing guide (Priority: P3)

**Goal**: A toolkit refresh tells the author about `theme: neutral` and `wordmark`; adding them works.

**Independent Test**: Refresh a 0.3.x fixture through the scaffold script, add `theme: neutral`, rebuild.

- [X] T032 [P] [US5] Update guide/skills/evolve/SKILL.md: after a toolkit refresh that moves a guide from below 0.4.0 to 0.4.0 or later, the summary names `theme: neutral` and `wordmark` as newly available and points to `docs/branding.md`; evolve never edits the branding block (FR-025)
- [X] T033 [US5] Extend tests/adapters/test_antora_neutral.sh: take the branded fixture from T029 after its refresh, add `theme: neutral`, rebuild with `make check`, and assert the neutral overlay (fonts, theme CSS link, outlined `logo_text`)

**Checkpoint**: Adoption path verified

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T034 [P] Update guide/docs/branding.md (FR-030): correct the opening paragraph (new guides get the neutral theme from create; RHDP is the look of guides without a block); add `wordmark` and `theme` to the key table; a "Neutral theme" section (fonts, the navbar rule, outlined logos, what it never changes, interaction with `color` and `ui/supplemental/`, the PDF typography); a "Red Hat Demo Platform look" section (remove the block, or `theme: stock` with `footer: rhdp`); the new validation lines; the font and OFL attribution; adoption needs toolkit 0.4.0
- [X] T035 [P] Set the version to 0.4.0 in guide/toolkit/VERSION, guide/.claude-plugin/plugin.json, and the plugin entry of .claude-plugin/marketplace.json; update the layout bullet for `guide/adapters/<format>/` in CLAUDE.md to mention the vendored fonts (FR-031)
- [X] T036 [P] Add `test_antora_neutral.sh` to the `test-adapters` target in the Makefile, next to `test_antora_branding.sh` (no change needed: `ADAPTER_TESTS := $(wildcard tests/adapters/test_*.sh)` already picks it up)
- [X] T037 Run `make test`, `make test-adapters`, and `make validate`; fix every failure; scan every changed file for code points 0x2014 and 0x2013 and remove any hit; check that the built neutral site adds at most 300 KB over a stock build (SC-005)
- [ ] T038 Run quickstart.md sections 1 to 6 and a `/guide:create` intake for a scratch Antora guide (section 7, both answers); refresh a guide scaffolded at `b0db967` through `/guide:evolve` and record that its summary names `theme: neutral` and `wordmark` (FR-025); record the outcomes in tests/manual/003-neutral-branding.md in the format of tests/manual/002-antora-branding.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 first (before any `branding.py` change); T002 before T003; T003 before T005 and T009; T004, T006, T007 independent
- **Foundational (Phase 2)**: depends on T001, T003, T006; blocks every user story
- **US1 (Phase 3)**: depends on Phase 2
- **US2 (Phase 4)**: depends on T017 (`outline()`) and T018 (theme passed to rendering)
- **US3 (Phase 5)**: depends on US1 and US2 (it proves their changes leave stock paths alone)
- **US4 (Phase 6)**: depends on T018 (`branding.json` fields)
- **US5 (Phase 7)**: depends on T029 (refreshed branded fixture)
- **Polish (Phase 8)**: after all stories

### Within Each Phase

- Tests marked as failing first are written and run before the implementation task that makes them pass.
- `branding.py` tasks (T011, T017, T018, T019, T026) touch the same file and run in order.
- `tests/adapters/test_antora_neutral.sh` tasks (T022, T027, T029, T031, T033) touch the same script and run in order.

### Parallel Opportunities

- T002, T004, T006, T007 in parallel
- T008, T009, T010 in parallel by intent (all in test_branding.py; write them in one sitting)
- T013, T014 (test_branding.py), T015 (test_check.py), T016 (test_playbook.py) in parallel across files
- T023 and T024 in parallel with the US1 implementation tasks
- T030 (print-pdf.mjs) in parallel with US2 and US3 once T018 is done
- T032, T034, T035, T036 in parallel

## Parallel Example: User Story 1

```text
Task: "T013/T014 [US1] outline and overlay tests in tests/toolkit/test_branding.py"
Task: "T015 [US1] neutral check tests in tests/toolkit/test_check.py"
Task: "T016 [US1] playbook subprocess test in tests/toolkit/test_playbook.py"
Task: "T023 [US1] create intake in guide/skills/create/SKILL.md"
Then: "T017 outline" -> "T018 overlay" -> "T019 dependencies" -> "T020 check.py" -> "T021/T022 smoke test"
```

## Implementation Strategy

### MVP first (User Story 1, with US3 as its guard)

1. Phase 1 and Phase 2 (T001 golden files first).
2. Phase 3 (US1): neutral wordmark guides build and create writes the block.
3. Stop and validate: run the US1 smoke test; the T001 golden tests still pass.

### Incremental delivery

4. US2 (hat variant), then US3 (byte-identity proof against `b0db967`), then US4 (PDF), US5 (adoption), polish.
