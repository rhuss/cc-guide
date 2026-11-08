# Feature Specification: Embedded guide with the README as front page

**Feature Branch**: `005-embedded-guide`

**Created**: 2026-11-07

**Status**: Draft

**Input**: User description: "Add an embedded mode where a guide lives inside the repository it documents, the top-level README.md is the guide's front page, development material (contributing, build, release) moves to a secondary developer README, existing documentation is consolidated, and /guide:evolve keeps the README current over time." Authoritative input: `brainstorm/05-embedded-guide.md`.

## Clarifications

### Session 2026-11-07

- Q: What counts as "the pull request brings the guide up to date" for the pull request check? → A: The pull request changes the `self` entry of the guide baseline (evidence that evolve verified the change) and the cited files at its latest commit match the fingerprints in that entry; editing pages alone does not count.
- Q: When the host repository already has a documentation site (a generator configuration such as `mkdocs.yml` or `antora.yml` with its content directory), what does the move plan propose by default? → A: Keep the site in place and register its pages as guide input; removal with stubs happens only when the author changes that destination in the move plan.
- Q: Should guide commands run from the host repository root find the embedded guide on their own? → A: Yes. When the current directory is not a guide project, commands look for exactly one embedded guide in its immediate subdirectories and use it; with none or several they stop and ask for the directory.
- Q: How is development material treated when it moves to the developer README? → A: Moved with its text unchanged except for heading levels and relative links, which are rewritten so they still resolve from the new location.
- Q: Does evolve repeat the consolidation when new documentation files appear in the host repository later? → A: No. Consolidation runs only during embedded create; evolve neither moves nor stubs files outside the guide subdirectory.
- Q: Where does the readable snapshot of the `self` source live, given that every guide file stays inside the guide subdirectory? → A: Outside the host repository, as a local cache at `${XDG_CACHE_HOME:-~/.cache}/cc-guide/self/<hash of the host path>/<commit>/`. A snapshot inside the host would be a second copy of the host code that the host's test runners and linters could pick up. It is the only exception; every other guide file and cache stays inside the guide subdirectory (FR-002).
- Q: Does a removed non-Markdown root README (or another root README beside the front page) or a `.github/README*` keep a stub like other removed documentation paths? → A: No. Both are removed or relocated without a stub, because a stub there would shadow the front page or leave two root READMEs (FR-023).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Turn an existing repository's README into a verified guide front page (Priority: P1)

An author maintains an existing code repository with a hand-written README and some loose documentation. They run the guide create command from that repository. The command offers an embedded guide, takes stock of the existing documentation, shows a move plan, and after the author approves it, sets up the guide machinery in one subdirectory, writes the persona pages there, and replaces the root README with a source-verified front page that introduces the project and links to each persona's entry page. Development material from the old README moves to a developer README linked from the front page. A visitor to the repository on GitHub now lands on the guide.

**Why this priority**: This is the whole feature for the case the author named first (existing repositories). Without it nothing else in this spec has a guide to act on.

**Independent Test**: Run create in embedded mode on a fixture repository that has a README with user and developer sections, a `CONTRIBUTING.md`, a `LICENSE`, and a `docs/` page; approve the move plan; confirm the resulting README is a guide front page with a sources block and persona links, the developer README holds the development material, the guide machinery is confined to the guide subdirectory, and the guide checks pass.

**Acceptance Scenarios**:

1. **Given** an existing repository with a README, `CONTRIBUTING.md`, `LICENSE`, and a `docs/` tree, **When** the author runs create from the repository root and chooses embedded mode, **Then** create lists every existing documentation file with a proposed destination (guide input, developer README, kept in place, or removed with a stub) and changes nothing before the author approves.
2. **Given** an approved move plan, **When** create finishes, **Then** the root README is the guide's front page (it carries a sources block, persona navigation, and a link to the developer README), the guide configuration, toolkit, build files, and persona pages all sit inside the guide subdirectory, and `LICENSE` is still at the repository root.
3. **Given** the author declines the move plan, **When** create stops, **Then** no file outside the guide subdirectory has been changed, moved, or removed.
4. **Given** the host repository has its own `Makefile`, `package.json`, or `docs/` directory, **When** embedded create finishes, **Then** those files and directories are unchanged unless the approved move plan named them.
5. **Given** a statement in the old README that the pinned code contradicts, **When** the guide is written, **Then** the statement does not appear in the guide and is listed in the run summary as dropped, with the contradicting source location.

---

### User Story 2 - Keep the README front page current with evolve (Priority: P1)

Later, the project's code changes. The author runs the evolve check and then evolve itself. The check reports the root README as affected when a file it cites changed, and evolve updates it with the same per-page review as any other guide page. Commits that only touch the guide do not show up as drift.

**Why this priority**: The author's explicit requirement is that the top-level README keeps evolving with the guide. An embedded guide that cannot be evolved is a one-time rewrite.

**Independent Test**: In a fixture repository with an embedded guide, change a file the README cites and commit it; run the drift check and confirm the README is reported as affected; run evolve and confirm the README is updated and the baseline moves forward; then commit a change that touches only guide pages and confirm the drift check reports no drift.

**Acceptance Scenarios**:

1. **Given** an embedded guide whose front page cites a file in the host repository, **When** that file changes in a later commit, **Then** the check-only mode lists the front page among the affected pages.
2. **Given** a later commit that changes only files inside the guide subdirectory, the front page, the developer README, or stubs, **When** the check-only mode runs, **Then** it reports no drift for the host repository source.
3. **Given** drift on the front page, **When** the author runs evolve, **Then** the front page is updated through the same page task and review flow as other pages and the new baseline is written only after the checks pass.
4. **Given** the host repository merges pull requests by squash or rebase, **When** the commit the guide was verified against is no longer reachable from the default branch, **Then** the drift check still reports correctly (no false drift for unchanged cited files, real drift for changed ones) and does not stop with a missing-pin error.

---

### User Story 3 - Old documentation links keep working (Priority: P2)

Blog posts, issues, and other repositories link to the project's old documentation paths, for example `docs/install.md`. After consolidation, each removed path holds a short stub that says the content moved and links to the new guide page, so a reader following an old link lands one click away from the right content.

**Why this priority**: Breaking inbound links is one of the named failure modes, but the guide is still usable without stubs, so it ranks below the two core stories.

**Independent Test**: Consolidate a fixture repository whose `docs/install.md` and `USAGE.md` are absorbed into the guide; confirm both paths still exist as stubs that link to the guide pages covering that content, and that the guide checks accept the stubs.

**Acceptance Scenarios**:

1. **Given** an approved move plan that removes `docs/install.md`, **When** consolidation runs, **Then** `docs/install.md` remains as a stub with a one-line notice and a working link to the guide page that now covers installation.
2. **Given** stubs in the repository, **When** the guide checks run, **Then** they verify that every stub link resolves and do not report stubs as orphan pages or as pages missing a sources block.
3. **Given** a removed file whose content had no guide destination (stale or contradicted material), **When** consolidation runs, **Then** its stub links to the guide front page.

---

### User Story 4 - Optional drift check on every pull request (Priority: P2)

During setup, the author is offered a check that runs on every pull request in the host repository. When a pull request changes files that guide pages cite, and does not bring the guide up to date, the check reports which pages are affected. Maintainers can mark a pull request as not needing a guide update when the change does not touch documented behavior.

**Why this priority**: The author asked for both modes, with CI integration optional. Occasional evolve runs already work without it, so it is not part of the minimum slice.

**Independent Test**: Opt in during embedded create; open a pull request in a fixture repository that changes a cited file without touching the guide and confirm the check reports the affected pages and fails; add the opt-out marker and confirm it passes with a note; open a pull request that changes only uncited files and confirm it passes.

**Acceptance Scenarios**:

1. **Given** the author declines the pull request check at setup, **When** create finishes, **Then** no pull request workflow is installed.
2. **Given** the pull request check is installed, **When** a pull request changes a cited file and does not advance the guide baseline, **Then** the check fails and its report names the changed files and the affected pages.
3. **Given** the pull request check is installed, **When** a pull request changes only files no page cites, **Then** the check passes.
4. **Given** a pull request that changes a cited file and carries the maintainers' opt-out marker, **When** the check runs, **Then** it passes and its report states that the guide update was skipped by request.
5. **Given** the pull request check is installed, **When** an external (non-host) source drifts, **Then** pull requests in the host repository are not failed by it; external drift stays with the scheduled drift check and evolve.

---

### User Story 5 - Separate guide repositories keep working unchanged (Priority: P3)

Authors who keep a guide in its own repository, or who choose Antora or MkDocs, see no change in create, evolve, preview, export, validate, or upstream.

**Why this priority**: A regression guard rather than new value, but every existing guide depends on it.

**Independent Test**: Run the existing toolkit tests and adapter smoke tests and the existing create flow on an empty directory; confirm results match the current behavior and that the intake does not offer embedded mode there.

**Acceptance Scenarios**:

1. **Given** an empty target directory, **When** the author runs create, **Then** the flow is the current one (new repository, remote offer) and embedded mode is not offered.
2. **Given** an existing guide project in its own repository, **When** any guide command runs, **Then** its behavior and output are unchanged.

### Edge Cases

- The host repository has uncommitted changes when embedded create starts: create stops and asks the author to commit or set them aside, so consolidation commits contain only guide work.
- The host repository's current branch is its default branch: create asks before committing there and offers to create a working branch first.
- The chosen guide subdirectory already exists and is not a guide project: create stops and asks for another name; it never merges into an unrelated directory.
- The host repository has no README at all: create writes a new front page and skips the developer README unless there is development material elsewhere to move.
- The README is `README.adoc`, `README.rst`, or another non-Markdown README: embedded gfm mode explains that it replaces the root README with a Markdown one and includes the old file in the move plan, where its only allowed destinations are guide input plus removal, or relocation under another name; it never leaves two root READMEs.
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, or similar community files exist: the move plan keeps them where GitHub still finds them (repository root, `.github/`, or `docs/`) and links to them from the developer README rather than merging them.
- A page's sources block cites a file inside the guide subdirectory, the front page, the developer README, or a stub: the guide checks reject it, because the guide must not verify itself against its own text.
- Existing documentation registered as input is later rewritten or removed by consolidation: evolve does not report it as a changed or unreadable input, because those inputs are recorded at the revision they were read from.
- The author asks for an internal part in embedded mode: create explains that embedded guides have no internal part and that a guide with internal pages must be a separate repository.
- The host repository is private and the pull request check cannot read another private source: external sources are not part of the pull request check, so this does not fail pull requests.
- The repository already has a `.github/workflows` file with the same name as the guide workflows: create stops before overwriting and asks for a different name.
- A link in the front page points to a guide page that was renamed: the guide checks report it as broken, the same as any other broken link.

## Requirements *(mandatory)*

### Functional Requirements

**Mode selection and layout**

- **FR-001**: create MUST offer embedded mode when its target is the root of an existing git repository that is not a guide project, and MUST let the author request embedded mode explicitly. It MUST NOT offer embedded mode for an empty target directory, whose flow stays as it is today. A non-empty directory that is not a git repository MUST still be refused as today, and a subdirectory of a git repository (for example a package in a monorepo) is not a valid embedded target in this release.
- **FR-002**: In embedded mode, every file the guide needs (configuration, baseline, input register, rules, style guide, toolkit, build and package files, installed tool dependencies, local caches and run data, persona and reference pages, diagrams) MUST live inside one guide subdirectory of the host repository. The default name is `guide/`; the author may choose another name at intake. The one exception is the readable snapshot of the `self` source (the exported host code that page writers and reviewers read): it is a local cache kept outside the host repository, at `${XDG_CACHE_HOME:-~/.cache}/cc-guide/self/<hash of the host path>/<commit>/`, so no second copy of the host code lies inside the host, where its test runners and linters could pick it up. Every other guide file and cache stays inside the guide subdirectory.
- **FR-003**: Outside the guide subdirectory, embedded create MUST change only the root README, the developer README, stubs, and files named in the approved move plan, plus the opted-in workflows (the pull request check and the scheduled drift check) in the host repository's `.github/workflows/`, where GitHub reads them; both workflows run with the guide subdirectory as their working directory. Session settings files that the author approves and that git does not track (for example a local tool permission) are also allowed. The host repository's own build files, package files, ignore rules, and documentation directories MUST stay unchanged unless the approved move plan names them.
- **FR-004**: The guide configuration MUST record that the guide is embedded and where its front page is, and the configuration validation MUST reject an embedded configuration whose front page is missing, whose format is not gfm, or that enables an internal part.
- **FR-005**: Embedded mode MUST support the gfm format only in this release. create MUST explain this when an author asks for Antora or MkDocs in embedded mode, and the embedded-mode design MUST keep format-specific behavior limited to the front page handling, so other formats can later add a landing-page README without changing the rest of the mode.
- **FR-006**: Embedded guides MUST NOT have an internal part. Confidential inputs remain possible, but no confidential fact reaches any committed file. In embedded mode the confidential terms and patterns MUST live in a local file inside the guide subdirectory that git ignores (the leak check still reads it), and confidential inputs MUST be registered under neutral ids whose locations are kept only in local, untracked state; committed run summaries and findings MUST NOT name them.
- **FR-007**: create in embedded mode MUST NOT initialize a new git repository and MUST NOT offer to create a remote repository; every commit goes to the host repository. Pushing remains a separate opt-in, as today, and every commit goes to the branch the author approved (see Edge Cases for the default branch).

**Front page**

- **FR-008**: The root README MUST be the guide's front page: one page, not a copy of another guide page. It introduces the project and carries the navigation that the gfm table of contents carries today (reading order and a link to each persona's entry page), plus a link to the developer README.
- **FR-008a**: In embedded mode the front page MUST replace the gfm table of contents as the guide's start page and navigation, and the overview page rules (why card, cold-reader test) MUST apply to it. The print order file MUST remain and list the front page first, and the structure checks MUST read the front page in place of the table of contents. The table of contents file inside the guide subdirectory MUST become a one-line pointer to the front page, so browsing that folder never shows a second front page.
- **FR-009**: The front page MUST be treated as a guide page in every guide command: it carries a sources block, it gets the same page task, per-page review, and final review as other pages, the checks validate it, preview serves it as the front page, and export prints it first.
- **FR-009a**: The front page MUST carry a comment stating that the guide owns it and how to change it. evolve MUST report hand edits made to the front page since the last baseline before updating it, and MUST NOT overwrite them silently.
- **FR-010**: Links between the front page and the pages in the guide subdirectory MUST resolve in both directions when browsed on GitHub, and the guide checks MUST report any that do not.
- **FR-010a**: Badges and a project logo from the old README MUST stay at the top of the front page; they are kept as they are and not verified. The inventory MUST flag package manifests that publish the README to a package registry, and for those the move plan MUST offer absolute links in the front page so it renders outside GitHub.

**Host repository as a source**

- **FR-011**: In embedded mode the host repository MUST be registered as a source with the reserved id `self`, pinned to an exact revision like any other source, and all verification MUST use that pinned revision, never the uncommitted working tree.
- **FR-012**: Source blocks MUST NOT cite files inside the guide subdirectory, the front page, the developer README, or stubs; the checks MUST reject such citations.
- **FR-013**: Drift for the `self` source MUST count only changes to files that pages cite, so commits that change only guide files are never drift.
- **FR-014**: For the `self` source, the baseline MUST also record a content fingerprint of every cited file at the pinned revision, and drift for `self` MUST compare those fingerprints with the cited files at the current head instead of relying on the pinned commit's history. Drift for the `self` source MUST therefore stay correct when the pinned revision is no longer reachable from the default branch because of squash or rebase merges: unchanged cited files MUST NOT be reported as drift, changed cited files MUST be, and the check MUST NOT stop with a missing-pin status for that reason alone.
- **FR-015**: Other sources in an embedded guide MUST behave exactly as in a separate guide (pinning, fetching, drift, change requests).

**Consolidation of existing documentation**

- **FR-016**: Before writing any file outside the guide subdirectory, embedded create MUST inventory the repository's existing documentation: the root README (in any format), any `.github/README*` or `docs/README*` that GitHub would show in place of or beside the root README, files such as `CONTRIBUTING.md`, `INSTALL.md`, `USAGE.md`, `CHANGELOG.md`, community health files, and documentation directories (`docs/`, `doc/`, `documentation/` at the root, and any directory holding a documentation generator configuration). A `.github/README*`, which GitHub shows in preference to the root README, MUST be proposed for removal or relocation so the front page is what visitors see.
- **FR-017**: create MUST classify each inventoried file, or each section of it where a file mixes audiences, into one destination: user-facing material that becomes guide input, development material that moves to the developer README, files kept in place (license, community health files GitHub detects, changelog), or material removed with a stub. An existing documentation site (a generator configuration with its content directory) MUST default to kept in place, with its pages registered as guide input; it is removed with stubs only when the author changes that destination.
- **FR-018**: create MUST show the complete move plan (each file or section, its destination, and every removal) and MUST NOT move, rewrite, or remove any existing file until the author approves the plan. The author MUST be able to change individual destinations before approving.
- **FR-019**: User-facing material MUST be registered as guide input and treated like any other input: its claims are verified against the pinned sources, only verified facts reach guide pages, and its text is never copied verbatim into the guide. Claims the sources contradict MUST be dropped and listed in the run summary with the contradicting source location; only those from material that stays in place are offered as upstream finding candidates.
- **FR-020**: Inputs taken from host repository documentation that consolidation rewrites or removes MUST be recorded at the revision they were read from, so that this is not later reported as a changed or unreadable input. Inputs kept in place (for example an existing documentation site) MUST be tracked for changes like any other input.
- **FR-021**: Development material MUST move to a developer README (default `DEVELOPMENT.md` at the repository root; the author may choose another path at intake) that is linked from the front page. When that file already exists, the move plan MUST propose appending the moved sections under a heading and show this in the plan. Development material is moved, not verified and rewritten, because it is maintained by the project's developers rather than by the guide: its text stays unchanged except for heading levels and relative links, which MUST be rewritten so they still resolve from the new location.
- **FR-022**: `LICENSE` (and any license file GitHub detects) MUST stay at the repository root. Community health files MUST stay in a location where GitHub still detects them.
- **FR-023**: Every removed documentation path MUST keep a stub: a short file stating that the content moved, with a link to the guide page that covers it, or to the front page when nothing covers it. Stubs MUST stay in place until an author removes them by hand. Exempt are a non-Markdown root README (for example `README.rst`; the same holds for any other root README beside the front page) and a `.github/README*`: they are removed or relocated without a stub, because a stub there would shadow the front page (GitHub shows `.github/README*` first) or leave two root READMEs.
- **FR-024**: The guide checks MUST verify that every link in stubs and in the developer README resolves. They MUST NOT report stubs as orphan pages or as pages without a sources block, and MUST NOT apply page content rules (sources block, style and character rules) to the developer README, whose text is moved unchanged.

**Pull request check (optional)**

- **FR-025**: Embedded create MUST offer a pull request check, default off, and install it only when the author opts in. The existing scheduled drift check remains a separate offer.
- **FR-026**: The pull request check MUST examine only the `self` source: it reports the cited files the pull request changes and the guide pages they affect. It MUST pass when the pull request changes no cited file. When it changes cited files, it MUST pass only when the pull request also changes the `self` entry of the guide baseline and every cited file at the pull request's latest commit matches the fingerprint recorded in that entry; otherwise it MUST fail (editing pages without re-verifying, or pushing further changes to cited files after re-verifying, does not count).
- **FR-027**: Maintainers MUST be able to mark a pull request as not needing a guide update; the check then passes and its report states that the update was skipped by request.
- **FR-028**: The pull request check MUST run without an AI session and without access to other sources, MUST NOT change the repository, and MUST NOT need write permissions beyond reporting its own result.

**Compatibility**

- **FR-029**: Separate guide repositories and the Antora and MkDocs formats MUST behave as they do today in every guide command.
- **FR-030**: All guide commands (create, evolve, preview, export, validate, upstream) MUST work on an embedded guide when pointed at its guide subdirectory, with no extra step beyond what a separate guide needs.
- **FR-031**: An embedded guide is recognized by a guide configuration in an immediate subdirectory that marks the guide as embedded (FR-004). When a guide command runs in a directory that is not a guide project, it MUST look for embedded guides in the immediate subdirectories and use the one it finds. When it finds more than one, it MUST stop and ask for the guide directory. When it finds none, create offers embedded mode (FR-001) and every other command stops and asks for the guide directory. When create finds one, it resumes that guide as it resumes a separate guide today.
- **FR-032**: Consolidation MUST run only during embedded create. evolve MUST NOT create, move, or remove any file outside the guide subdirectory. Outside it, evolve changes only the front page and, when a page that a stub or the front page links to is renamed or removed, the link targets in those stubs, so the checks keep passing.

### Key Entities

- **Host repository**: the code repository that contains the embedded guide; registered as the `self` source.
- **Guide subdirectory**: the one directory inside the host repository that holds all guide machinery and the non-front pages.
- **Front page**: the host repository's root README, owned entirely by the guide; a guide page with a sources block and the guide's navigation.
- **Developer README**: the file that receives development material from the old README; linked from the front page; maintained by the project's developers.
- **Move plan**: the list of existing documentation files or sections with their proposed destinations and removals; requires the author's approval before anything outside the guide subdirectory changes.
- **Stub**: a short file left at a removed documentation path that points to the new location.
- **Pull request check**: an optional workflow in the host repository that reports cited-file changes in a pull request and the affected guide pages.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a fixture repository with a README, `CONTRIBUTING.md`, `LICENSE`, and a `docs/` tree, embedded create produces a front page whose links to every persona entry page and to the developer README all resolve when browsed on GitHub, and the guide checks report zero broken links.
- **SC-002**: 100% of documentation paths removed by consolidation still exist as stubs that link to an existing page, and 100% of relative links in the developer README resolve.
- **SC-003**: Outside the guide subdirectory, the only changed tracked paths after embedded create are the front page, the developer README, stubs, files named in the approved move plan, and the opted-in workflows; every host repository build and package file the move plan does not name is byte-identical.
- **SC-004**: Declining the move plan leaves every file outside the guide subdirectory byte-identical to its state before create.
- **SC-005**: A commit that changes only guide files produces zero drift for `self`; a commit that changes a file cited by the front page lists the front page as affected in 100% of runs.
- **SC-006**: After a squash merge of the pull request that set the baseline, the drift check reports no false drift and no missing-pin error.
- **SC-007**: With the pull request check installed, a pull request that changes a cited file without a guide update fails, and a pull request that changes only uncited files passes, in 100% of test runs.
- **SC-008**: All existing toolkit tests and adapter smoke tests pass unchanged, and create on an empty directory never offers embedded mode.

## Assumptions

- The first delivery targets GitHub-hosted repositories, matching the gfm format's rendering target and the existing GitHub-only workflow templates.
- The default guide subdirectory name `guide/` and the default developer README `DEVELOPMENT.md` at the root are proposals from the brainstorm; authors can change both at intake.
- The `self` source is read from the local repository at the pinned revision, so private host repositories need no extra credentials for create and evolve.
- Stubs are plain Markdown files with a one-line notice and a link; they never expire automatically.
- The pull request check reports through its pass/fail status and job report; whether it blocks merging is the repository owner's choice through branch protection.
- The opt-out marker for the pull request check is a pull request label; its exact name is set during planning.
- Monorepo subdirectory targets, converting an existing separate guide repository into an embedded guide, guide-owned regions inside a hand-written README, and embedded Antora or MkDocs guides are out of scope for this release.
- The existing per-page review, final review, and rigor profiles apply to embedded guides unchanged.
