# Implementation Plan: Author-owned region on the generated front page

**Branch**: `006-author-owned-front-page-region` | **Date**: 2026-11-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-author-owned-front-page-region/spec.md`

## Summary

One guide-owned region per README, delimited by `<!-- guide:region -->` / `<!-- /guide:region -->` markers, with everything outside the markers author-owned. Two consumers share one mechanism: any gfm guide can declare a `publish` block in `guide.yaml` (a source page rendered with rebased links into a target README's region), and the embedded front page (spec 005) narrows its existing machinery to the region when markers are present. Embedded create gains "stays as the author region" as a move-plan destination. Author text is never modified or verified except by the whole-file link check; reviewer briefs flag contradictions as advisories.

## Technical Context

**Language/Version**: Python 3.11+ (PEP 723 toolkit scripts, run with `uv run`), no new runtime dependencies.

**Primary Dependencies**: existing toolkit modules only: `guidecfg` (config), `embed` (link rewriting, fence masking, front-page status), `check` (violations), `attrs` (generated regions), `fetch` (front page normalization). The toolkit must not import anything outside `tools/guide/` (repo rule), and all new modules live beside them.

**Storage**: files only: `guide.yaml`, `baseline.yaml` (existing `front_page_blob` semantics, see research R5), move-plan YAML in `.guide/runs/<run-id>/`.

**Testing**: pytest in `tests/toolkit/` (new `test_region.py`, `test_publish.py`; additions to `test_embed.py`, `test_check.py`, `test_guidecfg.py`); adapter smoke tests in `tests/adapters/` stay green.

**Target Platform**: developer machines running the guide plugin (Claude Code skills driving Python/Node scripts).

**Project Type**: plugin toolkit (Python scripts + skill markdown).

**Performance Goals**: N/A (small text files; region parse is linear).

**Constraints**: no em/en dash characters in any file; `uv` not pip; toolkit self-contained; never write secrets into fixtures.

**Scale/Scope**: one new toolkit module pair (`region.py`, `publish.py`), edits to five existing modules, three skill documents, one Makefile, one adapter descriptor.

## Constitution Check

`.specify/memory/constitution.md` is the unfilled template (no ratified principles), so there are no constitution gates to evaluate. Repo rules from `CLAUDE.md` apply as standing constraints (listed in Technical Context) and are honored by the design: no new top-level directories, toolkit stays self-contained, outward actions none.

## Project Structure

### Documentation (this feature)

```text
specs/006-author-owned-front-page-region/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── region-markers.md
│   ├── publish-cli.md
│   └── move-plan-destination.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
guide/
├── toolkit/
│   ├── region.py          # NEW: fence-aware marker parsing, region splice/extract
│   ├── publish.py         # NEW: publish writer and check (publish block in guide.yaml)
│   ├── guidecfg.py        # Publish dataclass, guide.yaml parsing + validation
│   ├── check.py           # region validity rule, structure scoping, link check targets
│   ├── embed.py           # front_page_status region scoping, move-plan destination, apply
│   └── attrs.py           # region-aware generated-region rewriting on the front page
├── adapters/gfm/
│   ├── adapter.yaml       # document the publish block and markers
│   └── scaffold/Makefile # publish / check-publish targets, check wiring
└── skills/
    ├── page-task/front-page-contract.md   # marker rules, author region, review advisories
    ├── page-task/page-procedure.md        # front-page task edits the region only
    ├── page-task/page-review-guide.md     # author-region contradiction advisory (FR-014)
    ├── create/SKILL.md                    # "stays as the author region" destination
    └── evolve/SKILL.md                    # hand-edit reporting scoped to the region

tests/toolkit/
├── test_region.py         # NEW
├── test_publish.py        # NEW
├── test_embed.py          # additions (front_page_status, move plan, apply)
├── test_check.py          # additions (region rule, structure, link check)
└── test_guidecfg.py       # additions (publish block parsing)
```

**Structure Decision**: two new modules in the existing flat toolkit directory, following the one-module-one-concern pattern (`attrs.py` for generated regions, `drift.py` for drift). `region.py` holds parsing and splicing with no CLI; `publish.py` is the CLI front end for the publish flow, mirroring how `attrs.py` pairs a library with a subcommand CLI. Skill and contract markdown is updated in place where the front-page rules already live, so there is exactly one place each rule is stated.

## Complexity Tracking

No constitution violations to justify. The one deliberate addition beyond the minimal fix is the standalone `region.py` module (instead of parsing inline in each consumer): three consumers (publish, check, embed/attrs) need identical fence-aware parsing, and divergent parsers would be a defect factory (research R1).
