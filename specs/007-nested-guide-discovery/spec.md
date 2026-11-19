# Feature Specification: Discover guide projects in nested directories

**Feature Branch**: `007-nested-guide-discovery`

**Created**: 2026-11-19

**Status**: Draft

**Input**: User description: "Discovery finds a guide project kept below the immediate subdirectories (for example `docs/guide/`), embedded or standalone, with a bounded search where the shallowest match wins." Authoritative input: `brainstorm/07-nested-guide-discovery.md`, from GitHub issue rhuss/cc-guide#4.

## Background

Every `/guide:*` command starts by resolving the guide project for the directory it runs in (spec 005, FR-031). Today the resolution knows two places only: the directory itself when it holds a guide configuration (`guide.yaml`), or the one immediate subdirectory whose guide configuration marks the guide as embedded. Every other layout reports "no guide project". A standalone guide kept in a documentation subdirectory, such as cc-review's guide at `docs/guide/guide.yaml`, is never found from the repository root, so the author has to pass `--dir docs/guide` to every command.

This feature replaces the second rule with a bounded search below the directory that accepts embedded and standalone guides alike, and amends FR-031 of spec 005 and its toolkit contract accordingly.

## Clarifications

### Session 2026-11-19

- Q: When a guide sits at depth 1 and another at depth 2 in an unrelated branch of the tree, should discovery still pick the depth 1 guide without asking? → A: Yes. The shallowest depth with a candidate decides, and deeper candidates are not reported (the issue's "return the shallowest match"); the author passes `--dir` to reach a deeper guide.
- Q: When several candidates tie at the shallowest depth, does the exit 3 list include deeper candidates too? → A: No. It lists only the tied candidates at the shallowest depth, sorted by path, because only those could be the result.
- Q: Does a directory or other non-file entry named `guide.yaml` make a candidate? → A: No. Only a regular file (or a symbolic link to one) named `guide.yaml` marks a candidate, matching rule 1 today.
- Q: Should template or fixture copies of `guide.yaml` be excluded from discovery? → A: No. They are documented as an edge case; `--dir` is the workaround, and the pruning list stays as in the issue.
- Q: What happens with an embedded guide found deeper than depth 1? → A: It is reported as embedded; extending spec 005's embedded layout rules to deeper levels is out of scope, and validation reports any resulting front page problem.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run a guide command from the repository root of a project with a nested standalone guide (Priority: P1)

An author keeps a standalone guide at `docs/guide/` of the repository it documents. They run `/guide:preview` (or any other guide command) from the repository root without `--dir`. The command finds `docs/guide/` as the guide project and runs against it, and it reports the guide as not embedded.

**Why this priority**: This is the reported problem (issue #4). Without it, every command in such a repository needs `--dir`.

**Independent Test**: Create a repository with `docs/guide/guide.yaml` (no `embedded` block) and nothing else that holds a guide configuration; run discovery from the root and confirm it prints the `docs/guide` path with success, and that the command's preflight reports `embedded=no`.

**Acceptance Scenarios**:

1. **Given** a directory whose only guide configuration is `docs/guide/guide.yaml` without an `embedded` block, **When** discovery runs on that directory, **Then** it succeeds and names `docs/guide` as the guide root.
2. **Given** the same layout, **When** a guide command's preflight resolves the guide, **Then** it reports the guide as not embedded.
3. **Given** a directory whose only guide configuration is `docs/user/guide/guide.yaml` (three levels down), **When** discovery runs, **Then** it succeeds and names that directory.
4. **Given** a directory that holds a guide configuration itself, **When** discovery runs, **Then** it names the directory itself, regardless of any guide configurations below it (unchanged behavior).

---

### User Story 2 - Several guides in one repository are never resolved silently (Priority: P1)

A repository holds more than one guide project below its root. Discovery must not pick one at random: when the closest guides are equally close, it stops and lists them so the command can ask which one to use. When one guide is strictly closer to the root than all others, that closest guide is used.

**Why this priority**: Silently picking the wrong guide would run commands (including writing ones such as `evolve`) against the wrong project.

**Independent Test**: Build layouts with two guides at the same depth and with guides at different depths; confirm the same-depth case exits with the "several candidates" status and lists both, and the different-depth case returns the shallower one.

**Acceptance Scenarios**:

1. **Given** `guide/guide.yaml` and `docs/guide/guide.yaml`, **When** discovery runs on the root, **Then** it names `guide` (depth 1 beats depth 2).
2. **Given** `docs/guide/guide.yaml` and `site/guide/guide.yaml` (both depth 2) and nothing shallower, **When** discovery runs, **Then** it exits with the "several candidates" status and lists both paths, sorted.
3. **Given** two embedded guides in immediate subdirectories, **When** discovery runs, **Then** it exits with the "several candidates" status and lists both (unchanged behavior).

---

### User Story 3 - Existing embedded guides keep working (Priority: P2)

An author with an embedded guide in an immediate subdirectory (spec 005 layout, for example `guide/` with an `embedded` block) sees no change: discovery from the host root finds it and preflight reports it as embedded.

**Why this priority**: Regression protection for an already shipped feature.

**Independent Test**: Run the existing embedded discovery tests; all pass, except the one prior assertion that a standalone guide in an immediate subdirectory is not found, which flips to "found, not embedded" (FR-003).

**Acceptance Scenarios**:

1. **Given** `guide/guide.yaml` with an `embedded` block, **When** discovery runs on the host root, **Then** it names `guide` and preflight reports `embedded=yes`.
2. **Given** an immediate subdirectory with a standalone guide configuration (no `embedded` block) and no other guide, **When** discovery runs, **Then** it names that subdirectory (newly accepted) and preflight reports `embedded=no`.

---

### User Story 4 - The search stays fast and ignores material that is not the author's guide (Priority: P2)

A repository has large dependency or build trees and hidden directories (version control data, virtual environments, the guide's own source cache). Discovery does not look inside them, so a guide configuration that happens to exist in a cloned source repository, a dependency package, or build output is never picked up, and the search does not slow down on large trees.

**Why this priority**: Prevents false matches and keeps every command's startup fast.

**Independent Test**: Place guide configurations only inside pruned locations (a hidden directory, `node_modules`, `build`, `dist`, `target`, a symlinked directory, and below an existing guide project) and confirm discovery reports "no guide project" or ignores them in favor of the real guide.

**Acceptance Scenarios**:

1. **Given** guide configurations only inside `.guide/cache/x/`, `.git/x/`, `node_modules/x/`, `build/x/`, `dist/x/`, or `target/x/`, **When** discovery runs, **Then** it reports "no guide project".
2. **Given** a symlinked directory whose target holds a guide configuration, **When** discovery runs, **Then** the symlinked directory is not entered.
3. **Given** `docs/guide/guide.yaml` and a nested `docs/guide/examples/guide.yaml`, **When** discovery runs, **Then** it names `docs/guide` and does not report the nested one as a candidate.
4. **Given** `.docs/guide.yaml`, `build/guide.yaml`, and a symlinked directory `shared` whose target holds `guide.yaml`, and no other guide configuration, **When** discovery runs, **Then** it reports "no guide project" (pruned directories are not candidates themselves).
5. **Given** a guide configuration only at depth 4 (for example `a/b/c/guide/guide.yaml`), **When** discovery runs, **Then** it reports "no guide project".

---

### Edge Cases

- `DIR` does not exist or is not a directory: discovery reports "no guide project" (exit 4), as today.
- A directory that cannot be read (permission denied) is skipped without failing the whole search.
- A candidate whose `guide.yaml` is not valid YAML or has no `embedded` block counts as a standalone candidate; validation of the configuration happens later in the command (as for rule 1 today). Its embedded status is `no`.
- A guide project directory found at depth 1 is not searched further, so a guide's own fixtures or examples never compete with it.
- A guide at depth 1 shadows a guide at depth 2 or 3 elsewhere in the tree; the deeper one is reachable only with `--dir`.
- An entry named `guide.yaml` that is a directory does not make its parent a candidate.
- Template or fixture copies of a guide configuration (for example `guide/templates/guide.yaml` or `tests/fixtures/sample-guide/guide.yaml` in the cc-guide repository itself) are candidates like any other, because they are valid configurations. An author in such a repository passes `--dir`; no extra names are pruned.
- An embedded guide found at depth 2 or 3 is reported as embedded (FR-008). This feature does not extend spec 005's embedded rules (front page location, host root) beyond immediate subdirectories; any resulting configuration problem, such as a front page path that does not resolve to the host README, is reported by the configuration validation, not by discovery.
- Directory names are compared exactly; `Build` or `node_modules_old` are not pruned.
- A pruned directory name at depth 1 is pruned at every depth (for example `docs/node_modules/`).
- `create` run from a repository root where a nested guide exists now resumes that guide instead of offering embedded mode. An author who wants a second, new guide passes `--dir`.
- Running a command from inside a guide's subdirectory (below the guide root) still does not find the guide; upward search is out of scope.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When the directory a command runs in (`DIR`) holds a guide configuration, discovery MUST resolve the guide root to `DIR` and MUST NOT search below it (rule 1, unchanged).
- **FR-002**: Otherwise discovery MUST search the directories below `DIR` level by level, from depth 1 (immediate subdirectories) up to and including depth 3, for directories that hold a guide configuration: a regular file (or a symbolic link to one) named `guide.yaml`. A directory or other entry named `guide.yaml` does not count.
- **FR-003**: A directory holding a guide configuration MUST qualify as a candidate whether or not its configuration marks the guide as embedded.
- **FR-004**: Discovery MUST resolve to the shallowest depth that has at least one candidate. Exactly one candidate at that depth: discovery succeeds and prints that directory. Several candidates at that depth: discovery MUST fail with the "several candidates" status (exit 3) and list every candidate at that depth (and no deeper candidate) on standard output, one per line, as resolved absolute paths sorted lexicographically. Candidates deeper than the resolved depth are never reported, so a shallower guide shadows deeper ones without asking. No candidate up to depth 3: discovery MUST fail with the "no guide project" status (exit 4).
- **FR-005**: At any depth, a pruned directory is neither a candidate nor searched. Pruned directories are: hidden directories (name starting with `.`), directories named exactly `node_modules`, `build`, `dist`, or `target`, and directories reached through a symbolic link.
- **FR-006**: Discovery MUST NOT search below a directory that holds a guide configuration.
- **FR-007**: Discovery MUST skip directories it cannot read and continue the search.
- **FR-008**: A command's preflight MUST report a resolved guide as embedded only when its guide configuration has an embedded block, and as not embedded otherwise, independent of where discovery found it.
- **FR-009**: The messages discovery prints MUST describe the new search: the exit 3 message refers to several guide projects (not only embedded guides), and the exit 4 message states that no guide project was found in `DIR` or the directories below it (up to three levels). The toolkit's own descriptions of discovery (module usage text, the discovery error message, the function documentation) MUST match.
- **FR-010**: FR-031 of `specs/005-embedded-guide/spec.md` MUST be amended to describe the bounded search, the shallowest-match rule, the acceptance of standalone guides, and the pruning, with a note that spec 007 amended it. The `discover` row of `specs/005-embedded-guide/contracts/toolkit-cli.md` MUST be updated to match.
- **FR-011**: The skill text that describes discovery (`guide/skills/preflight/SKILL.md`, `guide/skills/create/SKILL.md`, `guide/skills/evolve/SKILL.md`) MUST describe the new search, including preflight's stop message and its description of `GUIDE`. After the change, no text under `guide/` may state that discovery only looks in immediate subdirectories or only finds embedded guides.
- **FR-012**: The toolkit test suite MUST cover: the nested standalone layout found from the root; shallower beats deeper; two candidates at the same depth exit 3 with both listed; each pruned category ignored; nothing below a guide project reported; depth 4 not found; the existing embedded cases; a standalone guide at depth 1; a directory that cannot be read (FR-007); an entry named `guide.yaml` that is a directory (FR-002); a `guide.yaml` that is a symbolic link to a file; a pruned name below depth 1 (`docs/node_modules`).
- **FR-013**: The discovery change MUST stay inside the toolkit (no imports from outside its directory) and MUST NOT add dependencies.

### Key Entities

- **Guide configuration**: the `guide.yaml` file that marks a directory as a guide project; may contain an `embedded` block.
- **Candidate**: a directory below `DIR`, within the search depth and not pruned, that holds a guide configuration.
- **Depth**: the number of directory levels between `DIR` and a candidate (immediate subdirectory is 1).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From the root of a repository laid out like cc-review (`docs/guide/guide.yaml`, standalone), every guide command resolves the guide without `--dir` (0 extra arguments needed, previously 1 on every invocation).
- **SC-002**: All prior discovery scenarios still hold (100%), except the rejection of a standalone guide in an immediate subdirectory, which FR-003 deliberately reverses.
- **SC-003**: In every tested layout with two or more equally shallow guides, discovery never resolves silently (100% of such cases exit 3 with all candidates listed).
- **SC-004**: Discovery never lists the contents of a pruned directory: with a `node_modules` tree that cannot be read, discovery succeeds exactly as without it (pruned trees add no work).
- **SC-005**: No guide configuration inside a hidden, dependency, build, or symlinked directory is ever reported (0 false candidates in the pruning tests).

## Assumptions

- The search depth of 3 and the pruned names are fixed in this release; configuring them is out of scope.
- Searching upward into parent directories is out of scope.
- Extending spec 005's embedded layout rules to embedded guides deeper than an immediate subdirectory is out of scope.
- How `create` offers embedded mode when nothing is found is unchanged; only the set of layouts that count as "found" grows.
- Any file named `guide.yaml` marks a candidate, as rule 1 does today; the configuration is validated by the command afterwards, not during discovery.
- The output format stays as today: the resolved guide root on standard output for exit 0, candidates on standard output and a message on standard error for exit 3, a message on standard error for exit 4.
