# Research: Antora branding for guides

All findings below were checked against the pinned UI bundle (`https://github.com/rhpds/rhdp_showroom_theme/releases/download/v2.0.3/ui-bundle.zip`, unpacked) and the current toolkit in `guide/toolkit/`.

## R1. How branding reaches every Antora build without touching old Makefiles

**Decision**: `tools/guide/playbook.py path [--internal]` becomes the single hook. It validates the branding block and the overlay directory, renders the branding overlay into `build/branding/<view>/ui/`, and returns a generated playbook (`build/playbook.yml` or `build/playbook-internal.yml`) whenever the guide is branded, has an overlay directory, or is a linked worktree. Otherwise it returns `site.yml` / `site-internal.yml` unchanged, as today. Antora resolves `url: .` and `./` paths (content sources, `output.dir`, a local bundle, extensions) against the directory of the playbook file (`@antora/content-aggregator` calls `expandPath(url, { dot: playbook.dir })`), so a playbook generated into `build/` must carry absolute paths in a main checkout too: `url: .` becomes the absolute guide root, and the other relative paths go through the existing `_absolute` helper.

**Rationale**: Every Antora build entry point already calls `playbook.py path` before Antora runs: the scaffold Makefile's `BUILD` macro (used by `site`, `site-internal`, and through them `check`, `pdf`, `dist`) and `preview-watch.mjs`. Both scaffold files predate this feature, but `playbook.py` is part of the vendored toolkit that `scaffold-project.sh --toolkit-only` refreshes. So FR-010 (validate before the site generator runs) and FR-029 (adopt without editing build files) hold for old guides. Returning the committed playbook unchanged for unbranded guides keeps SC-002 byte-identical.

**Alternatives considered**: a new `make branding` target (needs a Makefile change, which a toolkit refresh does not deliver); an Antora extension registered in `site.yml` (needs a playbook edit in every existing guide, and Antora extensions cannot stop the build with a config report as cleanly).

## R2. Overlay mechanism

**Decision**: Antora `ui.supplemental_files` pointing at one merged directory per view, `build/branding/<view>/ui/`. The renderer writes the generated files first, then copies `ui/supplemental/` on top (author wins, FR-020), and swaps the directory in atomically (write to a temporary sibling, then rename) so a concurrent preview build never reads a half-written overlay. The generated playbook also sets `site.keys.navbar_logo: guide`, which Antora camelCases to `site.keys.navbarLogo` in the UI model (its playbook builder lowercases every key and camelCases on `_` and `-`, so a literal `navbarLogo` key would become `navbarlogo`).

**Rationale**: `supplemental_files` overlays files onto the bundle by path without forking it (FR-024), and `playbook.py` already rewrites that key for worktrees. One directory per view (`shareable`, `internal`) avoids two builds racing on the same files.

**Alternatives considered**: a list of `{path, contents}` entries inline in the playbook (unreadable for binaries such as favicons, and the generated playbook would carry the author's overlay content).

## R3. Bundle parts the overlay relies on

Findings in the pinned bundle:

| Part | Content | Use |
|---|---|---|
| `partials/header-content.hbs` | `<img src="{{uiRootPath}}/img/logo-{{or site.keys.navbarLogo 'demo-platform'}}.svg" alt="{{navbar-logo-alt (or site.keys.navbarLogo 'demo-platform')}}" class="navbar-logo-img">` | logo lookup by name: ship `img/logo-guide.svg`, set `navbarLogo: guide` |
| `helpers/navbar-logo-alt.js` | maps `demo-platform`, `summit`; falls back to "Red Hat Demo Platform" | replaced by a generated helper that returns the configured alt text |
| `partials/footer-content.hbs` | `<footer class="footer">` with "Powered by" and the Demo Platform logo linking `https://demo.redhat.com` | replaced for `footer: none` and `footer: {text, url}` |
| `partials/head.hbs` | `head-prelude, head-title, head-info, head-styles, head-meta, head-scripts, head-icons` in this order | `head-meta` renders after `head-styles` (which links `css/site.css`) |
| `partials/head-meta.hbs` | only `<link rel="icon" href="{{uiRootPath}}/img/favicon.ico" type="image/x-icon">` | replaced to add the branding and `extra.css` stylesheets after `site.css`, and the custom favicon |
| `partials/head-icons.hbs` | only the same favicon link with `{{{uiRootPath}}}`, indented by four spaces | replaced when `favicon` is set |
| `css/site.css` | accent blue `#06c` (hover `#004d99`) on `.doc a`, `.toc .toc-menu a:hover`, `.toc .toc-menu a.is-active` (border), `:focus-visible` (outline), `.skip-link`, `#search-input:focus` (border), plus `--link-font-color:#06c` (defined, unused) and `.doc .admonitionblock.note .icon` (kept stock) | `css/branding.css` overrides these selectors |
| `css/site.css` | `--navbar-background: var(--color-jet-70)` = `#151515`; `.navbar-logo-img{height:2rem;width:auto}` | PDF band color; logo scales by width |
| `img/logo-demo-platform.svg` | `viewBox="0 0 1080 178.739"`, no `width` or `height`: Red Hat wordmark as paths (top row, ending near x 601), the hat, a divider, and `<text data-name="Demo Platform" transform="translate(308 149)" fill="#fff" font-size="82" font-family="'RedHatDisplay', 'Red Hat Display', 'Overpass', overpass, helvetica, arial, sans-serif" font-weight="700"><tspan x="0" y="0">Demo Platform</tspan></text>` | basis of the `logo_text` template |
| `img/logo-summit.svg` | the same layout with "Summit", `viewBox="0 0 780 178.739"` | the narrowest stock logo; minimum width of the `logo_text` template |

**Decision**: replace `head-meta.hbs` (not `head-styles.hbs`) to load extra stylesheets: its stock content is one favicon line that the replacement reproduces, it renders after `site.css`, and it avoids copying the Google Fonts links of `head-styles.hbs`. The bundle contract (R9) pins every row of this table.

## R4. Logo text template and sizing without font metrics

**Decision**: ship `guide/adapters/antora/branding/logo-text.svg.tmpl`, derived from the bundle's `img/logo-demo-platform.svg` (MPL-2.0, notice kept as an XML comment in the template and the rendered file). The renderer replaces the text (both the `data-name` attribute and the `<tspan>` content carry it), sets `textLength` on the `<text>` element to an estimated width with `lengthAdjust="spacingAndGlyphs"` (Chromium applies it to the tspan child), and sets the viewBox width to `max(780, ceil(308 + width + 24))`. The width estimate uses the Helvetica-Bold advance widths (Adobe Core 14 AFM, units per 1000 em) for printable ASCII and 611 (the Helvetica-Bold average) for any other character, times the font size 82.

**Rationale**: the logo is shown through `<img>`, so web fonts never reach it and the text renders in the first installed font of the fallback chain, which is Helvetica or Arial (metric compatible) on almost every system. `textLength` with `spacingAndGlyphs` forces the rendered text to exactly the estimated width, so it can never run past the viewBox (no clipping, SC-004) whatever font is picked; with Helvetica-compatible fonts the estimate is close enough that the adjustment is invisible. The minimum width 780 is the width of the narrowest stock logo (`logo-summit.svg`; `logo-demo-platform.svg` is 1080) and keeps the Red Hat wordmark (which ends near x 601) inside the viewBox for very short texts; a `logo_text` of "Summit" renders with exactly the stock `logo-summit.svg` width, so short texts keep the stock proportions (FR-011). In Chromium the estimate for 40 "W" characters (3096) was within 2 % of the rendered width (3052).

**Alternatives considered**: converting the text to outlines (needs a font file and a shaping library, not available to a PEP 723 script without heavy dependencies); `lengthAdjust="spacing"` only (negative spacing makes glyphs overlap when the real font is wider than the estimate); a fixed wide viewBox (leaves a large empty area after short texts).

**Escaping**: the text is XML-escaped (`&`, `<`, `>`, `"`, `'`) before it goes into the template, and all placeholders are filled in one pass, so a text that contains a placeholder name stays literal (FR-017).

## R5. Alt text, footer, favicon, and color rendering

- **Alt text**: a generated `helpers/navbar-logo-alt.js` (`module.exports = () => <JSON string literal>`); Handlebars escapes the returned value inside the attribute.
- **Footer**: `none` renders `<footer class="footer"></footer>`; `{text, url}` renders the text (as a link with `target="_blank" rel="noopener"` when `url` is set) inside the footer element. Values are HTML-escaped, and `{` and `}` become `&#123;` and `&#125;` so Handlebars never interprets them (FR-017). `rhdp` writes nothing (the bundle partial stays).
- **Favicon**: the file is copied to `img/favicon-guide.<ext>`; `head-icons.hbs` and the `head-meta.hbs` replacement link it with the matching type (`image/x-icon`, `image/png`, `image/svg+xml`).
- **Color**: `css/branding.css` repeats the R3 selectors with the configured color; hover rules (`.doc a:hover` and every rule that uses `#004d99`) use the color with each RGB channel multiplied by 0.75 and rounded half up (`int(c * 0.75 + 0.5)`), the ratio between `#06c` and `#004d99` (0x66 times 0.75 is 76.5, which must round to 0x4d).
- **extra.css**: when `ui/supplemental/css/extra.css` exists, the `head-meta.hbs` replacement links it after `branding.css` (FR-019).

## R6. Validation placement

**Decision**: a new toolkit module `branding.py` holds the branding schema checks, path checks, overlay checks, and shadow warnings, plus `check_guide(root)`, which reads `guide.yaml` and the vendored adapter descriptor itself. `guidecfg.load_guide` only accepts the `branding` key (added to `GUIDE_KEYS`), checks that it is a mapping, and stores it raw; `guidecfg.validate` appends the `check_guide` lines, so `guidecfg.py validate` reports the same problems (FR-010), and `playbook.py` calls `check_guide` before rendering. Keeping the full checks out of `load_guide` matters because the scaffold Makefile reads `guidecfg.py get internal.enabled` in `site-internal` and `print-pdf` and treats a failing `get` as "internal part disabled" (exit 0); with a tolerant `load_guide` the build reaches `playbook.py`, which stops it with exit 1. MkDocs and gfm builds never call `playbook.py`, so `mkdocs_macros.define_env` and `attrs.py regions` (the first step of the gfm `site` targets) run `check_guide` too. Problems print as `<location>: <message>`, where the location names the file (`guide.yaml:branding.<key>`, `ui/supplemental:<rel path>`, `site.yml:ui.supplemental_files`); warnings (FR-020 shadowing) print as `ui/supplemental/<rel path>: warning: ...` and never change the exit status (contracts/branding-config.md). The adapter's supported keys come from a new `branding:` list in `adapter.yaml` (Antora: all six keys; MkDocs and gfm: empty), read through the existing `Adapter` dataclass (FR-009).

**Rationale**: `guidecfg.py` is the one place the guide schema lives today; keeping the branding rules in their own module keeps `guidecfg.py` format-neutral and lets `playbook.py`, `check.py`, and tests use the same code.

## R7. PDF title page

**Decision**: the renderer also writes `build/branding/<view>/branding.json` (`logo` path inside the merged overlay, `alt`). `print-pdf.mjs` reads it when `guide.yaml` has a `branding` block, embeds the logo as a `data:image/svg+xml;base64,...` `<img>` (never inline markup, FR-012/FR-026), and puts it in a band with background `#151515` at the top of the title page. Without a branding block, nothing in the title page changes (FR-027). When the block exists but the JSON is missing, the print fails with "branding output missing for the <view> view; run make check".

**Rationale**: the print HTML is the html-single export, which does not use the UI bundle, so the printer must add the logo itself. Reading the rendered result keeps one implementation of defaults and overlay precedence. The printer already allows `data:` URLs and uses `printBackground: true`, so the band prints.

**Verified in Chromium (Playwright headless shell)**: an SVG data URL without `width`/`height` reports `naturalWidth` 300, so the printer's broken-image check passes; the existing print rule `img { max-width: 100% !important; height: auto !important; }` overrides a plain `height: 14mm` (the logo grew to the full content width), so the band rule needs `!important`; the printed PDF draws the SVG as vector content in the page content stream (no image XObject), and pypdf's `extract_text` returns the logo text, also with `textLength`; page content streams of two prints of the same page are byte-identical (only metadata differs), which the SC-002 test relies on.

## R8. Guide-level branding check (FR-032)

**Decision**: `check.py` gains a branded-site check that runs when the guide has a branding block and a built view exists: every HTML page's header `img.navbar-logo-img` must point at `img/logo-guide.svg` and carry the expected alt text, a view in which no page shows the branded logo fails (a replaced bundle may have no `navbar-logo-img` at all), and, unless `footer` is `rhdp`, no page's footer element may contain `demo.redhat.com` or "Demo Platform" (page content may mention the Demo Platform). Pages under `_exports/` (the html-single export) are skipped. It reports `build/site/<page>:0: [branding] ...` lines (the existing `Violation` format).

**Rationale**: `make check` already builds both views before `check.py`, and the check catches an author who swaps the bundle in `site.yml` for one that ignores the overlay.

## R9. Bundle contract (FR-031)

**Decision**: `guide/adapters/antora/branding/contract.yaml` lists every R3 part as a rule: required files, required substrings or regular expressions, exact content for files the overlay replaces wholesale (`head-meta.hbs`, `head-icons.hbs`), and the accent selectors. `branding.py contract --bundle <zip|dir>` checks a bundle against it and names every missing part. `tests/toolkit/test_branding.py` runs the checker against a synthetic minimal bundle (pass) and copies with one part removed each (fail, SC-007), offline; `tests/adapters/test_antora_branding.sh` runs it against the real pinned bundle.

## R10. Distribution of the adapter's branding files

**Decision**: `scaffold-project.sh` copies `guide/adapters/<format>/branding/` (when present) to `tools/guide/branding/` in both the full scaffold and `--toolkit-only` mode, after the toolkit rsync. `branding.py` reads its templates and contract from `branding/` next to itself, so the toolkit still imports nothing from outside `tools/guide/`; in the plugin source tree (where pytest imports `guide/toolkit/branding.py`) it falls back to `../adapters/antora/branding/`, the pattern `runs.py` and `upstream.py` already use for their templates. Python imports the module `branding.py` ahead of the data directory `branding/` of the same name (a directory without `__init__.py` is only a namespace candidate), verified with CPython. The toolkit `VERSION` and the plugin version go to `0.2.0`, so evolve offers the refresh to existing guides.

## R11. Preview

**Decision**: `preview-watch.mjs` also watches `ui/` (overlay), `branding/` (files copied by create), and the `logo` and `favicon` paths named in `guide.yaml`, re-reading those paths when `guide.yaml` changes (FR-023).

## R12. Create intake

**Decision**: the create skill's intake gets one Antora-only branding question (stock look by default, or custom: logo text or own logo file, alt text, footer, optional favicon), with the FR-030 note that `logo_text` renders the Red Hat logo and is meant for guides about Red Hat products. Own files are copied into `GUIDE/branding/` and committed with the scaffold (FR-028). The evolve skill's toolkit refresh step mentions that branding becomes available after the refresh.
