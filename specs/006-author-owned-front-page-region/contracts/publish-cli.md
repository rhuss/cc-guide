# Contract: publish CLI

`uv run tools/guide/publish.py [--root DIR] [--write | --check]`

The gfm-adapter command that keeps a declared README region current (FR-006, FR-007). Exits 0 on success, 1 on error or difference.

## Preconditions

- `guide.yaml` has a `publish` block (page, target); without it the command prints a notice and exits 0 (no target, nothing to do).
- The guide is gfm; other formats fail validation earlier (research R8).
- The target file exists and has exactly one balanced marker pair (contracts/region-markers.md); otherwise exit 1 with the region error, nothing written.

## Modes

| Mode | Behavior |
|------|----------|
| `--check` | Render the source page, compare with the target's region, report differences (file, line) and exit 1 when any; also runs the region validity parse. Runs as part of `make check` (check-publish target). |
| `--write` | Render the source page and splice it into the region. Author text untouched (byte-identical). Runs as `make publish`. |

## Rendering rules

- The source page's text is copied; relative links and images are rebased from the page's directory to the target's directory (inline and reference links, angle-bracket forms; absolute URLs and fragments unchanged), using the same transform as the move-plan relocations (`embed.rewrite_links`).
- The `// Sources:` block and generated `guide:attr` regions are guide-owned content and are included (FR-009).
- Evolve updates the source page through the normal page flow; the region is refreshed by re-running the writer (the check fails until then, Clarifications).

## Output

Human-readable lines: `publish: <target> up to date` or `publish: <target> differs (<n> lines)` plus a unified diff in `--check`; errors on stderr with file and line.
