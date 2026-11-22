# Quickstart: validate captured visuals

Prerequisites: a checkout of this repository, `uv`, `node`/`npx`, podman with a running machine (macOS) or rootless podman (Linux), network access to `mcr.microsoft.com`, `ghcr.io`, and `docker.io`.

## 1. Unit tests (no podman)

```bash
make test        # includes test_visualcfg.py, test_visuals.py, test_runner.py, test_redact.py, test_render_cli.py
```

Expected: all pass; `test_render_cli.py` writes SVGs under pytest's tmp dir and asserts deterministic bytes, embedded fonts, styles, and redaction.

## 2. Podman smoke test

```bash
bash tests/adapters/test_visuals.sh
```

The script scaffolds a gfm guide (`tests/adapters/scaffold.sh`), writes the recipe from `tests/adapters/fixtures/visuals/` (an alpine CLI visual running `visuals/demo/colors.sh`, which prints colored output with the machine's real home path, user name, and host name substituted into the scratch copy by the script, and an nginx web visual with a seeded HTML page holding a table), then checks:

| Step | Expected |
|---|---|
| `make visuals` | exit 0; `docs/assets/visuals/colors.svg`, `docs/assets/visuals/table.png`, sidecars in `visuals/` |
| `grep -F` for the home path, the user name in path form, and the host name in images and sidecars | no match (SC-004) |
| `make check` after embedding both visuals with `visual:` citations (`tests/adapters/add_visuals.py gfm <guide> --embed-only`) | exit 0 |
| remove `table.png`, `make check` | fails with a `[visuals]` missing-image error; the image is restored afterwards |
| `uv run tools/guide/visuals.py drift` twice (GNU make would turn exit 10 into 2, so the script runs directly) | exit 0 both times (SC-002) |
| rename the `loss` header to `val-loss` in the seed page, drift again | exit 10; the report names `table`, shows the `columnheader "val-loss"` line, and `table.png` keeps its checksum (FR-030) |
| `podman ps -a --filter label=io.cc-guide.capture=1` and `podman network ls --filter label=io.cc-guide.capture=1` | empty (SC-006) |

The script prints the durations of the capture and of each drift round (the timings in `guide/docs/visuals.md` come from it). The Antora and MkDocs smoke tests (`test_antora.sh`, `test_mkdocs.sh`) embed the committed fixture visuals from `tests/adapters/fixtures/visuals/static/` without podman and check that the site and `make pdf` include them (US1 scenario 4).

It prints `SKIP: podman not available` and exits 0 when podman cannot run containers.

## 3. Manual look

Run the smoke test with `KEEP=1` to keep the guide project. Open `docs/assets/visuals/table.png` and check the outline, callout `1`, dimming, and crop; open `docs/assets/visuals/colors.svg` in a browser and check colors, bold, and the neutral prompt.

## 4. Workflow integration

- `/guide:evolve --visuals` in a guide without visuals: `uv run tools/guide/visuals.py init` writes `visuals.yaml` and `visuals/.gitkeep`; the Makefile targets are present (new scaffolds have them); `make check` passes. The toolkit must be 0.6.0 or later.
- Read `guide/skills/create/SKILL.md` plan instructions: proposed visuals per page, placeholders only with a ruling when podman is missing.
