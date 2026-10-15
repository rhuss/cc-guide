# Guided Demo Report

**Feature**: Neutral Red Hat inspired branding for new guides
**Date**: 2026-10-15
**Spec**: specs/003-neutral-branding/spec.md
**Result**: 6 passed, 1 skipped, 0 failed, 0 manual (out of 7)

---

## Triage Summary

| Tier | Count | Detail |
|------|-------|--------|
| full | 5 | uv, node 26, npx, pandoc, pdffonts, Playwright Chromium available |
| partial | 1 | Red Hat fonts are installed on the demo machine (`~/Library/Fonts`), so "no fonts installed" cannot be shown directly |
| setup_offered | 0 | |
| manual | 1 | Needs an interactive `/guide:create` and `/guide:evolve` session |

User selection: Run everything possible

Fixtures: `tests/adapters/scaffold.sh antora` (and `mkdocs`) into a session scratch directory; plugin checkout at `777f426`.

---

## Flow 1: Wordmark guide (User Story 1)

**Tier**: full
**Covers**: FR-001, FR-003, FR-004, FR-006, FR-009, FR-012, FR-013, FR-014, FR-015, FR-026, FR-027

### Setup
Scaffolded the Antora fixture guide and appended `branding: {wordmark: OpenClaw on OpenShift, theme: neutral, footer: none}` to `guide.yaml`.

### Evidence
**Execution**: `make check`, inspection of `build/site`, Playwright screenshot of `guide/index.html`.
**Output**:
```
guide configuration OK / check: OK / leakcheck: OK
logo-guide.svg: viewBox="0 0 898 178.739", translate(0 118.07), fill="#fff", 19 <path>, 0 <text>
alt text on every page: "OpenClaw on OpenShift"
_/font/: 6 woff2 + OFL.txt, 244 KB total (SC-005 limit 300 KB)
3 of 3 content pages link css/site.css, then css/theme-neutral.css
"Demo Platform" on no page
```
Screenshot: white outlined wordmark without the hat, red rule under the dark header, body in Red Hat Text, no footer.

### Verdict: PASS

Observation (outside the FR scope): `guide/_exports/index.html`, the print-export intermediate, is published and still links `fonts.googleapis.com` through Asciidoctor's default stylesheet. `check.py` skips `_exports` by design and the PDF printer blocks remote fonts, but a reader opening that URL directly would contact Google. Candidate follow-up.

**Verify yourself**:
1. `bash tests/adapters/scaffold.sh antora <dir>`, add the block, `make -C <dir> check`
2. `rg -c '<text' <dir>/build/site/_/img/logo-guide.svg` prints nothing; `ls <dir>/build/site/_/font/`

---

## Flow 2: Browser fonts, red rule, no Google requests

**Tier**: partial
**Covers**: FR-014, SC-002, SC-007

### Setup
The Flow 1 build.

### Evidence
**Execution**: `node tests/adapters/measure_neutral.mjs <guide>` (Chromium, every Google Fonts request aborted and counted).
**Output**:
```
loaded:         Red Hat Display normal, Red Hat Mono normal, Red Hat Text italic, Red Hat Text normal
bodyFont:       "Red Hat Text", RedHatText, ...
navbarShadow:   rgb(238, 0, 0) 0px -3px 0px 0px inset
navbarHeight:   63 (3.5rem at the bundle's 18 px root, same as the stock build)
googleRequests: 0
```

**Partial evidence disclaimer**: Red Hat fonts are installed locally, so the "machine without Red Hat fonts" condition is not reproduced. The evidence proves that the faces load as `FontFace` objects with Google blocked (only the vendored files can supply them); the adapter test's stock control shows that the same probe loads no Red Hat face on the stock build.

### Verdict: PASS

**Verify yourself**:
1. `node tests/adapters/measure_neutral.mjs <guide>`
2. On a machine without Red Hat fonts, repeat and check `bodyFont` and `loaded`.

---

## Flow 3: Hat variant (User Story 2)

**Tier**: full
**Covers**: FR-007, FR-027

### Setup
Replaced `wordmark` with `logo_text: OpenShift AI` in the Flow 1 fixture.

### Evidence
**Execution**: `make check`, SVG and HTML inspection, screenshot, outline advance widths at three weights.
**Output**:
```
check: OK
logo-guide.svg: MPL-2.0 "Derived from img/logo-demo-platform.svg ... v2.0.3" comment kept,
  OFL outline comment added, 15 <path>, 0 <text>, product name at translate(308 149) fill="#fff"
alt text: "Red Hat OpenShift AI"
outline("OpenShift AI") advance: 469.4 at 400, 476.0 at 500, 493.3 at 700 (logo_text uses 700)
```
Screenshot: hat, divider, "Red Hat / OpenShift AI" in Red Hat Display, red rule, Red Hat Text body.

### Verdict: PASS

**Verify yourself**:
1. Set `logo_text: OpenShift AI`, `theme: neutral`, run `make check`
2. `rg -o 'translate\(308 149\)' build/site/_/img/logo-guide.svg`

---

## Flow 4: Existing guides unchanged (User Story 3)

**Tier**: full
**Covers**: FR-008, FR-017, SC-004

### Setup
`tests/adapters/test_antora_neutral.sh` extracts the plugin at `b0db967` (main before the feature) and scaffolds an unbranded and a branded (`logo_text`, footer, no `theme`) fixture with it.

### Evidence
**Execution**: `KEEP=1 bash tests/adapters/test_antora_neutral.sh` (build and PDF with `b0db967`, toolkit refresh from this branch, rebuild with the same `SOURCE_DATE_EPOCH`, `diff -r`).
**Output**:
```
PASS unbranded: build/site identical before and after the feature (SC-004)
PASS unbranded: build/site-internal identical before and after the feature (SC-004)
PASS unbranded: PDF title page has the same text and content stream (SC-004)
PASS branded: build/site identical before and after the feature (SC-004)
PASS branded: build/site-internal identical before and after the feature (SC-004)
PASS branded: PDF title page has the same text and content stream (SC-004)
```
The full script reported 23 checks passed, none failed.

### Verdict: PASS

**Verify yourself**:
1. `KEEP=1 bash tests/adapters/test_antora_neutral.sh`
2. `diff -r <tmp>/before-branded/site <tmp>/branded/build/site` prints nothing

---

## Flow 5: Neutral PDF (User Story 4)

**Tier**: full
**Covers**: FR-018, FR-019, FR-020

### Setup
The Flow 3 fixture (hat variant, neutral).

### Evidence
**Execution**: `make pdf`, `pdffonts`, `pdftoppm` of pages 1 and 2, printer source at `tools/guide/print-pdf.mjs:387` and `:428`; adapter test checks.
**Output**:
```
wrote dist/minisvc-guide-2026-01-06.pdf (5 sheets)
pdffonts: Type 3 subsets of RedHatDisplay-Regular (default, wght 1F4 = 500, wght 2BC = 700),
  RedHatText-Regular, RedHatText-Italic, RedHatMono-Regular; other: Helvetica, Helvetica-Bold
  (page-number footer and admonition labels)
print-pdf.mjs: every request except file:, data:, blob:, about:, and images is aborted;
  each face is loaded with document.fonts.load before printing
PASS neutral PDF title band has the red rule (red rows 249-253 under the band ending at 248)
PASS print-pdf stops on a font that does not load and names it
```
Page 1: dark band with the hat logo and a red rule under it, title in Red Hat Display, text in Red Hat Text. Page 2: contents in Red Hat Display and Text.

### Verdict: PASS

**Verify yourself**:
1. `make pdf && pdffonts dist/*.pdf | rg -i redhat`
2. `pdftoppm -png -r 80 -f 1 -l 1 dist/*.pdf page` and look at the band

---

## Flow 6: Validation messages

**Tier**: full
**Covers**: FR-001, FR-002, FR-004, FR-005, FR-011, FR-016

### Setup
Branding variants swapped into the fixture's `guide.yaml` (restored afterwards); one vendored font tampered and then deleted in the fixture's `tools/guide/branding/fonts/` (restored); a MkDocs fixture scaffolded with `wordmark` and `theme`.

### Evidence
**Execution**: `uv run tools/guide/guidecfg.py validate` per case.
**Output**:
```
wordmark: 漢字                    exit 1  branding.wordmark: no glyph for "漢" (U+6F22) in Red Hat Display (and U+5B57)
logo_text: AI 🚀, neutral         exit 1  branding.logo_text: no glyph for "🚀" (U+1F680) in Red Hat Display
logo_text: AI 🚀, stock           exit 0  guide configuration OK
wordmark + logo_text              exit 1  branding: set exactly one of logo_text, wordmark, or logo
theme only, no logo key           exit 1  branding: set exactly one of logo_text, wordmark, or logo
theme: dark                       exit 1  branding.theme: must be neutral or stock (got dark)
41-character wordmark             exit 1  branding.wordmark: must be one line of 1 to 40 characters (got 41)
40 characters plus padding        exit 0  guide configuration OK
RedHatMono-VF.woff2 tampered      exit 1  checksum mismatch; refresh the toolkit (scaffold-project.sh --toolkit-only)
RedHatMono-VF.woff2 deleted       exit 1  missing; refresh the toolkit (scaffold-project.sh --toolkit-only)
mkdocs wordmark + theme           exit 1  branding.wordmark / branding.theme: not supported by the mkdocs adapter
```

### Verdict: PASS

**Verify yourself**:
1. Put each block into a fixture `guide.yaml` and run `uv run tools/guide/guidecfg.py validate`
2. Compare the messages with FR-002, FR-004, FR-011, FR-016

---

## Flow 7: Create intake and evolve notice

**Tier**: manual
**Covers**: FR-021, FR-022, FR-023, FR-024, FR-025

### Setup
None. The flow needs an interactive plugin session.

### Evidence
Not executed. Skill text only: `guide/skills/create/SKILL.md:61` asks "Is this guide about a Red Hat product?", `:86` writes `theme: neutral` and `footer: none`; `guide/skills/evolve/SKILL.md:45` names both keys after a refresh to 0.4.0 and forbids editing the block. This is not behavioral evidence.

### Verdict: SKIP

Skipped by user choice.

**Verify yourself**:
1. `make install`; in a new session in an empty directory run `/guide:create` for a scratch Antora guide, answer No; `guide.yaml` gets `wordmark: <title>`, `theme: neutral`, `footer: none`, and no RHDP option is offered.
2. Repeat with Yes and a product name: `logo_text: <name>`.
3. Scaffold a guide with the `b0db967` plugin, run `/guide:evolve`, accept the toolkit refresh: the summary names `theme: neutral`, `wordmark`, and `docs/branding.md`; the `branding` block is unchanged.
4. Record the runs in `tests/manual/003-neutral-branding.md`.

---

## FR Coverage

| FR | Flow | Verdict | Classification |
|----|------|---------|----------------|
| FR-001 | Flow 1, 6 | PASS | observable |
| FR-002 | Flow 6 | PASS | observable |
| FR-003 | Flow 1 | PASS | observable |
| FR-004 | Flow 1, 6 | PASS | observable |
| FR-005 | Flow 6 | PASS | observable |
| FR-006 | Flow 1 | PASS | observable |
| FR-007 | Flow 3 | PASS | observable |
| FR-008 | Flow 4 | PASS | observable |
| FR-009 | Flow 1 | PASS (golden SVG in unit tests) | observable |
| FR-010 | - | - | internal-only (verified by unit tests) |
| FR-011 | Flow 6 | PASS | observable |
| FR-012 | Flow 1 | PASS | observable |
| FR-013 | Flow 1 | PASS | observable |
| FR-014 | Flow 1, 2 | PASS | observable |
| FR-015 | Flow 1 | PASS | observable |
| FR-016 | Flow 6 | PASS | observable |
| FR-017 | Flow 4 | PASS | observable |
| FR-018 | Flow 5 | PASS | observable |
| FR-019 | Flow 5 | PASS | observable |
| FR-020 | Flow 5 | PASS (indirectly: the printer loads the faces) | observable |
| FR-021 | Flow 7 | SKIP | observable |
| FR-022 | Flow 7 | SKIP | observable |
| FR-023 | Flow 7 | SKIP | observable |
| FR-024 | Flow 7 | SKIP | observable |
| FR-025 | Flow 7 | SKIP | observable |
| FR-026 | Flow 1, 4 (adapter test) | PASS | observable |
| FR-027 | Flow 1, 3 | PASS | observable |
| FR-028 | - | - | internal-only (contract test) |
| FR-029 | - | - | internal-only (docs and notice files) |
| FR-030 | - | - | internal-only (docs) |
| FR-031 | - | - | internal-only (version files) |

## Internal-Only FRs

The following FRs describe internal behavior or repository files with no runtime effect a demo can show. They are verified by unit tests, the contract check, and review only:

- **FR-010**: outline rendering reads the vendored variable font and needs no system fonts (keyword: internal)
- **FR-028**: `contract.yaml` rules for the pinned bundle (keyword: contract, schema)
- **FR-029**: `NOTICE.md` lists the Red Hat fonts (keyword: file content, docs)
- **FR-030**: `docs/branding.md` content (keyword: docs)
- **FR-031**: version bump to 0.4.0 (keyword: constraint)
