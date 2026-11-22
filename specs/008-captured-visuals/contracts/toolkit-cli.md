# Contract: toolkit commands and build targets

## `tools/guide/visuals.py`

PEP 723 script (`pyyaml`), run from the guide root with `uv run tools/guide/visuals.py <command>` (or `--root DIR`).

| Command | Behavior | Exit |
|---|---|---|
| `validate` | Schema check of `visuals.yaml` (FR-007); no podman | 0 ok, 1 problems, 0 with `no visuals declared` |
| `capture [NAME...]` | Capture all or the named visuals (FR-008 to FR-022); writes images to the adapter `visual_dir` and sidecars to `visuals/`; prints a summary table | 0 all captured or skipped, 1 any visual or environment failed, 2 recipe/config error, no podman, or lock held |
| `drift [NAME...] [--format markdown\|json]` | Recapture into `.guide/visuals/<run-id>/out/` and compare (FR-027 to FR-029); never touches committed files; writes `report.md` and `report.json` in the run directory and prints the chosen format | 0 no drift, 10 drift, 2 environment failure, recipe/config error, no podman, lock held |
| `init` | For `/guide:evolve --visuals` (FR-034): write `visuals.yaml` from `tools/guide/templates/visuals.yaml` (copied by the scaffold script) when missing, create `visuals/` with a `.gitkeep`, and report what it created | 0, 1 when the guide has no adapter descriptor |
| `placeholder NAME...` | Write placeholder sidecars for declared visuals without a capture (FR-031a) | 0, 1 unknown name |
| `version` | Print the capture environment version (R3) | 0 |

`NAME` selects visuals; for drift, a selected visual brings its variants.

Summary line format for `capture`: `<status>  <name>[ (<variant>)]  <detail>` with status `captured`, `failed`, `skipped`.

## `tools/guide/capture/runner.py` (inside the capture container only)

| Command | Behavior |
|---|---|
| `ready --url URL --timeout S` | Poll until HTTP status < 400; exit 0, or 1 with the last status or error |
| `web --job /work/job.json --visual NAME [--variant light\|dark]` | Run the steps, redact, mask, annotate, crop, screenshot to `/work/out/<name>[-dark].png`, write `/work/out/<name>[-dark].result.json` (`text`, `highlights`, `redaction` counts, `masks`, `scripts`, `error`) |
| `cli --job /work/job.json --visual NAME` | Read `/work/raw/<name>.bin`, render to `/work/out/<name>.svg`, write `/work/out/<name>.result.json` (`text`, `style`, counts) |
| `diff A.png B.png --tolerance N` | Print `{"diff": <percent>}` |

Script steps: `visuals/scripts/<file>.py` defines `def run(page, base_url): ...`; the runner imports it with `importlib` and calls it with the Playwright page and the environment base URL.

## Changed toolkit scripts

- `check.py`: rule family `visuals` (FR-023); stale and behind-baseline are warnings printed as `path: [visuals] warning: ...` and do not affect the exit status.
- `sources.py`: `visual:<name>` reference kind (FR-026).
- `guidecfg.py`: `visual` is a reserved source id.
- `drift.py --check`: per drifted source, `affected_visuals: [names]` in JSON and an "Affected visuals" line in Markdown (FR-030a).
- `doctor.py`: new `optional` mapping in `adapter.yaml`; podman is listed there, a missing optional tool is a warning ("optional, needed for make visuals and make visuals-drift") and never fails `make doctor`.

## Build targets (every adapter Makefile)

```make
make visuals                 # uv run tools/guide/visuals.py capture $(VISUALS)
make visuals-drift           # uv run tools/guide/visuals.py drift $(VISUALS)
```

`make help` lists both. `make check` does not capture.
