# Implementation Plan: Captured visuals (web UI screenshots and rendered CLI output)

**Branch**: `008-captured-visuals` | **Date**: 2026-11-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/008-captured-visuals/spec.md`

## Summary

Guides gain captured visuals: annotated, cropped web UI screenshots and rendered colored CLI output, produced unattended from a declarative recipe (`visuals.yaml`). A host orchestrator (`tools/guide/visuals.py`) starts a throwaway podman network with the tool containers and a pinned capture container (Playwright Python, Chromium, fonts), seeds fictional data, replays the recipe, redacts and masks text before anything is rendered, and writes images plus text sidecars. Checks, reviews, and drift work on the sidecars, so text-only models can verify visuals; drift compares a fresh capture with the committed one by computed image and text differences.

## Technical Context

**Language/Version**: Python 3.11+ (PEP 723 scripts run with `uv run`), Python 3.12 inside the capture container; shell for Makefiles and smoke tests; Markdown for skills.

**Primary Dependencies**: Host: `pyyaml` only. Capture container: `mcr.microsoft.com/playwright/python:v1.49.1-noble` (digest pinned), `pyte==0.8.2`, `fonttools[woff]==4.67.0`, `pillow` (pinned), `pyyaml` (pinned), DejaVu Sans Mono and Noto Color Emoji fonts (apt, pinned). Runtime: podman.

**Storage**: Files in the guide project (`visuals.yaml`, `visuals/`, adapter `visual_dir`) and scratch under `.guide/visuals/`.

**Testing**: pytest (`make test`) for host logic and the CLI renderer; `tests/adapters/test_visuals.sh` podman smoke test (skips without podman).

**Target Platform**: macOS (podman machine, arm64 or amd64) and Linux (rootless podman, including GitHub Actions `ubuntu-latest`).

**Project Type**: Claude Code plugin with a vendored Python/Node toolkit and Markdown skills.

**Performance Goals**: A cached capture image and a running tool image capture 10 visuals in under 3 minutes; first image build under 10 minutes.

**Constraints**: No Docker, no pip (uv), no em or en dash characters, toolkit imports nothing outside `tools/guide/`, no secrets or host values in committed files, no published host ports, `check.py` never needs podman.

**Scale/Scope**: Up to about 50 visuals per guide; SVGs under 2 MB.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is the unfilled template, so there are no ratified principles to gate on. The repository rules in `CLAUDE.md` act as the gate:

| Rule | Status |
|---|---|
| No em or en dash characters; tests build them with `chr()` | Pass (all new files checked with `rg`) |
| uv instead of pip; podman instead of Docker | Pass (Containerfile uses `uv pip install --system`; podman only) |
| No secrets or raw inputs in guide projects, fixtures, run records | Pass (host values only in scratch `job.json`; sidecars carry rule ids; SC-004 test) |
| Outward actions shown and approved | Pass (CI workflow installed only when the author agrees; no pushes) |
| Toolkit self-contained (`guide/toolkit/` imports nothing outside) | Pass (capture build context is `tools/guide/capture/`) |
| Scripts never `cd` into `.guide/cache/` | Pass (visuals use `.guide/visuals/` only) |

Post-design re-check: pass, no violations; Complexity Tracking stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/008-captured-visuals/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── visuals-yaml.md
│   ├── sidecar.md
│   ├── toolkit-cli.md
│   └── workflow.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
guide/toolkit/
├── visuals.py                  # NEW host orchestrator: validate, capture, drift, init, placeholder, version
├── visualcfg.py                # NEW recipe loader, schema check, fingerprint, sidecar read/write, capture env version (shared by visuals.py and check.py)
├── capture/                    # NEW capture container build context
│   ├── Containerfile
│   ├── runner.py               # container entry: ready, web, cli, diff
│   ├── web.py                  # Playwright steps, redaction in page, overlays, aria snapshot
│   ├── render_cli.py           # pyte + SVG renderer (also runnable on the host for tests)
│   └── redact.py               # default rules, recipe rules, masks (pure Python)
├── check.py                    # + visuals rule family
├── sources.py                  # + visual:<name> references
├── guidecfg.py                 # + reserved source id `visual`
├── drift.py                    # + affected_visuals per drifted source
└── doctor.py                   # + optional podman
guide/adapters/{antora,mkdocs,gfm}/
├── adapter.yaml                # + visual_dir, podman optional in requires
└── scaffold/Makefile           # + visuals, visuals-drift targets
guide/templates/
├── visuals.yaml                # NEW commented recipe skeleton
└── guide-visuals.yml           # NEW CI workflow
guide/skills/{create,evolve,page-task,preflight}/   # skill text changes
guide/scripts/deps.sh           # + podman detection
guide/commands/evolve.md        # + --visuals
guide/docs/visuals.md           # NEW author reference
tests/toolkit/
├── test_visualcfg.py           # schema, fingerprint, sidecar
├── test_visuals.py             # orchestration with a fake podman
├── test_redact.py
├── test_render_cli.py
└── (additions to test_check.py, test_sources.py, test_guidecfg.py, test_drift.py, test_doctor.py, test_workflows.py, test_deps.py)
tests/adapters/
├── test_visuals.sh             # NEW podman smoke test
└── fixtures/visuals/           # NEW recipe, seed page, expected texts
```

**Structure Decision**: Extend the existing toolkit, adapters, templates, and skills in place; add one new host module pair (`visuals.py`, `visualcfg.py`) and one container build context (`capture/`). This matches how specs 001 to 007 grew the plugin.

## Design notes for implementers

1. **Shared logic in `visualcfg.py`**: recipe parsing and validation, defaults resolution, visual and environment lookup, fingerprint (research R11), capture environment version (R3), sidecar load and dump (`contracts/sidecar.md`), adapter `visual_dir` lookup, `visual:` reference parsing helper. `check.py` imports it; it must not import podman logic.
2. **Podman wrapper**: `visuals.py` calls podman through one small class (`Podman.run(args) -> CompletedProcess`) so `test_visuals.py` can inject a fake that records calls and returns canned output. No other module shells out to podman.
3. **Run sequence (capture and drift)** (drift additionally copies committed PNGs into `<run dir>/committed/` so the container can diff them): lock, sweep stale labeled resources, ensure the capture image, create the network, start the capture container (`--network`, `--hostname capture`, mounts `visuals/` at `/visuals:ro` and the run dir at `/work`), for each needed environment start the tool container (`--network`, `--hostname <env>`, `/visuals:ro`, env vars, labels), readiness via the runner, seed steps via `podman exec`, then visuals (CLI: host pty exec then `runner.py cli`; web: `runner.py web` per variant), then teardown in `finally`.
4. **Placing outputs**: capture moves `/work/out/<name>.{png,svg}` into the adapter `visual_dir` and writes the sidecar from the result JSON plus provenance; a failed visual leaves committed files untouched (FR-012). Drift reads the committed sidecar and compares with the result JSON and `runner.py diff`.
5. **Dark variant decision**: after capturing light and dark, compare their texts and run `diff`; equal text and diff below threshold means `dark: skipped` (FR-037).
6. **check.py visuals rules**: run only when `visuals.yaml` exists or an image under `visual_dir` is embedded. Page image embeds are found per adapter (`image::visuals/...` for Antora, Markdown image syntax for MkDocs and gfm). Confidential terms reuse the existing confidential configuration loader.
7. **Skill edits** follow `contracts/workflow.md`; keep FR numbers in the text as other skills do.
8. **No dash characters**: tests that need them build them with `chr(0x2014)` and `chr(0x2013)`.

## Complexity Tracking

No violations.
