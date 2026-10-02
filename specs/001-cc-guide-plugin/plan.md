# Implementation Plan: cc-guide, a plugin for source-verified guides

**Branch**: `001-cc-guide-plugin` | **Date**: 2026-10-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-cc-guide-plugin/spec.md`

## Summary

cc-guide is a Claude Code plugin (`guide`) with six commands: create, evolve, preview, export, upstream, and validate. It turns transcripts, notes, and pinned source repositories into a persona-split guide whose pages are verified against the sources task by task, and it keeps the guide current through a recorded baseline.

The plugin orchestrates the superpowers flow (brainstorming, writing-plans, subagent-driven development, final review) and contributes everything specific to guides:
- intake and source pinning
- page and review templates
- three output adapters (Antora, MkDocs Material, GitHub Markdown) behind one make-target contract
- a vendored, format-neutral toolkit for checks, drift, leak detection, PDF printing, and validation
- Excalidraw diagram rules
- an approval-gated upstream reporting flow

Deterministic logic lives in the toolkit, which create copies into each guide repository, so scheduled drift checks run in CI without Claude Code (research R4).

Terminology: the spec's "source reference block" (the per-page list of supporting sources, FR-010) is called "source block" for short in this plan and in tasks.md.

## Technical Context

**Language/Version**:
- Plugin behavior: Markdown command and skill definitions (Claude Code plugin format).
- Toolkit: Python 3.11+ scripts with PEP 723 inline metadata, run with `uv run`.
- Antora, Playwright, and preview: Node 20+.
- Make targets: Bash for thin glue.

**Primary Dependencies**:
- Runtime: superpowers 6.3.0 or later (required for create and evolve), the Excalidraw MCP server `yctimlin/mcp_excalidraw` 1.0.7 (diagrams only), cc-prose (optional).
- Adapters: Antora `~3.2` with `@antora/html-single-extension`; MkDocs Material `>=9.5,<9.8` with `mkdocs-macros-plugin` and `mkdocs-print-site-plugin ~=2.8`; Pandoc 3 and `markserv` for GitHub Markdown.
- Shared tooling: Playwright `^1.48` with Chromium, `js-yaml` (for `print-pdf.mjs`), PyYAML, `pypdf` (PDF leak check and tests), `git`, `gh`.
- Antora preview: `chokidar` and `browser-sync` (rebuild and reload in `antora-watch.mjs`).
- Antora UI: the RHDP showroom UI bundle (lightbox for `role=expand`); MkDocs: `mkdocs-glightbox`.
- Diagram check: Pillow (PNG crops) in `diagram_check.py`.

**Storage**: Files in the guide project: YAML (`guide.yaml`, `baseline.yaml`, `inputs.yaml`, `findings/upstream.yaml`), Markdown run summaries, and content pages. Run state is local and git-ignored. See [data-model.md](data-model.md).

**Testing**:
- `pytest` (via `uv run`) for the toolkit.
- Shell smoke tests per adapter on a fixture guide.
- `claude plugin validate` for manifests.
- agent-eval-harness cases (`eval.yaml`, `eval/cases/`) for review, upstream, and classifier behavior.
- Manual end-to-end scenarios in [quickstart.md](quickstart.md).

**Target Platform**: macOS and Linux author machines running Claude Code; GitHub Actions `ubuntu-latest` for the drift workflow.

**Project Type**: Claude Code plugin plus a vendored command-line toolkit and format adapters.

**Performance Goals**:
- Preview of a 25-page guide in under 1 minute (SC-008).
- PDF of a 25-page guide in under 3 minutes (SC-011).
- Drift check over 3 sources in under 2 minutes in CI.

**Constraints**:
- No em or en dash characters in any shipped text.
- Podman instead of Docker in any container instructions; `uv` instead of pip.
- No secrets or raw inputs in the guide project.
- Every outward action (remote creation, push, issue, change proposal, cluster mutation) needs explicit approval.
- Subagents are dispatched without a model override.

**Scale/Scope**: Guides of up to about 50 pages, up to 5 sources and 10 inputs, and runs of 20 to 40 tasks.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution (`.specify/memory/constitution.md`) is still the unfilled template, so it defines no gates. The design instead follows the binding constraints in the spec:
- approval before outward actions (FR-005c, FR-033, FR-039)
- no secrets or raw inputs in the repository (FR-005, FR-039a)
- source verification before facts enter the guide (FR-011, FR-012)

**Result**: pass, both before research and after design. Ratifying a constitution with these principles (`/speckit-constitution`) is recommended before implementation starts, so later reviews can enforce them.

## Project Structure

### Documentation (this feature)

```text
specs/001-cc-guide-plugin/
├── spec.md              # Feature specification (clarified)
├── plan.md              # This file
├── research.md          # Phase 0 decisions R1 to R13
├── data-model.md        # Guide project files and entities
├── quickstart.md        # End-to-end validation scenarios
├── contracts/
│   ├── commands.md          # Six commands, flags, shared preflight, superpowers probe
│   ├── adapter.md           # Adapter descriptor, scaffold, uniform make targets
│   └── page-conventions.md  # Source blocks, checks and expectations, read-only classes
├── checklists/
│   └── requirements.md
└── tasks.md             # Created by /speckit-tasks
```

### Source Code (repository root)

```text
cc-guide/
├── .claude-plugin/marketplace.json      # marketplace "guide-plugin-development"
├── Makefile                             # validate, install, uninstall, test, test-adapters, eval, help
├── README.md  LICENSE  CLAUDE.md
├── eval.yaml                            # agent-eval-harness configuration
├── eval/cases/                          # review, upstream, classifier cases
├── tests/
│   ├── toolkit/                         # pytest for guide/toolkit
│   ├── adapters/                        # smoke tests per format, convert.py, scaffold.sh
│   ├── manual/                          # recorded quickstart runs (evidence for verification)
│   └── fixtures/
│       ├── sample-guide/                # format-neutral fixture content
│       └── mini-project/                # source repo with planted drift, transcript with a false claim
└── guide/                               # the installed plugin
    ├── .claude-plugin/plugin.json
    ├── compat.yaml                      # known-good superpowers versions
    ├── commands/
    │   ├── create.md  evolve.md  preview.md  export.md  upstream.md  validate.md
    ├── skills/
    │   ├── preflight/SKILL.md           # shared: guide project, dependencies, probe, settings notice
    │   ├── create/SKILL.md              # intake, scaffold, pin, spec, plan, execute, final review
    │   ├── evolve/SKILL.md              # drift, impact set, adopt, update plan, rebaseline
    │   ├── preview/SKILL.md
    │   ├── export/SKILL.md
    │   ├── upstream/SKILL.md            # re-verify, dedupe, draft, approve, file
    │   ├── validate/SKILL.md            # classify, run, redact, findings
    │   ├── page-task/                   # templates handed to superpowers dispatches
    │   │   ├── SKILL.md
    │   │   ├── page-procedure.md
    │   │   ├── page-review-guide.md
    │   │   ├── global-constraints.template.md
    │   │   ├── final-review-addendum.md
    │   │   └── style-rules.md           # built-in style rules when cc-prose is absent
    │   └── diagrams/SKILL.md            # Excalidraw rules: curved arrows, palette, dedupe, backup
    ├── templates/                       # guide.yaml, inputs.yaml, baseline.yaml, styleguide.md,
    │                                    # guide-rules.yaml, run-summary.md, upstream-issue.md,
    │                                    # guide-drift.yml, adopt-map.example.yaml
    ├── adapters/
    │   ├── antora/{adapter.yaml, scaffold/}
    │   ├── mkdocs/{adapter.yaml, scaffold/}
    │   └── gfm/{adapter.yaml, scaffold/}
    ├── toolkit/                         # copied into guide projects as tools/guide/
    │   ├── VERSION
    │   ├── guidecfg.py                  # load and validate guide.yaml, baseline.yaml, inputs.yaml
    │   ├── sources.py                   # parse source blocks, resolve refs at pinned commits
    │   ├── fetch.py                     # blobless clones and pinned worktrees under .guide/cache
    │   ├── drift.py                     # baseline vs heads, change requests, impact set, inputs
    │   ├── check.py                     # page conventions, typography, versions, stubs, rule files
    │   ├── leakcheck.py                 # confidential terms, patterns, internal links in built output
    │   ├── ledger.py                    # strict-rigor claim ledger
    │   ├── attrs.py                     # generated regions for the gfm adapter
    │   ├── classify.py                  # read-only classifier, expectation matcher, redaction
    │   ├── diagram_check.py             # overlap gate on .excalidraw JSON, native-resolution crops
    │   ├── playbook.py                  # Antora playbooks for linked git worktrees
    │   ├── doctor.py                    # tool chain check from tools/guide/adapter.yaml
    │   ├── runs.py                      # run summary from the ledger, findings-add
    │   ├── adopt.py                     # migrate a foreign baseline, report missing source blocks
    │   ├── upstream.py                  # reverify, draft, sanitize, dedupe, existing issues
    │   ├── mkdocs_macros.py             # baseline values for the mkdocs adapter
    │   ├── antora-watch.mjs             # Antora rebuild and browser reload for preview
    │   ├── assemble.py                  # fallback print-HTML assembler (only if html-single falls short)
    │   ├── print-pdf.mjs                # title page, TOC, print CSS, page.pdf()
    │   └── shoot.mjs                    # screenshots for diagram review
    ├── validate/readonly.yaml           # default query allowlist
    └── docs/
        ├── learnings.md                 # lessons from the SAW guide (FR-041)
        ├── settings.md                  # model, effort, permission allowlist (FR-041)
        └── adapters.md
```

**Structure Decision**: One repository with the plugin in `guide/`, mirroring cc-prose and cc-blog (research R1). The toolkit is a directory inside the plugin that create copies into each guide project, versioned with `toolkit/VERSION` (research R4). Tests and evals live at the repository root so they are not installed with the plugin.

## Design Overview

### How create drives superpowers

1. **Preflight**: resolve the guide project, check dependencies, run the superpowers contract probe, and state the session recommendations ([contracts/commands.md](contracts/commands.md)).
2. **Intake**: interview the author; scaffold the adapter and copy the toolkit; write `guide.yaml`; pin the sources (`fetch.py`, `baseline.yaml`); register the inputs (`inputs.yaml`). The remote and push opt-ins are asked here.
3. **Guide spec**: invoke superpowers `brainstorming` with an injected instruction naming the spec location (`docs/guide/spec.md`), the persona and voice decisions already made, and the research notes extracted from the inputs.
4. **Guide plan**: invoke superpowers `writing-plans` with the plan location (`docs/guide/plan.md`), the page task template (one task per page or diagram, each with an outline, voice, facts to verify with source hints, and the content check rules for that page), and the Global Constraints rendered from `global-constraints.template.md` and `guide.yaml`.
5. **Approval**: the author approves the plan.
6. **Execution**: invoke superpowers `subagent-driven-development` with the dispatch additions from `page-task/`:
   - implementers receive `page-procedure.md` and the global constraints as files
   - reviewers receive `page-review-guide.md` (at least 12 spot-checks, or all statements)
   - controller rulings come pre-seeded from the lessons (never `cd` into `.guide/cache`; resume after a prose check; controller re-verifies disputed findings against the source before applying them, FR-012)
   - the rigor profile decides whether task reviews run
7. **Final review**: `requesting-code-review` with `final-review-addendum.md` (cross-page consistency, persona journeys, leak boundary), followed by one fix round.
8. **Wrap-up**: write the run summary, list the rulings, and record upstream findings in `findings/upstream.yaml`.

### Rigor profiles

- **fast**: skips task reviews, keeps the final review.
- **standard**: per-task review plus the final review.
- **strict**: adds the claim ledger (`ledger.py`, `make check STRICT=1`), and reviewers cite claim identifiers.

### Evolve

1. Run `drift.py` to produce the drift report.
2. Re-evaluate change requests through `gh api .../compare` at the recorded heads.
3. Compute the impact set from the source blocks plus the inbound links.
4. Generate a plan limited to that set and execute it with the same templates.
5. Write the new baseline last.

`--adopt` first migrates a foreign baseline (such as the SAW schema) and adds missing source blocks page by page with reviews.

### Upstream and validate

Both are command-level skills without superpowers dispatch. Each outward step goes through the approval contract: show the full text, get explicit consent, then act.

## Phasing (mirrors tasks.md)

1. **Setup and foundation**: repository skeleton, manifests, Makefile, `plugin.json` dependency check (R2), fixtures, toolkit core (configuration, sources, fetch, check, leak check, doctor), superpowers contract probe, and preflight skill.
2. **US1 with Antora (MVP)**: `attrs.py`, Antora adapter and smoke test, page-task templates, diagrams skill (curved-arrow verification first, R9), run summary and strict ledger, create skill and command; quickstart scenarios 3 and 4.
3. **US1 with MkDocs and GitHub Markdown**: both adapters, generated regions, smoke tests for all three formats.
4. **US2 evolve**: drift (including renames and deletions), adoption, evolve skill, drift workflow template; quickstart scenarios 6 and 7 on a copy of saw-guide (SC-005).
5. **US3 preview**: Antora watch and reload, preview targets, preview skill.
6. **US4 PDF export**: `print-pdf.mjs`, print HTML per adapter (html-single verification and fallback, R5), export skill.
7. **US5 upstream and US6 validate**, in either order: upstream re-verification and approval flow; read-only classifier, redaction, and validate skill; quickstart scenarios 8 and 9.
8. **Polish**: `learnings.md` and `settings.md` (curved arrows preferred, per-task reviews), agent-eval-harness cases, README, marketplace listing, timing checks on the 25-page fixture.

## Risks

| Risk | Mitigation |
|---|---|
| superpowers changes its scripts or skill names | Contract probe, `compat.yaml`, `bash <script>` invocation, fixture test of the `wrote <path>:` output (R3) |
| `@antora/html-single-extension` 1.0.0 falls short | Verified first on saw-guide content; fallback assembler in the toolkit (R5) |
| MkDocs Material maintenance mode | Pinned versions; documented; a Zensical adapter later (R6) |
| Curved arrows not rendered by the MCP server | Verified in the first diagram task; fallback to elbowed arrows (R9) |
| Automated diagram fixing loops without converging, or a subagent claims a clean diagram that is not | Deterministic overlap gate, controller review of the export at native resolution, versioned rounds, at most two automated rounds, then manual editing by the author (R9) |
| Builds break inside a spex worktree (`.claude/worktrees/`) | Worktree detection and generated playbooks (R9a) |
| Full create runs are too expensive to test automatically | Behavioral evals target the judgment points; full runs are manual quickstart scenarios (R11) |

## Complexity Tracking

No constitution violations to justify.
