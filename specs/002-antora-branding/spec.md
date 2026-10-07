# Feature Specification: Antora branding for guides

**Feature Branch**: `002-antora-branding`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "Antora branding for guides: build the feature described in brainstorm/02-antora-branding.md (decision: Approach A, overlay rendered at build time). Use that document as the source of requirements, scope, out-of-scope items, and open questions."

## Overview

Every Antora guide that cc-guide scaffolds looks like a Red Hat Demo Platform lab. The header shows the "Red Hat | Demo Platform" logo, its alt text reads "Red Hat Demo Platform", and the footer says "Powered by Red Hat Demo Platform" with a link to demo.redhat.com. Nothing in the guide configuration changes this, so a guide for another product (the first one is the agentic-starter-kits guide, which should read "Red Hat | Agent Starter Kits") either misrepresents itself or needs hand edits that the next toolkit refresh can lose.

This feature lets a guide author give an Antora guide its own branding from the guide configuration: the logo (custom text on the Red Hat logo layout, or the author's own image), the logo's alt text, the footer, the browser-tab icon, and one accent color, plus a directory for any further visual override. The branding appears on both site views and on the PDF title page. Guides that do not use the feature keep today's look exactly.

## Clarifications

### Session 2026-10-07

- Q: Should an author-supplied SVG logo ever be inserted into the site or the PDF as markup, or only shown as an image? → A: Only as an image, in both the site and the PDF; anything inside the SVG (such as scripts) never runs.
- Q: How does a logo made for the dark site header stay legible on the white PDF title page? → A: The title page shows the logo on a band in the site header's background color, so text logos and own logos look as they do in the site; no separate print logo.
- Q: Should the guide's own check step catch a branded guide whose branding silently stopped working (for example after the author changed the UI bundle in their build configuration)? → A: Yes. For a branded guide, the check fails when the built header does not show the branded logo, or when the Red Hat Demo Platform notice still appears although `footer` is not `rhdp`.
- Q: When the author gives an own logo or favicon file during the create intake, where does it go? → A: Create copies it into the guide project's `branding/` directory, points the branding block at the copy, and commits it with the scaffold; the original stays where it was.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Brand an Antora guide from its configuration (Priority: P1)

A guide author has an Antora guide. They add a branding block to the guide configuration with the logo text "Agent Starter Kits" and a footer that links to the starter kits repository, then build the guide. The site header now shows the Red Hat hat, the divider, and "Agent Starter Kits"; screen readers announce the configured alt text; the footer shows the author's text and link instead of the Red Hat Demo Platform notice. The shareable and the internal view look the same.

**Why this priority**: This is the whole point of the feature and unblocks the paused agentic-starter-kits guide. Without it, every branded guide needs hand edits outside the plugin's control.

**Independent Test**: Take a fixture Antora guide, add a branding block with logo text and a footer, build both views, and inspect the generated pages: header logo, alt text, and footer show the configured values, and no file in the guide's git working tree changed.

**Acceptance Scenarios**:

1. **Given** an Antora guide with `branding.logo_text: Agent Starter Kits`, **When** the author builds the site, **Then** every page header shows the Red Hat logo layout with "Agent Starter Kits" as its text.
2. **Given** a branding block with `logo_alt: Red Hat Agent Starter Kits`, **When** the site is built, **Then** the header logo's alt text is "Red Hat Agent Starter Kits" on every page.
3. **Given** `footer: {text: "Agent Starter Kits on GitHub", url: "https://github.com/red-hat-data-services/agentic-starter-kits"}`, **When** the site is built, **Then** the footer shows that text as a link to that address and no longer mentions the Red Hat Demo Platform.
4. **Given** an internal part is enabled, **When** both views are built, **Then** the internal view carries the same logo, alt text, and footer as the shareable view.
5. **Given** a branded guide, **When** the build finishes, **Then** `git status` in the guide project shows no new or changed files.

---

### User Story 2 - Keep unbranded guides unchanged (Priority: P1)

An author of an existing Antora guide refreshes the guide's toolkit to the version that contains this feature but does not add a branding block. Their site and PDF look exactly as before.

**Why this priority**: Existing guides (for example the SAW guide) must not change their appearance or break because a new feature arrived.

**Independent Test**: Build a fixture guide without a branding block and without an overlay directory, before and after the change; compare the built pages and the PDF title page.

**Acceptance Scenarios**:

1. **Given** an Antora guide without a branding block and without an overlay directory, **When** the author builds the site after a toolkit refresh, **Then** the built pages are identical to the pages built before the refresh.
2. **Given** the same guide, **When** the author exports the PDF, **Then** the title page shows no logo, as before.

---

### User Story 3 - Branded PDF title page (Priority: P2)

The author exports the branded guide as a PDF to send to a partner. The title page shows the same logo the site header shows, legible on the printed page, above the guide title, baseline date, and sources.

**Why this priority**: The PDF is the shareable artifact that leaves the team; a branded site with an unbranded PDF looks inconsistent, but the site matters first.

**Independent Test**: Export the PDF of a branded fixture guide and inspect the title page.

**Acceptance Scenarios**:

1. **Given** a branded guide with `logo_text`, **When** the author exports the PDF (shareable or internal), **Then** the title page shows the branded logo above the title and the logo text is fully readable.
2. **Given** a branded guide with an own logo image, **When** the PDF is exported, **Then** the title page shows that image.
3. **Given** a branded guide, **When** the PDF is exported without network access to anything but the already required build inputs, **Then** the logo still appears (it is embedded, not linked).

---

### User Story 4 - Choose branding while creating a guide (Priority: P2)

An author starts a new guide with the create command and chooses the Antora format. The intake interview asks whether the guide uses the stock look or its own branding, and if so, the logo text (or an own logo file), alt text, footer, and an optional favicon. The scaffolded guide is branded from its first build. The accent color and the overlay directory are later edits to the guide project.

**Why this priority**: New guides should not need a manual configuration edit after create; the paused agentic-starter-kits run resumes through this path.

**Independent Test**: Run create on a fixture with the Antora format, answer the branding questions, and build the scaffolded guide.

**Acceptance Scenarios**:

1. **Given** the author chooses the Antora format, **When** the intake reaches the branding question, **Then** the author can keep the stock look (the default) or enter logo text or an own logo file, alt text (required for an own logo file), a footer, and an optional favicon file.
2. **Given** the author chose MkDocs or GitHub Markdown, **When** the intake runs, **Then** no branding question is asked.
3. **Given** the author entered branding answers, **When** the guide project is set up, **Then** its configuration contains the branding block and the guide validates.

---

### User Story 5 - Adopt branding in an existing guide (Priority: P3)

An author of an existing Antora guide runs the evolve command, accepts the offered toolkit refresh, and adds a branding block to the configuration. The next build is branded. They do not edit any build file of the guide project.

**Why this priority**: Existing guides benefit too, but they can keep the stock look until their authors opt in.

**Independent Test**: Take a fixture guide scaffolded with the previous toolkit, refresh only the toolkit, add a branding block, and build.

**Acceptance Scenarios**:

1. **Given** a guide scaffolded before this feature, **When** the author refreshes the toolkit and adds a branding block, **Then** the next build shows the branding without any change to the guide's build files.

---

### User Story 6 - Fine-tune the look (Priority: P3)

The author wants the browser tab to show the product icon and the site's accent color (links, the table-of-contents marker, and focus outlines) to use the product color. For one more change the block does not cover (for example a font size tweak), they put a stylesheet named `css/extra.css` into the guide's overlay directory.

**Why this priority**: Useful polish, not needed for a correct, honest guide.

**Independent Test**: Build a fixture guide with a favicon, an accent color, and an extra stylesheet in the overlay directory, and inspect the built pages.

**Acceptance Scenarios**:

1. **Given** `branding.favicon` points to an icon file in the guide project, **When** the site is built, **Then** every page links that icon as its browser-tab icon.
2. **Given** `branding.color: "#3e8635"` (a color the stock bundle does not use), **When** the site is built, **Then** links in page content, the active table-of-contents entry, and the keyboard focus outline use that color, and note admonitions keep their stock blue.
3. **Given** a static file (for example an image) in the guide's overlay directory, **When** the site is built, **Then** the built site's UI output contains that file at the same relative path, replacing the bundle's file of the same path.
4. **Given** a partial template in the overlay directory with the same path as a bundle partial, **When** the site is built, **Then** every rendered page uses the author's partial instead of the bundle's.
5. **Given** a stylesheet at `css/extra.css` in the overlay directory, **When** the site is built, **Then** every page loads it after the bundle's and the branding styles, so its rules take effect without any template change.

---

### User Story 7 - Notice when the UI bundle stops fitting (Priority: P3)

A plugin maintainer tries a newer version of the pinned UI bundle. The plugin's test suite tells them right away when the bundle no longer provides the parts the branding relies on.

**Why this priority**: Protects the feature over time; it matters only when the bundle changes.

**Independent Test**: Run the contract test against the pinned bundle (passes) and against a copy with the logo lookup removed (fails, naming the missing part).

**Acceptance Scenarios**:

1. **Given** the pinned bundle, **When** the maintainer runs the adapter tests, **Then** the branding contract test passes.
2. **Given** a bundle that no longer has a part the branding relies on, **When** the contract test runs, **Then** it fails and names the missing part.

---

### Edge Cases

- Both `logo_text` and `logo` are set, or a branding block sets neither: validation fails and names both keys.
- `logo` is set without `logo_alt`: validation fails and names `logo_alt`.
- A path in the branding block (logo, favicon) does not exist, points outside the guide project, or has an unsupported file type: validation fails and names the key and the path.
- The branding block appears in a MkDocs or GitHub Markdown guide: validation fails and names each key the guide's format does not support.
- `logo_text` contains characters with special meaning in markup (`&`, `<`, `>`, quotes): the header and the PDF show them literally; they never become markup.
- `logo_text` is empty, only whitespace, contains a line break, or is longer than 40 characters: validation fails and states the rule.
- The footer `url` is not an absolute `http` or `https` address: validation fails.
- `color` is not a six-digit hexadecimal color: validation fails.
- A file in the overlay directory has the same path as a file the branding block generates: the author's file wins, and validation warns that it shadows the generated file.
- The overlay directory exists but the guide has no branding block: the overlay files are still applied.
- The author removes the branding block: the next build returns to the stock look (or to the overlay directory alone).
- The guide is built from a linked git worktree: branding and overlay apply exactly as in the main checkout.
- The author edits the branding block or a file in the overlay directory while the live preview runs: the preview rebuilds and shows the change.
- An own logo is light on a dark background (made for the dark site header): it stays legible on the PDF title page because the title page shows it on a band in the site header's background color.
- An own SVG logo contains a script or event handler: it is shown as an image in the site and the PDF, so the script never runs.
- The author of a branded guide replaces the UI bundle in their build configuration and the new bundle ignores the overlay: the guide's check step fails and names what is missing (branded logo or leftover Red Hat Demo Platform notice).
- During create, the author names an own logo file outside the new guide project: create copies it into `branding/`; the branding block points at the copy.
- The guide's playbook (`site.yml` or `site-internal.yml`) already sets its own supplemental UI files, and the guide has a branding block or an overlay directory: validation fails, names the playbook key, and asks the author to move those files into `ui/supplemental/`. Without a branding block and an overlay directory, the playbook is used as is (FR-001).
- An author adds a branding block before refreshing a toolkit that predates this feature: the old toolkit's validation rejects `branding` as an unknown key; the evolve command's toolkit refresh resolves it.
- An invalid branding block or overlay directory when the author runs only a site build or the live preview (not the check step): the build stops before the site generator runs and reports every violation (FR-010).

## Requirements *(mandatory)*

### Functional Requirements

**Configuration**

- **FR-001**: The guide configuration MUST accept an optional `branding` block. A guide with neither a branding block nor an overlay directory MUST build to the same site pages and the same PDF title page as before this feature.
- **FR-002**: A branding block MUST set exactly one of `logo_text` (a short product name rendered on the Red Hat logo layout: the Red Hat hat, a vertical divider, and the text) or `logo` (a path to the author's own SVG image). Validation MUST fail when both or neither are set.
- **FR-003**: `logo_text` MUST be a single line of 1 to 40 characters after leading and trailing whitespace is removed.
- **FR-004**: The branding block MUST accept `logo_alt`, the logo's alternative text. With `logo_text`, it is optional and defaults to "Red Hat " followed by `logo_text`. With `logo`, it is required, because only the author knows what the image shows (the guide title already appears as text next to the header logo).
- **FR-005**: The branding block MUST accept `footer` as `rhdp` (the stock Red Hat Demo Platform footer), `none` (an empty footer), or a mapping with `text` (required) and `url` (optional; an absolute `http` or `https` address). When a branding block exists and `footer` is omitted, the footer MUST be `none`.
- **FR-006**: The branding block MUST accept `favicon`, a path to an icon file (`.ico`, `.png`, or `.svg`) that becomes the browser-tab icon.
- **FR-007**: The branding block MUST accept `color`, a six-digit hexadecimal color (`#rrggbb`) that replaces the bundle's accent blue as described in FR-016.
- **FR-008**: Every path in the branding block MUST be relative to the guide project root and resolve inside it.
- **FR-009**: Each output adapter MUST declare which branding keys it supports. Validation MUST reject every branding key the guide's adapter does not support, naming the key and the format. In this feature only the Antora adapter supports branding keys.
- **FR-010**: Every site build (shareable view, internal view, live preview, check, PDF, and dist) MUST validate the branding block and the overlay directory before the site generator runs, and stop with every violation reported with the offending key. The configuration validation of the check step MUST report the same violations. This MUST work with the build files of guides scaffolded before this feature, which a toolkit refresh does not change (FR-029).

**Site output (Antora)**

- **FR-011**: With `logo_text`, every page header MUST show the Red Hat logo layout with the configured text, matching the proportions, colors, and font of the UI bundle's own logos, with the full text visible.
- **FR-012**: With `logo`, every page header MUST show the author's image in place of the stock logo. The image MUST be shown as an image, never inserted as markup, so nothing inside the SVG runs.
- **FR-013**: The header logo MUST carry the configured or default alt text on every page.
- **FR-014**: The footer MUST follow the `footer` setting: the stock footer for `rhdp`, no footer content for `none`, and the given text (as a link when `url` is set) for a mapping.
- **FR-015**: With `favicon`, every page MUST use the configured icon as its browser-tab icon.
- **FR-016**: With `color`, the configured color MUST replace the pinned bundle's accent blue (`#06c`) on links in page content, the hovered and active table-of-contents entries, the keyboard focus outline, the skip link, and the header search field's focus border. The link hover color MUST be derived from the configured color, so none of these elements keeps the stock blue or its hover shade (`#004d99`). Note admonitions, the header background, the logo, and the Red Hat hat keep their stock colors.
- **FR-017**: Text from the branding block MUST appear literally in the built site and PDF; it MUST NOT be interpreted as markup.
- **FR-018**: The shareable and the internal view MUST carry the same branding.
- **FR-019**: The guide project MAY contain an overlay directory `ui/supplemental/`. Every file in it MUST be added to the UI the site is built with, at the same relative path, replacing a bundle file of the same path, whether or not a branding block exists. Static files (stylesheets, scripts, images, fonts) appear in the built site's UI output at that path; templates (layouts, partials, helpers) take effect in every rendered page. A stylesheet at `ui/supplemental/css/extra.css` MUST be loaded on every page after the bundle's and the branding styles.
- **FR-020**: When a file in the overlay directory has the same path as a file produced from the branding block, the author's file MUST win, and validation MUST warn that it shadows the branding setting.
- **FR-021**: Branding MUST be produced at build time from the guide configuration. A build MUST NOT create or change any file tracked by, or visible to, the guide project's git repository; build products stay in the existing ignored build output.
- **FR-022**: Branding and the overlay directory MUST apply equally to builds from the main checkout and from a linked git worktree.
- **FR-023**: The live preview MUST rebuild when the branding block, a logo or favicon file the block points to, or a file in the overlay directory changes.
- **FR-024**: The scaffold MUST keep the pinned, unmodified RHDP showroom bundle; the plugin MUST apply branding on top of it and MUST NOT fork, patch, or replace it. (An author who replaces the bundle in their own build configuration is covered by FR-032.)

**PDF output**

- **FR-025**: For a branded guide, the PDF title page (shareable and internal) MUST show the branded logo above the title on a band in the site header's background color, so a text logo or an own logo looks as it does in the site header.
- **FR-026**: The logo MUST be embedded in the PDF as an image (never as markup); exporting MUST NOT need to fetch the logo from a network location.
- **FR-027**: For a guide without a branding block, the PDF title page MUST stay as it is today.

**Commands and adoption**

- **FR-028**: The create intake MUST ask about branding when the format is Antora (default: stock look) and write the answers into the branding block; it MUST NOT ask for MkDocs or GitHub Markdown. The branding questions cover the logo (text or own file), the alt text (required for an own file), the footer, and an optional favicon; the accent color and the overlay directory are not part of the intake. An own logo or favicon file the author names MUST be copied into the guide project's `branding/` directory and committed with the scaffold; the branding block points at the copy.
- **FR-029**: An existing Antora guide MUST be able to adopt branding through the evolve command's toolkit refresh plus a branding block, without editing any other file of the guide project.
- **FR-030**: The plugin documentation and the create intake MUST state that `logo_text` renders the Red Hat logo and is meant for guides about Red Hat products; guides about other products use an own `logo`.

**Contract guard**

- **FR-031**: The adapter test suite MUST include a contract test that fails, naming the missing part, when the pinned UI bundle no longer provides any part the branding relies on (the logo lookup by name, the alt-text helper, the footer, the favicon reference, the stylesheet references the overlay extends, and the accent-blue style rules the `color` setting overrides).
- **FR-032**: For a branded guide, the guide's check step MUST fail when the header of either built view does not show the branded logo, or when the Red Hat Demo Platform notice still appears in either view although `footer` is not `rhdp`, naming what it found.

### Key Entities

- **Branding block**: the optional part of the guide configuration that describes the guide's look: logo text or logo file, alt text, footer, favicon, accent color. Owned by the guide project, the single source of truth for branding.
- **Overlay directory**: an optional directory in the guide project whose files replace or add UI files on top of the pinned bundle. The author's escape hatch for changes the branding block does not cover.
- **Branding overlay**: the set of UI files produced from the branding block at build time. Never committed; lives in the build output.
- **Adapter branding capability**: the list of branding keys an output adapter declares it supports; drives validation.
- **UI bundle contract**: the parts of the pinned UI bundle the branding overlay relies on; checked by the contract test.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An author brands an Antora guide (logo text, alt text, footer) by adding at most six lines to the guide configuration and rebuilding, with no other file edited.
- **SC-002**: For a guide without a branding block and without an overlay directory, building with the toolkit before and after this feature gives byte-identical files in the built site output, and a PDF title page with the same text that renders to the same image (PDF metadata such as the creation date excluded).
- **SC-003**: Every invalid branding configuration listed in the edge cases is reported by validation before a build starts, and each report names the offending key.
- **SC-004**: In the Chromium browser the tool chain already installs, at a 1280-pixel-wide window and with whatever font the bundle's font fallback resolves to, a logo text of 40 characters shows completely in the site header (not clipped and not overlapping the site title next to it) and on the PDF title page.
- **SC-005**: After building a branded guide, the guide project's git status is unchanged.
- **SC-006**: An existing guide adopts branding with one toolkit refresh and one configuration change.
- **SC-007**: Removing any one relied-upon part from a copy of the UI bundle makes the contract test fail.
- **SC-008**: A fixture guide with the agentic-starter-kits branding block (`logo_text: Agent Starter Kits` and a footer linking to the starter kits repository) shows "Red Hat | Agent Starter Kits" in the header of both views and on the PDF title page, and no Red Hat Demo Platform notice appears in either view or the PDF. The real agentic-starter-kits guide, created after this feature lands, is its first production use.

## Assumptions

- The pinned UI bundle stays the RHDP showroom bundle v2.0.3; upgrading it is a separate change that the contract test guards.
- Guides about Red Hat products may use the Red Hat logo layout; the author is responsible for using it only for such guides (FR-030 makes this explicit).
- `logo_text` uses the same font family as the bundle's own logos; when that font is not available in the reader's browser, the bundle's font fallback applies, as it does for the stock logos.
- The accent color affects the site only; the PDF carries the logo but keeps its neutral print styling.
- Branding for MkDocs Material and GitHub Markdown sites, shared branding presets across guides, a forked or upgraded UI bundle, and theming beyond one accent color are out of scope.
- The overlay directory is an expert escape hatch: the plugin applies its files but does not check that they fit the bundle.
- No new system tools are needed; the existing tool chain (Node.js, uv, Antora) suffices.
