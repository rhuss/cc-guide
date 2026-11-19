# Data Model: Discover guide projects in nested directories

No persisted data. The entities below exist only during one discovery run.

## Search root (`DIR`)

- The directory passed with `--dir` (default `.`).
- Rule 1: when `DIR/guide.yaml` is a regular file, `DIR` is the result and nothing else is searched.

## Candidate

- A directory `C` below `DIR` with depth 1 to 3 such that:
  - every directory on the path from `DIR` to `C` (including `C`) is a real directory (not a symlink), not hidden, and not named `node_modules`, `build`, `dist`, or `target`;
  - no directory strictly between `DIR` and `C` holds a `guide.yaml` regular file;
  - `C/guide.yaml` is a regular file (or a symlink to one).
- Attributes: `path` (resolved absolute path when printed), `depth` (number of path components between `DIR` and `C`).
- Embedded status is not a candidate attribute; callers read it from the configuration.

## Discovery result

| State | Condition | Exit | Output |
|---|---|---|---|
| Self | `DIR/guide.yaml` is a file | 0 | `DIR` resolved, stdout |
| Found | exactly one candidate at the shallowest depth with candidates | 0 | candidate path, stdout |
| Ambiguous | two or more candidates at that depth | 3 | message on stderr; candidates sorted, one per line, stdout |
| None | `DIR` missing, not a directory, or no candidate up to depth 3 | 4 | message on stderr |
