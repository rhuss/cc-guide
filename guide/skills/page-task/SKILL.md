---
name: page-task
description: Templates and controller rules that the guide create and evolve skills hand to superpowers subagent-driven-development dispatches (page procedure, review guide, global constraints, final review addendum, built-in style rules). Used by the create and evolve skills; not invoked directly by authors.
allowed-tools: ["Bash", "Read", "Write"]
---

# Page tasks under superpowers

cc-guide does not reimplement subagent execution. The create and evolve skills run superpowers `subagent-driven-development` (SDD) on the guide plan and add the files in this directory to its dispatches. This skill says how.

## Files

| File | Who reads it | Purpose |
|---|---|---|
| `page-procedure.md` | page implementers | Steps of every page task, format snippets, input rules, report format |
| `page-review-guide.md` | per-task reviewers | At least twelve factual spot-checks (or all statements), severity calibration, output format (FR-011) |
| `global-constraints.template.md` | the controller renders it | The plan's Global Constraints section and `global-constraints.md` for dispatches |
| `final-review-addendum.md` | the final reviewer | Cross-page consistency, persona journeys, boundary, deferred minors (FR-013) |
| `style-rules.md` | implementers and reviewers when cc-prose is absent | Built-in voices and banned phrasing (FR-003a) |

## Setup before the first dispatch

The controller (the session running `/guide:create` or `/guide:evolve`) does this once per run, after the author approved the plan:

1. Resolve the plan workspace: `bash <superpowers>/skills/subagent-driven-development/scripts/sdd-workspace docs/guide/plan.md` (always `bash <script>`; `<superpowers>` is `installPath` from the preflight probe). It prints the workspace directory, `.superpowers/sdd/plan/` or a disambiguated variant.
2. Copy into the workspace: `page-procedure.md`, `page-review-guide.md`, `final-review-addendum.md`, `style-rules.md`, and the rendered `global-constraints.md` (the same text as the plan's Global Constraints section). Copy the guide's `styleguide.md` there too.
3. Let SDD create the ledger (`<workspace>/progress.md`, identity line naming `docs/guide/plan.md`), then record the pre-seeded rulings below as the first ruling lines, numbered `Ruling R1:` onwards, before the first dispatch.

## Dispatch additions

- **Implementer of a page task**: add to the SDD implementer dispatch: "Before you start, read `<workspace>/page-procedure.md`, `<workspace>/global-constraints.md`, and the guide's `styleguide.md`. They bind this task and win over generic instructions where they differ. cc-prose is <present|absent>." When absent, also name `<workspace>/style-rules.md`.
- **Implementer of a diagram task**: name the diagrams skill (`guide:diagrams`) and `<workspace>/global-constraints.md`. The controller, not the implementer, reviews the export (FR-023a).
- **Task reviewer**: add: "Use `<workspace>/page-review-guide.md` as your review guide and output format. The pinned sources are under `.guide/cache/<source-id>/`." Pass the review package path from `review-package` as usual.
- **Final reviewer** (`requesting-code-review`): add `<workspace>/final-review-addendum.md`, the deferred-minor and parked lines from the ledger, and the paths of `build/site` and `build/site-internal`.

## Rigor profiles (FR-021)

| Profile | Per-task review | Final review | Extra |
|---|---|---|---|
| `fast` | skipped; ledger line `Task <N>: review skipped (rigor fast)` | yes | none |
| `standard` | yes, every page task | yes | none |
| `strict` | yes | yes | claim ledger (`make check STRICT=1`); reviewers cite claim identifiers; stubs forbidden |

Diagram tasks always get the controller's export review and the overlap check, whatever the profile (FR-023, FR-023a).

## Pre-seeded controller rulings

Record these at the start of every run (FR-014); each says what it costs if wrong.

- **R1** Implementers receive `page-procedure.md`, `global-constraints.md`, and `styleguide.md` (plus `style-rules.md` without cc-prose) as files, and reviewers receive `page-review-guide.md`, because `task-brief` extracts only the task section. Cost if wrong: none.
- **R2** Every dispatch runs commands from the guide project root with path arguments and never changes into `.guide/cache/`; git runs there only as `git -C`. A changed directory inside the cache stalled subagents repeatedly. Cost if wrong: none, it only restricts how commands are phrased.
- **R3** Subagents are dispatched without a model parameter and inherit the session model. Cost if wrong: higher token use per task.
- **R4** Before applying a review finding that changes a fact, the controller reads the cited pinned source itself (FR-012). A finding the source contradicts is rejected and logged as `Task <N>: finding rejected-by-source: <finding> (<source-id>:<path>:<lines> says <what>)`. Cost if wrong: a correct finding is dropped; the final review samples facts again.
- **R5** With cc-prose present, the prose check ends an implementer's turn; the controller resumes the same implementer with "finish" and records nothing else. Cost if wrong: one extra message per page.
- **R6** When an isolated or background session refuses a `git` command because a shell hook rewrites it (for example `rtk git`), the subagent calls `/usr/bin/git` directly. Cost if wrong: none.
- **R7** A small fix that the controller has verified against the pinned source (a wrong number, a typo in a target name) may be applied by the controller directly instead of a fix dispatch plus re-review; it is logged as a fix round with the commit. Cost if wrong: the fix skips an independent re-review; the final review covers it.
- **R8** Push policy: <pushes after each completed task | local commits only>, as the author chose at intake (FR-005c). A failed push is reported once, retried after the next completed task, and unpushed commits are listed at the end. Cost if wrong: commits stay local until the author pushes.

## Resume (FR-013a)

The SDD ledger is the recovery map. Its identity line names the plan file, so a ledger for another plan is never resumed. `uv run tools/guide/runs.py resume --workspace <workspace>` prints the first task without a `complete` line (or `done`); a task whose last line is a fix round resumes at its next review. Commits named in the ledger are trusted over the session's memory.
