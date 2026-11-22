# Code Review: Captured visuals (web UI screenshots and rendered CLI output)

**Spec:** specs/008-captured-visuals/spec.md
**Date:** 2026-11-22
**Reviewer:** Claude (speckit.spex-gates.review-code)
**Change:** `git diff main...HEAD` on branch `008-captured-visuals`

## Compliance Summary

**Overall Score: 98% (50.5 of 51 checks)**

- Functional Requirements: 39.5/40 (99%) (FR-001 to FR-037 with FR-002a, FR-030a, FR-031a)
- Edge Cases: 11/11 (100%)
- Error handling (US1-3, US2-3, US2-5, FR-002a, FR-012, FR-028 exit codes): covered inside the FR count
- Spec-declared constants: none (the spec has no `## Constants` section)

## Detailed Review

### Recipe file

| Req | Implementation | Status |
|-----|----------------|--------|
| FR-001 | `guide/toolkit/visualcfg.py` `RECIPE`, `load_recipe` | Compliant |
| FR-002 | `visualcfg._check_environment` (web/cli, `kind-cluster` "not supported yet", `source:` against baseline, host-name env names); `visuals.Run.start_environment` / `start_capture` (`--network-alias`, `--hostname`, `GUIDE_ENV_<NAME>_URL` via `url_vars`) | Compliant |
| FR-002a | `capture/runner.py ready` (status < 400, polled from the capture container); `visuals.Run.wait_ready` (last status plus `podman logs --tail 40`) | Compliant |
| FR-003 | `visualcfg._image_ok` (no tag, `latest`) | Compliant |
| FR-004 | `visuals.Run.seed` (`in: tool` default, `in: capture`), seed files under `visuals/` checked by `_visual_file` and mounted read-only | Compliant |
| FR-005 | `visualcfg._check_steps` (step set, one crop, distinct labels, selector forms); `capture/web.py capture`, `locate`, `run_script(page, base_url)` | Compliant |
| FR-006 | `visualcfg._check_visual` (cli keys), `visuals.Run.run_cli` (host pty via `podman exec -t`, `COLUMNS`, `TERM=xterm-256color`, `env_vars`) | Compliant |
| FR-007 | `visualcfg.validate`, `visuals.py validate` (path with visual name and zero-based step index, no podman) | Compliant |

### Capture run

| Req | Implementation | Status |
|-----|----------------|--------|
| FR-008 | `visuals.Run.execute` (teardown in `finally`, SIGINT/SIGTERM raise), `labels()`, `sweep()` (dead pid on this host), `acquire_lock` (exit 2 "capture already running") | Minor deviation: labels carry a 12 hex hash of the guide path and of the host name, not the raw path and host. The sweep needs only host identity and pid, and the hash keeps host values out of `podman inspect` output. Spec evolution candidate. |
| FR-009 | `capture/Containerfile` (digest-pinned base and uv, pinned apt and Python packages, DejaVu and Noto Color Emoji with licenses), `visualcfg.capture_env_version`, `Run.ensure_image` (`localhost/cc-guide-capture:<hash>`) | Compliant |
| FR-010 | No kubeconfig, credential, or host network mount; only `visuals/` (read-only) and the run directory are mounted | Compliant |
| FR-011 | No `-p`/`--publish` in any `podman run`; readiness from the capture container | Compliant |
| FR-012 | `Run.execute` (per-visual try), `capture_web` (failed variant leaves committed files), `cmd_capture` exit 0/1/2, `_load` prints "no visuals declared" before `check_podman` | Compliant |
| FR-013 | `web.py` StepError path writes `/work/debug/<stem>-step<N>.png` (redacted) | Compliant |
| FR-014 | `web.py` context: fixed viewport, device scale 2, `en-US`, `UTC`, reduced motion, still CSS, fixed clock | Compliant |

### Output

| Req | Implementation | Status |
|-----|----------------|--------|
| FR-015 | `visual_dir` in the three `adapter.yaml` files, `visualcfg.visual_dir`, `Visual.extension` | Compliant |
| FR-016 | `capture/render_cli.py` (pyte, SGR colors, bold, dim, italic, underline, WOFF2 subsets, CBDT emoji PNGs, 2 MB limit) | Compliant |
| FR-017 | `visuals.Run.sidecar`, `env_record` (digest, platform, source, source_commit), `visualcfg.fingerprint` (entry, env, seed and file hashes, scripts, rule templates, masks, capture env version) | Compliant |
| FR-018 | `redact.apply` masks after rules; `render_cli.redact_cells`; `web.redact_page` before snapshot and screenshot | Compliant |

### Annotations, redaction

| Req | Implementation | Status |
|-----|----------------|--------|
| FR-019 | `web.OVERLAY_JS` (outline, badge placed outside the box, dimming mask), crop clip with `MARGIN` | Compliant |
| FR-020 | Boxes from `getBoundingClientRect` at capture time | Compliant |
| FR-021 | `capture/redact.py DEFAULT_RULES` (home, user path, user@, k8s API, host, IPv4 with exemptions incl. run subnet, JWT, bearer, API keys) | Compliant |
| FR-022 | `redaction.rules`, `disable_redaction`, recorded under `redaction.disabled` | Compliant |

### Checks and review

| Req | Implementation | Status |
|-----|----------------|--------|
| FR-023 | `check.check_visuals` (undeclared embed, missing image or sidecar, unredacted, undeclared `visual:`, embed without citation, confidential terms and patterns, schema problems; warnings for placeholder, stale, rebaseline) | Compliant |
| FR-024 | `check_visuals` reads committed files only | Compliant |
| FR-025 | `guide/skills/page-task/page-review-guide.md` item 9 | Compliant |
| FR-026 | `sources.parse_ref` (`visual:`), `guidecfg.VISUAL_ID` reserved in `load_baseline` | Compliant |

### Visual drift

| Req | Implementation | Status |
|-----|----------------|--------|
| FR-027 | `DriftRun.compare`, `committed_diff`, `runner.image_diff` (tolerance 16), CLI style fingerprint, `text_diff` over text and highlights only | Compliant |
| FR-028 | `DriftRun.compare` (threshold, platform mismatch), `drift_visual` (recapture failed with step and selector), `drift_exit` (10/0/2) | Compliant |
| FR-029 | `drift_markdown`, `report.json` | Compliant |
| FR-030 | `DriftRun` never calls `place` | Compliant |
| FR-030a | `drift._affected_visuals`, `to_markdown` | Compliant |

### Workflow integration and variants

| Req | Implementation | Status |
|-----|----------------|--------|
| FR-031 | `guide/skills/create/SKILL.md` spec and plan instructions | Compliant |
| FR-031a | `guide/scripts/deps.sh` `podman`, preflight skill, create 6b2, `visuals.py placeholder` | Compliant |
| FR-032 | create SKILL.md (platform-only UIs noted as out of scope) | Compliant |
| FR-033 | evolve SKILL.md step 2a, impact set, plan instructions | Compliant |
| FR-034 | evolve SKILL.md section 3b, `visuals.py init` | Compliant |
| FR-035 | three scaffold Makefiles, `optional: podman` in adapters, `doctor.py` warn status | Compliant |
| FR-036 | `guide/templates/guide-visuals.yml` | Compliant |
| FR-037 | `Visual.outputs`, `Run.capture_web`, `dark_equals_light`, validate `-dark` collision, `DriftRun.drift_visual` skipped-now-differs | Compliant |

### Edge Cases

All eleven edge cases map to implemented behavior: duplicate names (`_UniqueKeyLoader`), unsafe names (`VISUAL_NAME_RE`), missing podman (`check_podman`, doctor), unpullable image (`start_environment`), busy host port (none published), wide output (`wrap` at width 100 default), emoji (`_Emoji`), volatile values (masks), dark equals light (`skipped`), script steps (`scripts` in sidecar), no recipe ("no visuals declared", exit 0), confidential sidecar text (check).

### Extra Features (Not in Spec)

- `visuals.py version` (prints the capture environment version): helpful, small.
- `print-pdf.mjs` drops links that wrap images: needed so visuals in MkDocs/gfm print as images (supports US1-4).

## Recommendations

### Spec Evolution Candidates
- [ ] FR-008: state that labels carry identifiers (hashes) of the guide path and host rather than raw values.

## Deep Review Report

**Gate: PASS** (after fix round 1 of 3). Details per finding: `review-findings.md`.

| Agent | Found | Fixed | Remaining | Status |
|-------|-------|-------|-----------|--------|
| Correctness | 7 | 3 | 3 Minor, 1 Notable | completed |
| Architecture & Idioms | 9 | 2 | 6 Minor, 1 Notable | completed |
| Security | 9 | 7 | 1 Minor, 1 Notable | completed |
| Production Readiness | 9 | 6 | 2 Minor, 1 Notable | completed |
| Test Quality | 11 | 7 | 4 Minor | completed |
| Goal Alignment | 0 | 0 | 0 | skipped (no PR found) |
| CodeRabbit (external) | 10 | 10 | 0 | completed |
| Copilot (external) | 0 | 0 | 0 | skipped (disabled in config) |
| Codex (external) | 4 | 3 | 0 (1 rejected) | completed |
| Test Suite (regression) | 0 | 0 | 0 | passed |

The rows count raw reports before deduplication. After merging: 1 Critical (rejected as a false positive), 22 Important (all fixed), 23 Minor (9 fixed, 14 remaining), 4 Notable (captured to `brainstorm/idea-inbox.md`).

MVP: Test Quality (11 findings)

Key fixes:
1. Redaction completeness on web pages: shadow roots, same-origin iframes, more attributes, values split across inline elements, a second pass right before the screenshot, and element marks so `text=` selectors survive redaction (security, CodeRabbit).
2. Redaction of failure details (seed output, container logs, build and render errors) before they reach the console, reports, or the CI job summary (security, CodeRabbit).
3. The run network is `--internal`, so tools and pages have no route out (FR-010) (security).
4. Cleanup guarantees: resources recorded before creation, signals ignored during teardown, timeouts on every podman call, leftovers named on interrupt (production, correctness).
5. Scratch hygiene: earlier runs' job files and raw output deleted under the lock, run directories pruned, the job file private (codex, security).
6. `drift --format json` keeps stdout pure JSON; a failed image comparison is no longer "unchanged" (architecture, correctness, CodeRabbit).
7. check: dark images need `visual:<name>-dark`; embedded placeholders are not broken links (codex).
8. CLI: soft-wrapped secrets rejoined before redaction; quoted credential keys, OpenShift tokens, private keys, and case-insensitive host names (CodeRabbit, security).
9. evolve forwards `--visuals` to preflight; doctor probes podman with `podman info`; the CI workflow has a timeout, uploads the redacted reports and debug images, and shows the error tail (CodeRabbit, architecture, production).
10. Tests: web and token redaction against real values, emoji, a failing visual, and byte-identical recapture in the podman smoke test, plus pty, drift failure, cleanup, and redaction unit tests (test quality).

Post-fix spec coverage: 40/40 functional requirements verified, none dropped. The FR-008 label deviation (hashed guide path and host name) stays a spec evolution candidate.

Tests after fixes: `make test` 1289 passed, 1 skipped. `bash tests/adapters/test_visuals.sh` (podman 6.2.0) 36/36 checks pass, including no labeled container or network left after the failed run (SC-006).
