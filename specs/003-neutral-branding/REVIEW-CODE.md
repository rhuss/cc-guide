# Code Review: Neutral Red Hat inspired branding for new guides

**Spec:** specs/003-neutral-branding/spec.md
**Date:** 2026-10-15
**Reviewer:** Claude (speckit.spex-gates.review-code)
**Range:** `b0db967..003-neutral-branding`

## Compliance Summary

**Overall Score: 100% after reconciliation** (91% before: three minor deviations, all resolved by updating the spec to the implemented and reviewed behavior)

- Functional Requirements: 31/31
- Error handling (validation messages, missing fonts, missing faces in the printer): 7/7
- Edge cases: 10/10
- Success criteria: 6/7 verified automatically; SC-001 partly (the interactive `/guide:create` run is still open, see tests/manual/003-neutral-branding.md)

## Functional Requirements

| FR | Implementation | Status |
|---|---|---|
| FR-001 wordmark key | `guide/toolkit/branding.py` `KEYS`, `_check_block` (shared length rule) | Compliant |
| FR-002 exactly one logo key | `_check_block`, message at branding.py:230 | Compliant |
| FR-003 wordmark alt default | `resolve()`, branding.py:502 | Compliant |
| FR-004 theme values, default stock | `_check_block` (branding.py:286), `resolve()` | Compliant |
| FR-005 not supported in MkDocs, gfm | adapter lists unchanged; `test_new_keys_not_supported_elsewhere` | Compliant |
| FR-006 wordmark SVG | `wordmark_svg()` branding.py:647 | Deviation (minor), reconciled: width is `ceil(advance)` without side bearings; capitals centered (research R8) |
| FR-007 neutral logo_text | `logo_svg(text, "neutral")`, weight 700 at translate(308 149) | Compliant |
| FR-008 stock logo_text unchanged | stock branch untouched; golden files from `b0db967` | Compliant |
| FR-009 deterministic | `_num()`, no kerning; `test_outline_counts_and_advance` | Compliant |
| FR-010 vendored woff2, no system fonts | `_display()` lazy fontTools, instancer | Compliant |
| FR-011 glyph coverage from manifest | `missing_glyphs()`, branding.py:123 | Compliant |
| FR-012 vendored fonts, manifest | `guide/adapters/antora/branding/fonts/`, `update-fonts.py` | Compliant |
| FR-013 scaffold copies fonts | `scaffold-project.sh` rsync (maintainer script excluded) | Compliant |
| FR-014 overlay: fonts, theme CSS, navbar rule, head-styles without Google Fonts | `_render_into`, `theme_css()`, `NEUTRAL_HEAD_STYLES` | Compliant |
| FR-015 head-meta order | `head_meta(..., theme)` | Compliant |
| FR-016 missing or changed fonts | `check_fonts()` branding.py:145 | Compliant |
| FR-017 stock publishes nothing new | `test_wordmark_with_stock_theme`, `test_logo_text_without_theme_renders_the_spec_002_file_set` | Compliant |
| FR-018 PDF band rule | `neutralCss()` print-pdf.mjs:325 | Compliant |
| FR-019 PDF typography | `neutralCss()`, explicit `document.fonts.load()` | Deviation (minor), reconciled: `body *` scope and heading weight 500 added to the spec |
| FR-020 branding.json fields | `_render_into` meta | Deviation (minor), reconciled: `fonts` and `font_faces` named in the spec |
| FR-021 to FR-023 create intake | `guide/skills/create/SKILL.md` step 5 and 5.3 | Compliant (text); live run open |
| FR-024 template | `guide/templates/guide.yaml` | Compliant (`test_template_branding_example_validates`) |
| FR-025 evolve note | `guide/skills/evolve/SKILL.md` | Compliant (text); live run open |
| FR-026 make check | `check_neutral_theme()` check.py:446 | Compliant |
| FR-027 wordmark passes the branded-site check | `test_neutral_theme_passes` | Compliant |
| FR-028 contract rules | contract.yaml `head-styles-stock`, `font-stacks`, `navbar-rule`, `navbar-css` | Compliant |
| FR-029 NOTICE, OFL published | NOTICE.md, overlay `font/OFL.txt` | Compliant |
| FR-030 docs | `guide/docs/branding.md`, `guide/docs/adapters.md` | Compliant |
| FR-031 versions | 0.4.0 in VERSION, plugin.json, marketplace.json | Compliant |

## Extra Behavior (not in the original spec)

- **Dropping Google Fonts** (`head-styles.hbs`): decided by the author during implementation, recorded in spec clarifications, FR-014, FR-026, FR-028, SC-007, research R11.
- **Wordmark vertical centering**: found in visual review, recorded in research R8 and the contract.
- **Printer fails when a vendored face does not load**: recorded in contracts/theme-build.md and FR-019.

All three are now in the spec; no unspecified behavior remains.

## Code Quality Notes

- fontTools stays out of validation-only scripts (lazy imports; only `branding.py` and `playbook.py` declare it), confirmed by `test_validate_neutral_branding_with_pyyaml_only`.
- `check_neutral_theme()` repeats the view and page selection of `check_branded_site()`; a shared helper would remove about ten lines. Not changed, to keep the spec 002 function untouched.
- `_font_names()` swallows manifest errors and returns `[]`; validation reports the missing manifest separately, so nothing is lost.

## Verification

- `make test`: 708 passed
- `make test-adapters`: 8 suites, 123 checks, 0 failed (`test_antora_neutral.sh`: 22 checks)
- `make validate`: pass
- Contract against the pinned bundle: OK

## Open

- The interactive `/guide:create` intake and `/guide:evolve` refresh runs (T038, FR-021 to FR-023, FR-025 live behavior).
