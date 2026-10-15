# Implementation Plan: Neutral Red Hat inspired branding for new guides

**Branch**: `003-neutral-branding` | **Date**: 2026-10-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-neutral-branding/spec.md`

## Summary

Give new Antora guides a neutral, Red Hat inspired look instead of the Red Hat Demo Platform branding. Two new `branding` keys do it: `wordmark` (a text logo without the Red Hat hat) and `theme: neutral` (vendored Red Hat fonts and a red rule under the navigation bar). Logo text is rendered as Red Hat Display outlines with fontTools, so the logo no longer depends on the reader's installed fonts. Everything rides on the spec 002 overlay renderer in `branding.py`; `/guide:create` writes the preset, choosing hat or wordmark from one question. Guides without `theme` build byte-identical to today.

## Technical Context

**Language/Version**: Python 3.11+ (PEP 723 scripts run with `uv run`), Node.js 20+ (ES modules), Bash, Markdown skills

**Primary Dependencies**: PyYAML (existing); fontTools 4.67.0 with the `woff` extra (brotli), NEW, declared only in `branding.py` and `playbook.py` and imported lazily (research R4); Antora 3.2 with the pinned RHDP showroom UI bundle v2.0.3 (existing, unchanged); Playwright Chromium (existing). Red Hat font release 5.0.0 (OFL-1.1), vendored as six variable `woff2` files.

**Storage**: Files only: `guide.yaml` (input), vendored fonts and manifest under `tools/guide/branding/fonts/`, rendered output in `build/branding/<view>/` (ignored)

**Testing**: pytest through `make test` (`tests/toolkit/`); shell plus Playwright smoke tests through `make test-adapters` (`tests/adapters/`)

**Target Platform**: macOS and Linux author machines; guide builds in CI (drift workflow)

**Project Type**: Claude Code plugin with a vendored toolkit (CLI scripts) and adapter scaffolds

**Performance Goals**: Outline rendering adds under 0.5 s to a build (spike: 0.13 s per logo including font load)

**Constraints**: Byte-identical output for guides without `theme` (SC-004); deterministic logo bytes (FR-009); toolkit imports nothing from outside `tools/guide/`; no network at build or print time beyond `uv` resolving declared dependencies; added site weight at most 300 KB (SC-005, measured 227 KB); no em or en dash characters in any file

**Scale/Scope**: One adapter (Antora), two new keys, six font files, one generated stylesheet, both views and the PDF, create and evolve skill text

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, so the repository rules in `CLAUDE.md` serve as the gates:

| Gate | Status |
|---|---|
| No em dash or en dash characters; tests build them with `chr()` | Pass: artifacts checked; tests that need CJK or dash input build it from code points |
| `uv` instead of pip, podman instead of Docker | Pass: fontTools comes through PEP 723 headers resolved by `uv run`; no container steps |
| No secrets, tokens, kubeconfig content, or raw inputs in guide projects, fixtures, run records | Pass: fonts, a manifest, and product names only |
| Outward actions only after approval | Pass: no outward action; the font download happens once, by a maintainer script run by hand, and its output is committed |
| Subagents without a model override | Pass: no new dispatch |
| Commits end with `Assisted-By: 🤖 Claude Code` | Pass: applies to implementation commits |
| Scripts never `cd` into `.guide/cache/` | Pass: branding never touches the cache |
| Toolkit self-contained | Pass: fonts and manifest vendored to `tools/guide/branding/fonts/` by the existing scaffold copy of `adapters/antora/branding/`; the maintainer script is excluded from the copy |

Post-design re-check: Pass. The one new third-party dependency (fontTools) is pinned exactly, confined to the two rendering scripts, and imported lazily, so validation-only scripts keep their environments (R4).

## Project Structure

### Documentation (this feature)

```text
specs/003-neutral-branding/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── branding-config.md
│   ├── theme-build.md
│   └── bundle-contract.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
guide/
├── adapters/
│   └── antora/
│       ├── adapter.yaml                 # + wordmark, theme in branding:
│       └── branding/
│           ├── contract.yaml            # + font-stacks, navbar-rule, navbar-css
│           ├── NOTICE.md                # + Red Hat fonts (OFL-1.1), outlined text note
│           └── fonts/                   # NEW, vendored to tools/guide/branding/fonts/
│               ├── fonts.yaml           # manifest: release, checksums, axes, Display coverage
│               ├── OFL.txt
│               ├── RedHat{Display,Text,Mono}{,-Italic}-VF.woff2
│               └── update-fonts.py      # maintainer script, excluded from the vendored copy
├── toolkit/
│   ├── branding.py                      # + keys, validation, manifest, outline renderer, theme overlay, branding.json fields
│   ├── playbook.py                      # + fonttools in the PEP 723 header (it calls render)
│   ├── check.py                         # + neutral theme check (FR-026)
│   ├── print-pdf.mjs                    # + neutral typography from branding.json font_faces, band rule
│   └── VERSION                          # 0.4.0
├── scripts/scaffold-project.sh          # exclude fonts/update-fonts.py from the branding copy
├── templates/guide.yaml                 # + wordmark and theme in the commented example
├── skills/create/SKILL.md               # step 5 rewritten (Red Hat product question)
├── skills/evolve/SKILL.md               # + 0.4.0 note
├── docs/branding.md                     # neutral theme, wordmark, RHDP opt-out, opening corrected
└── .claude-plugin/plugin.json           # 0.4.0

.claude-plugin/marketplace.json          # 0.4.0

tests/
├── toolkit/
│   ├── test_branding.py                 # + validation, outline golden files, theme overlay, manifest checksums
│   ├── test_playbook.py                 # + neutral overlay reaches the generated playbook
│   ├── test_check.py                    # + neutral theme check cases
│   └── test_scaffold_project.py         # + fonts vendored, update-fonts.py excluded
├── fixtures/branding/                   # NEW: golden wordmark.svg and logo-text-neutral.svg
├── adapters/
│   ├── test_antora_neutral.sh           # NEW: end to end build, Playwright font and navbar checks, PDF fonts, SC-004
│   └── measure_neutral.mjs              # NEW: Playwright probe (fonts loaded, navbar shadow and height)
└── manual/003-neutral-branding.md       # NEW: recorded create intake run
```

**Structure Decision**: Same split as spec 002. Runtime logic stays in the vendored toolkit (`branding.py`), so a toolkit refresh delivers it; Antora-specific assets (fonts, manifest, contract) live in the adapter's `branding/` directory, which `scaffold-project.sh` already vendors as a whole. `branding.asset_dir()` already finds that directory in both the guide project and the plugin source tree, so tests run against the source tree. No scaffold Makefile or playbook changes.

## Implementation Phases

1. **Assets**: `update-fonts.py`; run it once for release 5.0.0; commit fonts, `OFL.txt`, `fonts.yaml`; NOTICE; scaffold exclusion. Tests: manifest checksums match files; scaffold vendors fonts and skips the maintainer script.
2. **Configuration (FR-001 to FR-005, FR-011, FR-016)**: `KEYS`, adapter list, exclusivity, `wordmark` length rules, `theme` values, glyph coverage from the manifest, font presence and checksum checks, `Resolved` fields and alt default. Tests first in `test_branding.py`.
3. **Outline renderer (FR-006 to FR-010)**: lazy fontTools import, instancing, path drawing, wordmark SVG, neutral `logo_text` SVG; stock path untouched. Golden SVG tests; determinism test; stock byte-identity test against the existing golden output.
4. **Theme overlay (FR-012 to FR-015, FR-017, FR-020)**: fonts and `theme-neutral.css` into the overlay, `head_meta` theme flag, `generated_files` entries, `branding.json` fields; fontTools in `playbook.py` header. Tests in `test_branding.py` and `test_playbook.py`.
5. **Checks and contract (FR-026 to FR-028)**: `check.py` neutral check; three contract rules. Tests in `test_check.py`; contract run against the pinned bundle in the adapter test.
6. **PDF (FR-018, FR-019)**: `print-pdf.mjs` neutral typography and band rule.
7. **Create, evolve, docs, versions (FR-021 to FR-025, FR-029 to FR-031)**: skill text, template, `docs/branding.md`, versions 0.4.0.
8. **End-to-end validation**: `test_antora_neutral.sh` with `measure_neutral.mjs`, SC-004 comparison, PDF font check; `make test`, `make test-adapters`, `make validate`; manual create run recorded.

## Complexity Tracking

No gate violations. One new dependency (fontTools), justified in research R3 and confined by R4.
