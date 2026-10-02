# Data Model: cc-guide

All persistent state lives in the **guide project** (the repository that holds a guide), not in the plugin. Files marked *committed* travel with the guide; files marked *local* stay git-ignored on the author's machine. Paths are relative to the guide project root.

## Overview

```text
guide.yaml                    committed  Guide project configuration
guide-rules.yaml              committed  Optional per-page content rules (require, forbid, require_order)
baseline.yaml                 committed  Pinned sources and change requests (the baseline)
inputs.yaml                   committed  Input register (references only, never raw content)
findings/upstream.yaml        committed  Upstream findings and their filing status
runs/<run-id>.md              committed  Run summary: rulings, review statistics, findings
docs/guide/spec.md            committed  Guide specification produced by create (superpowers brainstorming)
docs/guide/plan.md            committed  Guide plan executed by create and evolve (superpowers writing-plans)
tools/guide/                  committed  Vendored toolkit, VERSION, and adapter.yaml
.github/workflows/guide-drift.yml  committed  Optional scheduled drift check
diagrams/<name>.excalidraw    committed  Final diagram sources (exports live in the adapter's image directory)
<adapter content>             committed  Pages, partials, images, diagram sources
.guide/                       local      Run working state (git-ignored)
  cache/<source-id>/          local      Pinned source checkouts (partial clones)
  runs/<run-id>/              local      Briefs, reports, review packages, validation output
  diagrams/<name>/round<N>/   local      Every diagram round: scene, SVG, PNG, overlap report, review notes
  canvas-backup/              local      Read-only backups of the author's canvas
.superpowers/sdd/<plan>/      local      superpowers workspace incl. the progress ledger
```

## Entities

### Guide project configuration (`guide.yaml`, committed)

| Field | Type | Rules |
|---|---|---|
| `schema` | integer | Required. Current value `1`; bumped on breaking changes. |
| `title` | string | Required. Shown on the PDF title page and site header. |
| `format` | enum `antora`, `mkdocs`, `gfm` | Required. Selects the adapter. Immutable after create (changing it is a migration, out of scope). |
| `personas` | list of `{id, title, start}` | At least one. `id` is a slug; `start` is the persona's entry page. |
| `sections` | list of `{id, title, voice}` | Ordered navigation sections; `voice` is a cc-prose voice name or a built-in style id. |
| `rigor` | enum `fast`, `standard`, `strict` | Default `standard`. Can be overridden per run. |
| `internal.enabled` | boolean | Default `false`. Enables the internal part. |
| `internal.confidential_terms` | list of strings | Exact terms that must never appear in shareable output (case-insensitive match). |
| `internal.confidential_patterns` | list of regex | For example a ticket key format `\b[A-Z]{2,}-\d+\b`. |
| `clusters.<name>.kubeconfig` | path | Reference only; the file content is never read into the project. |
| `clusters.<name>.context` | string | Optional kube context. |
| `clusters.<name>.disposable` | boolean | Default `false`. Only `true` permits the full validate tier (FR-039). |
| `validate.extra_queries` | list of command patterns | Optional. Additive only: extends the read-only allowlist; cannot remove the default-deny rule or reclassify a command on the explicit mutating list. |
| `drift.schedule` | cron string or `off` | Default `off`; set when the author opts into the scheduled check (FR-025b). |
| `upstream.target` | enum `github` | Only `github` in v1. |

Validation: unknown keys are errors; `format` must have an installed adapter; every `personas[].start` and `sections[].id` must resolve to content after create.

### Baseline (`baseline.yaml`, committed)

| Field | Type | Rules |
|---|---|---|
| `captured` | date | Required. Date the sources were pinned. |
| `sources[]` | list | At least one source. |
| `sources[].id` | slug | Unique; used as the prefix in source references (`<id>:<path>:<lines>`). |
| `sources[].repo` | URL | Clone URL or `owner/name`. |
| `sources[].ref` | string | Tag or branch the pin was taken from (informational). |
| `sources[].commit` | 40-hex SHA | Required. The pin; all verification uses it. |
| `sources[].status` | enum `verified`, `unverified` | `unverified` when the source could not be fetched and the author chose to continue. |
| `sources[].attributes` | map | Values exposed to pages through the adapter (for example `version: 0.0.116-rhaiv.0`). |
| `change_requests[]` | list | In-flight upstream changes documented as experimental. |
| `change_requests[].source` | source id | Must exist in `sources`. |
| `change_requests[].number` | integer | Pull request number. |
| `change_requests[].head` | 40-hex SHA | Head revision the documentation describes. |
| `change_requests[].state` | enum `open`, `merged`, `closed` | State at capture time. |
| `change_requests[].tier` | enum `in-review`, `on-main` | Experimental tier used in pages. |
| `change_requests[].anchor` | string | Page anchor of the experimental section. |

State transitions per change request (evolve, FR-027): `open → open` (head moved: re-verify), `open → merged` (tier `on-main`, or label removed once released), `open → closed` (content removed or reworked, ruling recorded).

A baseline is replaced only after a run passes its checks (FR-029); the previous baseline remains in git history.

### Input register (`inputs.yaml`, committed)

| Field | Type | Rules |
|---|---|---|
| `inputs[].id` | slug | Unique. |
| `inputs[].kind` | enum `transcript`, `ticket`, `link`, `notes`, `document` | |
| `inputs[].location` | path or URL | Where the input lives; never inside the guide project. |
| `inputs[].role` | string | What the input contributes (for example "walkthrough part 1"). |
| `inputs[].sha256` | hex | Checksum of the content at registration; empty for links that are not fetched. |
| `inputs[].confidential` | boolean | Asked per input during intake. When `true`, content derived from it may only reach the internal part, cited there as `input:<id>`. |
| `inputs[].registered` | date | |

Validation: a `location` inside the guide project is rejected (FR-005). evolve compares checksums and reports changed or unreadable inputs (FR-005a).

### Page (content files, committed)

Every page carries a **source reference block** ("source block" for short; FR-010): one entry per line, each `<source-id>:<path>[:<lines>]`, `url:<url>`, or, on internal pages only, `input:<input-id>`. The block syntax is adapter-specific (see `contracts/page-conventions.md`), its grammar is shared.

Task steps on admin and user pages carry a `Check:` line followed by a command listing and an optional **expectation** used by validate (FR-038).

### Upstream finding (`findings/upstream.yaml`, committed)

| Field | Type | Rules |
|---|---|---|
| `id` | string | `UF-<n>`, unique per guide. |
| `source` | source id | Repository the finding is about. |
| `kind` | enum `doc-drift`, `stale-reference`, `dead-config`, `missing-doc`, `naming-ux`, `bug` | `naming-ux` may only be filed as an issue (FR-034). |
| `locations[].ref` | `<path>:<lines>` | At the pinned commit. |
| `locations[].quote` | string | The text at that location when the finding was collected; re-verification searches for it on the default branch, tolerating moved lines. |
| `summary` | string | One sentence. |
| `evidence` | string | What contradicts what. |
| `status` | enum | See transitions. |
| `reverified_commit` | SHA | Default-branch commit the finding was re-checked against (FR-032). |
| `filed` | URL | Issue or pull request URL once filed. |
| `merged_into` | finding id | When deduplicated. |
| `note` | string | Reason for `dropped`. |

Transitions: `collected → reverified → drafted → approved → filed`; from `collected` or `reverified` to `dropped` (no longer holds) or `merged` (duplicate); `drafted → rejected` (author declined). Mechanical re-verification that cannot find a quoted location sets `needs-review` (from `collected`, `reverified`, or `drafted`); the semantic check then moves it to `reverified`, `dropped`, or `merged`. A draft can be redrafted (`drafted → drafted`), and an approval can be withdrawn before filing (`approved → rejected`). Nothing reaches `filed` without `approved` (FR-033).

### Ruling (inside the run summary and the ledger)

`Ruling R<n>: <decision>; <reason>; <cost if wrong>`. Numbered per run. Every ruling is listed in the run summary (FR-014).

### Review finding (run-local, summarized in the run summary)

`{task, severity: critical|important|minor, location: <page>:<line>, statement, verdict: confirmed|rejected-by-source|deferred, ruling?}`. Findings rejected after re-verification against the pinned source (FR-012) are kept with verdict `rejected-by-source`.

### Progress ledger (`.superpowers/sdd/<plan>/progress.md`, local)

The superpowers ledger. Its first line is the superpowers identity line naming the plan file (`# SDD ledger`, a separator, then `plan: <plan file>`), which serves as the run identity (FR-013a); cc-guide reads it but never writes it. cc-guide adds only line formats it understands: `Task <N>: dispatched (base <sha>)`, `Task <N>: review <verdict>`, `Task <N>: fix round <r>/5 ...`, `Task <N>: complete (commits <a>..<b>)`, `Ruling R<n>: ...`. Resume = first task without a `complete` line; a task whose last line is a fix round resumes at the next round.

### Run summary (`runs/<run-id>.md`, committed)

`run-id` = `<YYYY-MM-DD>-<command>[-<n>]`. Contains: command and rigor, baseline before and after, tasks with review verdicts and fix-round counts, all rulings, review findings rejected by source, upstream findings collected, validation results summary (no command output), the model the run used, and the recommended effort (the effort setting itself is not observable by the plugin, research R13).

### Validation result (run-local)

`{page, line, command, tier: read-only|full, classification: query|mutating, outcome: match|mismatch|not-evaluable|skipped|confirmed-and-run|declined, redacted_output_excerpt}`. Mismatches become review findings (FR-040). Output is redacted before it is written anywhere (FR-039a).
