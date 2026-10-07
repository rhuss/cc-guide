# Deep Review Findings

**Date:** 2026-10-07
**Branch:** 002-antora-branding
**Rounds:** 2 (round 1 fixed every Critical and Important finding; round 2 applied follow-ups from the re-review)
**Gate Outcome:** PASS
**Invocation:** quality-gate (speckit-spex-ship, stage review-code)

## Summary

| Severity | Found | Fixed | Remaining |
|----------|-------|-------|-----------|
| Critical | 0 | 0 | 0 |
| Important | 9 | 9 | 0 |
| Minor | 36 | 16 | 20 |
| Notable | 5 | - | 5 |
| **Total** | **50** | **25** | **25** |

Findings with the same root cause were merged across agents (the "also reported by" field names them); counts above are after merging.

**Agents completed:** 5/5 internal (correctness, architecture, security, production readiness, test quality) plus one re-review agent for round 2. Goal alignment: skipped (no pull request for the branch).
**External tools:** CodeRabbit completed (3 runs: the feature diff, round 1, round 2; 0 findings each). Copilot skipped (disabled in config). Codex failed (usage limit reached, no findings recorded).

## Findings

### FINDING-1
- **Severity:** Important
- **Confidence:** 90
- **File:** guide/toolkit/preview-watch.mjs (brandingPaths, watcher setup)
- **Category:** correctness
- **Source:** correctness-agent (also reported by: production-readiness-agent, test-quality-agent, stage 1 spec compliance)
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:**
The preview handed chokidar only branding inputs that existed when it started (`existsSync` filter) and recomputed the list only when guide.yaml changed. A `ui/supplemental/` created during the preview, a `branding/` directory created later, or a logo file copied in after guide.yaml named it never triggered a rebuild.

**Why this matters:**
FR-023 requires a rebuild when the branding block, a named logo or favicon file, or a file in the overlay directory changes. The common sequence "name the logo in guide.yaml, then copy the file in" left the preview on a failed build until guide.yaml was touched again.

**How it was resolved:**
The first fix (pass missing paths to chokidar) passed the unit level but the new smoke test step failed: chokidar 4.0.3 throttles `readdir` per directory and reports only one missing entry per parent. The final fix splits the inputs with `watchPlan()`: existing inputs join the main watch; a missing input whose topmost missing ancestor is a direct child of the guide root is reported by a second, depth-0 watcher on the root and then joins the main watch; a missing input deeper down is covered by watching its nearest existing directory. The preview smoke test now creates `ui/supplemental/` after start, edits an overlay file, names a logo in a missing `assets/` directory, creates it, and edits it; every step rebuilds.

### FINDING-2
- **Severity:** Important
- **Confidence:** 80
- **File:** guide/toolkit/check.py (check_branded_site); guide/toolkit/playbook.py
- **Category:** correctness
- **Source:** correctness-agent (also reported by: production-readiness-agent)
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:**
The FR-032 check read every page under `build/site` and `build/site-internal`, including output the current build did not produce: `build/site-internal` left over after the internal part was disabled, and orphan pages of renamed pages (Antora does not clean its output directory by default).

**Why this matters:**
US5 (adopting branding in a guide that was built before) produced "header does not show the branded logo" and "no page shows the branded logo" on stale pages, which blocked `make check`, `make pdf`, and `make dist` with a misleading message.

**How it was resolved:**
The internal view is checked only while the internal part is enabled, and the playbook generated for a branded or overlaid guide sets `output.clean: true`, so no page of an earlier build survives. Unbranded guides keep the committed playbook (FR-001, SC-002 unchanged; the smoke test still shows byte-identical output). Tests cover both cases.

### FINDING-3
- **Severity:** Important
- **Confidence:** 80
- **File:** guide/toolkit/check.py (footer notice detection)
- **Category:** correctness
- **Source:** correctness-agent
- **Round found:** 1
- **Resolution:** fixed (round 1, refined in round 2)

**What is wrong:**
Any footer that contained "Demo Platform" or "demo.redhat.com" counted as the leftover stock notice, so an allowed custom footer such as "Order this lab on Red Hat Demo Platform" failed `make check` on every page.

**Why this matters:**
FR-005 allows any footer text; such a guide could never be exported.

**How it was resolved:**
The stock notice is recognized by its `class="poweredBy"` link (now also a contract needle). Notice text alone still fails for foreign footers (a replaced bundle), but not for the footer generated from `branding.footer` (`class="guide-footer"`) or, on pages whose header shows the branded logo, the author's own `footer-content.hbs` overlay. Tests cover the custom footer, a foreign footer, the own partial, and the replaced-bundle case.

### FINDING-4
- **Severity:** Important
- **Confidence:** 80
- **File:** guide/adapters/antora/branding/contract.yaml; tests/toolkit/test_branding.py
- **Category:** test-quality
- **Source:** test-quality-agent
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:**
SC-007 requires that removing any one relied-upon part of the bundle fails the contract. A copy of the pinned bundle with `{{> footer-content}}` inlined out of `footer.hbs`, or `{{> header-content}}` removed from `header.hbs`, passed. The unit test only removed the first needle of each rule.

**Why this matters:**
A bundle upgrade that restructures the include chain would silently disable the footer or logo branding while the guard stayed green.

**How it was resolved:**
New rules `layout-includes`, `layout-404-includes`, `header-include`, `footer-include`; unit tests for every needle of every rule and for the include chain; a smoke test step that applies 35 mutations to the real pinned bundle (every string, pattern, recorded content, file-only rule, accent and restore rule) and requires each to fail the rule that names it.

### FINDING-5
- **Severity:** Important
- **Confidence:** 85
- **File:** tests/toolkit/test_branding.py; tests/adapters/test_antora_branding.sh
- **Category:** test-quality
- **Source:** test-quality-agent
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:**
No test checked that note admonitions keep the stock blue (US6-2), and the color test derived its expectations from contract.yaml itself.

**Why this matters:**
Adding an admonition selector to the contract would have recolored note admonitions with every test green.

**How it was resolved:**
Unit assertions that no accent selector and no generated rule names admonitions; the smoke test checks the built `branding.css` for each spec-named rule with the expected values and that the bundle's `site.css` still colors `.doc .admonitionblock.note .icon` with `#06c`, on every page with a header. The correctness review also found that `branding.css` recolored a hovered active TOC entry; a restore rule now keeps it dark.

### FINDING-6
- **Severity:** Important
- **Confidence:** 85
- **File:** tests/adapters/test_antora_branding.sh
- **Category:** test-quality
- **Source:** test-quality-agent
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:**
The PDF checks only extracted text, so removing the `#151515` band (FR-025) or clipping the logo (SC-004) would have passed.

**Why this matters:**
A white logo on a white page still extracts as text.

**How it was resolved:**
`pdf_band` renders page 1 with pypdfium2 and requires a `#151515` band across most of the page with the light logo pixels inside it, clear of its edges; it runs for both views, the own logo, and the 40-character logo.

### FINDING-7
- **Severity:** Important
- **Confidence:** 80
- **File:** tests/adapters/test_antora_branding.sh
- **Category:** test-quality
- **Source:** test-quality-agent
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:**
No test used an own SVG logo with a script or event handler (FR-012, FR-026, edge case).

**Why this matters:**
A regression to inline markup in the PDF printer would go unnoticed.

**How it was resolved:**
The own-logo fixture now carries a `<script>`, an `onload` handler, and an `<image onerror>` handler that would rewrite every `h1`; inline insertion would run the `onerror` handler (verified in Chromium), an image does not. The test requires the title intact, no marker in the PDF, the band, and the site logo copied byte for byte and shown as `<img>` with its alt text.

### FINDING-8
- **Severity:** Important
- **Confidence:** 75
- **File:** guide/skills/create/SKILL.md; guide/templates/guide.yaml
- **Category:** test-quality
- **Source:** test-quality-agent
- **Round found:** 1
- **Resolution:** fixed (round 1; residual tracked as MINOR-20)

**What is wrong:**
Nothing covered US4, FR-028, or FR-030; the manual record lists the create intake as not run.

**Why this matters:**
The paused agentic-starter-kits guide resumes through this path.

**How it was resolved:**
Pytest guards: the template's commented branding example validates when uncommented, and the create intake keeps the Antora-only question, the Red Hat products statement, the own-file alt text rule, the excluded color and overlay, and the copy into `branding/`; the docs keep the FR-030 statement. An end-to-end create run (eval case or recorded manual run) remains open as MINOR-20.

### FINDING-9
- **Severity:** Important
- **Confidence:** 95
- **File:** guide/toolkit/print-pdf.mjs (broken-image check)
- **Category:** regression
- **Source:** test-suite (round 1 adapter smoke tests)
- **Round found:** 1
- **Resolution:** fixed (round 1)

**What is wrong:**
The printer inserts the branded logo as a data URL during the transform and checked `complete` and `naturalWidth` right afterwards. Chromium decodes the image asynchronously (even a plain SVG reports `complete=false` at that moment), so a larger logo failed with "images failed to load"; earlier runs passed by timing luck.

**Why this matters:**
`make pdf` could fail at random for a branded guide.

**How it was resolved:**
The printer waits (at most 15 s) for pending images to load or fail before judging them. The error message also shortens data URLs, so a failing logo no longer dumps its content into logs (security finding).

### Minor findings

| ID | File | Source | Description | Resolution |
|----|------|--------|-------------|------------|
| MINOR-1 | contract.yaml, branding.py | architecture | `exists` documented but never read; `exists: false` would be ignored | fixed: unknown keys and `exists` other than true are rejected |
| MINOR-2 | branding.py hover_shade | architecture | unreachable 3-digit color branch, duplicate regex | fixed |
| MINOR-3 | docs/branding.md | architecture | symlink rule, branding.json, "writes nothing" statements did not match code | fixed |
| MINOR-4 | scaffold site.yml | architecture | comment said only worktrees use the generated playbook | fixed |
| MINOR-5 | preview-watch.mjs | architecture | comments called `ui/` the overlay directory | fixed |
| MINOR-6 | check.py | architecture | `BRANDED_LOGO` duplicated `branding.LOGO_FILE`; view list duplicated | partially fixed (logo path shared; view mapping still duplicated) |
| MINOR-7 | contract.yaml | correctness | `branding.css` recolored a hovered active TOC entry | fixed (restore rule) |
| MINOR-8 | branding.py render, _swap | correctness | staged directory left behind on failure; swap error lost | fixed |
| MINOR-9 | check.py | correctness | crash on an invalid block when run directly | fixed (problems reported) |
| MINOR-10 | check.py | correctness | own overlay alt helper made every page fail | fixed (alt not compared then) |
| MINOR-11 | preview-watch.mjs | production | shadow warnings hidden on successful preview builds | fixed |
| MINOR-12 | test_check.py | test-quality | notice only in the internal view untested | fixed |
| MINOR-13 | test_antora_branding.sh | test-quality | footer link text unchecked | fixed |
| MINOR-14 | test_playbook.py | test-quality | worktree rendering content untested | fixed |
| MINOR-15 | test_branding.py | test-quality | 1 s wall-clock bound | fixed (5 s) |
| MINOR-16 | check.py | re-review | every branding problem reported against guide.yaml | fixed (round 2) |
| MINOR-17 | contracts/bundle-contract.md | re-review | design contract out of date after round 1 | fixed (round 2) |
| MINOR-18 | branding.py, guidecfg.py | architecture | adapter keys parsed twice, `DEFAULT_KEYS` copy, non-list value silently empty | open |
| MINOR-19 | branding.py | architecture | generated-file list kept in both `generated_files()` and `render()` | open |
| MINOR-20 | create skill | test-quality | no end-to-end create run (eval or manual) for US4 and the FR-028 file copy | open (residual of FINDING-8) |
| MINOR-21 | branding.py | architecture | stock favicon strings duplicated from contract.yaml | open |
| MINOR-22 | branding.py, playbook.py | architecture | validation runs several times per build | open |
| MINOR-23 | branding.py | architecture | parameter `adapter_keys` shadows the function of that name | open |
| MINOR-24 | branding.py | architecture | `logo_text` accepts numbers; `logo_alt` and `footer.text` do not | open |
| MINOR-25 | branding.py | security | symlinks resolving inside the project (for example to `.git/config` or `internal/`) are copied into the published UI | open (log dump part fixed) |
| MINOR-26 | branding.py | security | an own SVG is published as is; opened directly in a tab, its scripts run | open (docs now warn) |
| MINOR-27 | branding.py | production | temp directories of killed builds are not reclaimed | open (failure cleanup fixed) |
| MINOR-28 | playbook.py, branding.py | production | playbook written in place; short window where the overlay directory is missing | open |
| MINOR-29 | branding.py overlay_files | production | editor artifacts (dangling Emacs lock links fail validation; swap files and .DS_Store are copied) | open |
| MINOR-30 | check.py | production | one violation per page for a single UI-level cause | open |
| MINOR-31 | playbook.py | correctness | PyYAML 1.1 round trip changes `yes`/`off`/sexagesimal scalars in generated playbooks | open |
| MINOR-32 | test_antora_branding.sh | test-quality | FR-010 invalid block tested end to end only for `make site`, not the preview | open |
| MINOR-33 | test_antora_branding.sh | test-quality | no overlay file replacing a bundle file; no overlay-only end-to-end build | open (every-page checks fixed) |
| MINOR-34 | test_antora_branding.sh | test-quality | template hat and divider not compared with the bundle logo | open |
| MINOR-35 | test_antora_branding.sh | test-quality | SC-002 compares only the shareable PDF title page | open |
| MINOR-36 | branding.py load_block | stage 1 | `branding:` with a null value counts as no block (passes in a MkDocs guide) | open |

## Notable Observations

### NOTABLE-1
- **File:** guide/toolkit/guidecfg.py
- **Category:** architecture
- **Source:** architecture-agent
- **Description:** guidecfg imports branding at module level, and branding.py keeps its own guide.yaml and adapter.yaml readers.
- **Rationale:** The core loader now depends on a feature module; captured to brainstorm/idea-inbox.md.

### NOTABLE-2
- **File:** guide/toolkit/print-pdf.mjs, guide/toolkit/preview-watch.mjs
- **Category:** architecture
- **Source:** architecture-agent
- **Description:** The Node scripts hard-code the branding output layout, band color, and path-valued keys.
- **Rationale:** A second source of truth; captured to brainstorm/idea-inbox.md.

### NOTABLE-3
- **File:** guide/toolkit/attrs.py, mkdocs_macros.py, playbook.py
- **Category:** architecture
- **Source:** architecture-agent
- **Description:** The FR-010 guard lives in three unrelated modules, one per format.
- **Rationale:** A new adapter or entry point must remember a fourth place; captured to brainstorm/idea-inbox.md.

### NOTABLE-4
- **File:** guide/toolkit/check.py
- **Category:** correctness
- **Source:** re-review agent
- **Description:** The own-footer exemption applied to every page even when the overlay did not apply.
- **Rationale:** Addressed in round 2 (the exemption now needs a branded header on the same page).

### NOTABLE-5
- **File:** guide/toolkit/preview-watch.mjs
- **Category:** correctness
- **Source:** re-review agent
- **Description:** Confirms chokidar 4.0.3 reports only one missing entry per directory, so the committed `watchPlan()` design is required and the `assets/` smoke step is a real regression guard.
- **Rationale:** Informational.

## Post-Fix Spec Coverage

The fix rounds removed only dead code (`hover_shade` 3-digit branch) and replaced implementations in place. Every requirement still has its implementation:

| Requirement | Implementation | Status |
|-------------|---------------|--------|
| FR-001..FR-010 (configuration, validation in every build) | branding.py check/check_guide; guidecfg.validate; playbook.py; mkdocs_macros.py; attrs.py | ✓ |
| FR-011..FR-020 (site output, overlay, shadow warning) | branding.py render, logo_svg, alt_helper, footer_partial, head_meta, accent_css | ✓ |
| FR-021, FR-022 (build output only, linked worktrees) | branding.py render under build/; playbook.py | ✓ |
| FR-023 (preview rebuilds) | preview-watch.mjs brandingInputs, watchPlan, root watcher | ✓ |
| FR-024 (unmodified bundle) | playbook.py ui.supplemental_files only | ✓ |
| FR-025..FR-027 (PDF title page) | print-pdf.mjs readBrand, band CSS, image wait | ✓ |
| FR-028..FR-030 (create, evolve, docs) | skills/create, skills/evolve, docs/branding.md, templates/guide.yaml | ✓ |
| FR-031 (contract test) | contract.yaml, branding.py check_bundle, adapter smoke test | ✓ |
| FR-032 (check step) | check.py check_branded_site | ✓ |

All spec requirements verified after the fix loop.

## Test Suite Results

| Round | Test Command | Exit Code | Failures | Status |
|-------|-------------|-----------|----------|--------|
| baseline | make test | 0 | 0 | 598 passed |
| 1 | make test | 0 | 0 | 613 passed |
| 1 | make test-adapters | 2 | 3 | own-logo PDF (FINDING-9), preview logo file in a missing directory (2 steps, FINDING-1) |
| 1 (after fixes) | test_preview_antora.sh, test_antora_branding.sh | 0 | 0 | passed |
| 2 | make test | 0 | 0 | 615 passed |
| 2 | make validate | 0 | 0 | passed |
| 2 | make test-adapters | 0 | 0 | 101 passed |

The three round 1 smoke test failures came from the new tests and were fixed in the same round (they are FINDING-9 and part of FINDING-1).

## Remaining Findings

No Critical or Important findings remain. The 20 open Minor findings (MINOR-18 to MINOR-36, with MINOR-6 partly open) are listed above; none blocks the gate.
