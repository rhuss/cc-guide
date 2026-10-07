# Quickstart: validating Antora branding

Prerequisites: the tool chain of `make test-adapters` (node 20+, npx, uv, git, Playwright Chromium) and network access for the pinned UI bundle.

## 1. Unit tests (offline)

```bash
make test
```

Expect `tests/toolkit/test_branding.py` (validation per edge case, rendering and escaping, overlay precedence, contract checker against a synthetic bundle with each part removed), the extended `test_guidecfg.py`, `test_playbook.py`, and `test_check.py` to pass.

## 2. Bundle contract against the pinned bundle

```bash
curl -sL -o /tmp/ui-bundle.zip "$(yq -r .bundle guide/adapters/antora/branding/contract.yaml)"
uv run guide/toolkit/branding.py contract --bundle /tmp/ui-bundle.zip --contract guide/adapters/antora/branding/contract.yaml
```

Expect exit 0. Delete `partials/header-content.hbs` from an unpacked copy and rerun: expect exit 1 naming `logo-lookup` (SC-007).

## 3. Branded fixture guide end to end

```bash
bash tests/adapters/test_antora_branding.sh
```

The script scaffolds the fixture guide, adds the agentic-starter-kits branding block (`logo_text: Agent Starter Kits`, footer link to the starter kits repository, favicon, color `#3e8635`, and `ui/supplemental/css/extra.css`), runs `make check pdf VIEW=shareable` and `make pdf VIEW=internal`, and asserts:

- both views: every page header references `img/logo-guide.svg` with alt "Red Hat Agent Starter Kits"; the footer shows the configured link and no `demo.redhat.com` (FR-011 to FR-014, FR-018, SC-008)
- `_/css/branding.css` and `_/css/extra.css` are linked after `site.css`; the favicon link points at `img/favicon-guide.png` (FR-015, FR-016, FR-019)
- `git status --porcelain` in the guide project is empty after the build (FR-021, SC-005)
- the text of the PDF's first page contains "Agent Starter Kits" before the guide title, an own logo shows on the title page, and no PDF page mentions the Demo Platform (FR-025, FR-026, SC-008)
- a 40-character `logo_text` measured in Chromium at 1280 px: the logo's text box fits inside its viewBox, the header image does not overlap the site title, and the PDF's first page contains the whole text (SC-004)
- an unbranded fixture built with the toolkit of `BASELINE_REF` and again after a toolkit refresh gives identical site trees and the same PDF title page (SC-002)
- removing the branding block and the overlay returns the build to the stock logo and footer
- a toolkit refresh (`scaffold-project.sh --toolkit-only`) restores `tools/guide/branding/` and keeps the branding working without touching the Makefile or `site.yml` (FR-029, SC-006)
- an invalid block (both logo keys) makes `make site` fail before Antora runs, naming `branding` (FR-010)

## 4. Preview

```bash
bash tests/adapters/test_preview_antora.sh
```

Extended: with a branding block, changing `logo_text` while the preview runs produces a rebuilt header with the new text (FR-023).

## 5. Manual look

```bash
cd <fixture guide> && make preview
```

Open the site: header shows "Red Hat | Agent Starter Kits", links are green, the footer shows the starter kits link. `make pdf` and open the PDF: the title page starts with the dark band and the logo.
