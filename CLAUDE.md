# cc-guide repository rules

This repository holds the Claude Code plugin `guide` (in `guide/`), its tests (`tests/`), and its evaluation suite (`eval.yaml`, `eval/cases/`). The design lives in `specs/001-cc-guide-plugin/`.

## Rules for every change

- No em dash or en dash characters in any file. Rephrase, or use commas, parentheses, or separate sentences. Tests that need such a character build it from its code point (`chr(0x2014)`, `chr(0x2013)`).
- Use `uv` instead of pip, and podman instead of Docker in any container instruction.
- Never write secrets, tokens, kubeconfig content, or raw inputs (transcripts, notes, ticket exports) into a guide project, a fixture, or a run record.
- Every outward action (creating a remote repository, pushing, filing an issue or pull request, changing a cluster) is shown in full and runs only after explicit approval.
- Dispatch subagents without a model override; they inherit the session model.
- Git commits end with the trailer `Assisted-By: 🤖 Claude Code`.
- Scripts never `cd` into `.guide/cache/` and never run git there except through `git -C <cache path>` from the guide project root.
- Never commit `.mcp.json`.

## Layout

- `guide/toolkit/`: format-neutral Python (PEP 723, run with `uv run`) and Node scripts. Create copies it into each guide project as `tools/guide/`, so it must not import anything from outside its own directory.
- `guide/toolkit/capture/`: the build context of the capture environment for captured visuals (specs/008): `Containerfile` (pinned base image digest, uv, fonts), the container-side `runner.py`, `web.py` (Playwright), `render_cli.py` (pyte to SVG), `redact.py` (also imported by the host scripts), and the font licenses. Its file hash is the capture environment version, so any change there marks every captured visual stale. `guide/toolkit/visuals.py` is the host orchestrator (the only code that runs podman); `visualcfg.py` holds the recipe model, fingerprints, and sidecars shared with `check.py` and `drift.py`.
- `guide/adapters/<format>/`: `adapter.yaml` plus the scaffold copied into a new guide project, and an optional `branding/` directory (Antora: logo template, UI bundle contract, MPL-2.0 notice, and the vendored Red Hat fonts in `fonts/` with their OFL license and manifest) that the scaffold script vendors to `tools/guide/branding/`. `fonts/update-fonts.py` is a maintainer tool that stays in the plugin.
- `guide/skills/`, `guide/commands/`: the plugin behavior. Commands are thin wrappers around the skill of the same name.
- `tests/toolkit/`: pytest for the toolkit. `tests/adapters/`: shell smoke tests per format. `tests/manual/`: recorded quickstart runs.

## Commands

```bash
make validate        # claude plugin validate on the marketplace and the plugin
make test            # pytest for the toolkit
make test-adapters   # adapter smoke tests (needs node, npx, uv, pandoc, Playwright Chromium; test_visuals.sh needs podman and skips without it)
make install         # install the plugin from this checkout
```
