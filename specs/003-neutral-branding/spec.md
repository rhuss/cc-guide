# Feature Specification: Neutral Red Hat inspired branding for new guides

**Feature Branch**: `003-neutral-branding`

**Created**: 2026-10-15

**Status**: Draft

**Input**: User description: "Can we create a neutral, Red Hat inspired branding by default (not the RHDP branding that we use now). Let's think about some proposals." Decision from the brainstorming session: Approach A, an explicit neutral preset on top of the existing RHDP showroom UI bundle, written into `guide.yaml` by `/guide:create`.

## Overview

A new Antora guide looks like a Red Hat Demo Platform lab: the header reads "Red Hat | Demo Platform" and the footer says "Powered by Red Hat Demo Platform". Guides built with cc-guide are not Demo Platform labs, so this default misrepresents them. Spec 002 added a `branding` block that fixes this per guide, but only when the author knows to ask for it.

The pinned bundle (RHDP showroom UI v2.0.3) already carries most of the Red Hat look: a `#151515` header, the Red Hat Text, Display, and Mono font stacks, and the Red Hat red `#e00`. Two things are missing. Only the logo and the footer are Demo Platform specific, and the bundle ships no font files: it loads the Red Hat fonts from Google Fonts on every page view, so every reader's browser contacts Google, and offline previews and the PDF (which blocks remote fonts) fall back to Noto or Helvetica.

This feature adds a neutral preset: a text wordmark logo without the Red Hat hat (for guides that are not about a Red Hat product), a `theme: neutral` setting that vendors the Red Hat fonts and adds one red accent rule under the header, and logo text rendered as outlines in Red Hat Display. `/guide:create` writes this preset into every new Antora guide, choosing the hat or the wordmark from one intake question. Existing guides keep their current look until their author opts in.

## Clarifications

### Session 2026-10-15

- Q: Should the default header carry the Red Hat logo (the hat), or only borrow the visual language? → A: Decide per guide at create time. A guide about a Red Hat product gets the hat layout (`logo_text`); any other guide gets a text wordmark without the hat (`wordmark`).
- Q: Implicit default (no block means neutral), explicit preset, or an own UI bundle? → A: Explicit preset. Create writes the `branding` block; a guide without a block still builds byte-identical to today.
- Q: What happens to a branded guide that has no `theme` key (for example the agentic-starter-kits guide)? → A: `theme` defaults to `stock`, so it builds exactly as before.
- Q: Does the create intake still offer the RHDP look? → A: No. RHDP stays reachable by editing `guide.yaml` (no block, or `footer: rhdp`) and is documented in `docs/branding.md`.
- Q: Which weight does the wordmark use? → A: Red Hat Display Medium (500).
- Q: Where does the spec live? → A: `specs/003-neutral-branding/`, following the spec-kit layout of 001 and 002.
- Q (during implementation): The stock bundle loads the Red Hat fonts from fonts.googleapis.com. What does `theme: neutral` do about that? → A: Drop it. The neutral theme replaces `partials/head-styles.hbs` with the stock partial minus its three Google Fonts links, so a neutral site makes no third-party request and uses the vendored fonts only.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - New guide about a non-Red Hat product gets a neutral look (Priority: P1)

An author runs `/guide:create` for a guide about an upstream project (for example OpenClaw on OpenShift). The intake asks whether the guide is about a Red Hat product; the author says no. The built site shows the guide title as a white wordmark in Red Hat Display on the dark header, a thin red rule below the header, body text in Red Hat Text, and an empty footer. Nothing on the page mentions the Red Hat Demo Platform, and no Red Hat logo appears.

**Why this priority**: This is the case the current default gets most wrong: it brands a non-Red Hat guide as a Red Hat Demo Platform lab.

**Independent Test**: Scaffold a fixture Antora guide with `branding: {wordmark: "OpenClaw on OpenShift", theme: neutral, footer: none}`, build it, and inspect the header image, the computed body font, the header border, and the footer in a browser.

**Acceptance Scenarios**:

1. **Given** a guide with `branding.wordmark: OpenClaw on OpenShift`, **When** the site is built, **Then** every page header shows `img/logo-guide.svg`, which contains the text as `<path>` outlines and no `<text>` element and no Red Hat hat.
2. **Given** the same guide, **When** the site is built, **Then** the header logo's alt text is "OpenClaw on OpenShift".
3. **Given** `theme: neutral`, **When** a page is opened in Chromium on a machine without Red Hat fonts installed, **Then** the computed font of body text resolves to the vendored Red Hat Text, and the navigation bar shows a 3px `#e00` rule along its bottom edge without changing its height.
4. **Given** `footer: none`, **When** the site is built, **Then** no page footer contains the Red Hat Demo Platform notice.
5. **Given** `theme: neutral`, **When** a page is opened in Chromium with every Google Fonts request blocked, **Then** the page makes no request to fonts.googleapis.com or fonts.gstatic.com and still loads Red Hat Text and Red Hat Display from the vendored files.

---

### User Story 2 - New guide about a Red Hat product keeps the hat (Priority: P1)

An author creates a guide about a Red Hat product and answers yes to the intake question, giving a short product name. The header shows the Red Hat hat, the divider, and the product name, now set in Red Hat Display as outlines instead of a fallback font. The rest of the page has the same neutral theme as in User Story 1.

**Why this priority**: Most guides cc-guide produces are about Red Hat products, and their logo text currently renders in whichever fallback font the browser has.

**Independent Test**: Build a fixture guide with `branding: {logo_text: "OpenShift AI", theme: neutral, footer: none}` and inspect the logo SVG and the page.

**Acceptance Scenarios**:

1. **Given** `logo_text: OpenShift AI` and `theme: neutral`, **When** the site is built, **Then** `img/logo-guide.svg` contains the Red Hat hat and wordmark paths from the template, the divider, and the product name as `<path>` outlines in Red Hat Display, and keeps the MPL-2.0 notice comment.
2. **Given** the same guide, **When** the site is built, **Then** the default alt text is "Red Hat OpenShift AI", as in spec 002.

---

### User Story 3 - Existing guides do not change (Priority: P1)

An author of an existing guide refreshes the toolkit to the version with this feature. A guide without a branding block, and a branded guide without a `theme` key, build exactly as before.

**Why this priority**: The SAW guide (no block) and the agentic-starter-kits guide (branded, no `theme`) must not change appearance because a toolkit refresh arrived.

**Independent Test**: Build both fixture kinds before and after the change and compare the built site directories and the PDF title pages byte by byte (excluding timestamps the build already varies).

**Acceptance Scenarios**:

1. **Given** an Antora guide without a branding block and without `ui/supplemental/`, **When** it is built after the refresh, **Then** the built pages are identical to the pages built before.
2. **Given** a guide with `branding.logo_text` and no `theme` key, **When** it is built after the refresh, **Then** `img/logo-guide.svg` and every other generated overlay file are identical to the files built before, and no fonts or `theme-neutral.css` are published.

---

### User Story 4 - Branded PDF matches the neutral site (Priority: P2)

An author exports the PDF of a neutral guide. The title page shows the outlined logo on the dark band with the same red rule below it, and the document body uses the vendored Red Hat fonts, without network access during printing.

**Why this priority**: The PDF is the shareable artifact; it should look like the site, but the site matters first.

**Independent Test**: Run `make pdf` for the User Story 1 fixture with networking disabled for the printer, then inspect the embedded fonts (`pdffonts`) and the title page image.

**Acceptance Scenarios**:

1. **Given** a neutral guide, **When** `make pdf` runs, **Then** the PDF title page shows the logo band with a red rule below it.
2. **Given** the same guide, **When** `make pdf` runs, **Then** the PDF embeds Red Hat Text, Red Hat Display, and Red Hat Mono, loaded from the vendored files through file URLs.

---

### User Story 5 - Adopt the neutral theme in an existing guide (Priority: P3)

An author of an existing guide refreshes the toolkit through `/guide:evolve`, which mentions that `theme: neutral` and `wordmark` are now available. The author adds `theme: neutral` (and optionally replaces `logo_text` with `wordmark`) and rebuilds.

**Why this priority**: Opting in is a two-line edit once the toolkit is current; the refresh path already exists from spec 002.

**Independent Test**: Take the User Story 3 branded fixture, refresh the toolkit, add `theme: neutral`, and build.

**Acceptance Scenarios**:

1. **Given** a guide on toolkit 0.3.x and earlier with a branding block, **When** `/guide:evolve` refreshes the toolkit, **Then** its summary names `theme: neutral` and `wordmark` as newly available keys and points to `docs/branding.md`.
2. **Given** the refreshed guide with `theme: neutral` added, **When** it is built, **Then** it shows the neutral theme as in User Story 1 or 2.

---

### Edge Cases

- A `wordmark` or outlined `logo_text` containing a character Red Hat Display has no glyph for (for example CJK or emoji): validation fails and names the character and the key.
- Whitespace: leading and trailing whitespace is trimmed before the length check (as in spec 002); internal runs of spaces are kept and rendered with the font's space advance.
- Characters `&`, `<`, `>`, and quotes in `wordmark` appear literally in the alt text and become glyph outlines in the logo; nothing is inserted as markup.
- A 40-character wordmark: the logo viewBox width follows the real advance widths, so the logo never clips; the header's `2rem` height sizing scales it.
- `theme: neutral` together with `logo` (own SVG): the fonts and the red rule apply; the own logo is copied unchanged as in spec 002.
- `theme: neutral` together with `color`: `branding.css` sets the accent color; `theme-neutral.css` does not touch link colors, so `color` wins.
- `ui/supplemental/css/theme-neutral.css` or `ui/supplemental/font/<file>`: the author's file shadows the generated or vendored one, with the shadowing warning from spec 002.
- A vendored font file missing from `tools/guide/branding/fonts/` (for example a partial toolkit copy) or not matching its pinned checksum: validation fails before Antora runs and tells the author to refresh the toolkit.
- `wordmark` or `theme` in a MkDocs or gfm guide: reported as not supported by that adapter, like the spec 002 keys.
- A playbook that names a different UI bundle: the existing `make check` logo check fails; the new theme check also fails when no page links `theme-neutral.css`.

## Requirements *(mandatory)*

### Functional Requirements

**Configuration**

- **FR-001**: The `branding` block MUST accept a new key `wordmark`, a short text shown as the header logo without the Red Hat hat. Its rules MUST match `logo_text`: one line, 1 to 40 characters after trimming.
- **FR-002**: Validation MUST require exactly one of `logo_text`, `wordmark`, and `logo`, and report `guide.yaml:branding: set exactly one of logo_text, wordmark, or logo` otherwise.
- **FR-003**: With `wordmark`, the default `logo_alt` MUST be the trimmed wordmark text with no prefix. `logo_alt` MAY override it.
- **FR-004**: The `branding` block MUST accept a new key `theme` with the values `neutral` and `stock`. A missing `theme` MUST behave as `stock`. Any other value MUST fail with `guide.yaml:branding.theme: must be neutral or stock (got <value>)`.
- **FR-005**: The MkDocs and gfm adapters MUST report `wordmark` and `theme` as not supported, in the same way as the spec 002 keys.

**Logo rendering**

- **FR-006**: A `wordmark` MUST render to `img/logo-guide.svg` as white (`#fff`) glyph outlines (`<path>` elements) in Red Hat Display at weight 500, on a transparent background, with a viewBox height of 178.739 (the stock logo height), a width of the rounded-up total advance width, and the baseline placed so the capitals are centered vertically (118.07 for Red Hat Display, research R8). The SVG MUST NOT contain a `<text>` element.
- **FR-007**: With `theme: neutral`, `logo_text` MUST render from the existing MPL-2.0 template with the `<text>` element replaced by glyph outlines of the same text in Red Hat Display, at the template's position (`translate(308 149)`), size (82), fill (`#fff`), and weight (700). The hat, the Red Hat wordmark paths, the divider, and the notice comment MUST stay unchanged.
- **FR-008**: With `theme: stock` (or no `theme`), `logo_text` MUST render byte-identical to the spec 002 output.
- **FR-009**: Outline rendering MUST be deterministic: the same text, font file, and toolkit version produce a byte-identical SVG.
- **FR-010**: Outline rendering MUST read the vendored `RedHatDisplay-VF.woff2` and instantiate the needed weight at build time; it MUST NOT require system fonts or network access beyond what `uv run` needs to resolve the script's declared dependencies.
- **FR-011**: Glyph coverage MUST be checked against the code point ranges recorded in the font manifest. When a character of `wordmark` (or of `logo_text` under `theme: neutral`) has no glyph in Red Hat Display, validation MUST fail with `guide.yaml:branding.<key>: no glyph for "<char>" (U+<hex>) in Red Hat Display`.

**Neutral theme**

- **FR-012**: The adapter MUST vendor the Red Hat font release 5.0.0 variable web fonts `RedHatDisplay-VF.woff2`, `RedHatDisplay-Italic-VF.woff2`, `RedHatText-VF.woff2`, `RedHatText-Italic-VF.woff2`, `RedHatMono-VF.woff2`, and `RedHatMono-Italic-VF.woff2` from https://github.com/RedHatOfficial/RedHatFont, with its `OFL.txt` and a manifest that pins the release, the upstream path, and the sha256 of each file.
- **FR-013**: `scaffold-project.sh` (full and `--toolkit-only`) MUST copy the fonts, `OFL.txt`, and the manifest to `tools/guide/branding/fonts/`.
- **FR-014**: With `theme: neutral`, the overlay MUST publish the six fonts and `OFL.txt` under `_/font/`, and a generated `css/theme-neutral.css` that:
  - declares `@font-face` rules with the family names "Red Hat Display", "Red Hat Text", and "Red Hat Mono", the weight range of each variable font as recorded in the manifest (read from the font's `wght` axis when vendoring), normal and italic styles, and `font-display: swap`;
  - draws a 3px `#e00` rule along the bottom edge of the navigation bar (`.navbar`) as an inset box shadow (`box-shadow: inset 0 -3px 0 #e00`), so the bar keeps its height and the page content does not move;
  - sets no colors on links, admonitions, code blocks, or the table of contents;
  - and replaces `partials/head-styles.hbs` with the stock partial minus its three Google Fonts links (two `preconnect` links and the `fonts.googleapis.com` stylesheet), keeping the `css/site.css` link.
- **FR-015**: `partials/head-meta.hbs` MUST link `css/theme-neutral.css` after `css/branding.css` and before `css/extra.css` when each is present.
- **FR-016**: Validation MUST fail when a vendored font file is missing or its sha256 does not match the manifest, naming the file and suggesting a toolkit refresh.
- **FR-017**: With `theme: stock`, no fonts and no `theme-neutral.css` MUST be published, and `head-meta.hbs` MUST be identical to its spec 002 output for the same block.

**PDF**

- **FR-018**: For a neutral guide, the PDF title page band MUST show a 3px `#e00` rule along its bottom edge.
- **FR-019**: For a neutral guide, the PDF printer MUST set body text and every element in it in Red Hat Text (`body *`, which also reaches Asciidoctor's serif block titles), headings, the title page, and the table of contents in Red Hat Display with headings at weight 500, and code in Red Hat Mono (replacing its stock Noto Serif and Helvetica), loading every vendored face explicitly through `file:` URLs before printing, with no network request, and failing when a face does not load. Without `theme: neutral` the PDF typography MUST stay unchanged.
- **FR-020**: `branding.json` MUST carry the theme, the rendered font directory, and the font faces (family, file, weight range, style), so the printer reads neither `guide.yaml` nor the font manifest itself.

**Create and evolve**

- **FR-021**: The create intake (step 5, Antora only) MUST ask whether the guide is about a Red Hat product. Yes MUST lead to `logo_text` with a short product name (1 to 40 characters); no MUST lead to `wordmark`, defaulting to the guide title when it is 40 characters or fewer and otherwise asking for a shorter text.
- **FR-022**: Create MUST write `theme: neutral` and `footer: none` into the `branding` block of every new Antora guide, and keep offering the own-logo, footer text and link, and favicon choices as follow-ups.
- **FR-023**: The create intake MUST NOT offer the RHDP look; `docs/branding.md` MUST describe how to get it (remove the block, or set `footer: rhdp` with `theme: stock`).
- **FR-024**: The `guide.yaml` template MUST show `wordmark` and `theme` in its commented branding example.
- **FR-025**: After a toolkit refresh that moves a guide from below 0.4.0 to 0.4.0 or later, evolve MUST mention `theme: neutral` and `wordmark` and MUST NOT edit the branding block.

**Checks and contract**

- **FR-026**: For a guide with `theme: neutral`, `make check` MUST fail when a built page of a checked view does not link `css/theme-neutral.css` (`[branding] page does not load the neutral theme`), or still links a Google Fonts host (`[branding] page still loads Google Fonts`), or when `_/font/` lacks any of the six fonts or `OFL.txt` (`[branding] neutral theme font missing: <file>`).
- **FR-027**: The existing header and footer checks of spec 002 MUST apply to `wordmark` guides, with the wordmark-derived alt text.
- **FR-028**: `contract.yaml` MUST pin the whole stock `partials/head-styles.hbs` (rule `head-styles-stock`, replacing the spec 002 rule `head-styles-site-css`, whose `css/site.css` link it includes), and add a rule `font-stacks` (`css/site.css` contains the family names "Red Hat Text", "Red Hat Display", and "Red Hat Mono") and the rules `navbar-rule` (`partials/header-content.hbs` contains `<nav class="navbar">`) and `navbar-css` (`css/site.css` contains `.navbar{background:#151515` and `position:fixed`), the element the red rule targets.

**Licensing and docs**

- **FR-029**: `guide/adapters/antora/branding/NOTICE.md` MUST add the Red Hat fonts (OFL-1.1, release, upstream URL) and state that logos with outlined text are a rendering of Red Hat Display under the OFL. The built site MUST publish `OFL.txt` next to the fonts.
- **FR-030**: `docs/branding.md` MUST describe `wordmark`, `theme`, the neutral theme's effects, its interaction with `color` and `ui/supplemental/`, the RHDP opt-out path, and correct its opening paragraph, which states that every Antora guide looks like a Demo Platform lab.
- **FR-031**: The toolkit `VERSION`, the plugin version, and the marketplace entry MUST move to 0.4.0.

### Key Entities

- **Branding block** (`guide.yaml` `branding`): gains `wordmark` (string) and `theme` (`neutral` or `stock`, default `stock`).
- **Font manifest** (`branding/fonts/fonts.yaml`): release tag, upstream repository, per file the upstream path, sha256, family, style, and `wght` axis range, and the code point ranges Red Hat Display covers (so validation checks glyph coverage without loading the font).
- **Outline renderer** (in `branding.py`): turns a text, a weight, and a font file into SVG path data and an advance width; reports missing glyphs.
- **Neutral theme output** (`build/branding/<view>/ui/`): `font/*.woff2`, `font/OFL.txt`, `css/theme-neutral.css`, and the extended `partials/head-meta.hbs`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A guide created with `/guide:create` after this change shows no Red Hat Demo Platform logo or notice on any page or in the PDF.
- **SC-002**: On a machine without Red Hat fonts installed, body text, headings, and code in a neutral guide render in the vendored Red Hat fonts (computed font checked by Playwright).
- **SC-003**: The header logo of a neutral guide looks identical in Chromium, Firefox, and WebKit, because it contains no text that depends on installed fonts.
- **SC-004**: The SAW-style fixture (no block) and the starter-kits-style fixture (branded, no `theme`) build byte-identical site output before and after the change.
- **SC-005**: The neutral theme adds at most 300 KB to the built site (fonts, `OFL.txt`, CSS).
- **SC-007**: A page of a neutral guide makes no request to fonts.googleapis.com or fonts.gstatic.com (Playwright, requests counted).
- **SC-006**: `make test` and `make test-adapters` pass, including the new golden SVG, glyph coverage, checksum, and Playwright font tests.

## Assumptions

- The RHDP showroom UI bundle stays pinned at v2.0.3; this feature does not change the bundle.
- fontTools (with brotli for woff2) can be declared in the PEP 723 header of `branding.py` and resolved by `uv run`; the toolkit stays free of imports from outside its own directory.
- Red Hat font release 5.0.0 is the current release on 2026-10-15; later releases are adopted by updating the manifest and the golden test files.
- The SIL Open Font License 1.1 allows bundling the fonts with the toolkit and the built site, and allows rendering glyphs as outlines in a logo.
- Red Hat Display covers Latin, Latin Extended, and common punctuation, which is enough for product names and guide titles; other scripts are rejected by FR-011 rather than rendered with a fallback.

## Out of Scope

- Theming for the MkDocs and gfm adapters.
- An own UI bundle, or removing the remaining RHDP assets from the pinned bundle.
- Changing the look of already branded or unbranded existing guides without the author opting in.
- A dark mode, a color palette beyond the single red rule, or changes to link, admonition, or code block colors.
