# Research: Neutral Red Hat inspired branding for new guides

All findings were checked against the pinned UI bundle (RHDP showroom UI v2.0.3, unpacked), the Red Hat font release 5.0.0 (https://github.com/RedHatOfficial/RedHatFont), and the toolkit on branch `003-neutral-branding`. A throwaway spike (fontTools against the release fonts, kept outside the repository) backs R2 and R3.

## R1. What the bundle already provides

**Decision**: Keep the pinned bundle unchanged and add only fonts, one CSS file, and logo rendering.

**Rationale**: `css/site.css` already uses the Red Hat look: `.navbar{background:#151515;...}`, body text in `Red Hat Text,RedHatText,Noto Sans ...,helvetica,arial,sans-serif`, the navbar and headings in `Red Hat Display,...`, code in `Red Hat Mono,RedHatMono,...`, and `#e00` for unresolved links. The bundle ships no font files (no `font/` directory); `partials/head-styles.hbs` loads the three families from Google Fonts instead (see R11, a correction found during implementation: the first version of this note said the stacks fall back to system fonts, which holds only offline and in the PDF). Declaring `@font-face` rules under the family names the stacks already name ("Red Hat Text", "Red Hat Display", "Red Hat Mono") makes the stacks resolve to the vendored files without overriding a single selector.

**Alternatives considered**: overriding `font-family` on `body`, `.navbar`, headings, and code (duplicates the bundle's stacks and must track every selector that sets a font); an own UI bundle (out of scope, spec Approach C).

## R2. Fonts to vendor

**Decision**: The six variable web fonts of release 5.0.0, plus `OFL.txt`:

| File | Upstream path | `wght` axis | sha256 |
|---|---|---|---|
| `RedHatDisplay-VF.woff2` | `fonts/Proportional/RedHatDisplay/webfonts/` | 300 to 900 | `69dca56dda2a2b067dee3e910323c97e54b8544f90f3d1c2192b5a37c0eb1ec3` |
| `RedHatDisplay-Italic-VF.woff2` | `fonts/Proportional/RedHatDisplay/webfonts/` | 300 to 900 | `ad58f7fcae1bb271807d629e3d7bf370be17b13436c1753720db1f389d8cc114` |
| `RedHatText-VF.woff2` | `fonts/Proportional/RedHatText/webfonts/` | 300 to 700 | `1a5c9a8a88447c5b171ae99dab5daa4c1d49e3502db0fdc0da65d59fc5603feb` |
| `RedHatText-Italic-VF.woff2` | `fonts/Proportional/RedHatText/webfonts/` | 300 to 700 | `97b89f470394820fd11c803b65c7272fe193e179adea956e0ac3495e290c6dd4` |
| `RedHatMono-VF.woff2` | `fonts/Mono/RedHatMono/webfonts/` | 300 to 700 | `54145e1e268b1c5359966336a6b6b12a5dfa046e493d3b4f2dc620c5edd12b62` |
| `RedHatMono-Italic-VF.woff2` | `fonts/Mono/RedHatMono/webfonts/` | 300 to 700 | `d5d585590a2439bbb5429863b2c11bc76512bfb37e60fc5696462e1866bfc2c1` |

Total 222 KB for the fonts and 4.3 KB for `OFL.txt`, inside the 300 KB budget (SC-005). All six are TrueType-flavored (`glyf`) variable fonts with one `wght` axis; the upright Display font maps 406 code points.

**Rationale**: Variable fonts cover every weight the bundle uses in one file per style; static fonts would need about four files per family for the same weights. The repository is OFL-1.1 (GitHub license metadata), which allows bundling and redistribution with the toolkit and the built site as long as `OFL.txt` travels with the fonts.

**Alternatives considered**: loading the fonts from a CDN or Google Fonts (the print path blocks remote fonts for determinism, and an offline preview would lose them); subsetting to Latin (saves little on fonts that are already Latin plus Latin Extended, and adds a build step).

## R3. Logo text as outlines

**Decision**: Render logo text with fontTools: open `RedHatDisplay-VF.woff2` (`fontTools.ttLib.TTFont`; woff2 decoding needs brotli, which the `fonttools[woff]` extra pulls in), pin the weight with `fontTools.varLib.instancer.instantiateVariableFont(font, {"wght": W})`, and draw each glyph through `TransformPen(SVGPathPen, (s, 0, 0, -s, x, 0))` with `s = 82 / unitsPerEm`, advancing `x` by the glyph's advance width. Coordinates are formatted with at most two decimals. Kerning is not applied.

**Rationale**: The spike rendered "OpenClaw on OpenShift" at weight 500 in about 0.13 s (font load and instancing included), produced byte-identical path data on repeated runs, and reported the missing glyphs for "漢字". Outlines remove the font dependency of a logo shown through `<img>`, which cannot use web fonts, and make the logo identical in every browser and in the PDF. The real advance widths replace the Helvetica-Bold width table and `textLength` for these logos. Kerning (GPOS) would need a shaping engine (uharfbuzz) for a small visual gain at header size, and leaving it out keeps the output stable across fontTools releases.

The fontTools version is pinned exactly (`fonttools[woff]==4.67.0`, the version the spike resolved) in the PEP 723 headers of the scripts that render, because the golden SVG tests compare bytes.

**Alternatives considered**: shipping `<text>` with an embedded `@font-face` data URL inside the SVG (browsers do load fonts embedded in an SVG image, but it adds 40 KB per logo and the PDF printer's image path is untested); HTML text in the header (replaces `header-content.hbs`, a much larger contract surface); a static Medium TTF for outlines (a second copy of the font).

## R4. Which scripts need fontTools

**Decision**: Only rendering needs fontTools. `branding.py` imports it lazily inside the outline function, and the PEP 723 headers of `branding.py` and `playbook.py` (the scripts that call `render()`) add `fonttools[woff]==4.67.0`. Validation (glyph coverage, FR-011) reads the code point ranges recorded in the font manifest, so `guidecfg.py`, `check.py`, `attrs.py`, and `mkdocs_macros.py`, which import `branding` for validation only, keep their dependency lists.

**Rationale**: Every toolkit script runs with its own PEP 723 environment, and five of them import `branding`. A top-level `import fontTools` would break each one that does not declare it. Recording coverage in the manifest keeps validation fast and dependency free.

**Alternatives considered**: adding fontTools to all five headers (slower first runs, wider blast radius for a dependency only rendering needs).

## R5. Where the red rule goes

**Decision**: `.navbar { box-shadow: inset 0 -3px 0 #e00; }` in `css/theme-neutral.css`.

**Rationale**: The header markup is `<header class="header"><nav class="navbar">`. In `site.css`, `.navbar` is `position:fixed;height:3.5rem` and `body` has `padding-top:3.5rem`; `*` inherits `box-sizing: border-box` from `html`. A `border-bottom` on `.navbar` would eat 3px of the fixed height and nudge the vertically centered logo; a border on `header` would sit under the fixed bar. An inset box shadow paints inside the bar without affecting layout. In print media the bundle sets `.navbar{background:none;position:absolute}`; the shadow is harmless there and the PDF does not use the bundle layout anyway (R7).

**Alternatives considered**: `border-bottom` plus a height correction (couples to the bundle's height value); a `::after` pseudo-element (more CSS for the same effect).

## R6. How the theme files reach the build

**Decision**: Extend the existing overlay renderer. With `theme: neutral`, `_render_into` adds `font/<six files>`, `font/OFL.txt`, and `css/theme-neutral.css`, and `head_meta` gains a theme flag that inserts `<link rel="stylesheet" href="{{{uiRootPath}}}/css/theme-neutral.css">` after the `branding.css` link and before the `extra.css` link. `generated_files()` lists the new paths so author files in `ui/supplemental/` that shadow them get the existing warning. The `@font-face` `src` URLs are relative to the stylesheet (`../font/RedHatText-VF.woff2`), so they work under any `uiRootPath`.

**Rationale**: The spec 002 overlay already merges generated files with `ui/supplemental/`, swaps the result in atomically, and feeds `ui.supplemental_files`. The head partial order (`head-styles`, then `head-meta`, then `head-icons`) is part of the bundle contract, so a stylesheet linked from `head-meta` loads after `site.css`.

**Alternatives considered**: a separate overlay directory per theme (a second `supplemental_files` entry is not supported by Antora; one directory is).

## R7. PDF

**Decision**: `branding.json` gains `"theme"` and `"fonts"` (the absolute path of the rendered `ui/font/` directory). For `theme: neutral`, `print-pdf.mjs` prepends `@font-face` rules with `file:` URLs to that directory and overrides its own typography: `body` in Red Hat Text, `h1` to `h6` and `.guide-title-page` in Red Hat Display, `pre` and `code` in Red Hat Mono. The title band gets the same inset `#e00` rule (as a `border-bottom` on the band, which has no fixed height, so a border is fine there).

**Rationale**: The printer loads the html-single export from a `file:` URL and blocks remote fonts, scripts, and styles for determinism; `file:` font URLs are local and allowed. Its stylesheet sets Noto Serif for the body and Helvetica for the title page and the table of contents, so the neutral PDF needs explicit overrides; without the theme, nothing changes (FR-019).

**Alternatives considered**: embedding the fonts as data URLs in the injected CSS (larger page, same result).

## R8. Wordmark geometry

**Decision**: The wordmark SVG uses the stock logo height (`viewBox="0 0 W 178.739"`), font size 82 at weight 500, the first glyph at x 0, fill `#fff`, and `W = ceil(advance width)`. The baseline centers the capitals vertically: `(178.739 + capHeight) / 2`, which is 118.07 for Red Hat Display (cap height 700 of 1000 units, 57.4 at size 82). A comment names the font and its license.

**Rationale**: The header scales the logo to `height: 2rem` (contract rule `site-css`), so keeping the stock height and font size makes the wordmark text exactly the size of the product name in the hat variant. The stock baseline 149 was the first choice, but the stock logo has two rows ("Red Hat" on top, the product name below at 149); a wordmark on that baseline rendered with an empty upper half and sat visibly low in the navbar during implementation review, so the capitals are centered instead. In the spike, 40 lowercase "x" measured 1,650 units and "OpenClaw on OpenShift" 897 units; at a 2rem (about 36 px) logo height that is about 330 px and 180 px wide. Wider glyphs (W, M) make a 40-character text wider, which the existing header layout already handles for long `logo_text` logos.

**Alternatives considered**: a larger font size for the wordmark alone (would make hat and no-hat guides look inconsistent); centering on the cap height (the stock baseline already centers the hat variant).

## R9. Adoption without surprises

**Decision**: A missing `theme` means `stock`; the renderer, `head_meta`, and `logo_svg` take the spec 002 code path unchanged for `stock`. Create writes `theme: neutral` explicitly.

**Rationale**: SC-004 requires byte-identical output for the agentic-starter-kits guide (branded, no `theme`) and the SAW guide (no block). Keeping the stock path untouched, rather than parameterizing it, makes that easy to prove with the existing golden files.

## R11. Google Fonts in the stock bundle

**Decision**: The neutral theme replaces `partials/head-styles.hbs` with the stock partial minus its three Google Fonts links (`preconnect` to fonts.googleapis.com and fonts.gstatic.com, and the `css2?family=Red+Hat+Display...` stylesheet), keeping the `css/site.css` link. The contract rule `head-styles-stock` pins the whole stock partial with `equals` (it replaces the spec 002 rule `head-styles-site-css`, whose `site.css` check it includes), so a bundle that changes the partial fails the contract before the overlay could drop something else. `check.py` fails a neutral page that still links a Google Fonts host.

**Rationale**: The US1 smoke test showed Red Hat faces loaded on a stock build too; the source was the Google Fonts stylesheet in `head-styles.hbs`. With the vendored fonts in place, the Google request adds nothing for a neutral site but a third-party call on every page view (a privacy concern for readers in the EU, and a failure mode offline). The author chose to drop it. Playwright with Google blocked confirms the result: the stock page loads no Red Hat face, the neutral page loads the vendored ones and makes no Google request.

**Alternatives considered**: keeping both (the vendored `@font-face` rules and the Google stylesheet declare the same families; it works offline but still contacts Google on every view).

## R10. Create intake wording

**Decision**: Step 5 asks "Is this guide about a Red Hat product?" Yes: ask for the short product name (`logo_text`). No: propose the guide title as `wordmark` when it has at most 40 characters, otherwise ask for a shorter text. Then offer the follow-ups (own logo instead, footer text and link, favicon). Write `theme: neutral` and `footer: none` unless a follow-up set another footer.

**Rationale**: One yes or no question decides the trademark question that the spec 002 intake left to a long explanation, and the title is almost always the right wordmark.
