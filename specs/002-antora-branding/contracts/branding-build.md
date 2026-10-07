# Contract: branding in builds, preview, check, and PDF

## `tools/guide/playbook.py path [--internal] [--root DIR]`

| Guide state | Output (stdout) | Side effects |
|---|---|---|
| no branding block, no `ui/supplemental/`, main checkout | `<root>/site.yml` (or `site-internal.yml`) | none (unchanged behavior, SC-002) |
| no branding block, no overlay, linked worktree | generated playbook (existing behavior) | `build/playbook*.yml` |
| branding block and/or overlay | generated playbook with absolute paths (`url: .` becomes the guide root in a main checkout, the worktree rewrites apply in a linked worktree, `output.dir`, bundle, and extensions absolute), `ui.supplemental_files`, and `site.keys.navbar_logo: guide` when branded (the UI sees `site.keys.navbarLogo`) | renders `build/branding/<view>/` |
| invalid branding or overlay | nothing; problems on stderr; exit 1 | none |

## `tools/guide/branding.py`

```text
uv run tools/guide/branding.py validate [--root DIR]
    same branding lines as guidecfg validate; exit 1 on problems
uv run tools/guide/branding.py render --view shareable|internal [--root DIR]
    renders build/branding/<view>/ and prints its path (playbook.py calls the same function)
uv run tools/guide/branding.py contract --bundle <ui-bundle.zip|dir> [--contract FILE]
    exit 0 when every contract rule holds; otherwise one line per failing rule
    (`contract: <rule id>: <file>: <what is missing>`) and exit 1
```

Python API used by `guidecfg.py`, `playbook.py`, `mkdocs_macros.py`, `attrs.py`, and `check.py` (full signatures in tasks.md, section Interfaces): `check(root, raw, fmt, adapter_keys) -> (problems, warnings)` as `(location, message)` pairs, `check_guide(root) -> (problem lines, warning lines)`, `resolve(root, raw) -> Resolved | None`, `hover_shade(color) -> str`, `render(root, view) -> Path`, `logo_svg(text) -> str`, `check_bundle(bundle, contract) -> list[str]`. Templates and the contract come from `asset_dir()`: `tools/guide/branding/` in a guide project, `guide/adapters/antora/branding/` in the plugin source tree.

## Rendered files

| File | Content |
|---|---|
| `img/logo-guide.svg` | `logo_text`: the template with the escaped text (in `data-name` and the tspan), `textLength`, `lengthAdjust="spacingAndGlyphs"`, viewBox width `max(780, ceil(308 + width + 24))`; `logo`: a byte copy of the author's file |
| `helpers/navbar-logo-alt.js` | `'use strict'` and `module.exports = () => <JSON string of alt>` |
| `partials/footer-content.hbs` | `none`: `<footer class="footer"></footer>`; mapping: `<footer class="footer"><p class="guide-footer">` + escaped text, wrapped in `<a href="<escaped url>" target="_blank" rel="noopener">` when `url` is set, + `</p></footer>` |
| `partials/head-meta.hbs` | the favicon link (stock or custom), then `<link rel="stylesheet" href="{{{uiRootPath}}}/css/branding.css">` when `color`, then `<link rel="stylesheet" href="{{{uiRootPath}}}/css/extra.css">` when the overlay has `css/extra.css` |
| `partials/head-icons.hbs` | `<link rel="icon" href="{{{uiRootPath}}}/img/favicon-guide.<ext>" type="<mime>">` |
| `css/branding.css` | the contract's accent selectors with the color, hover selectors with the hover shade |

All author text is escaped for its context (XML for the SVG, HTML plus `{`/`}` entities for partials, JSON for the helper) (FR-017).

## Preview (`tools/guide/preview-watch.mjs`)

Watches, in addition to today's paths: `ui/`, `branding/`, and the `logo` and `favicon` paths from `guide.yaml` (re-read when `guide.yaml` changes). A change triggers the existing debounced rebuild (FR-023). A failed branding validation prints the problems and keeps the last good site.

## Check (`tools/guide/check.py`)

When `guide.yaml` has a branding block, for each built view that exists (`build/site`, `build/site-internal`), over its `*.html` pages outside `_exports/`, reported as `Violation` entries with rule `branding` and line 0:

- every page with a `navbar-logo-img` image must reference `img/logo-guide.svg` with the resolved alt text: otherwise `build/site/<page>:0: [branding] header does not show the branded logo (found <src>)`;
- a view in which no page shows the branded logo (for example a replaced bundle without `navbar-logo-img`) fails: `build/site:0: [branding] no page shows the branded logo`;
- unless `footer` is `rhdp`, the page's `<footer class="footer">` element may not contain `demo.redhat.com` or `Demo Platform`: otherwise `build/site/<page>:0: [branding] Red Hat Demo Platform notice still present`. Only the header and footer elements are inspected, so a guide whose content mentions the Demo Platform does not trip the check.

## PDF (`tools/guide/print-pdf.mjs`)

When `guide.yaml` has a branding block: reads `build/branding/<view>/branding.json`, embeds the logo file as a base64 `data:image/svg+xml` `<img alt="<alt>">` inside `<div class="guide-brand-band">` (background `#151515`, full width, logo height 14 mm set with `!important`, because the print CSS forces `height: auto !important` on every image) as the first element of the title page, built inside `transformDocument` from `meta.brand`. Chromium prints the SVG as vector content, so tests read the logo text from the page text, not from an image XObject. Missing JSON or logo: exit 1 with `print-pdf: branding output missing for the <view> view; run make check`. Without a branding block the title page is unchanged.

## Scaffold (`guide/scripts/scaffold-project.sh`)

Copies `guide/adapters/<format>/branding/` to `<guide>/tools/guide/branding/` (full scaffold and `--toolkit-only`), when the adapter has that directory.
