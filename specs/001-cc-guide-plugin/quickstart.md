# Quickstart: validating cc-guide end to end

Runnable scenarios that prove the feature works. Each names the spec items it covers. Details of files and flags are in [data-model.md](data-model.md) and [contracts/](contracts/).

## Prerequisites

- Claude Code with the superpowers plugin (6.3.0 or later) and, for scenario 3 onwards, the plugin installed from this repository (`make install`).
- `uv`, Node 20+, `git`, `gh` (authenticated), Pandoc 3 (for the `gfm` adapter); Playwright Chromium (`npx playwright install chromium`).
- Optional: cc-prose; the Excalidraw MCP server with its canvas open; for scenario 9, a disposable local cluster (for example kind with the podman provider) and a read-only connection to any cluster.

## 1. Plugin structure and dependency checks (FR-001 to FR-004, SC-009)

```bash
make validate          # claude plugin validate on the marketplace and the plugin
make test              # pytest for the toolkit and adapter smoke tests
```

In a scratch session where superpowers is disabled, run `/guide:create`. Expected: the command stops in its first step, names superpowers, shows the install command, and writes no file. With cc-prose disabled, `/guide:create` continues and shows the one-line prose notice.

## 2. Adapter smoke tests (FR-016 to FR-020, FR-030 to FR-030f, SC-011, SC-012)

For each format (`antora`, `mkdocs`, `gfm`), `make test-adapters` scaffolds the fixture guide `tests/fixtures/sample-guide` and runs:

```bash
make doctor check                 # passes
make pdf                          # dist/sample-guide-<date>.pdf exists
make pdf VIEW=internal            # dist/sample-guide-<date>-INTERNAL.pdf, footer marked
```

Expected:
- `pdftotext` of the shareable PDF contains the title page, every page title in navigation order, and none of the fixture's confidential terms.
- Planting a confidential term in a shareable page makes `make check` and `make pdf` fail, and no PDF is written.
- Planting a typed version string, an em dash, or a page without a source block makes `make check` fail with the page and line.

## 3. Create on a fixture project (User Story 1, SC-001 to SC-003)

Fixture: `tests/fixtures/mini-project` (a small source repository with a README that contradicts a configuration default, and a transcript that makes one false claim about a port).

```text
/guide:create --dir /tmp/guide-demo --format gfm --source <fixture repo> --input <fixture transcript>
```

Answer the intake with two personas (admin, user) and the standard profile. Expected:
- Raw inputs are referenced in `inputs.yaml` with checksums and are not present in the repository.
- `baseline.yaml` pins the fixture repository by full commit SHA.
- The plan is shown for approval before any page is written.
- Each page task is followed by a review; the false port claim does not reach any page, and the run summary lists it as rejected by source.
- `make check` passes; every page has a source block; the README drift appears in `findings/upstream.yaml`.

## 4. Resume after interruption (FR-013a)

Stop the session during scenario 3 after two page tasks are complete, start a new session in `/tmp/guide-demo`, and rerun `/guide:create`. Expected: it resumes at the third task and does not redo the first two.

## 5. Preview (User Story 3, SC-008)

```text
/guide:preview
/guide:preview --internal
```

Expected: the browser opens within one minute; editing a page refreshes the view.

## 6. Drift check and scheduled workflow (FR-025a, FR-025b)

Add a commit to the fixture source repository that changes a cited file.

```bash
make drift; echo $?      # 10, report lists the changed file and the affected pages
```

With the drift workflow enabled during create, push the guide to a private test repository and trigger the workflow manually. Expected: one `guide-drift` issue is opened; a second run updates it instead of opening another.

## 7. Evolve the SAW guide (User Story 2, FR-028, SC-004, SC-005)

In a copy of `~/Work/projects/saw-guide`:

```text
/guide:evolve --adopt          # migrates baseline.yaml to the cc-guide schema, adds tools/guide/
/guide:evolve
```

Expected: the drift report shows the SAW commits since `c84103d`, including the merged OpenShell v0.1.2 upgrade (PR 56); the experimental notice for PR 56 moves to the on-main tier or is removed; only pages citing changed files and pages linking to them are modified; `make check` passes; the new baseline is written last.

## 8. Upstream findings (User Story 5, SC-006)

```text
/guide:upstream
```

On the fixture from scenario 3 (pushed to a throwaway GitHub repository you own), expected:
- Each finding is re-verified on the default branch; a finding fixed in the meantime is dropped with a note.
- Every draft is shown in full, includes the provenance note, and contains none of the confidential terms.
- Nothing is posted until you approve; declining leaves the finding as `rejected`.

## 9. Validate (User Story 6, SC-007)

```text
/guide:validate --cluster readonly-test
/guide:validate --cluster readonly-test --tier full     # refused: not disposable
/guide:validate --cluster kind-disposable --tier full
```

Expected: the read-only tier runs only allowlisted queries and reports match, mismatch, or not evaluable per check; the full tier is refused on a connection without `disposable: true`; on the disposable cluster every mutating command waits for confirmation; no token or kubeconfig content appears in any file under the guide project.

## 10. Behavioral evals (SC-002)

```text
/eval-run          # agent-eval-harness, cases under eval/cases/
```

Expected: the page-review cases catch every planted false statement; the upstream cases drop every stale finding; the classifier cases mark every mutating command as mutating.
