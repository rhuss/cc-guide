# Implementation Plan: Discover guide projects in nested directories

**Branch**: `007-nested-guide-discovery` | **Date**: 2026-11-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-nested-guide-discovery/spec.md`

## Summary

Replace the second discovery rule in `guide/toolkit/guidecfg.py` (`discover`: one immediate subdirectory with an `embedded` block) with a bounded, level-by-level search below `DIR` (depth 1 to 3) that accepts any directory holding a regular `guide.yaml` file, prunes hidden, dependency, build, and symlinked directories, stops below a found guide, and resolves to the shallowest depth with a candidate (one: exit 0; several: exit 3 with sorted absolute paths; none: exit 4). Update the CLI messages and module docs, the three skills that describe discovery, spec 005 (FR-031, its clarification, research R-entry) and its toolkit contract, and extend `tests/toolkit/test_guidecfg.py`.

## Technical Context

**Language/Version**: Python 3.11+ (PEP 723 script run with `uv run`)

**Primary Dependencies**: standard library only for the change (`pathlib`, `os`); `pyyaml` is already a dependency of the module but discovery does not need it any more

**Storage**: N/A (reads the file system only)

**Testing**: pytest (`make test`), existing `tests/toolkit/test_guidecfg.py` with its `embedded` and `mini_host` fixtures and `tmp_path`

**Target Platform**: macOS and Linux developer machines, GitHub Actions runners

**Project Type**: CLI toolkit inside a Claude Code plugin (`guide/toolkit/`), copied into each guide project as `tools/guide/`

**Performance Goals**: discovery visits at most the directories within depth 3 that are not pruned; pruned trees are never listed (SC-004)

**Constraints**: toolkit must not import from outside its directory (FR-013); no new dependencies; no em or en dash characters in any file; output format of the CLI unchanged apart from message wording

**Global Constraints** (from the spec): search depth fixed at 3; pruned names fixed (hidden, `node_modules`, `build`, `dist`, `target`, symlinked directories), no `templates`/`fixtures`/`tests`/`examples` pruning; no new dependencies; CLI output format unchanged apart from message wording; spec 005 embedded layout rules not extended to deeper guides.

**Scale/Scope**: one function (`discover`) plus its CLI branch and error class message; three skill files; two spec 005 files (plus research.md entry); about ten new or changed tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is the unfilled template, so there are no ratified principles to check. The repository rules in `CLAUDE.md` act as the gate:

| Rule | Status |
|---|---|
| No em or en dash characters in any file | Pass: all new text is checked; tests build such characters with `chr()` only if needed (not needed here) |
| `uv` instead of pip, podman instead of Docker | Pass: no install or container instruction added |
| No secrets or raw inputs in fixtures or run records | Pass: tests build synthetic layouts in `tmp_path` |
| Outward actions only after approval | Pass: no remote action in the implementation |
| Toolkit self-contained | Pass: change uses the standard library inside `guidecfg.py` |
| Scripts never `cd` into `.guide/cache/` | Pass: discovery prunes hidden directories, so it never enters `.guide/` |
| Commit trailer `Assisted-By: 🤖 Claude Code` | Applies at commit time |

Post-design re-check: unchanged, all pass.

## Project Structure

### Documentation (this feature)

```text
specs/007-nested-guide-discovery/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── discover-cli.md  # Phase 1 output: the amended discover contract
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
guide/
├── toolkit/
│   └── guidecfg.py            # discover(), DiscoverError message, CLI branch, module usage text
└── skills/
    ├── preflight/SKILL.md     # GUIDE definition, exit table rows 0/3/4, stop message
    ├── create/SKILL.md        # section 3 exit 3 wording
    └── evolve/SKILL.md        # "Resolve the guide" bullet

specs/005-embedded-guide/
├── spec.md                    # FR-031 amended, note on clarification line 17
├── research.md                # discover decision entry amended
└── contracts/toolkit-cli.md   # discover row

tests/toolkit/
└── test_guidecfg.py           # discover tests extended; one assertion flips
```

**Structure Decision**: Single existing project; the change touches the toolkit module, its tests, three skills, and spec 005 documents. No new modules.

## Design

### Algorithm (`discover(directory)`)

1. `directory = Path(directory)`. If `directory / "guide.yaml"` is a file, return `directory` (rule 1, unchanged; `Path.is_file()` follows a symlink to a file).
2. If `directory` is not a directory, raise `DiscoverError(4, [])`.
3. `level = [directory]`. For depth 1 to `DISCOVER_MAX_DEPTH` (3):
   - `found, nxt = [], []`
   - For each `parent` in `level`, list its entries with `os.scandir` inside `try/except OSError` (unreadable: skip, FR-007).
   - For each entry: skip unless `entry.is_dir(follow_symlinks=False)` (drops symlinked directories and files); skip when `entry.name` starts with `.` or is in `DISCOVER_PRUNED = frozenset({"node_modules", "build", "dist", "target"})`.
   - If `Path(entry.path) / "guide.yaml"` is a regular file (`is_file()`): append to `found` (do not descend, FR-006). Otherwise append to `nxt`.
   - After the level: if `found` has one entry, return it; if several, raise `DiscoverError(3, sorted(found, key=lambda p: str(p.resolve())))`; else `level = nxt`.
4. Raise `DiscoverError(4, [])`.

Sorting: candidates are sorted once, inside `discover()`, by their resolved path string, so the Python API and the CLI agree; the CLI prints `cand.resolve()` per line in that order.

### Messages

- `DiscoverError` text: `"several guide projects"` (code 3) / `"no guide project found"` (code 4).
- CLI exit 3 (stderr): `several guide projects found; name one with --dir:` then candidates on stdout.
- CLI exit 4 (stderr): `no guide project in DIR or the directories below it (up to 3 levels)`.
- Module usage text and the `discover` docstring describe the bounded search.

### Callers

Preflight already derives `embedded` from the configuration (`get embedded.front_page`), so FR-008 needs only wording changes. `create` section 3: exit 0 resumes the found guide (unchanged), exit 3 wording generalized; exit 4 branches unchanged. `evolve`: wording only.

## Complexity Tracking

No violations; section intentionally empty.
