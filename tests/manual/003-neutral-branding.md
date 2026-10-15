# Feature 003: neutral branding (quickstart sections 1 to 6)

Recorded 2026-10-15 during implementation (T038), on macOS with uv, Node, and Playwright Chromium from the fixture guide, toolkit 0.4.0, on branch `003-neutral-branding`. Sections 2 to 5 ran as part of `make test-adapters`; the bundle download went to a scratch directory instead of `/tmp`.

## Section 1: unit tests and contract

| Step | Result |
|---|---|
| `make test` | pass: 708 passed |
| `tests/toolkit/test_branding_neutral.py` | stock golden files (logo and head-meta byte-identical to `b0db967`), every new validation message, font manifest checksums and coverage, outline determinism, internal spaces, wordmark and hat golden SVGs, the neutral overlay (fonts, theme CSS, head partials, link order, shadow warnings, `branding.json` fields), and the spec 002 file set for a block without `theme` |
| `uv run guide/toolkit/branding.py contract --bundle <pinned ui-bundle.zip>` | exit 0, `contract: OK` (includes `head-styles-stock`, `font-stacks`, `navbar-rule`, `navbar-css`) |
| `make validate` | pass |

## Sections 2 to 5: `bash tests/adapters/test_antora_neutral.sh`

Exit 0, 22 checks passed, none failed.

| Expectation | Result |
|---|---|
| Stock reference build, Google Fonts blocked: no Red Hat face loads (the stock bundle gets its fonts from Google) | pass (1 Google request blocked, no face loaded, navbar 63 px) |
| Wordmark guide, both views: every page shows the outlined `logo-guide.svg` with alt "OpenClaw on OpenShift", links `css/theme-neutral.css`, no Demo Platform footer; `_/font/` holds the six fonts and `OFL.txt` (FR-006, FR-012 to FR-015) | pass (3 and 4 pages with a header) |
| Chromium with Google Fonts blocked: Red Hat Text and Display load from the vendored files; no Google request (SC-002, SC-007) | pass |
| Navbar: `box-shadow` is `rgb(238, 0, 0) 0px -3px 0px 0px inset`, height 63 px as in the stock build | pass |
| `git status --porcelain` empty after the build | pass |
| `check.py` without `_/font/OFL.txt` reports `neutral theme font missing: OFL.txt` (FR-026) | pass |
| Hat variant (`logo_text: OpenShift AI`, `theme: neutral`): hat paths and MPL-2.0 comment kept, product name outlined, alt "Red Hat OpenShift AI" (FR-007) | pass |
| SC-004, unbranded and RHDP-branded fixtures built with the plugin at `b0db967`, refreshed, rebuilt: both site trees identical, PDF page 1 same text and content stream | pass (one `SOURCE_DATE_EPOCH` for both builds) |
| Neutral PDF: Type3 fonts (Chromium's embedding of the vendored variable fonts) and no serif fallback; red rule under the title band (FR-018, FR-019) | pass (red rows directly under the band) |
| Refreshed branded fixture adopts `theme: neutral` with one added line (US5) | pass |

Size (SC-005): the neutral site's `_/` is 236 KB larger than the stock one (fonts 227 KB).

Visual review: the wordmark in a mocked navbar, the hat variant next to the stock logo, and PDF pages 1 and 3 were rendered and looked at during implementation. Two fixes came out of it: the wordmark capitals are centered vertically (research R8), and PDF headings use weight 500 instead of Asciidoctor's 300.

## Section 6: validation messages

Run in a kept fixture guide with `uv run tools/guide/guidecfg.py validate`:

| Block | Output | Exit |
|---|---|---|
| `wordmark` of two CJK characters | `guide.yaml:branding.wordmark: no glyph for "漢" (U+6F22) in Red Hat Display` and the same for U+5B57 | 1 |
| `logo_text` and `wordmark` | `guide.yaml:branding: set exactly one of logo_text, wordmark, or logo` | 1 |
| `theme: dark` | `guide.yaml:branding.theme: must be neutral or stock (got dark)` | 1 |

## All adapter tests

`make test-adapters`: 8 suites, 123 checks passed, none failed (including the spec 002 branding test with the renamed `head-styles-stock` contract rule).

## Not run yet

- Section 7: an interactive `/guide:create` intake for a scratch Antora guide (both answers to "Is this guide about a Red Hat product?").
- The `/guide:evolve` refresh of a guide scaffolded at `b0db967`, to record that its summary names `theme: neutral` and `wordmark` (FR-025).

Both need a live, interactive plugin session and were left for the author.
