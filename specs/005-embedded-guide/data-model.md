# Data Model: Embedded guide

Paths in configuration files are relative to the guide root unless stated otherwise. "Host" means the repository that contains the guide subdirectory.

## guide.yaml: `embedded` block (new)

```yaml
embedded:
  front_page: ../README.md          # default ../README.md when omitted; must exist after create; .md only
  developer_readme: ../DEVELOPMENT.md   # optional; omitted when nothing moved
  stubs:                            # host paths left as redirect stubs
    - ../docs/install.md
    - ../USAGE.md
  pr_check: off                     # off | on (records whether the workflow was installed)
```

Validation (guidecfg, FR-004):
- `embedded` present requires `format: gfm`, `internal.enabled: false`, empty `internal.confidential_terms` and `internal.confidential_patterns`.
- `front_page` must resolve outside the guide root, inside the host toplevel, end in `.md`, and exist (existence is checked by `guidecfg.py validate`, not by the schema load, so create can validate before the page is written by passing `--allow-missing-front-page`).
- `developer_readme` and every `stubs` entry must resolve inside the host toplevel and outside the guide root.
- Unknown keys are errors.

## confidential.local.yaml (new, git-ignored, embedded only)

```yaml
confidential_terms: [ACME Corp]
confidential_patterns: ['\b[A-Z]{2,}-\d+\b']
inputs:                 # real locations for inputs registered as local:<id>
  call-2026-10: ~/transcripts/acme-call.txt
```

`load_guide` merges terms and patterns into `Guide.confidential_terms/patterns`. A missing file means no terms. The file is never read into any committed output.

## baseline.yaml: `self` source (extended entry)

```yaml
sources:
  - id: self
    repo: ..                       # the host repository (local path)
    ref: main                      # tracked branch
    commit: 0123...                # 40 hex
    status: verified
    web: https://github.com/owner/name   # optional; from origin when it is GitHub
    front_page_blob: 77be...       # git hash-object of the front page when the baseline was written
    fingerprints:                  # cited path -> git blob id at `commit`
      src/cli.py: 9f1c...
      config/defaults.yaml: 41aa...
```

Rules:
- `self` is reserved: allowed only in embedded guides, at most once, and `repo` must resolve to the host toplevel.
- `fingerprints` is allowed only on `self`; keys are host paths (repository-relative), values 40-hex blob ids.
- `pin` and `rebaseline` recompute `fingerprints` from the citations of all pages at that moment.
- `front_page_blob` is written by `embed.py front-page-status --record` and by `fetch.py rebaseline` (both store the normalized front page in the host object database). create and evolve run `front-page-status --record` after the final `make check` (so generated region rewrites and check fixes are included); generated `guide:attr` regions are normalized before hashing. evolve compares it to detect hand edits (FR-009a). For the diff, the recorded text is read from the front page in the commit that last changed `baseline.yaml` (verified against `front_page_blob`), so it survives pushes, fresh clones, squash merges, and `git gc`; the loose object written by `--record` is only the fallback before that commit exists.
- When `commit` is missing from the repository (fresh clone after a squash merge), readers fall back on `fingerprints`: blobs by id for citations, the tracked head for the snapshot when all fingerprints match it, otherwise the source is drifted with "pin unavailable".
- `ref` defaults to the host's default branch (`origin/HEAD`, else `main`, else `master`), even when the pinned commit is on a working branch, so drift and links keep working after that branch is merged and deleted.

## inputs.yaml entries (extended)

| Field | Values | Meaning |
|---|---|---|
| `location` | path, URL, `self:<host path>`, `local:<id>` | `self:` for host documentation that consolidation rewrites or removes; `local:` for confidential inputs whose real location is in `confidential.local.yaml` |
| `revision` | 40 hex | required with `self:`; the commit the input was read at |
| `sha256` | as today | not used for `self:` entries |
| `blob` | 40 hex | required with `self:`; blob id at `revision` |

Drift status for `self:` inputs is `recorded` (never `changed` or `unreadable`). `local:` inputs are compared as today after resolving the location, and reports show only the id.

## Move plan (new, run-local file)

Written by the create skill to `.guide/runs/<run-id>/move-plan.yaml`, shown to the author, executed by `embed.py apply` after approval.

```yaml
self_revision: 0123...             # host HEAD when the inventory ran
developer_readme: ../DEVELOPMENT.md
developer_readme_exists: false
entries:
  - path: ../README.md
    section: null                  # whole file
    destination: input             # input | developer | keep | remove | relocate
  - path: ../README.md
    section: "Building from source"   # heading text; the section runs to the next heading of the same or higher level
    destination: developer
  - path: ../docs/install.md
    destination: input
    stub: true                     # remove after reading, leave a stub
  - path: ../.github/README.md
    destination: relocate
    to: ../.github/README.old.md
manifests:                          # flagged by inventory; absolute links offered
  - path: ../pyproject.toml
    publishes_readme: true
absolute_links: true
```

Validation: every `path` exists at `self_revision`; `remove` and `stub: true` entries are documentation files only (never `LICENSE*`, never files outside the inventory); `stub: true` is never allowed on `.github/README*` or on a root README, because a stub there would shadow the front page or leave two root READMEs (exemption from FR-023); a `section` that is not found is an error; the root README's only allowed destinations are `input` (it is replaced by the front page) plus `developer` sections; a non-Markdown root README must be `input` plus removal or `relocate`.

## Stub file

```markdown
<!-- guide: moved -->
# Installation

This page moved to [Installation](../guide/docs/admin/install.md).
```

Exactly one marker line, one heading, one link. Listed in `embedded.stubs`.

## Front page (host README)

- First line: `<!-- guide: front page. This file is generated and maintained by cc-guide; change it with /guide:evolve. -->`
- Then a Markdown `#` title, optional badges and logo (kept as they were, not verified), the sources block, the why card and overview content (overview contract), persona navigation (one link per persona entry page, in section order), and a link to the developer README.
- Links into the guide use host-relative paths (`guide/docs/...`) or absolute URLs when `absolute_links: true`.

## Drift report additions

- `sources[].mode`: `commit` (as today) or `fingerprint` (for `self`).
- `changed_files[].change` for `self`: `modified` or `deleted` (rename only when the pin is reachable).
- `inputs[].status`: adds `recorded`.
- PR mode rules: a base commit without the guide's `baseline.yaml` counts as "baseline changed"; a cited file without a fingerprint counts as a mismatch; a base SHA missing from the checkout exits 2.
- PR mode JSON: `{base, head, cited_changed: [paths], affected_pages, baseline_updated: bool, fingerprints_match: bool, skipped: bool, result: pass|fail}`.

## State transitions

Embedded create: intake → scaffold the guide subdirectory and pin `self` (changes only the subdirectory) → `inventory` → move plan proposed → (author edits) → approved → `apply` (developer README, inputs recorded, stubs to front page, removals) → guide spec and plan → pages written → `retarget` stubs → final review → rebaseline with fingerprints → commit.

Declined plan: nothing outside the guide subdirectory changes; create stops and offers to remove the uncommitted guide subdirectory.
