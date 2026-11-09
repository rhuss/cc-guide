# Data Model: Author-owned region on the generated front page

Phase 1 output. Entities, validation rules, and state as the toolkit sees them. All paths are guide-root-relative unless stated otherwise.

## Entities

### Region (parsed view of a file with markers)

| Field | Type | Description |
|-------|------|-------------|
| author_prefix | str | File content before the begin marker, byte-identical on every write |
| content | str | File content between the markers (guide-owned) |
| author_suffix | str | File content after the end marker, byte-identical on every write |
| begin_line | int | 1-based line of the begin marker, for violation reporting |
| end_line | int | 1-based line of the end marker |

**Identity**: one region per file (FR-001). A file either has no markers (whole file is one implicit guide-owned block, for files the guide owns) or exactly one balanced pair.

**Validation** (checked by `region.parse`, reported by `check.py` rule `region`):
- Exactly one begin and one end marker outside fenced code blocks; the begin precedes the end. Violations: `region-unbalanced`, `region-duplicate` (FR-004).
- Marker text inside fenced code blocks is author text, never a delimiter (FR-005).

**Operations**:
- `splice(text, new_content)`: replaces `content`, leaves prefix and suffix untouched; the writer's only mutation.
- `normalized(text)`: `content` with generated `guide:attr` region values emptied (the comparison key for hand-edit detection, research R5).

### Publish declaration (guide.yaml `publish` block)

| Field | Type | Description |
|-------|------|-------------|
| page | str | Source page, guide-root-relative; MUST resolve inside the content root and exist |
| target | str | Target README, guide-root-relative (typically `../README.md`); MUST resolve outside the content root |

**Validation** (in `guidecfg` guide loading, `ConfigError` on failure):
- Both keys required, non-empty strings; no unknown keys.
- `page` inside `content_root` and an existing file; `target` outside `content_root`.
- Allowed for the gfm adapter only (adapter capability `publish`); other formats fail `validate`.
- At most one `publish` block per guide (v1).

**Lifecycle**: static configuration, edited by the author. Declaring it opts the guide into README publishing; every command that respects it (publish, check, evolve) reads it through `guidecfg`.

### Move-plan entry (embedded create, extends spec 005's model)

| Field | Type | Description |
|-------|------|-------------|
| path | str | Host-relative file path (existing field) |
| section | str or null | Heading title when the entry is a section (existing field) |
| destination | str | `input`, `developer`, `keep`, `remove`, `relocate`, or the new `author-region` |
| stub / to | as today | Unchanged semantics for the other destinations |

**Validation** (extends the existing plan validator):
- `author-region` is valid only for entries whose `path` is the root Markdown README, with a non-null `section`.
- `author-region` cannot be combined with `stub: true`.
- The root README's destinations remain constrained as today (research R9): its sections may be `input`, `developer`, or `author-region`; non-section entries follow today's rules.

**Lifecycle**: written by create's classification, edited by the author, applied once by `embed.apply`. `apply` writes the begin and end markers immediately below the last retained `author-region` section and leaves the retained text byte-identical; the front page task later fills the region.

### Front-page blob (baseline.yaml `self` entry, existing field with narrowed meaning)

| Field | Type | Description |
|-------|------|-------------|
| front_page_blob | str | Blob id of the normalized front page; with markers, the normalized region only (research R5) |

**State transitions**: `unrecorded` (no blob) -> `recorded` (create/evolve run `front-page-status --record` after checks) -> `unchanged` or `edited` on the next comparison. Adding markers to a previously whole-file front page makes the next comparison report `edited` once (the recorded blob covers the whole file); re-recording after that evolve settles it.

## Relationships

- A `Publish` declaration points at one source page (a guide page like any other: sources block, reviews, checks) and one target file that holds one `Region`.
- The embedded front page holds one `Region` when markers are present; the whole file is the guide's page when they are not (FR-002).
- `Region.content` is the only text any guide command writes, checks, reviews, or drift-detects; `author_prefix`/`author_suffix` are read only by the whole-file link check (FR-003, FR-008).
