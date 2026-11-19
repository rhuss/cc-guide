# Brainstorm: Discover guide projects in nested directories

**Date:** 2026-11-19
**Status:** active
**Source:** https://github.com/rhuss/cc-guide/issues/4

## Problem Framing

`guidecfg.py discover` (`guide/toolkit/guidecfg.py`, function `discover`) resolves the guide project for a `/guide:*` command from only two places:

1. `DIR/guide.yaml`
2. an immediate subdirectory whose `guide.yaml` contains an `embedded` block

Every other layout exits 4, so a standalone guide kept in a documentation subdirectory is never found. Example: cc-review stores its guide at `docs/guide/guide.yaml` (format `gfm`, no `embedded` block). Running any `/guide:*` command from the repository root reports no guide project, and the author must pass `--dir docs/guide` every time.

```text
$ cd cc-review
$ uv run .../guidecfg.py discover --dir .
no guide project in .../cc-review or its immediate subdirectories
$ echo $?
4
$ ls docs/guide/guide.yaml
docs/guide/guide.yaml
```

FR-031 in `specs/005-embedded-guide/spec.md` mandates "immediate subdirectories" for embedded guides, and the `discover` row in `specs/005-embedded-guide/contracts/toolkit-cli.md` describes the same rule, so this is a spec change as well as a code change.

Success: running any `/guide:*` command from a repository root finds a guide kept in `docs/guide/` (or a similar nested location) without `--dir`, embedded or not, and reports correctly whether it is embedded.

Failure even if it technically works:
- The search walks huge trees (`node_modules`, build output, cloned source caches) and becomes slow.
- A `guide.yaml` inside a cloned source repository (`.guide/cache/`) or inside another guide's tree is picked up by mistake.
- Two guides in one repository silently resolve to one of them instead of asking.
- Callers report a nested standalone guide as embedded.

## Approaches Considered

### A: Bounded breadth-first search, shallowest depth wins (chosen)

Keep rule 1 (`DIR/guide.yaml`). Otherwise search below `DIR` breadth-first up to a fixed maximum depth, collecting every directory that holds a `guide.yaml`. The shallowest depth with any match decides: one match there is the result; several at that depth exit 3 and list them.

- Pros: finds `docs/guide/` and similar layouts; deterministic; bounded cost; keeps exit codes 3 and 4.
- Cons: a fixed depth limit is arbitrary; a guide deeper than the limit still needs `--dir`.

### B: Unbounded recursive search

- Pros: finds any layout.
- Cons: slow on large repositories, more risk of false matches (vendored projects, fixtures); harder to reason about.

### C: Configured search paths (a list of well-known locations such as `docs/guide`, `documentation/guide`)

- Pros: cheap and predictable.
- Cons: misses every layout not on the list; a list in the toolkit is a maintenance burden.

## Decision

Approach A, with these points:

- **Depth.** Immediate subdirectories are depth 1. The search covers depth 1 through depth 3 (for example `docs/guide/` is depth 2, `docs/user/guide/` is depth 3). Deeper guides still need `--dir`.
- **Embedded and standalone both count.** A `guide.yaml` found below `DIR` qualifies whether or not it has an `embedded` block. Restricting the deeper search to embedded guides would not fix the cc-review layout. This also widens depth 1: a standalone guide in an immediate subdirectory is now found too.
- **Embedded status comes from the configuration, not from the location.** Callers report `embedded=yes` only when the found `guide.yaml` has an `embedded` block, and `embedded=no` otherwise. A nested standalone guide is not an embedded guide in the spec 005 sense.
- **Shallowest wins, ties ask.** Return the single match at the shallowest depth that has any match. Several matches at that depth: exit 3 and list all candidates found (so the caller asks which one to use). No match up to depth 3: exit 4.
- **Pruning.** Do not descend into hidden directories (name starts with `.`, which covers `.git`, `.guide`, `.venv`), dependency or build directories (`node_modules`, `build`, `dist`, `target`), or symlinked directories (avoids loops and leaving the tree). Do not descend into a directory that holds a `guide.yaml` (its own content is not searched for further guides).
- **Ordering.** Candidates are listed sorted by path so output is deterministic.
- **Spec and contract updates.** Update FR-031 in `specs/005-embedded-guide/spec.md` and the `discover` row in `specs/005-embedded-guide/contracts/toolkit-cli.md` to describe the new search. Update the skill text that describes discovery (`guide/skills/preflight/SKILL.md`, `guide/skills/create/SKILL.md`, `guide/skills/evolve/SKILL.md`) where it says "immediate subdirectory" or "embedded guide subdirectory".
- **Tests.** Extend `tests/toolkit/test_guidecfg.py`: cc-review layout (`docs/guide/` standalone) found from the root; shallower match wins over a deeper one; two matches at the same depth exit 3; pruned directories are ignored; depth 4 is not found; the existing embedded cases keep working.

## Out of Scope

- Searching upward from `DIR` (parent directories).
- A configurable depth or ignore list.
- Changing how `create` offers embedded mode when nothing is found.
