# User Story 1: create (quickstart scenarios 3 and 4)

These scenarios need an interactive Claude Code session with the plugin installed (`make install`), superpowers, and the time and cost of a full guide run (each page task dispatches an implementer and a reviewer). They were **not run during implementation**; this file is the procedure and the place to record the results.

## Setup

```bash
# from the cc-guide checkout
make install
SCRATCH=$(mktemp -d)
bash tests/fixtures/make-mini-repo.sh "$SCRATCH/mini"     # prints FIRST, SECOND, THIRD
git -C "$SCRATCH/mini" checkout -q "$(git -C "$SCRATCH/mini" rev-list --max-parents=0 HEAD)" -b pinned
```

The `pinned` branch keeps the source at its first commit (README says port 8080, config says 9090; the transcript claims an admin UI on port 7070, which no source supports).

## Scenario 3: create with Antora (and later gfm, T039)

In a new session:

```text
/guide:create --dir /tmp/guide-demo --format antora --source mini=<SCRATCH>/mini@pinned \
  --input <cc-guide>/tests/fixtures/mini-transcript.txt \
  --input <cc-guide>/tests/fixtures/mini-confidential-notes.txt \
  "Admin and user guide for minisvc"
```

Intake answers: personas admin and user, rigor standard, internal part yes with the confidential term `ACME Corp` and the pattern `\b[A-Z]{2,}-\d+\b`, the notes input confidential, no remote, no drift schedule.

Record:

| Expectation | Result |
|---|---|
| `inputs.yaml` lists both inputs with checksums; neither file is in the repository | |
| `baseline.yaml` pins `mini` by its full first-commit SHA | |
| The plan is shown for approval before any page is written | |
| Every page task is followed by a review (ledger shows `review` lines per task) | |
| The port 7070 claim is on no page; the run summary lists it under "Review findings rejected by source" | |
| `make check` passes; every page has a source block | |
| `findings/upstream.yaml` contains the README port drift (README.md line 8 vs config/defaults.yaml) | |
| `ACME Corp` appears only on internal pages; `make check` and `make dist` pass | |

### SC-002: independent factual sample

Pick at least 15 factual statements across the shareable pages yourself (not from the run's review tables) and check each against `.guide/cache/mini/` at the pinned commit.

| # | Page:line | Statement | Supported? |
|---|---|---|---|

Supported share: __ / __ (target at least 95%).

### SC-010: fast versus standard

Run the same scenario a second time into `/tmp/guide-demo-fast` with `--rigor fast`. Compare the "Review dispatches" field of both run summaries (`runs/<run-id>.md`).

| Run | Review dispatches |
|---|---|
| standard | |
| fast | |

Target: fast at most half of standard.

### SC-013: diagram

Ask for one architecture diagram in the intake (Excalidraw MCP server running, canvas open in a browser).

| Expectation | Result |
|---|---|
| `diagram_check.py check` reports zero findings on the accepted round | |
| `.guide/diagrams/<name>/round<N>/review.md` holds the controller's crop review | |
| At most two automated fix rounds before the manual hand-off | |
| Manual hand-off exercised once (decline the automated result, edit on the canvas, say "done") | |

## Scenario 4: resume

During scenario 3, stop the session after two page tasks are complete (the ledger shows two `complete` lines). Start a new session in `/tmp/guide-demo` and run `/guide:create` again.

| Expectation | Result |
|---|---|
| It reports "Resuming the guide run at task 3" | |
| Tasks 1 and 2 are not dispatched again (ledger and git log) | |

## Run 1 (2026-10-01): antora, standard rigor, headless sessions

Driven from the implementing session with headless Claude Code (`claude -p --plugin-dir guide`, the author answering intake and approval questions relayed by the driver). Guide kept at `~/Development/context-engineering/cc-guide-e2e/minisvc-guide` (source copy in `mini-source/`, inputs in `inputs/`). Intake as specified above; no diagrams. Plan: 8 pages (7 shareable, 1 internal). Cost about 18 USD plus the interrupted turn; wall time about 70 minutes of page work.

### Scenario 3

| Expectation | Result |
|---|---|
| `inputs.yaml` lists both inputs with checksums; neither file is in the repository | pass (locations outside the project, sha256 recorded, `git ls-files` has no input file) |
| `baseline.yaml` pins `mini` by its full first-commit SHA | pass (`7ca3fb3...`; port, bind, timeout read from the source as attributes) |
| The plan is shown for approval before any page is written | pass (8 pages, 17 dispatches estimated; content directories untouched until "approve") |
| Every page task is followed by a review | pass (8 of 8 `review clean`, two after a controller fix verified against the source) |
| Port 7070 claim on no page; run summary lists it as rejected by source | pass (no 7070 or 8080 on any page; both transcript claims under "Review findings rejected by source") |
| `make check` passes; every page has a source block | pass (`make check`, leak check, and `check.py --structure` OK) |
| `findings/upstream.yaml` has the README port drift | pass (UF-1, README.md:8 quoted, status collected) |
| `ACME Corp` only on internal pages; `make check` and `make dist` pass | pass (only `internal/.../account-context.adoc`; shareable tarball has no internal path; both PDFs written) |

### SC-002: independent factual sample (20 statements, checked by the implementing session against the pinned source, not by the run's reviewers)

| # | Page | Statement | Supported? |
|---|---|---|---|
| 1 | admin/install | small status service answering on a single port | yes (README.md:3, Makefile:7) |
| 2 | admin/install | "other tools and scripts can poll" it | no (embellishment, not in the source) |
| 3 | admin/install | clone, check out the pin, `make install`, `make status` | yes (docs/setup.md:1-5) |
| 4 | admin/install | status check returns `ok` | yes (docs/setup.md:4) |
| 5 | admin/install | `curl -s http://127.0.0.1:9090/status` | yes (Makefile:7) |
| 6 | admin/install | binds to 127.0.0.1, reachable only locally | yes (config/defaults.yaml:4) |
| 7 | admin/configure | settings come from `config/defaults.yaml` | yes (README.md:10) |
| 8 | admin/configure | file holds port, bind, timeout, admin UI keys | yes (config/defaults.yaml:1-7) |
| 9 | admin/configure, reference | `timeout` is "the request timeout in seconds" | no (unit and meaning not in the source) |
| 10 | admin/configure | default values block | yes (config/defaults.yaml:2-7) |
| 11 | admin/configure | `server.port` default 9090 is the listening port | yes (config/defaults.yaml:3, Makefile:7) |
| 12 | admin/configure | `admin.enabled` default false, admin UI disabled | yes (config/defaults.yaml:6-7) |
| 13 | admin/configure | no admin UI port defined in the source | yes |
| 14 | admin/configure | NOTE: `admin.enabled` "does not affect the status service endpoint" | no (inference; deferred by the task 2 review, not fixed or ruled on in the final review) |
| 15 | admin/configure | WARNING: set `server.bind` to `0.0.0.0` to allow remote access | no (operational advice not in the source; no review flagged it) |
| 16 | user/check-status | `make status` prints `ok` | yes (docs/setup.md:4) |
| 17 | user/check-status | curl and `make status` give the same answer | yes (Makefile:7 runs that curl) |
| 18 | reference | `install` uses `config/defaults.yaml` | yes (Makefile:4) |
| 19 | reference | `status` queries `http://127.0.0.1:9090/status` | yes (Makefile:7) |
| 20 | index | admin UI optional and off by default | yes (config/defaults.yaml:6-7) |

Supported share: **16 / 20 = 80%** (target at least 95%): **SC-002 not met.** The four unsupported statements are plausible inferences or general advice, not contradictions, but the spec counts only statements the pinned sources support.

Process gaps behind it:
- The per-page reviews treated unsourced inferences (units, side effects, how-to advice) as Minor or did not flag them; `page-review-guide.md` says an unsupported statement is Important.
- The final review fixed three deferred minors but neither fixed nor recorded a ruling for the NOTE in #14, although `final-review-addendum.md` requires one of the two for every deferred minor.

### Scenario 4: resume

| Expectation | Result |
|---|---|
| Interrupted after two completed page tasks | the session was killed at 17:05:39, right after `Task 2: complete`; working tree clean |
| A new session resumes at task 3 | pass: `runs.py resume` printed `3`; a fresh `/guide:create --dir ...` session (no `--resume`) wrote the task-3 brief two minutes after start |
| Tasks 1 and 2 are not redone | pass: no new dispatch or commit for them; their ledger lines and commits unchanged |

### SC-013: diagram (run the same evening, headless session on the standard guide)

The architecture diagram was added as a diagram task to the finished standard guide, with the canvas at localhost:3000 and the author at the browser.

| Expectation | Result |
|---|---|
| `diagram_check.py check` reports zero findings on the accepted round | pass (0 findings in every round, 1 to 3) |
| `review.md` in each round directory holds the controller's crop review | pass (round 1 accepted; round 2 needs fixes: an orphaned label and a legend row for a color no longer used, found by the crop review although the mechanical gate was clean; round 3 accepted) |
| At most two automated fix rounds before the manual hand-off | pass (initial draw, then one automated fix round after the manual edit) |
| Manual hand-off exercised once | pass (author declined round 1 and removed the Admin UI box on the canvas; the session exported the edit as round 2 and reviewed it) |
| Wrap-up | scene in `diagrams/`, SVG and 2x PNG in the image directory, embedded with quoted alt text and `role=expand`, `make check` passes, author's canvas backup restored (verified at 40 elements) |

Extras observed: `make check` rejected a typed port in the alt text on the first embed attempt (the attribute `{mini-port}` is used instead), and the skill's canvas-identification step surfaced a real config mismatch (the user-level MCP config pointed at port 3100 while the canvas ran on 3000; the session improvised a local TCP forward, which goes beyond the skill's instructions and is noted as an observation).

### SC-010: fast versus standard (run the same evening, `minisvc-guide-fast`)

Same fixture, same intake, `--rigor fast`, run end to end without interruption.

| Run | Review dispatches (run summary) | Final review |
|---|---|---|
| standard (`minisvc-guide`) | 10 | 1 dispatch, verdict clean |
| fast (`minisvc-guide-fast`) | 0 (all 8 tasks `review skipped (rigor fast)`) | 1 dispatch, verdict "with fixes" (1 Critical, 4 Important, 1 Minor), resolved in one fix round with the corrections re-verified against the pinned source |

Fast used at most half the standard run's review dispatches: **SC-010 (fast half) pass**. The quality trade-off showed up exactly as the rigor table predicts: the standard run's final review was clean because per-page reviews had already caught everything, while the fast run's defects surfaced only at the final review. `make check` passes on the fast guide, no planted port appears on any page, and the README drift was collected again as an upstream finding.

Not exercised: the strict half of SC-010 (claim ledger with an identifier per verifiable statement) needs a third run with `--rigor strict`.

## Scenario 3 with gfm (T039)

Repeat scenario 3 with `--format gfm --dir /tmp/guide-demo-gfm` and record the same table here.

| Expectation | Result |
|---|---|
| (as above) | |
