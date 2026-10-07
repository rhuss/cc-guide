# Implementation Plan: Antora branding for guides

**Branch**: `002-antora-branding` | **Date**: 2026-10-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-antora-branding/spec.md`

## Summary

Let an Antora guide carry its own branding (logo text on the Red Hat logo layout or an own SVG, alt text, footer, favicon, accent color, plus a free overlay directory) from a `branding` block in `guide.yaml`, on both site views and the PDF title page, while unbranded guides stay byte-identical. The vendored toolkit's `playbook.py`, which every Antora build entry point already calls, validates the block and renders an overlay into `build/branding/<view>/ui/` that a generated playbook passes to Antora as `ui.supplemental_files`, on top of the pinned, unmodified RHDP bundle. A new `branding.py` module holds the schema, rendering, and the bundle contract checker; `check.py` verifies branded output; `print-pdf.mjs` adds the logo band; the create intake asks for branding.

## Technical Context

**Language/Version**: Python 3.11+ (PEP 723 scripts run with `uv run`), Node.js 20+ (ES modules), Bash, Markdown skills

**Primary Dependencies**: PyYAML (existing), Antora 3.2 with the RHDP showroom UI bundle v2.0.3 (existing, pinned), Playwright Chromium and js-yaml (existing), chokidar and browser-sync (existing). No new dependencies.

**Storage**: Files only: `guide.yaml` (input), `build/branding/<view>/` and `build/playbook*.yml` (ignored build output)

**Testing**: pytest through `make test` (`tests/toolkit/`), shell smoke tests through `make test-adapters` (`tests/adapters/`)

**Target Platform**: macOS and Linux author machines; guide builds in CI (the drift workflow)

**Project Type**: Claude Code plugin with a vendored toolkit (CLI scripts) and adapter scaffolds

**Performance Goals**: Rendering the overlay adds well under one second to a build (measured in `test_branding.py`: rendering a block with every key takes under one second)

**Constraints**: Unbranded guides byte-identical (SC-002); no build file change needed in existing guides (FR-029); the toolkit imports nothing from outside `tools/guide/`; no em or en dash characters in any file; the bundle is never forked or patched (FR-024)

**Scale/Scope**: One adapter (Antora), six branding keys, one overlay directory, both views and the PDF

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template, so the repository rules in `CLAUDE.md` serve as the gates:

| Gate | Status |
|---|---|
| No em dash or en dash characters; tests build them with `chr()` | Pass: plan artifacts checked; new tests follow the rule |
| `uv` instead of pip, podman instead of Docker | Pass: only `uv run` scripts; no container steps |
| No secrets, tokens, kubeconfig content, or raw inputs in guide projects, fixtures, run records | Pass: branding holds product names, URLs, and image paths only |
| Outward actions only after approval | Pass: no outward action in the feature; create's existing remote and push gates are unchanged |
| Subagents without a model override | Pass: no new dispatch |
| Commits end with `Assisted-By: 🤖 Claude Code` | Pass: applies to implementation commits |
| Scripts never `cd` into `.guide/cache/` | Pass: branding never touches the cache |
| Toolkit self-contained (no imports from outside its directory) | Pass: `branding.py` reads its templates from `tools/guide/branding/`, vendored by the scaffold script (R10) |

Post-design re-check: Pass (no new gate concerns from the contracts).

## Project Structure

### Documentation (this feature)

```text
specs/002-antora-branding/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── branding-config.md
│   ├── branding-build.md
│   └── bundle-contract.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
guide/
├── adapters/
│   ├── antora/
│   │   ├── adapter.yaml               # + branding: [logo_text, logo, logo_alt, footer, favicon, color]
│   │   └── branding/                  # NEW, vendored to tools/guide/branding/
│   │       ├── logo-text.svg.tmpl     # derived from the bundle's logo-demo-platform.svg (MPL-2.0 notice)
│   │       ├── contract.yaml          # bundle contract and accent selectors
│   │       └── NOTICE.md              # MPL-2.0 attribution for the derived template
│   ├── mkdocs/adapter.yaml            # + branding: []
│   └── gfm/adapter.yaml               # + branding: []
├── toolkit/
│   ├── branding.py                    # NEW: schema checks, check_guide, resolve, render, logo_svg, contract checker, CLI
│   ├── guidecfg.py                    # + branding in GUIDE_KEYS (raw block on Guide), Adapter.branding, branding lines and warnings in validate
│   ├── playbook.py                    # + validate, render, generated playbook (absolute paths) for branded/overlaid guides
│   ├── mkdocs_macros.py               # + stop the MkDocs build on branding problems (FR-009, FR-010)
│   ├── attrs.py                       # + `regions` stops the gfm build on branding problems (FR-009, FR-010)
│   ├── check.py                       # + branded-site check (FR-032)
│   ├── print-pdf.mjs                  # + logo band on the title page
│   ├── preview-watch.mjs              # + watch ui/, branding/, logo and favicon paths
│   └── VERSION                        # 0.2.0
├── scripts/scaffold-project.sh        # + copy adapters/<format>/branding/ to tools/guide/branding/
├── templates/guide.yaml               # + commented branding block with the Red Hat logo note
├── skills/create/SKILL.md             # + Antora branding intake question, own files copied to branding/
├── skills/evolve/SKILL.md             # + note: branding available after the toolkit refresh
├── docs/branding.md                   # NEW: author documentation (keys, overlay, Red Hat logo note, contract)
├── docs/adapters.md                   # + branding row
└── .claude-plugin/plugin.json         # version 0.2.0

.claude-plugin/marketplace.json        # plugin entry version 0.2.0
CLAUDE.md                              # layout bullet: optional adapters/<format>/branding/

tests/
├── toolkit/
│   ├── test_branding.py               # NEW
│   ├── test_guidecfg.py               # + branding cases
│   ├── test_playbook.py               # + generated playbook cases, unbranded unchanged
│   ├── test_check.py                  # + branded-site check cases
│   ├── test_scaffold_project.py       # + branding/ vendored in full and --toolkit-only mode
│   ├── test_mkdocs_macros.py          # + branding block stops the MkDocs build
│   └── test_attrs.py                  # + branding block stops `regions` (gfm build)
├── adapters/
│   ├── test_antora_branding.sh        # NEW: end to end, PDF, contract on the real bundle, SC-002, SC-004, refresh
│   ├── measure_logo.mjs               # NEW: Playwright measurement for SC-004
│   └── test_preview_antora.sh         # + branding change triggers a rebuild
└── manual/002-antora-branding.md      # NEW: recorded quickstart run (T040)
```

**Structure Decision**: Keep all runtime logic in the vendored toolkit (so a toolkit refresh delivers it to existing guides) and the Antora-specific templates and contract in the Antora adapter (vendored next to the toolkit by the scaffold script). `branding.py` finds them in `tools/guide/branding/` inside a guide project and in `guide/adapters/antora/branding/` inside the plugin source tree (the lookup pattern `runs.py` and `upstream.py` use for their templates), so the pytest suite runs against the source tree. No scaffold file (Makefile, `site.yml`) changes.

## Implementation Phases

1. **Foundation**: adapter `branding` lists; `branding.py` schema checks, `check_guide`, and `resolve`; `guidecfg.py` integration (key, raw block, adapter capability, branding lines and warnings in `validate`); MkDocs and gfm builds stop on a branding block. Tests first (`test_branding.py` validation cases, `test_guidecfg.py`, `test_mkdocs_macros.py`, `test_attrs.py`).
2. **Rendering and playbook (US1, US2)**: logo template and `logo_svg` sizing; helper, footer, head partials, CSS; overlay merge with precedence and atomic swap; `playbook.py` generation (absolute content, output, bundle, and extension paths, because the generated playbook lives in `build/`); scaffold script copies `branding/`. Tests: rendering and escaping units, playbook cases, unbranded unchanged.
3. **Guide check and contract (US7, FR-032)**: `contract.yaml`, checker and CLI; `check.py` branded-site check.
4. **PDF (US3)**: `branding.json`, band and embedded logo in `print-pdf.mjs`.
5. **Preview, create, evolve, docs (US4, US5, US6)**: watcher paths; create intake; evolve note; `templates/guide.yaml`; `docs/branding.md`, `docs/adapters.md`; versions.
6. **End-to-end validation**: `test_antora_branding.sh`, `measure_logo.mjs`, preview test; run `make test`, `make test-adapters`, `make validate`.

## Complexity Tracking

No gate violations.
