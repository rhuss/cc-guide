# Branding an Antora guide

A `branding` block in `guide.yaml` sets the look of an Antora guide: the header logo, its alt text, the footer, the browser-tab icon, the accent color, and the theme. `/guide:create` writes one for every new Antora guide, with the neutral theme described below and either the Red Hat logo with the product name or a text logo without the Red Hat hat. The overlay directory `ui/supplemental/` covers anything else. Branding applies to both site views and to the PDF.

A guide without a block shows the stock UI bundle, which looks like a Red Hat Demo Platform lab: the header shows the "Red Hat | Demo Platform" logo, and the footer says "Powered by Red Hat Demo Platform" with a link to demo.redhat.com. Guides created before toolkit 0.4.0 keep that look, or their own branding, until the author changes the block; a toolkit refresh alone changes nothing.

Branding is available for the antora format only. A `branding` block in a MkDocs or gfm guide fails validation, and every key is reported as not supported by that adapter.

## The branding block

```yaml
branding:
  logo_text: Agent Starter Kits
  footer:
    text: Agent Starter Kits on GitHub
    url: https://github.com/red-hat-data-services/agentic-starter-kits
```

These five lines are enough for a header that reads "Red Hat | Agent Starter Kits", the alt text "Red Hat Agent Starter Kits", and a footer that links to the starter kits repository.

| Key | Value | Default | Rules |
|---|---|---|---|
| `logo_text` | short product name | none | one line, 1 to 40 characters after trimming; set exactly one of `logo_text`, `wordmark`, and `logo` |
| `wordmark` | text logo without the Red Hat hat | none | one line, 1 to 40 characters after trimming; every character must exist in Red Hat Display |
| `logo` | path to your own SVG logo | none | an `.svg` file inside the guide project; requires `logo_alt` |
| `logo_alt` | alt text of the header logo | `Red Hat <logo_text>`, or the `wordmark` | one non-empty line; required with `logo` |
| `theme` | `neutral` or `stock` | `stock` | `neutral` adds the vendored Red Hat fonts and a red rule under the header; see below |
| `footer` | `rhdp`, `none`, or `{text, url}` | `none` | `text` is required in the mapping; `url` is an absolute `http` or `https` address |
| `favicon` | path to the browser-tab icon | the bundle's icon | an `.ico`, `.png`, or `.svg` file inside the guide project |
| `color` | accent color `"#rrggbb"` | the bundle's blue (`#06c`, that is `#0066cc`) | six hexadecimal digits; quote it, because `#` starts a YAML comment |

Paths are relative to the guide root and must stay inside the guide project: absolute paths, `..`, and symbolic links that resolve outside are rejected. Keep your own files in `branding/` (`/guide:create` copies them there).

### Logo text and the Red Hat logo

`logo_text` renders the Red Hat logo layout (the Red Hat hat, a vertical divider, and your text) from the bundle's own Demo Platform logo, with the same colors, size, and font. It is meant for guides about Red Hat products. A guide about another product uses `wordmark` or its own `logo` instead.

With `theme: neutral`, the text is drawn as Red Hat Display Bold outlines (SVG paths), so it looks the same in every browser and in the PDF, and the logo's width follows the real glyph widths.

With the stock theme, the text stays an SVG `<text>` element. The header shows the logo as an image, so web fonts never reach it and the text renders in the first installed font of the bundle's fallback list (Helvetica or Arial on most systems). The logo's width comes from Helvetica-Bold character widths. The text is drawn at exactly that width (`textLength`), so a 40-character text never runs past the logo's edge, whichever font the reader's browser picks. Short texts keep the proportions of the bundle's narrowest stock logo (`logo-summit.svg`).

### Wordmark

`wordmark` is a text logo without the Red Hat hat, for guides that are not about a Red Hat product. The text is drawn white as Red Hat Display Medium outlines, at the size of the product name in the `logo_text` layout and centered vertically in the header. It needs no installed font and looks the same everywhere, with either theme. Every character must exist in Red Hat Display (Latin, Latin Extended, and common punctuation); others fail validation, for example `guide.yaml:branding.wordmark: no glyph for "漢" (U+6F22) in Red Hat Display`. The alt text defaults to the wordmark.

Characters such as `&`, `<`, `>`, and quotes appear literally in the logo, the alt text, and the footer; they never become markup.

### Custom logo

Your own logo is copied unchanged and shown as an image in the site header and on the PDF title page. It is never inserted as markup, so a script or event handler inside the SVG does not run there. The file itself is published as `_/img/logo-guide.svg`, and a browser that opens that file directly (for example with "Open image in new tab") treats it as a document, so use a logo without scripts or event handlers. The header has a dark background (`#151515`), so use a logo made for a dark background. The PDF title page shows the logo on a band of the same color.

### Footer

- `rhdp` keeps the stock footer, "Powered by Red Hat Demo Platform".
- `none` renders an empty footer. It is the default once a branding block exists.
- `{text, url}` shows the text. When `url` is set, the text links there and opens in a new tab.

### Accent color

`color` replaces the bundle's accent blue on links in page content, the hovered and the active table-of-contents entry, the keyboard focus outline, the skip link, and the border of the header search field. The link hover color is derived from it: each RGB channel is multiplied by 0.75 (the ratio between the stock `#06c` and its hover shade `#004d99`). `NOTE` admonitions, the header background, the logo, and the Red Hat hat keep their stock colors, and unresolved links stay red. The PDF keeps its neutral print styling.

## The neutral theme

`theme: neutral` gives a guide a neutral, Red Hat inspired look on top of the stock bundle:

- The Red Hat Display, Text, and Mono fonts (release 5.0.0, SIL Open Font License 1.1) are published with the site under `_/font/`, together with `OFL.txt`. The generated `css/theme-neutral.css` declares them under the family names the bundle's stylesheet already uses, so body text, headings, the header, and code use them without any other override.
- The stock bundle loads the same fonts from Google Fonts on every page view. The neutral theme removes those links (it replaces `partials/head-styles.hbs` with the stock partial minus the Google Fonts lines), so a neutral site makes no third-party request and works offline.
- A 3px red rule (`#e00`) runs along the bottom edge of the header. It is an inset shadow, so the header keeps its height.
- `logo_text` is drawn as outlines (see above).
- In the PDF, body text is set in Red Hat Text, headings, the title page, and the table of contents in Red Hat Display, and code in Red Hat Mono, and the title band gets the same red rule.

The theme changes nothing else: links keep the bundle's blue (or `color`), admonitions, code blocks, and the table of contents keep their colors. `color` and the files in `ui/supplemental/` apply on top of it: `css/branding.css` and the theme stylesheet load before `css/extra.css`, and an own `ui/supplemental/css/theme-neutral.css` or `partials/head-styles.hbs` replaces the generated one (with a shadowing warning).

### The Red Hat Demo Platform look

To get the stock Demo Platform look back, remove the `branding` block (the guide then builds exactly as an unbranded guide). To keep your own logo but show the stock footer, set `theme: stock` (or leave `theme` out) and `footer: rhdp`.

## The overlay directory `ui/supplemental/`

Every file in `ui/supplemental/` is added to the UI the site is built with, at the same relative path, on top of the pinned UI bundle. It works with or without a branding block.

- Static files (stylesheets, scripts, images, fonts) appear in the built site under `_/<path>`, replacing a bundle file of the same path.
- Templates (`layouts/`, `partials/`, `helpers/`) take effect on every page. A partial with the same path as a bundle partial replaces it.
- `css/extra.css` is linked on every page after the bundle's `site.css` and the branding styles, so its rules win without a template change.

Files generated from the branding block are written first and your files are copied on top, so your file always wins. In that case, validation warns that your file shadows the generated one, for example:

```text
ui/supplemental/partials/footer-content.hbs: warning: shadows the file generated for branding.footer
```

Each entry must be a regular file. A symbolic link to a file is followed when it resolves inside the guide project; a link that resolves outside it, and a link to a directory, are rejected. The plugin applies the overlay but does not check that your templates fit the bundle.

A playbook (`site.yml` or `site-internal.yml`) must not set `ui.supplemental_files` while the guide has a branding block or the overlay directory; move those files into `ui/supplemental/`.

## How a build applies the branding

Every Antora build (`make site`, `make site-internal`, `make check`, `make pdf`, `make dist`, and the preview) asks `tools/guide/playbook.py path` for its playbook before Antora runs. For a branded or overlaid guide, the script:

1. validates the branding block and the overlay directory, reports every problem, and stops the build (exit 1) before Antora runs;
2. renders the overlay for the view into `build/branding/<view>/ui/` (the generated files, then `ui/supplemental/` on top) and, for a branded guide, writes `build/branding/<view>/branding.json` for the PDF printer;
3. writes `build/playbook.yml` (or `build/playbook-internal.yml`): a copy of the committed playbook with `ui.supplemental_files` pointing at that directory, `output.clean: true` (no page of an earlier build survives), `site.keys.navbar_logo: guide` for a branded guide, and absolute paths (Antora resolves `./` paths against the playbook's directory, which is now `build/`).

| File | Generated for |
|---|---|
| `img/logo-guide.svg` | `logo_text` (rendered) or `logo` (copied) |
| `helpers/navbar-logo-alt.js` | the alt text |
| `partials/footer-content.hbs` | `footer: none` or `{text, url}` |
| `img/favicon-guide.<ext>`, `partials/head-icons.hbs` | `favicon` |
| `css/branding.css` | `color` |
| `css/theme-neutral.css`, `partials/head-styles.hbs`, `font/*` | `theme: neutral` |
| `partials/head-meta.hbs` | `color`, `favicon`, `theme: neutral`, or `ui/supplemental/css/extra.css` |

Everything lives in `build/`, which the guide's `.gitignore` excludes, so a build never changes the guide's git status. The UI bundle itself stays the pinned, unmodified RHDP showroom bundle v2.0.3. Branding works the same from a linked git worktree.

Without a branding block and without `ui/supplemental/` (and outside a linked git worktree, which always gets a generated playbook), `playbook.py` prints the committed `site.yml` and writes nothing. Removing the block (and the overlay) returns the guide to the stock look with the next build.

## Validation

`uv run tools/guide/guidecfg.py validate` (also run by `make check`) and every build report one line per problem and name the key:

```text
guide.yaml:branding: set exactly one of logo_text, wordmark, or logo
guide.yaml:branding.logo_text: must be one line of 1 to 40 characters (got 41)
guide.yaml:branding.wordmark: no glyph for "漢" (U+6F22) in Red Hat Display
guide.yaml:branding.theme: must be neutral or stock (got dark)
tools/guide/branding/fonts/RedHatText-VF.woff2: missing; refresh the toolkit (scaffold-project.sh --toolkit-only)
guide.yaml:branding.logo_alt: required with branding.logo
guide.yaml:branding.favicon: file not found: branding/favicon.png
guide.yaml:branding.footer.url: must be an absolute http or https URL
guide.yaml:branding.color: must be a #rrggbb color (got 3e8635)
guide.yaml:branding.logo_text: not supported by the mkdocs adapter
ui/supplemental:css/x.css: links outside the guide project
site.yml:ui.supplemental_files: already set; move these files into ui/supplemental/
```

`uv run tools/guide/branding.py validate` prints the branding lines alone.

## PDF

For a branded guide, the PDF title page (shareable and internal) starts with the logo on a band in the header's color, above the title, the baseline date, and the sources. The logo is embedded in the PDF as an image, so printing needs no network access for it. The printer reads `build/branding/<view>/branding.json`; when that output is missing, `make print-pdf` stops with `branding output missing for the <view> view; run make check`. `make pdf` builds it first. Without a branding block, the title page is unchanged. With `theme: neutral`, the PDF body, headings, title page, table of contents, and code use the vendored Red Hat fonts (loaded from `build/branding/<view>/ui/font/`, never from the network), and the band has a red rule along its bottom edge. Admonition labels and the page-number footer keep Helvetica. A font file that does not load stops the print with `vendored fonts failed to load: <face> (<file>): <reason>`.

## Preview

`make preview` also watches `ui/`, `branding/`, and the `logo` and `favicon` files named in `guide.yaml`, and rebuilds when any of them or the branding block changes. They are watched even before they exist, so creating `ui/supplemental/` or copying in a logo file while the preview runs also rebuilds. A branding problem fails the rebuild and keeps the last good site, like any other build error. Branding warnings (an overlay file that shadows a generated one) appear in the preview output after a successful build.

## Checks that catch broken branding

### make check

For a branded guide, `make check` looks at the header and footer of every built page in the shareable view, and in the internal view while the internal part is enabled. It fails when a page does not show `img/logo-guide.svg` with the configured alt text (`[branding] header does not show the branded logo`). It also fails when no page of a view shows the logo at all (`[branding] no page shows the branded logo`), which happens when `site.yml` names another UI bundle that ignores the overlay. A footer that still carries the Red Hat Demo Platform notice fails too, unless `footer` is `rhdp`. The stock notice is recognized by its "Powered by" link; your own footer text (from `footer` or from `ui/supplemental/partials/footer-content.hbs`) may name the Demo Platform. Page content may mention it as well; only the header and the footer are inspected. With your own `helpers/navbar-logo-alt.js` in `ui/supplemental/`, only the logo file is checked, not the alt text.

With `theme: neutral`, `make check` also fails when a page with the header does not link `css/theme-neutral.css` (`[branding] page does not load the neutral theme`), when it still links Google Fonts (`[branding] page still loads Google Fonts`), and when `_/font/` lacks one of the vendored fonts or `OFL.txt` (`[branding] neutral theme font missing: <file>`).

### The bundle contract

`guide/adapters/antora/branding/contract.yaml` (vendored as `tools/guide/branding/contract.yaml`) lists every part of the pinned bundle the branding relies on: the logo lookup by name, the alt-text helper, the footer partial, the layouts and partials that include the header, footer, and head partials, the head partials and their order, the whole stock `head-styles.hbs` (which the neutral theme replaces), the logo size and header color in `site.css`, the font family names in `site.css` and the navigation bar the red rule sits on, the stock logo, and every rule that uses the accent blue (plus the rules that must keep their stock color on top of it). Check a newer bundle against it before switching:

```bash
uv run tools/guide/branding.py contract --bundle ui-bundle.zip
```

Each missing part prints as `contract: <rule id>: <file>: <what is missing>`, and the exit status is 1. The plugin's adapter tests run the same check against the pinned bundle.

## Adopting branding in an existing guide

Branding needs toolkit 0.2.0 or later, `wordmark` and `theme` need 0.4.0. Run `/guide:evolve` and accept the toolkit refresh (`scaffold-project.sh --toolkit-only`), which also vendors `tools/guide/branding/` with the fonts. Then add or extend the branding block, for example with `theme: neutral`. No Makefile or playbook change is needed. A block or key added before the refresh fails validation with `guide.yaml:branding: unknown key`. Toolkit 0.4.0 renders outlined logos with fontTools, which `uv run` installs on the first Antora build after the refresh (and caches), so that first build needs access to PyPI.

## Attribution

The logo template `guide/adapters/antora/branding/logo-text.svg.tmpl` is derived from `img/logo-demo-platform.svg` of the RHDP showroom UI theme v2.0.3 (https://github.com/rhpds/rhdp_showroom_theme) and is covered by the Mozilla Public License 2.0; see `NOTICE.md` next to it. Every logo rendered from it carries the notice as an XML comment.

The Red Hat fonts in `guide/adapters/antora/branding/fonts/` (release 5.0.0 of https://github.com/RedHatOfficial/RedHatFont) are covered by the SIL Open Font License 1.1 (`OFL.txt` next to them). A neutral guide publishes them with `OFL.txt` under `_/font/`. Outlined logo text is a rendering of Red Hat Display glyphs, and each outlined logo names the font and its license in an XML comment.
