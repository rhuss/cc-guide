# Code Review: Antora branding for guides

**Spec:** specs/002-antora-branding/spec.md
**Date:** 2026-10-07
**Reviewer:** Claude (speckit-spex-gates-review-code, ship pipeline stage 7)
**Diff:** `git diff main...HEAD` (feature commits plus the review fix commits f8bc96d and 9511150)

## Compliance Summary

**Overall Score: 100%** after the fix loop (98% before it: 59 of 60 checks, FR-023 partial)

- Functional Requirements: 32/32 (100%)
- Edge Cases: 20/20 (100%)
- Success Criteria: 8/8 (100%)
- Spec-declared constants: none (the spec has no `## Constants` section)

## Detailed Review

### Functional Requirements

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| FR-001 optional block; unbranded build unchanged | guidecfg.py `GUIDE_KEYS`; playbook.py returns the committed playbook without block, overlay, or worktree; print-pdf.mjs no band without block | Compliant (smoke test: byte-identical site, same PDF title page) |
| FR-002 exactly one of logo_text or logo | branding.py `_check_block` | Compliant |
| FR-003 logo_text 1..40 chars, one line | branding.py `_check_block` | Compliant |
| FR-004 logo_alt default and required with logo | branding.py `_check_block`, `resolve` | Compliant |
| FR-005 footer rhdp/none/{text,url}, default none | branding.py `_check_block`, `resolve`, `footer_partial` | Compliant |
| FR-006 favicon .ico/.png/.svg | branding.py `FAVICON_TYPES`, `_check_path` | Compliant |
| FR-007 color #rrggbb | branding.py `COLOR_RE` | Compliant |
| FR-008 paths inside the project | branding.py `_check_path` (absolute, `~`, `..`, symlink escape) | Compliant |
| FR-009 adapter branding capability | adapters/*/adapter.yaml `branding:`; branding.py `adapter_keys` | Compliant |
| FR-010 validation before every build | playbook.py (Antora site, internal, preview, check, pdf, dist); mkdocs_macros.py; attrs.py regions (gfm); guidecfg validate | Compliant |
| FR-011 logo_text on the Red Hat layout | logo-text.svg.tmpl, branding.py `logo_svg` (textLength, viewBox) | Compliant |
| FR-012 own logo as image only | `img/logo-guide.svg` via the bundle's `<img>` | Compliant |
| FR-013 alt text on every page | generated `helpers/navbar-logo-alt.js` | Compliant |
| FR-014 footer per setting | `partials/footer-content.hbs` for none and mapping | Compliant |
| FR-015 favicon | `head-meta.hbs`, `head-icons.hbs`, `img/favicon-guide.*` | Compliant |
| FR-016 accent color | contract.yaml selector lists; branding.py `accent_css` (checked against every `#06c`/`#004d99` rule of the pinned site.css) | Compliant |
| FR-017 literal text | `_xml`, `_html` (braces as entities), `json.dumps`, escaped PDF alt | Compliant |
| FR-018 same branding in both views | `render(view)` from one block | Compliant |
| FR-019 overlay directory, extra.css last | `overlay_files`, `render` merge order, `head_meta` | Compliant |
| FR-020 author file wins, warning | `generated_files`, `check` warnings | Compliant |
| FR-021 no tracked or visible file changes | output under build/; toolkit .gitignore for `__pycache__` | Compliant |
| FR-022 linked worktrees | playbook.py worktree branch | Compliant |
| FR-023 preview rebuilds on branding changes | preview-watch.mjs `brandingInputs`, `watchPlan`, depth-0 root watcher | Compliant after fix (was partial: inputs missing at start were never watched) |
| FR-024 unmodified bundle | `ui.supplemental_files` only | Compliant |
| FR-025 PDF band in header color | print-pdf.mjs `.guide-brand-band` | Compliant |
| FR-026 logo embedded as image | print-pdf.mjs `readBrand` base64 data URL in `<img>` | Compliant |
| FR-027 unbranded PDF unchanged | print-pdf.mjs | Compliant |
| FR-028 create intake | skills/create/SKILL.md step 5 and configuration step | Compliant |
| FR-029 adoption via toolkit refresh | scaffold-project.sh vendors `tools/guide/branding/`; Makefile unchanged | Compliant |
| FR-030 Red Hat logo statement | docs/branding.md, create intake, template, NOTICE.md | Compliant |
| FR-031 contract test | contract.yaml, `check_bundle`, adapter smoke test | Compliant |
| FR-032 check step catches broken branding | check.py `check_branded_site` | Compliant |

### Edge Cases

All 20 edge cases are handled: validation messages name the key (both or neither logo key, missing `logo_alt`, bad paths, unsupported format, logo_text rules, footer URL, color), shadowing warns, the overlay applies without a block, removing the block restores the stock look, linked worktrees, preview edits, the dark band for light logos, SVG scripts never run, the check catches a replaced bundle, create copies own files, a playbook with its own `supplemental_files` fails validation, the old toolkit rejects the key, and an invalid block stops the build before Antora.

### Extra Features (Not in Spec)

- `branding.py contract --bundle` CLI and `validate` subcommand: helpful, documented in docs/branding.md (supports FR-031).
- `output.clean: true` in generated playbooks of branded or overlaid guides: added by the review fix loop so stale pages cannot fail FR-032; documented.
- Shadow warnings printed by the preview after a successful build: supports FR-020.

## Code Review Guide

Where a reviewer should look first:

1. `guide/toolkit/branding.py`: validation (`_check_block`, `overlay_files`, `check`), rendering (`render`, `_render_into`, `_swap`), and the bundle contract checker (`check_bundle`).
2. `guide/toolkit/playbook.py`: the generated playbook (absolute paths, `supplemental_files`, `navbar_logo`, `output.clean`).
3. `guide/toolkit/check.py` `check_branded_site` and `_stock_notice`: the FR-032 heuristics (poweredBy marker, generated and own footers, internal view only when enabled).
4. `guide/toolkit/preview-watch.mjs` `watchPlan` and the root watcher: chokidar 4 reports only one missing entry per directory.
5. `guide/toolkit/print-pdf.mjs`: the band, the data URL, and the wait for pending images before the broken-image check.
6. `guide/adapters/antora/branding/contract.yaml`: every relied-upon bundle part, including the include chain and restore rules.

## Deep Review Report

**Gate: PASS** (after fix round 1; round 2 applied re-review follow-ups)

| Severity | Found | Fixed | Remaining |
|----------|-------|-------|-----------|
| Critical | 0 | 0 | 0 |
| Important | 9 | 9 | 0 |
| Minor | 36 | 16 | 20 |
| Notable | 5 | - | 5 |

| Agent | Found | Fixed | Remaining | Status |
|-------|-------|-------|-----------|--------|
| Correctness | 8 | 7 | 1 | completed |
| Architecture & Idioms | 15 | 5 | 10 | completed |
| Security | 2 | 0 | 2 | completed (both partly mitigated) |
| Production Readiness | 7 | 3 | 4 | completed |
| Test Quality | 14 | 10 | 4 | completed |
| Re-review (round 2) | 4 | 3 | 1 | completed |
| Goal Alignment | 0 | 0 | 0 | skipped (no PR found) |
| CodeRabbit (external) | 0 | 0 | 0 | completed (3 runs) |
| Copilot (external) | 0 | 0 | 0 | skipped (disabled in config) |
| Codex (external) | 0 | 0 | 0 | failed (usage limit) |
| Test Suite (regression) | 3 | 3 | 0 | 3 failures in round 1, fixed |

Agent counts are before merging; the severity table counts merged findings.

MVP: Architecture & Idioms (15 findings)

Key fixes applied:

1. Preview watches branding inputs created while it runs (FR-023), with a depth-0 root watcher because chokidar 4 reports one missing entry per directory (correctness, production, test suite).
2. Branded-site check ignores stale output: internal view only while enabled, `output.clean` in generated playbooks (correctness, production).
3. Stock Demo Platform notice recognized by its poweredBy link, so custom footers may name the Demo Platform (correctness).
4. Contract guards the include chain; per-needle unit tests and 35 real-bundle mutations (SC-007, test quality).
5. PDF printer waits for the inserted logo before its broken-image check (test suite regression).
6. New tests: PDF band raster check, script-carrying own SVG logo, accent and note-admonition CSS on every page, create intake and template guards, preview steps for late overlay and logo files.
7. Docs, scaffold comment, and design contract brought in line with the code.

Post-fix spec coverage: 32/32 requirements verified, none dropped.

Notable observations: 3 captured to brainstorm/idea-inbox.md.

Details: specs/002-antora-branding/review-findings.md

## Test Results

- `make test`: 615 passed (baseline 598).
- `make validate`: passed.
- `make test-adapters`: 101 passed, 0 failed (final run after round 2).

## Recommendations

### Critical (Must Fix)

None.

### Spec Evolution Candidates

- MINOR-36: decide whether `branding:` with a null value is an empty block (validation error) or no block.

### Optional Improvements

- The 20 open Minor findings in review-findings.md, mainly: refuse in-project symlinks into `.git`, `.guide`, `build`, or the internal part (MINOR-25); skip editor artifacts in `ui/supplemental/` (MINOR-29); a single source for adapter keys and the generated-file list (MINOR-18, MINOR-19); an end-to-end create run for US4 (MINOR-20).

## Conclusion

The implementation matches the spec. The review found nine Important issues (four behavior bugs, one latent PDF printer race, four test gaps against spec scenarios); all are fixed and covered by tests. The feature is ready for verification.
