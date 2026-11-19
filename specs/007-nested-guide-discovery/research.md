# Research: Discover guide projects in nested directories

## R1: Traversal strategy

- **Decision**: Level-by-level (breadth-first) traversal with `os.scandir`, maximum depth 3, returning as soon as a level has candidates.
- **Rationale**: Breadth-first gives "shallowest wins" directly and stops early; most repositories resolve at depth 1 or 2 after listing a handful of directories. `os.scandir` exposes `is_dir(follow_symlinks=False)` without an extra `stat`, which makes symlink pruning cheap and exact.
- **Alternatives considered**: `os.walk` with in-place pruning of `dirnames` (depth-first order, needs depth bookkeeping and full collection before choosing the shallowest); `Path.rglob("guide.yaml")` (cannot prune, walks `node_modules`, unbounded); a fixed list of known locations (misses layouts, rejected in the brainstorm).

## R2: Symbolic links

- **Decision**: Never descend into or accept a directory reached through a symbolic link (`entry.is_dir(follow_symlinks=False)` false for symlinks). A `guide.yaml` that is itself a symlink to a regular file counts (`Path.is_file()` follows it), matching rule 1.
- **Rationale**: Prevents loops and leaving the tree; keeps rule 1 and rule 2 consistent about the configuration file.
- **Alternatives considered**: following directory symlinks with a visited set (more code, can still leave the repository).

## R3: Pruned names

- **Decision**: Hidden names (leading `.`) plus exact names `node_modules`, `build`, `dist`, `target`, at every depth, fixed in code.
- **Rationale**: Matches the issue; the user decided not to add `templates`, `fixtures`, `examples`, `tests` (documented edge case, `--dir` workaround).
- **Alternatives considered**: configurable ignore list (out of scope), honoring `.gitignore` (needs git or a parser; out of scope).

## R4: Unreadable directories

- **Decision**: Catch `OSError` around `os.scandir(parent)` and skip that parent. Testing uses `chmod 000` on a directory, skipped when running as root.
- **Rationale**: FR-007; a permission problem in an unrelated tree must not break every guide command.

## R5: Embedded status and depth

- **Decision**: Discovery no longer reads `guide.yaml`; it only checks that the file exists. Embedded status stays with the callers (`get embedded.front_page`). Embedded guides deeper than depth 1 are found and reported embedded; spec 005's layout rules are not extended (user decision).
- **Rationale**: Separation of concerns; validation reports bad front page paths.

## R6: Output ordering

- **Decision**: The CLI resolves each candidate and prints them sorted lexicographically by the resolved path string.
- **Rationale**: Deterministic output (FR-004) independent of file system listing order and of whether `DIR` was given relative or absolute.

## R7: Tests and the testing hook for SC-004

- **Decision**: SC-004 is tested by making a `node_modules` directory unreadable (`chmod 000`) next to a real guide at depth 2; discovery must succeed with the same result, proving the pruned tree is not listed (an unreadable pruned tree would otherwise be skipped silently too, so the test additionally places a guide under `node_modules/x/` with normal permissions in a second case and asserts it is not found).
- **Rationale**: Deterministic, no timing.
