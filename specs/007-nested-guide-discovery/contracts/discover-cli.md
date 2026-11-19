# Contract: `guidecfg.py discover` (amends specs/005-embedded-guide/contracts/toolkit-cli.md)

```text
uv run tools/guide/guidecfg.py discover [--dir DIR]
```

| Aspect | Contract |
|---|---|
| Rule 1 | `DIR` (default `.`) holds a regular file `guide.yaml`: print `DIR` (resolved), exit 0. Nothing below `DIR` is searched. |
| Rule 2 | Otherwise search directories below `DIR`, depth 1 (immediate subdirectories) to 3, level by level. A candidate is a directory holding a regular file `guide.yaml`, embedded or not. |
| Pruning | Never a candidate and never searched: names starting with `.`, `node_modules`, `build`, `dist`, `target`, directories reached through a symlink, directories below a candidate, unreadable directories (skipped silently). |
| Exit 0 | Exactly one candidate at the shallowest depth with candidates: its resolved path on stdout. |
| Exit 3 | Several candidates at that depth: stderr `several guide projects found; name one with --dir:`, stdout the candidates as resolved absolute paths, sorted lexicographically, one per line. Deeper candidates are not listed. |
| Exit 4 | `DIR` missing or not a directory, or no candidate up to depth 3: stderr `no guide project in DIR or the directories below it (up to 3 levels)`, stdout empty. |
| Embedded | Not reported by `discover`. Callers run `guidecfg.py get embedded.front_page --root GUIDE` (non-empty means embedded). |

Python API: `discover(directory: Path) -> Path`; raises `DiscoverError(code, candidates)` with `code` 3 (candidates sorted) or 4 (empty list).
