# Feature 002: Antora branding (quickstart sections 1 to 4)

Recorded 2026-10-07 during implementation (T040), on macOS with Node 26.10, uv 0.8.12, toolkit 0.2.0, at commit `3bd2c0a` of branch `002-antora-branding`. Sections 3 and 4 ran as part of `make test-adapters`; the bundle download went to a scratch directory instead of `/tmp`.

## Section 1: unit tests (offline)

| Step | Result |
|---|---|
| `make test` | pass: 598 passed (the suite had 463 tests before the feature) |
| `tests/toolkit/test_branding.py` | 101 tests: every validation row of contracts/branding-config.md, resolve and hover shade, logo SVG sizing and escaping, alt helper (checked with `node -e`), footer partials, render (overlay precedence, atomic swap, overlay-only guides, nothing written outside `build/`, under one second with every key), favicon, accent CSS, head partials, and the contract checker against a synthetic bundle with each of the 17 parts removed |
| `test_guidecfg.py`, `test_playbook.py`, `test_check.py`, `test_scaffold_project.py`, `test_mkdocs_macros.py`, `test_attrs.py` | pass, including the new branding cases |

## Section 2: bundle contract against the pinned bundle

| Step | Result |
|---|---|
| `curl` the `bundle` URL of `guide/adapters/antora/branding/contract.yaml` | `ui-bundle.zip` of rhdp_showroom_theme v2.0.3 |
| `uv run guide/toolkit/branding.py contract --bundle ui-bundle.zip --contract guide/adapters/antora/branding/contract.yaml` | exit 0, `contract: OK` |
| Same against an unpacked copy without `partials/header-content.hbs` | exit 1, `contract: logo-lookup: partials/header-content.hbs: missing file` (SC-007) |

## Section 3: branded fixture guide end to end

`bash tests/adapters/test_antora_branding.sh`: exit 0, 29 checks passed, none failed.

| Expectation | Result |
|---|---|
| Both views: every page header shows `img/logo-guide.svg` with alt "Red Hat Agent Starter Kits"; the footer links the starter kits repository, no `demo.redhat.com` (FR-011 to FR-014, FR-018, SC-008) | pass (3 pages with a header in `build/site`, 4 in `build/site-internal`; the root redirect page has no header) |
| `git status --porcelain` empty after the branded build (FR-021, SC-005) | pass |
| Both logo keys set: `make site` fails with a `guide.yaml:branding` line and leaves no `build/site` (FR-010) | pass |
| PDF page 1 shows "Agent Starter Kits" before the title in both views; no page mentions the Demo Platform (FR-025, FR-026, SC-008) | pass |
| Own logo (`OwnLogoMarker`) shows on the title page (US3 scenario 2) | pass |
| `make print-pdf` without `build/branding/shareable/branding.json` fails with "branding output missing for the shareable view" | pass |
| Favicon, `color: "#3e8635"`, `ui/supplemental/css/extra.css`: pages link `site.css`, `branding.css`, `extra.css` in that order, `img/favicon-guide.png` as `image/png`; `_/css/branding.css` contains `#3e8635` (FR-015, FR-016, FR-019) | pass |
| An overlay `partials/footer-content.hbs` wins and the build prints the shadowing warning (FR-020) | pass |
| Removing the block and the overlay: `playbook.py path` prints the committed `site.yml`; the stock logo and footer are back | pass |
| SC-002: the fixture built with the plugin at `161d92f`, then refreshed and rebuilt: `diff -r` finds no difference in both site trees; no `build/branding/` or generated playbook; PDF page 1 has the same text and content stream | pass (with one `SOURCE_DATE_EPOCH` for both builds: the html-single export prints its build time, which differs between any two builds) |
| Adoption: the `161d92f` toolkit rejects the block with `guide.yaml:branding: unknown key`; after `scaffold-project.sh --toolkit-only` the guide builds branded; `Makefile`, `site.yml`, `site-internal.yml` unchanged (FR-029, SC-006) | pass |
| Contract on the downloaded pinned bundle and on a copy without the logo lookup (SC-007) | pass |
| 40-character `logo_text` ("Agent Starter Kits for OpenShift AI Labs") in Chromium at 1280 px: header logo from 36 to 418 px, site title at 436 px; logo text inside the viewBox; PDF page 1 contains the whole text (SC-004) | pass |

## Section 4: preview

`bash tests/adapters/test_preview_antora.sh`: exit 0, 9 checks passed. The fixture carries a branding block; the served `_/img/logo-guide.svg` showed "Preview Brand One", and after `logo_text` changed to "Preview Brand Two" the rebuilt logo was served within the 60 s timeout (FR-023).

## Other adapter suites

`make test-adapters` exit 0: `test_antora.sh` 9, `test_mkdocs.sh` 9, `test_gfm.sh` 11, `test_pdf.sh` 15, `test_preview_mkdocs.sh` 7 checks passed, unchanged by the feature. `make validate`: marketplace and plugin manifests pass.

## Findings during implementation

- **Antora camelCases playbook keys.** Its playbook builder lowercases every key and camelCases it on `_` and `-`, so a generated `site.keys.navbarLogo` arrived in the UI as `navbarlogo` and the header kept the stock logo. The generated playbook writes `site.keys.navbar_logo: guide`, which the UI templates see as `site.keys.navbarLogo` (data-model.md and research.md R2 updated).
- **Toolkit bytecode in git status.** Python writes `tools/guide/__pycache__/` whenever a toolkit script imports another one (also before this feature, for example `check.py` importing `guidecfg`). `guide/toolkit/.gitignore` (vendored as `tools/guide/.gitignore`) ignores it, so builds leave the guide's git status unchanged (FR-021).

## Not run

- `/guide:create` with the Antora branding question and `/guide:evolve` with the toolkit refresh in an interactive Claude Code session (US4, US5 skill text). The deterministic parts (block validation, own files under `branding/`, the refresh) are covered above.
- Section 5 (manual look in a browser); screenshots of the branded header and the PDF title page were checked during implementation.
