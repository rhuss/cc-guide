# Guided Demo Report

**Feature**: cc-guide, a plugin for source-verified guides
**Date**: 2026-10-01
**Spec**: specs/001-cc-guide-plugin/spec.md
**Result**: 6 passed, 0 skipped, 0 failed, 1 manual (out of 7)

---

## Triage Summary

| Tier | Count | Detail |
|------|-------|--------|
| full | 6 | All infrastructure available (tool chain, today's e2e guide at `~/Development/context-engineering/cc-guide-e2e/minisvc-guide`, free ports, pdftotext) |
| manual | 1 | Upstream filing and cluster validation deferred by the author; procedures in `tests/manual/` |

User selection: "Run what's ready" (flows 1 to 6; flow 7 recorded as manual).

---

## Flow 1: Validation gates

**Tier**: full
**Covers**: FR-001, FR-002, FR-003, FR-003a, FR-004, FR-016, FR-017, FR-018, FR-019, FR-020, FR-021, FR-042

### Setup
None (repository worktree as checked out).

### Evidence
**Execution**: `make validate`; `bash guide/scripts/superpowers-probe.sh`; `make test`; `bash tests/adapters/test_antora.sh`
**Output**: both manifests "Validation passed"; probe JSON `{version: 6.4.1, known: true, ok: true, problems: []}`, exit 0; `463 passed in 45.32s`; adapter smoke test 9/9 PASS including "planted confidential term fails make check" and "shareable tarball has no internal/ path".

### Verdict: PASS

**Verify yourself**:
1. `make validate test` in the repository
2. `bash tests/adapters/test_antora.sh`; expect 9 PASS lines

---

## Flow 2: Create-run evidence (real run of 2026-10-01)

**Tier**: full
**Covers**: FR-005, FR-005b, FR-005c, FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, FR-012, FR-013, FR-013a, FR-014, FR-015

### Setup
None; reviews the artifacts of the standard-rigor create run executed earlier today in headless sessions (recorded in `tests/manual/us1-create.md`).

### Evidence
**Execution**: inspected `baseline.yaml`, `inputs.yaml`, `git ls-files`, the superpowers ledger, `runs/2026-10-01-create.md`, `runs.py resume`, and a page scan in the e2e guide.
**Output**: baseline pins the source by full SHA with `captured: 2026-10-01`; the input register holds checksums and the confidential flag while `git ls-files` shows no raw input; the ledger records 8 completed tasks with reviews, 9 rulings, and both transcript claims as `rejected-by-source` with the contradicting source line; the run summary records rigor standard, 10 review dispatches, and upstream finding UF-1; `resume` prints `done`; no page contains the planted ports 7070 or 8080. The resume behavior itself was exercised earlier today: a killed session continued at task 3 in a fresh session without redoing tasks 1 and 2.

### Verdict: PASS

**Verify yourself**:
1. In `~/Development/context-engineering/cc-guide-e2e/minisvc-guide`: `rg rejected-by-source .superpowers/sdd/plan/progress.md`
2. `less runs/2026-10-01-create.md`

---

## Flow 3: Live preview with reload

**Tier**: full
**Covers**: FR-030, FR-016a

### Setup
Started `make preview OPEN=0 PORT=<free>` in the e2e guide.

### Evidence
**Execution**: curl of a built page, append of a marker line to `user/check-status.adoc`, curl until the marker appeared, revert, curl until it disappeared, server stopped by port.
**Output**: first build served in under 2 s; the marker was served 3 s after the edit and gone 3 s after the revert; the watcher stopped cleanly and the working tree ended clean. (First attempt used a page name that does not exist in this guide; the 404 and the stray file were the demo script's fault, were cleaned up, and the corrected run behaved as specified. FR-016a's linked-worktree build is additionally covered by `tests/adapters/timing.sh`, recorded in `tests/manual/README.md`.)

### Verdict: PASS

**Verify yourself**:
1. `make preview` in the guide, edit any page, watch the browser refresh

---

## Flow 4: PDF export with the leak gate

**Tier**: full
**Covers**: FR-030a, FR-030b, FR-030c, FR-030d, FR-030e, FR-030f

### Setup
Deleted the shareable PDF and regenerated it with `make pdf` (which runs `make check` first).

### Evidence
**Execution**: `make pdf`; `pdftotext` on both PDFs.
**Output**: exit 0; title page shows the guide title, "Verified against the baseline captured on 2026-10-01", and the pinned source; 0 confidential hits in the shareable PDF; the internal PDF carries the INTERNAL marker 12 times and the `-INTERNAL` file name. (The no-partial-PDF-on-failure path is covered per format by `tests/adapters/test_pdf.sh`.)

### Verdict: PASS

**Verify yourself**:
1. `open dist/minisvc-admin-and-user-guide-2026-10-01.pdf` in the guide

---

## Flow 5: Drift check-only mode

**Tier**: full
**Covers**: FR-025, FR-025a, FR-025b (workflow template installed by opt-in; CI execution deferred with flow 7)

### Setup
None for the negative case; for the positive case the tracked `pinned` branch of the fixture source was advanced two commits and restored afterwards.

### Evidence
**Execution**: `uv run tools/guide/drift.py --check` three times (before, during, after).
**Output**: exit 0 with the tracked ref unmoved and both inputs reported unchanged; exit 10 after the ref moved, reporting `deleted Makefile`, `modified config/defaults.yaml`, and `renamed docs/setup.md -> docs/install.md`, each mapped to the pages citing it (6 affected pages); exit 0 again after the restore. The guide itself was never modified.

### Verdict: PASS

**Verify yourself**:
1. `uv run tools/guide/drift.py --check` in the guide; expect "no drift"

---

## Flow 6: Diagram gate, rounds, and hand-off record

**Tier**: full
**Covers**: FR-022, FR-022a, FR-023, FR-023a, FR-023b, FR-024

### Setup
None; reviews the artifacts of today's diagram task (three rounds, one author hand-off, recorded in `tests/manual/us1-create.md`).

### Evidence
**Execution**: read each round's `check.txt` and `review.md`, the embedded image macro, and the canvas backup.
**Output**: gate 0 findings in all three rounds; controller verdicts accepted / needs fixes / accepted (round 2's orphaned label and stale legend row were caught by the crop review although the mechanical gate was clean); the image is embedded with a quoted alt text and `role=expand`; the author's 40-element canvas backup is kept read-only and was restored after the task.

### Verdict: PASS

**Verify yourself**:
1. `ls .guide/diagrams/01-architecture/round*/` in the guide
2. `open content/modules/ROOT/images/01-architecture.svg`

---

## Flow 7: Upstream filing and cluster validation

**Tier**: manual
**Covers**: FR-031, FR-032, FR-033, FR-034, FR-035, FR-036, FR-037, FR-038, FR-039, FR-039a, FR-040

### Verdict: MANUAL

Deferred by the author (needs a throwaway GitHub repository and a kind cluster). Deterministic parts are covered by unit tests (173 classifier tests, 33 upstream tests) and the offline eval case. Manual procedure:

1. Follow `tests/manual/us5-upstream.md`: push the fixture source to a private repository, collect findings, run `/guide:upstream`, approve one draft, verify the filed issue URL is recorded.
2. Follow `tests/manual/us6-validate.md`: kind cluster via podman, read-only tier, refused full tier on a non-disposable connection, full tier with per-command confirmation.

---

## FR Coverage

| FR group | Flow | Verdict |
|----|------|---------|
| FR-001..004, FR-042 (structure, dependencies, probe, session notice) | Flow 1 | PASS |
| FR-016..021 (adapter contract, checks, packages, rigor) | Flow 1 (plus `make test-adapters`, 58 checks) | PASS |
| FR-005..015 (create, inputs, baseline, reviews, resume, rulings, experimental) | Flow 2 | PASS |
| FR-030, FR-016a (preview, worktrees) | Flow 3 | PASS |
| FR-030a..030f (PDF) | Flow 4 | PASS |
| FR-025, FR-025a, FR-025b (drift) | Flow 5 | PASS |
| FR-022..024 (diagrams) | Flow 6 | PASS |
| FR-026..029 (evolve, adoption) | partially: adoption migration and drift on a SAW copy ran (`tests/manual/us2-evolve.md`); full evolve run open | not demonstrated live |
| FR-031..040 (upstream, validate) | Flow 7 | MANUAL |
| FR-041 (documentation) | inspection: `guide/docs/learnings.md`, `settings.md`, `adapters.md` exist and are current | not a runtime behavior |

## Notes

- SC-002's independent sample from today's standard run was 80% (target 95%); review rules were tightened in response (commit 2b9e08e) and a re-measurement run is open. Recorded in `tests/manual/us1-create.md`.
- The strict half of SC-010 (claim ledger run) is open; the fast half passed.
