# Implementation Plan: Embedded guide with the README as front page

**Branch**: `005-embedded-guide` | **Date**: 2026-11-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-embedded-guide/spec.md`

## Summary

Add an embedded mode for gfm guides: the guide project lives in one subdirectory of the repository it documents, the host's root README is the guide's front page, and the host repository is a pinned source `self`. The toolkit learns an `embedded` block in `guide.yaml`, treats the front page as a page everywhere through `guidecfg.pages()`, reads `self` from the local repository without cloning it into the host, records per-file blob fingerprints so drift survives squash merges, and gains a pull request mode in `drift.py`. A new `embed.py` handles the deterministic parts of consolidation (inventory, applying an approved move plan, stubs, retargeting, staging the front page for site and PDF builds). The create, evolve, preflight, preview, and page-task skills get an embedded branch, and two workflow templates (scheduled drift, pull request check) run from the guide subdirectory. Separate guides and the Antora and MkDocs formats stay unchanged.

## Technical Context

**Language/Version**: Python 3.11+ (PEP 723 scripts run with `uv run`), Bash, Lua (pandoc filters), Node.js 20+ (unchanged scripts), Markdown skills

**Primary Dependencies**: PyYAML (existing), git CLI, pandoc 3+, markserv, Playwright Chromium (all existing). No new dependencies.

**Storage**: Files only: `guide.yaml`, `baseline.yaml`, `inputs.yaml`, git-ignored `confidential.local.yaml`, run-local `move-plan.yaml`, the `self` snapshot under `${XDG_CACHE_HOME:-~/.cache}/cc-guide/self/`

**Testing**: pytest through `make test` (`tests/toolkit/`), shell smoke tests through `make test-adapters` (`tests/adapters/`), a manual Claude Code run recorded in `tests/manual/`

**Target Platform**: macOS and Linux author machines; GitHub Actions (`ubuntu-latest`) for the workflows

**Project Type**: Claude Code plugin with a vendored toolkit (CLI scripts), adapter scaffolds, and skills

**Performance Goals**: The pull request check finishes in under one minute on a repository with a few thousand files (blob comparisons only, no clones); staging adds well under one second to a build.

**Constraints**: Standalone guides byte-identical in output and build files (SC-008, FR-029); toolkit imports nothing outside `tools/guide/`; no em or en dash characters in any file; no copy of the host code inside the host repository; no confidential data in committed files; every outward action approved.

**Scale/Scope**: One adapter (gfm), one new toolkit module, changes to seven toolkit modules, four pandoc/Make files, two workflow templates, six skills, plugin docs and contracts.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is an unfilled template, so the gates are the repository rules in `CLAUDE.md`:

| Gate | Status |
|---|---|
| No em or en dash characters in any file; tests build them with `chr()` | Pass (design adds none; the dash check extends to the front page) |
| `uv` instead of pip, podman instead of Docker | Pass (no container steps; scripts run with `uv run`) |
| No secrets, kubeconfig content, or raw inputs in guide projects, fixtures, or run records | Pass (R9 moves confidential terms and locations to a git-ignored file; inputs are never copied) |
| Outward actions shown in full and run only after approval | Pass (move plan approval, workflow install on opt-in, no remote creation, pushes stay opt-in) |
| Subagents without model override | Pass (skills unchanged in this respect) |
| Never `cd` into `.guide/cache/`; git there only through `git -C` | Pass (`self` is never placed in `.guide/cache/`; all host reads use `git -C <toplevel>`) |
| Toolkit self-contained | Pass (`embed.py` imports only toolkit modules) |
| Never commit `.mcp.json` | Pass (untouched) |

Post-design re-check: pass; no violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/005-embedded-guide/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── toolkit-cli.md
│   ├── workflows.md
│   └── front-page.md
└── tasks.md            # next stage
```

### Source Code (repository root)

```text
guide/
├── toolkit/
│   ├── guidecfg.py        # embedded block, discover, confidential.local.yaml, self/fingerprints, inputs self:/local:
│   ├── fetch.py           # self from the local repo, read-tree/checkout-index snapshot, where, fingerprints in pin/rebaseline
│   ├── sources.py         # self git dir, self-citation helper
│   ├── drift.py           # fingerprint mode, --pr, --source, _rel fix, local: masking, recorded inputs
│   ├── check.py           # front page, stubs, developer README, self-citation ban, structure via front page
│   ├── attrs.py           # front page regions, self links at the tracked branch
│   ├── ledger.py          # embedded ledger location
│   ├── upstream.py        # own remotes via git toplevel
│   └── embed.py           # NEW: inventory, apply, retarget, stage, front-page-status
├── adapters/gfm/
│   ├── adapter.yaml       # comment update only
│   ├── embedded/docs/README.md   # NEW: pointer page
│   └── scaffold/
│       ├── Makefile       # staging, regions, preview when embedded
│       └── pandoc/render.sh, print.sh   # docs directory parameter (default docs)
├── scripts/scaffold-project.sh   # --embedded
├── templates/
│   ├── guide.yaml         # commented embedded block
│   ├── guide-drift.yml    # {{GUIDE_DIR}}
│   ├── guide-pr-check.yml # NEW
│   ├── confidential.local.yaml   # NEW example
│   └── run-summary.md     # dropped claims section
├── skills/
│   ├── create/SKILL.md    # embedded branch, consolidation section
│   ├── evolve/SKILL.md    # discover, hand edits, retarget, fingerprints
│   ├── preflight/SKILL.md # discover, embedded= result
│   ├── preview/SKILL.md   # open README.md
│   └── page-task/         # front-page-contract.md (NEW), registration in SKILL.md and templates
└── docs/
    ├── embedded.md        # NEW author documentation
    └── adapters.md        # embedded row

tests/
├── toolkit/
│   ├── test_embed.py      # NEW
│   ├── test_guidecfg.py, test_fetch.py, test_drift.py, test_check.py, test_attrs.py   # embedded cases
│   └── test_scaffold_project.py
├── fixtures/mini-host/    # NEW host repository fixture
├── adapters/test_gfm_embedded.sh   # NEW
└── manual/                # recorded embedded run (after implementation)

README.md                  # format table and embedded mode mention
specs/001-cc-guide-plugin/contracts/*.md   # adapter, commands, page conventions updates
```

**Structure Decision**: Extend the existing plugin layout; all toolkit logic for consolidation and staging goes into one new module (`embed.py`) so the other modules only gain small, mode-gated branches.

## Implementation phases

1. **Configuration and discovery** (guidecfg): embedded block, validation, discover, local confidential file, baseline `self` and fingerprints schema, inputs `self:`/`local:`. Foundation for everything else.
2. **Self source** (fetch, sources, attrs): local reads, snapshot export, `where`, fingerprints in pin and rebaseline, branch links.
3. **Front page as a page** (guidecfg.pages, drift._rel, check, attrs regions, structure check, self-citation ban, stubs, developer README).
4. **Drift** (fingerprint mode, recorded inputs, local masking, `--source`, `--pr`).
5. **Consolidation** (`embed.py inventory`, `apply`, `retarget`, `front-page-status`).
6. **Build** (`embed.py stage`, render.sh/print.sh parameter, Makefile branches, preview, scaffold `--embedded`, pointer page).
7. **Workflows** (templates).
8. **Skills** (preflight, create, evolve, preview, page-task front page contract, upstream own remotes).
9. **Docs and contracts**, adapter smoke test, regression run of all existing tests.

## Complexity Tracking

No constitution violations.
