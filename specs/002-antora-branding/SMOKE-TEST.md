# Guided Demo Report

**Feature**: Antora branding for guides
**Date**: 2026-10-07
**Spec**: specs/002-antora-branding/spec.md
**Result**: 6 passed, 0 skipped, 0 failed, 1 manual (out of 7)

---

## Triage Summary

| Tier | Count | Detail |
|------|-------|--------|
| full | 6 | node, npx, uv, pandoc, pdftoppm, git, Playwright Chromium, network for the pinned bundle |
| partial | 0 | |
| setup_offered | 0 | |
| manual | 1 | interactive preview watcher and a live `/guide:create` session |

User selection: Run what's ready

All flows ran against a fixture guide scaffolded with `tests/adapters/scaffold.sh antora` in the session scratchpad, with the toolkit from branch `002-antora-branding`.

---

## Flow 1: Brand a fixture guide and inspect both built views

**Tier**: full
**Covers**: FR-002, FR-004, FR-005, FR-011 to FR-014, FR-017, FR-018, FR-021, FR-022, FR-024

### Setup
Scaffolded the fixture guide; added `branding: {logo_text: Agent Starter Kits, footer: {text: Agent Starter Kits on GitHub, url: https://github.com/red-hat-data-services/agentic-starter-kits}}` and committed it.

### Evidence
**Execution**: `make check`
**Output**:
```
check: OK
leakcheck: OK
build/site/guide/index.html and build/site-internal/guide/index.html:
<img src="../_/img/logo-guide.svg" alt="Red Hat Agent Starter Kits" class="navbar-logo-img">
<footer class="footer"><p class="guide-footer"><a href="https://github.com/red-hat-data-services/agentic-starter-kits" target="_blank" rel="noopener">Agent Starter Kits on GitHub</a></p></footer>
demo.redhat.com: 0 hits
git status --porcelain: ?? package-lock.json   (created by the scaffold's npm install before the build)
```
Chromium screenshot at 1280 px: header shows the Red Hat hat, divider, and "Red Hat / Agent Starter Kits". Every content page carries the logo; only Antora's root redirect `build/site/index.html` has no header, as in the stock build.

### Verdict: PASS

**Verify yourself**:
1. Build a branded guide with `make check` and open `build/site/guide/index.html`.
2. Look at the header logo, its alt text, and the footer link.

---

## Flow 2: Invalid branding stops the build before Antora runs

**Tier**: full
**Covers**: FR-002, FR-003, FR-005, FR-007, FR-008, FR-009, FR-010

### Evidence
**Execution**: `make site` with both logo keys (after `rm -rf build/site`); `guidecfg.py validate` with invalid values; validate in a MkDocs copy of the guide.
**Output**:
```
guide.yaml:branding: set exactly one of logo_text or logo
guide.yaml:branding.logo: file not found: branding/logo.svg
guide.yaml:branding.logo_alt: required with branding.logo
playbook: fix the branding problems above (guide.yaml branding, ui/supplemental/)
make: *** [site] Error 1            (build/site not recreated)

guide.yaml:branding.logo_text: must be one line of 1 to 40 characters (got 44)
guide.yaml:branding.footer.url: must be an absolute http or https URL
guide.yaml:branding.favicon: must be a path inside the guide project (got ../outside.png)
guide.yaml:branding.color: must be a #rrggbb color (got #06c)
exit=1

guide.yaml:branding.logo_alt: required with branding.logo          exit=1
guide.yaml:branding.logo_text: not supported by the mkdocs adapter (format: mkdocs)
guide.yaml:branding.footer: not supported by the mkdocs adapter    exit=1
```

### Verdict: PASS

**Verify yourself**:
1. Set both `logo_text` and `logo` in a branded guide and run `make site`.
2. Expect the `guide.yaml:branding` lines and no Antora run.

---

## Flow 3: Favicon, accent color, and the overlay directory

**Tier**: full
**Covers**: FR-006, FR-007, FR-015, FR-016, FR-019, FR-020

### Setup
Added `favicon: branding/favicon.png` (16 x 16 PNG), `color: "#3e8635"`, and `ui/supplemental/css/extra.css` (`.doc h1 { border-bottom: 4px solid #3e8635; }`); later added `ui/supplemental/partials/footer-content.hbs`.

### Evidence
**Execution**: `make site`, `guidecfg.py validate`
**Output**:
```
<link rel="stylesheet" href="../../_/css/site.css">
<link rel="icon" href="../../_/img/favicon-guide.png" type="image/png">
<link rel="stylesheet" href="../../_/css/branding.css">
<link rel="stylesheet" href="../../_/css/extra.css">
<link rel="icon" href="../../_/img/favicon-guide.png" type="image/png">

branding.css: .doc a, .toc .toc-menu a:hover, .toc .toc-menu a.is-active (border), :focus-visible,
.skip-link, #search-input:focus -> #3e8635; .doc a:hover -> #2f6528; .doc a.unresolved stays #e00

ui/supplemental/partials/footer-content.hbs: warning: shadows the file generated for branding.footer
guide configuration OK (exit 0)
built footer: <footer class="footer"><p>Author footer from ui/supplemental</p></footer>
```
Chromium screenshot: content links green, NOTE badge stock blue, green h1 rule from extra.css.

### Verdict: PASS

**Verify yourself**:
1. Add `color` and `ui/supplemental/css/extra.css`, run `make site`, open a page with links.
2. Check the head link order and the link color.

---

## Flow 4: Branded PDF title page

**Tier**: full
**Covers**: FR-025, FR-026

### Evidence
**Execution**: `make pdf`, `make pdf VIEW=internal`, `pdftoppm -f 1 -l 1`, `pdftotext -f 1 -l 1`
**Output**:
```
dist/minisvc-guide-2026-01-06.pdf, dist/minisvc-guide-2026-01-06-INTERNAL.pdf
page 1 text: "Agent Starter Kits" / "minisvc guide" / "Verified against the baseline captured on 2026-01-06" / ...
Demo Platform: 0 hits in both PDFs
```
Rendered page 1 of both PDFs: a dark band with the "Red Hat | Agent Starter Kits" logo above the title; the internal PDF keeps its red INTERNAL banner.

### Verdict: PASS

**Verify yourself**:
1. `make pdf` in a branded guide and open the PDF in `dist/`.
2. The title page starts with the dark logo band.

---

## Flow 5: Unbranded guide unchanged, then adoption by toolkit refresh

**Tier**: full
**Covers**: FR-001, FR-027, FR-029 (SC-002, SC-006)

### Setup
`git archive 161d92f guide tests` (the plugin before this feature); scaffolded the unbranded fixture with that plugin's `scaffold.sh`; `SOURCE_DATE_EPOCH` pinned for both builds (the html-single export prints its build time).

### Evidence
**Execution**: `make check pdf` with toolkit 0.1.0; `scaffold-project.sh --toolkit-only` from the branch; `make clean check pdf` with toolkit 0.2.0; then a branding block and `make site`.
**Output**:
```
old toolkit + branding block: guide.yaml:branding: unknown key   (validate exit=1)
toolkit 0.2.0 installed ... tools/guide/branding present
diff -rq: identical: site and site-internal (29 + 30 files)
minisvc-guide-2026-01-06.pdf page1 text same: True | content stream same: True
after adding branding: make site exit=0; <img src="../_/img/logo-guide.svg" alt="Red Hat Agent Starter Kits"
git diff -- Makefile site.yml site-internal.yml package.json: (no changes)
```

### Verdict: PASS

**Verify yourself**:
1. Refresh an existing guide's toolkit with `/guide:evolve` and rebuild without a branding block; compare `build/site`.
2. Add a branding block and rebuild; no build file needs an edit.

---

## Flow 6: Bundle contract and the guide's branding check

**Tier**: full
**Covers**: FR-031, FR-032 (SC-007)

### Evidence
**Execution**: `branding.py contract` against the pinned bundle and a copy without `partials/header-content.hbs`; `make check` on the branded guide with `site.yml` pointing at a bundle whose header hardcodes `logo-demo-platform.svg`.
**Output**:
```
contract: OK (ui-bundle.zip)                                         exit=0
contract: logo-lookup: partials/header-content.hbs: missing file      exit=1
build/site/guide/index.html:0: [branding] header does not show the branded logo (found ../_/img/logo-demo-platform.svg, alt 'Red Hat Agent Starter Kits')
build/site:0: [branding] no page shows the branded logo
(same for every page of build/site-internal)
```

### Verdict: PASS

**Verify yourself**:
1. `uv run tools/guide/branding.py contract --bundle <ui-bundle.zip>` in a guide project.
2. Expect `contract: OK` for the pinned bundle.

---

## Flow 7: Live preview rebuild and the create intake

**Tier**: manual
**Covers**: FR-023, FR-028, FR-030

### Verdict: MANUAL

1. In a branded guide run `make preview`, change `logo_text` in guide.yaml, and confirm the page reloads with the new text; repeat with `ui/supplemental/css/extra.css`. (Automated coverage: `tests/adapters/test_preview_antora.sh`.)
2. Resume the paused agentic-starter-kits run with `/guide:create --dir ~/Development/ai/agentic-starter-kits-guide --format antora` and confirm the intake asks the branding question with the Red Hat logo note, writes the `branding` block, and copies own logo or favicon files into `branding/`.

---

## FR Coverage

| FR | Flow | Verdict | Classification |
|----|------|---------|----------------|
| FR-001 | Flow 5 | PASS | observable |
| FR-002 | Flows 1, 2 | PASS | observable |
| FR-003 | Flow 2 | PASS | observable |
| FR-004 | Flow 1 | PASS | observable |
| FR-005 | Flows 1, 2 | PASS | observable |
| FR-006 | Flow 3 | PASS | observable |
| FR-007 | Flows 2, 3 | PASS | observable |
| FR-008 | Flow 2 | PASS | observable |
| FR-009 | Flow 2 | PASS | observable |
| FR-010 | Flow 2 | PASS | observable |
| FR-011 | Flow 1 | PASS | observable |
| FR-012 | - | - | own-logo rendering covered by test_antora_branding.sh (own SVG with script) |
| FR-013 | Flow 1 | PASS | observable |
| FR-014 | Flows 1, 3 | PASS | observable |
| FR-015 | Flow 3 | PASS | observable |
| FR-016 | Flow 3 | PASS | observable |
| FR-017 | Flow 1 | PASS | observable (escaping unit-tested in test_branding.py) |
| FR-018 | Flow 1 | PASS | observable |
| FR-019 | Flow 3 | PASS | observable |
| FR-020 | Flow 3 | PASS | observable |
| FR-021 | Flow 1 | PASS | observable |
| FR-022 | - | - | linked worktree builds covered by test_playbook.py |
| FR-023 | Flow 7 | MANUAL | observable |
| FR-024 | Flows 1, 6 | PASS | observable |
| FR-025 | Flow 4 | PASS | observable |
| FR-026 | Flow 4 | PASS | observable |
| FR-027 | Flow 5 | PASS | observable |
| FR-028 | Flow 7 | MANUAL | observable |
| FR-029 | Flow 5 | PASS | observable |
| FR-030 | Flow 7 | MANUAL | observable |
| FR-031 | Flow 6 | PASS | observable |
| FR-032 | Flow 6 | PASS | observable |
