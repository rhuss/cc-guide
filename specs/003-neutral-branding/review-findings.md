# Deep Review Findings

**Date:** 2026-10-15
**Branch:** 003-neutral-branding
**Rounds:** 1 fix round plus a narrowed re-review, then the re-review's minor findings
**Gate Outcome:** PASS
**Invocation:** quality-gate (after `/speckit-implement`), external tools disabled (`--no-external`: CodeRabbit and Codex would send the code to external services without the author's approval)

## Summary

| Severity | Found | Fixed | Remaining |
|----------|-------|-------|-----------|
| Critical | 0 | 0 | 0 |
| Important | 3 | 3 | 0 |
| Minor | 23 | 23 | 0 |
| Notable | 3 | 3 | 0 |
| **Total** | **29** | **29** | **0** |

Counts are after deduplication (the damaged-manifest crash was reported by correctness and production readiness; the font-load rejection in print-pdf likewise).

**Agents completed:** 5/5 internal (Correctness, Architecture and Idioms, Security, Production Readiness, Test Quality), run one at a time (teams extension off), plus one combined re-review of fix round 1.
**Skipped:** Goal Alignment (no pull request yet); CodeRabbit, Copilot, Codex (disabled for this run).

## Findings

### FINDING-1 (Important, test-quality): logos could clip glyph ink
- **File:** guide/toolkit/branding.py (`wordmark_svg`, `logo_svg` neutral), tests/toolkit/test_branding_neutral.py
- **What was wrong:** The viewBox width was the advance width, and the tests compared it with the same number. A wordmark starting with "j" drew at x = -3.29, outside the viewBox; glyphs such as "ľ" or "\" put ink past their advance.
- **Why it matters:** The spec edge case "the logo never clips" was not met for real Red Hat Display glyphs.
- **Resolution (round 1, completed after the re-review):** `_outline` returns the horizontal ink extent; the wordmark shifts right by the left overhang and its width covers both the advance and the ink; the hat variant's width covers the ink too. Tests parse every path coordinate and assert the ink lies inside the viewBox for "jOpenClaw", 40 × "W", "fy", "j", and two texts that really overhang on the right (a guard test keeps them overhanging).

### FINDING-2 (Important, test-quality): Red Hat Mono and the body font were not checked in the browser
- **File:** tests/adapters/test_antora_neutral.sh, tests/adapters/measure_neutral.mjs
- **Resolution:** The probe result must contain Red Hat Text, Display, and Mono faces loaded with Google Fonts blocked, and the body's computed font must start with "Red Hat Text".

### FINDING-3 (Important, test-quality): the PDF check was a weak proxy and the failure path was untested
- **File:** tests/adapters/test_antora_neutral.sh
- **Resolution:** The check requires at least three distinct Type3 font programs and no font other than Helvetica (footer and admonition labels). Chromium embeds variable fonts as unnamed Type3 fonts, so families cannot be told apart in the PDF; the browser probe proves all three load, and the message says exactly what is checked. A truncated `RedHatMono-VF.woff2` must stop `make print-pdf` with `vendored fonts failed to load: Red Hat Mono normal (RedHatMono-VF.woff2)`.

### Minor findings (all fixed in round 1 or after the re-review)

| # | Source | File | Finding | Resolution |
|---|---|---|---|---|
| 4 | correctness, production readiness | branding.py | A damaged `fonts.yaml`, a malformed entry, or a missing `tools/guide/branding/` crashed every entry point with a traceback | `check_fonts` reports `unreadable (<detail>); refresh the toolkit ...` or `missing`; `load_manifest` validates the shape; tests cover five damaged manifests and a missing directory |
| 5 | correctness, production readiness | print-pdf.mjs | A corrupt face rejected `Promise.all` with a generic NetworkError; no time bound | Each face settles on its own within 15 s; the error names face, file, and reason, and asks for a toolkit refresh |
| 6 | correctness | check.py | No fallback when no page of a view has the header | Covered by `check_branded_site` ("no page shows the branded logo"); after the re-review the neutral check no longer repeats it, and a test pins the single violation |
| 7 | security | update-fonts.py | Trust on first use: tag downloads, no comparison with recorded hashes, files overwritten before parsing, `--release` unvalidated | Downloads come from the tag's resolved commit into a temporary directory; every font is parsed before anything is copied; a recorded release refuses a moved tag or any changed checksum (fonts and `OFL.txt`); `--release` is validated |
| 8 | security | branding.py | `--` was allowed in the release that goes into an SVG comment | `RELEASE_RE` no longer allows repeated separators, in both scripts |
| 9 | architecture | branding.py, check.py | The font file list was built three times; check.py used a private helper | Public `font_files()` used everywhere |
| 10 | architecture | check.py | View and page selection duplicated, diverging on invalid blocks | The neutral check returns early on block problems like `check_branded_site` |
| 11 | architecture | branding.py | No-op conditional around `head_meta`; bool and string both called `theme` | One call; the bool is `neutral` |
| 12 | architecture | branding.py | Dead `LOGO_KEYS`, unused `check_fonts(manifest=...)` | `LOGO_KEYS` drives the exclusivity check; the parameter is gone |
| 13 | architecture | branding.py | Neutral path rebuilt the template's text attributes from constants silently | `TEXT_ATTRS` must all appear on the template's `<text>` element, or rendering fails loudly; `TEXT_Y`, `TEXT_FILL`, `LOGO_HEIGHT` sit with the other geometry constants |
| 14 | architecture | docs/branding.md | "The whole PDF uses the vendored fonts" overclaimed | Names what uses them and that labels and the footer keep Helvetica |
| 15 | production readiness | playbook.py, docs | Declaring fontTools on `playbook.py` makes the first Antora build after a refresh resolve it from PyPI | Kept (only `playbook.py` renders); docs/branding.md states that the first build after the refresh needs PyPI access |
| 16 | test quality | test_antora_neutral.sh | Stock reference not asserted | Stock page must make a blocked Google request and load no Red Hat face (positive control) |
| 17 | test quality | test_branding_neutral.py | Spec weights only via constants | Literal 500 and 700, and the logo paths equal `outline(text, 500/700)` |
| 18 | test quality | test_branding_neutral.py | Manifest values not tied to the font files | Weights, styles, families, and coverage compared with fontTools readings |
| 19 | test quality | (none) | SC-005 only recorded by hand | Unit test for the 300 KB budget |
| 20 | test quality | test_branding_neutral.py | Emoji, markup in outlined text, and author font files untested | Tests for U+1F600, well-formed SVG without markup, and `ui/supplemental/font/` shadowing |
| 21 | test quality | test_branding.py | FR-024 template content untested; FR-025 evolve text untested | Template must show `theme: neutral` and `wordmark:`; evolve text must name both keys |
| 22 to 26 | re-review | as above | right-overhang branch untested; PDF message overclaimed; duplicate no-header violation; `--` in release; moved tag and OFL not refused | Fixed as listed in rows 1, 3, 6, 7, 8 |

## Notable Observations

All three were acted on, so none went to the idea inbox:

- **NOTABLE-1 (correctness, test quality):** `_INSTANCES` cached the instanced font by weight only. Now keyed by font path and modification time; a test proves a changed file is reread.
- **NOTABLE-2 (security):** manifest values reached file paths, CSS, an SVG comment, and the printer unvalidated. Now validated in `load_manifest`.
- **NOTABLE-3 (test quality):** fixture isolation for the font cache. Resolved by NOTABLE-1's keying.

## Post-Fix Spec Coverage

No requirement lost code in the fix round (one helper, `_font_names`, was replaced by the public `font_files`). FR-001 to FR-031 verified again: `make test` 733 passed before the re-review fixes and the targeted suites pass after them; `test_antora_neutral.sh` passed 23 checks after round 1.

## Test Suite Results

| Round | Test Command | Result |
|-------|-------------|--------|
| 1 | `make test` | 733 passed |
| 1 | `bash tests/adapters/test_antora_neutral.sh` | 23 passed, 0 failed |
| re-review fixes | pytest on test_branding_neutral.py, test_check.py, test_branding.py | all passed |

## Remaining Findings

None.
