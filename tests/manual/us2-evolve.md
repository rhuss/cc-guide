# User Story 2: evolve (quickstart scenarios 6 and 7)

Recorded 2026-10-01 during implementation, on macOS with toolkit 0.1.0.

## Scenario 6: drift check on the fixture

Setup: `bash tests/adapters/scaffold.sh antora <dir>` (baseline pinned to the fixture's first commit; the fixture repository head is its third commit, which changes `config/defaults.yaml`, renames `docs/setup.md`, and deletes the `Makefile`).

| Step | Result |
|---|---|
| `uv run tools/guide/drift.py --check` | exit 10, "Drift found" |
| Changed cited files | `deleted Makefile`, `modified config/defaults.yaml`, `renamed docs/setup.md -> docs/install.md`, each with its citing pages |
| Affected pages | `admin/install`, `index`, `user/start`, internal `notes` (all four pages cite a changed file) |
| Change requests | reported `unchecked` (the fixture is a local repository, not on GitHub) |
| Inputs | both registered inputs `unchanged` |
| `make drift` | prints the same report; make itself exits 2 (GNU make reports any failing recipe as 2) |

**Ruling R-impl-1**: the contract's exit status 10 holds for `tools/guide/drift.py --check`, which is what the scheduled workflow and the evolve skill call; `make drift` can only signal drift as a non-zero exit (2), because make does not propagate a recipe's exit code. Cost if wrong: a script that tests `make drift` for exactly 10 must call drift.py instead.

Not yet run (needs the author): the scheduled workflow part (push the fixture guide to a private test repository, trigger `guide drift check` twice, expect one `guide-drift` issue opened and then updated).

## Scenario 7: evolve the SAW guide (deterministic part)

Setup: a copy of `~/Work/projects/saw-guide` (without `node_modules`, `build`, `dist`, `.cache`) in a scratch directory; toolkit installed with `scaffold-project.sh --format antora --toolkit-only`; a minimal `guide.yaml` (title, format antora, two personas, internal part with the `APPENG-<n>` pattern).

| Step | Result |
|---|---|
| `adopt.py migrate --map guide/templates/adopt-map.example.yaml` | valid cc-guide baseline: sources `saw` (`c84103d`), `openshell` (`d1155aa`, ref `v0.0.116`), `openshell-main` (`252882f`); six change requests (33, 37, 52, 53, 55, 56) with their anchors; original kept as `baseline.foreign.yaml` |
| `guidecfg.py validate` | OK |
| `adopt.py report` | one page without a source block: `internal/.../claim-ledger.adoc` (a ledger table; mark it no-sources during adoption) |
| `drift.py --check` (18 s, network) | exit 10. `saw`: 7 commits since `c84103d`, including `5da9de2 Merge pull request #56 ... openshell-0.1.2` |
| Change requests | #56 **merged** (move to on-main or remove), #33 closed without merge, #52 and #53 head moved, #37 and #55 unchanged |
| Affected pages | 19 of 20 pages (Makefile-quickstart, the chart values, and `apply_bom.py` are cited almost everywhere) |

Observation: the `openshell` source is pinned at a tag (`v0.0.116`), so drift compares it with the default branch (352 commits). For tag-pinned sources the useful target is the next release tag; the evolve skill asks the author for targets (`--to openshell=v0.1.2`), so this is noise in the report rather than a wrong update. Follow-up: report the newest tag for tag-pinned sources.

Not yet run (needs an interactive session with superpowers): `/guide:evolve --adopt` and `/guide:evolve` end to end, with the expectations of quickstart scenario 7 (PR 56 notice moves to on-main or is removed, only affected pages change, `make check` passes, baseline written last).
