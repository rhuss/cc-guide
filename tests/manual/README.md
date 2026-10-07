# Manual and end-to-end verification

Evidence for the final verification gate. Automated suites run with `make validate test test-adapters`; scenarios that need an interactive Claude Code session, a GitHub repository, or a cluster are recorded in the per-story files.

| File | Scenarios | State |
|---|---|---|
| this file | quickstart 1, 2, 5, 10 and the timing checks (T064) | automated parts run; session parts open |
| [us1-create.md](us1-create.md) | 3 and 4 (create, resume, SC-002, SC-010, SC-013), 3 with gfm | procedure; needs an interactive run |
| [us2-evolve.md](us2-evolve.md) | 6 and 7 | drift check and SAW adoption/drift run; session parts open |
| [us5-upstream.md](us5-upstream.md) | 8 | procedure; needs a throwaway GitHub repository |
| [us6-validate.md](us6-validate.md) | 9 | procedure; needs cluster connections |
| [002-antora-branding.md](002-antora-branding.md) | feature 002 quickstart 1 to 4 (Antora branding) | run; create and evolve session parts open |

## Automated suites (2026-10-01, macOS, Node 26, uv 0.8, Pandoc 3.11)

| Command | Result |
|---|---|
| `make validate` | marketplace and plugin manifests pass |
| `make test` | 448 passed |
| `make test-adapters` | exit 0; 58 checks across `test_antora.sh` (9), `test_mkdocs.sh` (9), `test_gfm.sh` (11), `test_pdf.sh` (all three formats, both views, planted failure), `test_preview_antora.sh` (7), `test_preview_mkdocs.sh` (7) |

## Scenario 1: plugin structure and dependency checks

| Expectation | Result |
|---|---|
| `make validate`, `make test` pass | pass (above) |
| Without superpowers, `/guide:create` stops in its first step, names superpowers, shows the install command, writes nothing | Changed by the manifest dependency (T001): Claude Code itself refuses to load the plugin and prints `Dependency "superpowers@claude-plugins-official" is not installed, run claude plugin install superpowers@claude-plugins-official` (verified with an isolated `HOME`). The runtime probe covers a missing or changed superpowers when the dependency check passes (`test_probe.py`: not installed, unknown version, missing script). An interactive session with superpowers disabled is still open. |
| Without cc-prose, `/guide:create` continues with a one-line notice | Not run (needs a session); the notice text is in the preflight skill, and `deps.sh` reports `prose: false` in `test_deps.py`. |

## Scenario 2: adapter smoke tests

Covered by `make test-adapters` for every format: `make doctor check dist`, the shareable PDF (title page with title, baseline date, and commits; every page title in navigation order; no confidential term), the internal PDF (`-INTERNAL` file name, INTERNAL in every footer), a planted em dash failing `make check` with no PDF written, and a planted `ACME Corp` failing `make check`.

## Scenario 5: preview

`test_preview_antora.sh` and `test_preview_mkdocs.sh`: serves the site, the browser-sync client is injected, a change rebuilds, a broken page keeps the last good site, and the fix recovers. gfm uses `markserv` (no build step, so nothing can break); its reachability is measured below. The `/guide:preview` command in a session (browser opens, editing refreshes) is still open.

## Timing checks on the 25-page fixture (`bash tests/adapters/timing.sh`)

| Format | Preview reachable (SC-008, < 60 s) | `make pdf` (SC-011, < 180 s) | `drift.py --check` (< 120 s) |
|---|---|---|---|
| antora | 1.6 s | 3.8 s | 0.4 s |
| mkdocs | 1.1 s | 4.1 s | 0.4 s |
| gfm | 1.1 s to 1.6 s | 7.1 s to 7.5 s | 0.4 s to 0.5 s |
| antora from a linked worktree (`.claude/worktrees/001-timing`) | 1.1 s | `make site pdf` 5.1 s | |

The drift timing uses the local fixture repository. Against the SAW guide's three GitHub sources (one of them OpenShell), the first drift run took 18 s including the blobless clones (`us2-evolve.md`).

## Scenario 10: behavioral evals

Not run during implementation (each case starts Claude Code sessions). Run with:

```bash
export CC_GUIDE_PLUGIN="$PWD/guide"
# then in Claude Code: /eval-run
```

The upstream case's scene was verified by hand: its setup script builds the source repository and guide project, and mechanical re-verification reports `UF-1 reverified` and `UF-2 needs-review` (quoted text gone on the default branch), which the skill must turn into `dropped`.
