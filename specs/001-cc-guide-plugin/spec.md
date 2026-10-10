# Feature Specification: cc-guide, a plugin for source-verified guides

**Feature Branch**: `001-cc-guide-plugin`

**Created**: 2026-10-01

**Status**: Draft

**Input**: User description: "cc-guide plugin: build the Claude Code plugin described in brainstorm/01-cc-guide-plugin.md (decision: Approach A, orchestrate superpowers). Use that document as the source of requirements, scope, out-of-scope items, and open questions."

## Overview

Engineers who adopt a fast-moving open source project (for example a validated pattern built on several upstream repositories) often have only walkthrough recordings, chat threads, tickets, and the source code to learn from. Turning these into a trustworthy, persona-split guide takes days, and the result drifts as soon as the sources change.

cc-guide is a Claude Code plugin that makes this a repeatable method. A guide author points it at the inputs; it produces a complete guide whose every page is checked against pinned sources, keeps a recorded baseline so the guide can be evolved when the sources move, reports problems it finds in the sources back to their owners, and can optionally validate the guide's recipes against a live cluster. It reuses the superpowers planning and subagent execution flow, adding the guide-specific templates, review rules, checks, and diagram rules learned while building the SAW guide.

## Clarifications

### Session 2026-10-01

- Q: Should cc-guide copy raw inputs (transcripts, chat excerpts, ticket exports) into the guide repository, or only reference them where they already live? → A: Reference only. The input register records each input's path, role, and checksum; raw inputs are never committed.
- Q: If a create or evolve run is interrupted, should running the same command again resume where it stopped? → A: Yes, automatic task-level resume from a progress ledger; a rerun continues at the first unfinished task, and finished tasks are never redone.
- Q: Should cc-guide require the prose plugin (cc-prose), use it when installed, or not use it? → A: Optional: use cc-prose voice profiles and AI-pattern checks when installed, fall back to built-in style rules otherwise, with a one-line notice.
- Q: How should the author find out that the sources have moved and the guide needs an evolve run? → A: A check-only evolve mode plus an opt-in scheduled workflow in the guide repository that runs the check and opens or updates one drift issue there.
- Q: When create starts a new guide, where should the guide project go, and should cc-guide create its remote repository? → A: A target directory (empty current directory or a new path) initialized as a git repository; a remote repository is offered, private by default, and created only after the author confirms name and visibility; pushing after each task is a separate opt-in asked once at the start.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a source-verified guide (Priority: P1)

A guide author has a set of inputs: one or more source repositories, meeting transcripts, ticket references, links, and notes. They run the create command, answer a short series of questions about audience, personas, scope, and output format, review the proposed outline and plan, and then let the plugin write the guide page by page. Every page is reviewed against the sources before the next one starts, and a final review covers the whole guide.

**Why this priority**: This is the core value: a guide that would take days by hand, with a factual accuracy that reviews can trust. Everything else builds on a guide created this way.

**Independent Test**: Run the create command on a small fixture project (one source repository and one transcript) and choose any one output format. The result is a buildable guide with persona sections, per-page source references, passing content checks, a recorded baseline, and a run summary.

**Acceptance Scenarios**:

1. **Given** a source repository and a transcript, **When** the author runs create and approves the outline and plan, **Then** the plugin produces a guide in the chosen format with one section per persona, a source reference block on every page, and a baseline file that pins every source to an exact revision.
2. **Given** a page task has finished, **When** its review finds a statement that the pinned sources contradict, **Then** the page is corrected before the next page task starts, and the correction is recorded in the run summary.
3. **Given** the transcript claims something the source code contradicts, **When** the page is written, **Then** the guide follows the source code and the discrepancy is recorded as a finding (and, when it concerns the upstream project, offered as an upstream finding).
4. **Given** the author marked some inputs as confidential (for example ones that mention customer names or ticket keys), **When** the guide is built, **Then** that content appears only in the internal part of the guide, and the shareable output passes a leak check.
5. **Given** a reviewer reports a finding that conflicts with the pinned source, **When** the plugin processes the finding, **Then** it re-checks the source before changing the page and records the decision.
6. **Given** the plan includes a diagram, **When** the diagram task finishes, **Then** the exported diagram passes the automated overlap check with zero findings and the controller has reviewed the exported image itself; if two automated fix rounds do not get there, the author is asked to finish the diagram on the canvas, and the plugin exports and checks it again after the author says it is done.

---

### User Story 2 - Evolve a guide when the sources change (Priority: P2)

Weeks later the upstream project has moved on. The author runs the evolve command. The plugin compares the recorded baseline with the current state of every source, shows which pages cite changed material, takes in any new inputs (for example a new walkthrough transcript), updates only the affected pages with the same per-page reviews, and records a new baseline.

**Why this priority**: Without evolve the guide decays and the effort of creating it is lost. It is the second reason the plugin exists.

**Independent Test**: Take a guide created by the plugin (or an existing guide that already has a baseline file and per-page source references, such as the SAW guide), move one pinned source forward by a known change, and run evolve. Only the pages that cite the changed material are updated, and the new baseline records the new revisions.

**Acceptance Scenarios**:

1. **Given** a guide with a baseline and one source that gained commits since, **When** the author runs evolve, **Then** the plugin lists the changed files, maps them to the pages that cite them, and proposes an update plan limited to those pages and the pages that reference them.
2. **Given** an upstream change request that was documented as experimental has since been merged, **When** evolve runs, **Then** the experimental label for that feature moves to the merged tier or is removed, and the page text reflects the merged state.
3. **Given** a cited file was renamed or deleted upstream, **When** evolve runs, **Then** the affected source references are flagged and resolved during the page task, never silently dropped.
4. **Given** the author supplies a new transcript, **When** evolve runs, **Then** new claims from the transcript are verified against the current sources before they enter the guide.
5. **Given** evolve completes, **When** the author inspects the guide, **Then** the baseline file records the new revisions and the previous baseline remains in version history.
6. **Given** the author enabled the scheduled drift check, **When** a pinned source gains changes that touch cited material, **Then** the next scheduled check opens (or updates) a single drift issue in the guide repository listing the affected pages, and the guide itself is not changed.

---

### User Story 3 - Preview the guide (Priority: P3)

At any point, including while a run is in progress, the author runs the preview command and sees the rendered guide in a browser, refreshing as pages change.

**Why this priority**: Authors judge layout, navigation, admonitions, and diagrams visually; text in a terminal is not enough. It is cheap to provide and used constantly.

**Independent Test**: In a guide created in any of the supported formats, run preview; the browser shows the guide, and editing a page updates the view.

**Acceptance Scenarios**:

1. **Given** a guide in any supported format, **When** the author runs preview, **Then** the guide is built and opened locally in a browser within one minute.
2. **Given** preview is running, **When** a page changes, **Then** the rendered view updates without restarting preview.
3. **Given** the guide has an internal part, **When** the author previews, **Then** they can choose between the shareable and the internal view.
4. **Given** preview is running, **When** a change breaks the build, **Then** the last good site stays visible, the build error is reported, and the next successful build replaces it.
5. **Given** the guide project is a linked git worktree (for example one created by a spec workflow), **When** the author runs preview, build, or export, **Then** the guide builds from the worktree's branch exactly as from the main checkout.

---

### User Story 4 - Export the full guide as a PDF (Priority: P4)

The author needs to hand the guide to people who will not open a website: reviewers who annotate on paper or in a PDF reader, a customer team behind a firewall, or a meeting where the guide is attached to an invitation. They run the export command and get one PDF of the whole guide, in reading order, with a title page that states the baseline it was verified against.

**Why this priority**: A single document is the most common way a guide actually travels, and the site tarball does not serve readers who want to print, annotate, or attach it. It reuses the built guide, so it is cheap once preview works.

**Independent Test**: In a guide created in any supported format, run export; the result is one PDF that contains every page of the shareable guide in navigation order, all diagrams, a table of contents, and a title page with the baseline date and source revisions.

**Acceptance Scenarios**:

1. **Given** a guide in any supported format, **When** the author runs export, **Then** one PDF of the shareable guide is produced, with a title page (guide title, baseline capture date, pinned source revisions), a table of contents, page numbers, and every page in navigation order.
2. **Given** the guide has an internal part, **When** the author runs export without asking for internal content, **Then** the PDF contains no internal pages, no links into the internal part, and none of the author's confidential terms.
3. **Given** the guide has an internal part, **When** the author explicitly asks for the full guide including internal content, **Then** the PDF includes the internal part, its file name and every page footer mark it as internal, and the plugin warns that it must not be shared outside the internal audience.
4. **Given** pages with diagrams, admonitions, experimental labels, code listings, and wide tables, **When** the PDF is produced, **Then** diagrams appear as sharp vector or high-resolution images, admonitions and experimental labels stay visually distinct, code listings wrap instead of being cut off, and tables fit the page width.
5. **Given** cross-references between pages and links to sources, **When** the reader clicks them in the PDF, **Then** cross-references jump to the target section inside the PDF and source links open the pinned revision.

---

### User Story 5 - Report problems found in the sources (Priority: P5)

While building or evolving the guide, the plugin collects problems in the upstream sources: documentation that contradicts the code, stale versions, dead configuration, confusing names that the guide has to warn about, missing documentation for a needed setting. The author runs the upstream command, reviews each drafted report, and approves which ones to file. Small mechanical fixes can also be offered as a change proposal from a fork.

**Why this priority**: The guide becomes a feedback loop that improves the upstream project, which also reduces the warnings the guide has to carry. It is valuable but not needed to produce a guide.

**Independent Test**: In a fixture repository with planted drift (a README value that contradicts a configuration default), run create and then upstream; a drafted report names both locations, is re-verified against the current default branch, and is only filed after explicit approval.

**Acceptance Scenarios**:

1. **Given** collected findings, **When** the author runs upstream, **Then** each finding is re-verified against the current default branch of its repository, findings that no longer hold are dropped with a note, and the remaining drafts are shown in full.
2. **Given** a drafted report, **When** the author has not approved it, **Then** nothing is posted.
3. **Given** a finding about a naming or user-experience problem, **When** it is drafted, **Then** it is proposed as a report with a suggested improvement, not as a change, because renames affect existing users.
4. **Given** a finding about a mechanical documentation fix, **When** the author chooses a change proposal, **Then** the plugin prepares it from a fork for the author to approve before submission.
5. **Given** the target repository is public, **When** a report is drafted, **Then** it contains no ticket keys, customer names, internal links, or links to private repositories, and it briefly explains that it came from an automated, source-verified documentation review.
6. **Given** a matching report already exists upstream, **When** drafts are prepared, **Then** the plugin shows the existing report instead of drafting a duplicate.

---

### User Story 6 - Validate recipes against a live cluster (Priority: P6)

Before publishing, the author wants proof that the documented commands work. They run the validate command against a named cluster connection. In the read-only tier, every check command in the guide runs and its result is compared with the documented expectation. In the full tier, which is only allowed on a cluster the author has marked as disposable, the install and onboarding recipes run end to end, and each command that changes the cluster needs the author's confirmation.

**Why this priority**: Source verification proves the guide matches the code; live validation proves the instructions work. It is opt-in and needs infrastructure, so it comes last.

**Independent Test**: Against a test cluster, run validate in the read-only tier on a guide with one correct and one deliberately wrong check; the report marks the first as passing and the second as a finding, and nothing on the cluster changes.

**Acceptance Scenarios**:

1. **Given** a guide and a named cluster connection, **When** the author runs validate in the read-only tier, **Then** only commands that query state are executed and each result is reported as matching, not matching, or not evaluable.
2. **Given** a cluster not marked as disposable, **When** the author requests the full tier, **Then** the plugin refuses and explains how to mark a cluster as disposable.
3. **Given** the full tier on a disposable cluster, **When** a recipe step would change the cluster, **Then** the plugin shows the command and waits for confirmation.
4. **Given** validation results, **When** the author continues, **Then** mismatches become review findings that the next page update addresses.

---

### Edge Cases

- A source repository is private, unreachable, or requires credentials the session does not have: the plugin reports which source failed and continues with the others only if the author agrees; the baseline marks the source as unverified.
- A pinned revision no longer exists upstream (force-pushed or deleted branch): evolve reports it and asks for a new pin instead of failing silently.
- A recorded change request was closed without merge: evolve removes or reworks the experimental content and records the decision.
- An input transcript quotes a person: quotations appear only verbatim; otherwise the content is paraphrased without quotation marks.
- The diagram tool is unavailable: the command warns with an install hint and asks whether to continue; on yes, diagram tasks are skipped with a placeholder that names the missing diagram, and the run continues (FR-003).
- The component that renders the PDF is missing, or the guide's content checks fail: export stops before writing a file and names the cause, so no incomplete PDF is ever handed out.
- A table or diagram is too wide for a portrait page: export switches that page to landscape or scales the element, never cuts it off.
- A required companion plugin is missing or too old: when superpowers is missing, Claude Code does not load the plugin and names the install command; when it is too old or its contract changed, create and evolve stop before any work, name the missing piece, and show how to install or update it.
- A subagent stalls or ends its turn early (for example after invoking a writing-quality check): the run detects it, resumes or restarts the task, and records a ruling.
- The session ends or the context is compacted mid-run: rerunning the same command resumes at the first unfinished task from the progress ledger; commits named in the ledger are trusted over the session's memory.
- Pushing to the remote fails because credentials are locked: the run keeps committing locally, reports the failure once, and retries later.
- The author's own drawing canvas has content when diagrams are created: it is backed up before and restored after, including before any operation that replaces the whole scene.
- Several drawing canvases are running (for example a project-level and a user-level diagram server): the plugin determines which canvas its diagram tools talk to before drawing and tells the author which one to open.
- No browser is connected to the canvas, so image export is impossible: the plugin opens the canvas in the browser, or asks the author to, before exporting.
- A diagram still fails the overlap check after two automated fix rounds: the plugin stops fixing, hands the diagram to the author on the canvas, and resumes only when the author says the manual edit is done.
- A git command is refused in an isolated or background session because a shell hook rewrites it: the run calls the git binary by its absolute path instead and records a ruling.
- Two findings describe the same upstream problem: they are merged into one report.
- A check command in the guide has no stated expectation: validate reports it as not evaluable rather than guessing.

## Requirements *(mandatory)*

### Functional Requirements

**Plugin structure and dependencies**

- **FR-001**: The plugin MUST be distributed as its own repository following the structure of the author's other `cc-` plugins (a marketplace manifest at the root, the plugin in a subdirectory with its own manifest, commands, skills, scripts, documentation, a build file, and an evaluation suite) and the usual Claude Code plugin conventions.
- **FR-002**: The plugin MUST expose the commands create, evolve, preview, export, upstream, and validate.
- **FR-003**: The plugin MUST declare the superpowers plugin as a hard dependency in its manifest, so Claude Code refuses to load the plugin without it and names the install command (author decision 2026-10-01: every command, including the check-only evolve mode, then needs superpowers installed; the scheduled drift check is unaffected because it runs without Claude Code). create and evolve MUST additionally verify the superpowers version and contract at start (FR-004) and stop with an actionable hint when it fails. When diagrams are requested and the diagram server is not available, the command MUST warn with an install hint and ask whether to continue with diagram placeholders; it MUST NOT silently produce a guide without the requested diagrams.
- **FR-003a**: The prose plugin (cc-prose) MUST be an optional companion: when installed, create and evolve MUST use its voice profiles for the per-section voices and its AI-pattern check in reviews; when absent, they MUST apply the plugin's built-in style rules and show a one-line notice that installing cc-prose improves voice and pattern checks. A missing prose plugin MUST never stop a run.
- **FR-004**: The plugin MUST detect when the superpowers components it relies on have changed incompatibly (renamed or missing skills or helper scripts) and report this instead of running a degraded flow silently.

**Create**

- **FR-005**: create MUST accept as inputs any combination of source repositories, transcript files, ticket references, web links, and free-form notes, and MUST record each input in an input register in the guide project with its location, role, and a checksum of its content. Raw inputs (transcripts, notes, ticket exports) MUST NOT be copied into or committed to the guide repository; only facts verified against the sources reach the pages, and confidential context reaches only the internal part.
- **FR-005a**: evolve MUST detect inputs whose checksum changed or whose location is no longer readable, and report them before planning updates.
- **FR-005b**: create MUST set up the guide project in a target directory, either the current directory when it is empty or a new path it creates, and initialize it as a git repository; it MUST refuse a non-empty directory that is not already a guide project.
- **FR-005c**: create MUST offer to create a remote repository for the guide project, private by default, and MUST create it only after the author confirms the name and visibility. Pushing to the remote after each completed task MUST be a separate opt-in, asked once at the start of the run; without it, the run only commits locally.
- **FR-006**: create MUST ask the author for audience, personas, scope, output format, voice per section, rigor profile, whether the guide has an internal part, and the confidential terms and patterns (for example customer names and ticket key formats) that must never appear in shareable output, using recommended defaults where possible.
- **FR-007**: create MUST pin every source repository to an exact revision in a baseline file at the start of the run, and all verification during the run MUST use those pinned revisions.
- **FR-008**: create MUST produce a written guide specification and plan for the author to approve before any page is written, using the superpowers brainstorming and planning flow.
- **FR-009**: create MUST execute the plan as one task per page or asset, using the superpowers subagent execution flow, with a review after each task under the standard and strict profiles.
- **FR-010**: Each page MUST carry a source reference block that lists the pinned files, line ranges, or links that support its statements.
- **FR-011**: The per-task review MUST check outline compliance, the guide's global rules, prose quality, and at least twelve factual statements per page (or every factual statement, if the page has fewer) against the pinned sources, and MUST classify findings by severity.
- **FR-012**: Before applying a review finding that changes a fact, the plugin MUST re-verify it against the pinned source; findings that the source contradicts are rejected and recorded.
- **FR-013**: create MUST finish with a whole-guide review covering cross-page consistency, persona journeys, the shareable/internal boundary, and guide-wide prose, followed by one fix round.
- **FR-013a**: create and evolve MUST keep a progress ledger that records each task's status (dispatched, implemented, in review with its fix round, complete) and its commits. Running the same command again after an interruption MUST resume at the first unfinished task without redoing finished tasks; a task interrupted during review or a fix round MUST resume at its next review or fix round. The ledger MUST identify the run it belongs to, so a ledger from a different run is never resumed by mistake.
- **FR-014**: create MUST record every autonomous decision taken during the run (what was decided, why, and what it costs if wrong) and present the list to the author at the end.
- **FR-015**: create MUST support documenting in-flight upstream change requests as experimental content in two tiers (merged but unreleased, and in review), labelled consistently and recorded with the change request's revision in the baseline.

**Output formats**

- **FR-016**: The plugin MUST define one adapter contract covering scaffold, injection of baseline values, admonitions including experimental labels, optional internal part with leak check, build, content checks, preview, and downloadable packages.
- **FR-016a**: Every adapter MUST build, preview, and export correctly when the guide project is a linked git worktree, not only from the main checkout.
- **FR-017**: The first release MUST ship adapters for AsciiDoc with Antora, Markdown with MkDocs Material, and plain GitHub-rendered Markdown.
- **FR-018**: Version numbers and revisions shown in the guide MUST come from the baseline file through the adapter, never be typed into pages.
- **FR-019**: Each adapter MUST provide content checks that fail the build on: missing source reference blocks, typographic dashes, internal content on shareable pages (links into the internal part and any of the author's confidential terms and patterns), hard-coded versions, and (for AsciiDoc) more than one sentence per line and image macros whose alt text contains a comma without being quoted (AsciiDoc splits it into width and height values).
- **FR-020**: Each adapter MUST produce downloadable packages: one for the shareable part, and one for the full guide when an internal part exists.

**Rigor profiles**

- **FR-021**: The author MUST be able to choose a rigor profile: fast (final review only), standard (per-task reviews, diagram-only visual review, final review; the default), or strict (standard plus a claim ledger with identifiers for every verifiable statement).

**Diagrams**

- **FR-022**: Diagram tasks MUST follow fixed diagram rules:
  - prefer curved arrows
  - plan the layout before drawing arrows, leaving channels of 80 to 100 px between rows for arrows and their labels and at least 40 px between boxes
  - keep every box and label off frame borders
  - bind every arrow to the edges of the boxes it connects
  - group a frame with its label and its children (real frames or groups), so a layout change moves them together
  - keep arrows clear of notes, labels, and unrelated boxes
  - use one semantic color palette throughout the guide
  - have exactly one label per shape (duplicate labels removed before export)
  - keep editable sources in the guide project's `diagrams/` directory next to the exported images
- **FR-022a**: Diagrams in the HTML output MUST open enlarged on click (Antora: the UI's `role=expand` lightbox; MkDocs: a lightbox plugin; GitHub Markdown: the image links to its full-size SVG).
- **FR-023**: Before a diagram is exported, an automated overlap check MUST pass on the diagram source: no arrow path (curves included) may cross a text element or box it is not bound to, and no label or box may cross a frame border. A failing check blocks the export.
- **FR-023a**: After export, the controlling session (not the subagent that drew the diagram) MUST review the exported image itself, never only the canvas, at native resolution (cropped regions for large exports), and record the result.
- **FR-023b**: Each diagram round's output MUST be kept under a versioned name so a better earlier round is never overwritten. At most two automated fix rounds MUST run per diagram; after that, the plugin MUST hand the diagram to the author for manual editing on the canvas, wait until the author says it is done, then export, run the overlap check, and review again. Manual editing is a regular step of the diagram flow, not an error path.
- **FR-024**: Before drawing, the plugin MUST determine which canvas its diagram tools are connected to and whether a browser is attached to it (opening it when export needs one). It MUST back up the author's existing drawing before creating diagrams or replacing the scene, and restore it afterwards.

**Evolve**

- **FR-025**: evolve MUST compare every pinned source with its current state and list the changed files and the pages whose source references cite them.
- **FR-025a**: evolve MUST offer a check-only mode that compares the baseline with every source and input, reports changed material, affected pages, and change-request status changes, and modifies nothing. The check MUST run without an AI session so it can run unattended.
- **FR-025b**: create MUST offer, opt-in, a scheduled workflow for the guide repository that runs the check-only mode on a fixed interval (weekly by default) and opens one drift issue in the guide repository, or updates the existing one, when material has changed; it MUST never change the guide itself. Sources the workflow cannot reach are reported as unchecked, not as unchanged.
- **FR-026**: evolve MUST propose an update plan limited to affected pages, pages that link to them, and new material from new inputs, and execute it with the same review rules as create.
- **FR-027**: evolve MUST re-evaluate every recorded change request (merged, still open with a new revision, or closed) and update the experimental content accordingly.
- **FR-028**: evolve MUST work on guides not created by the plugin if they have a baseline file and per-page source references. For a guide that lacks them, evolve MUST stop and offer a separate adoption step that pins the sources, adds source reference blocks page by page with the same per-task reviews, and records the first baseline; the regular evolve runs only after adoption completes.
- **FR-029**: evolve MUST write a new baseline only after the update run passes its checks.

**Preview**

- **FR-030**: preview MUST build the guide with its adapter, serve it locally, and open it in a browser; it MUST let the author choose the shareable or the internal view. It MUST watch the content sources and rebuild on change with a short debounce, queue changes that arrive during a build instead of dropping them, keep serving the last good site when a build fails (and report the error), and reload the browser after each successful build.

**Export**

- **FR-030a**: export MUST produce a single PDF of the whole guide in navigation order, for every supported output format, from the same content the build uses (no separately maintained print copy).
- **FR-030b**: The PDF MUST have a title page with the guide title, the baseline capture date, and the pinned source revisions, followed by a table of contents; every page MUST carry a page number.
- **FR-030c**: The PDF MUST preserve diagrams at print quality (embedded as SVG, or as PNG at twice the display resolution or more), admonitions and experimental labels as visually distinct blocks, code listings without truncation, and tables within the page width.
- **FR-030d**: Cross-references between guide pages MUST become working links inside the PDF, and links to sources MUST point to the pinned revisions; the PDF text MUST be searchable.
- **FR-030e**: export MUST default to the shareable part and MUST run the same leak check on the PDF as on the shareable build; it MUST include the internal part only on explicit request, and then mark the file name and every page footer as internal and warn the author.
- **FR-030f**: export MUST fail with a clear message, and produce no partial PDF, when the guide's content checks fail or a required export component is missing.

**Upstream findings**

- **FR-031**: The plugin MUST collect findings about the sources during create, evolve, and validate (documentation drift, stale references, dead configuration, missing documentation, confusing naming or user experience) with exact file and line references.
- **FR-032**: upstream MUST re-verify each finding against the current default branch of its repository and drop or rewrite findings that no longer hold.
- **FR-033**: upstream MUST show every draft in full and post nothing without the author's explicit approval.
- **FR-034**: upstream MUST file approved findings as issues; for mechanical documentation fixes it MAY prepare a change proposal from a fork, also only after approval; naming and user-experience changes MUST be filed as issues with a proposal.
- **FR-035**: Drafts for public repositories MUST NOT contain ticket keys, customer names, internal links, or links to private repositories, and MUST include a short note that they come from an automated, source-verified documentation review.
- **FR-036**: upstream MUST check for existing matching reports and link the guide's internal notes to the filed reports.

**Validate**

- **FR-037**: validate MUST be opt-in and require a named cluster connection.
- **FR-038**: The read-only tier MUST execute only commands that are positively identified as queries; any command not identified as a query MUST be treated as changing the cluster and skipped in this tier. Each executed result MUST be compared with the expectation stated next to the command in the guide.
- **FR-039**: The full tier MUST refuse to run unless the named connection carries an explicit disposable flag in the guide project's configuration, set by the author, and MUST ask for confirmation before each command that changes the cluster.
- **FR-039a**: validate MUST NOT write credentials, tokens, or connection secrets into the guide project, the run records, the findings, or upstream drafts, and MUST redact them from reported command output.
- **FR-040**: Validation results MUST be reported per command and turned into review findings for mismatches.

**Overview pages**

- **FR-043**: The guide spec MUST start with a why card (problem, outcome, one definition per named product from that product's own pinned source, how the parts fit, why this combination, status and limits) that the author approves before any page is written. The start page and every section overview page MUST answer why before how in the shape the plugin's overview contract fixes, and their per-page and final reviews MUST apply a cold-reader test that treats an unanswered question, or a definition that only repeats a name or its containing repository, as an Important finding. evolve MUST add a missing why card, with the author's approval, and then revise the overview pages.

**Documentation**

- **FR-041**: The plugin MUST document the lessons learned while building the SAW guide (the list in the brainstorm document) and the recommended session settings: the most capable model for the controlling session, subagents inheriting it, a high reasoning effort for create and evolve and a higher one for strict rigor, and a permission allowlist for the tools the run needs instead of bypassing all permissions.
- **FR-042**: At command start the plugin MUST state the recommended model and effort, and MUST warn without blocking when the session's model is not the recommended one.

### Key Entities

- **Guide project**: The repository that holds the guide, its configuration (format, personas, voices, rigor, internal part), the baseline, and the run records.
- **Source**: A repository, document, or link the guide is verified against; pinned to an exact revision.
- **Baseline**: The recorded set of source revisions, change requests with their revisions, and the capture date that the current guide was verified against.
- **Input**: Material that informs the guide but is not authoritative (transcripts, tickets, notes); claims from inputs must be verified against sources. Inputs stay where they live; the guide project holds only an input register entry (location, role, checksum).
- **Persona**: A reader role (for example administrator or user) with its own section and journey.
- **Page**: A unit of the guide with an outline, a voice, and a source reference block.
- **Adapter**: The output-format implementation that fulfills the adapter contract.
- **Rigor profile**: The chosen verification depth for a run.
- **Finding**: A problem in the guide (review finding) or in a source (upstream finding), with location, severity, and status.
- **Ruling**: An autonomous decision taken during a run, with reason and cost if wrong.
- **Validation result**: The outcome of one executed check command against a cluster.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An author with one source repository and two transcripts gets a complete, buildable guide with both persona sections without writing any process artifacts (review guides, checks, plans) by hand.
- **SC-002**: For a guide created with the standard profile, at least 95% of factual statements in an independent sample (at least 15 per guide, drawn by the evaluation suite or checked by the author, not by the run's own reviewers) are supported by the pinned sources, and every fact planted as wrong in an evaluation fixture's inputs is caught.
- **SC-003**: Every page of a created guide has a source reference block, and the content checks pass on the first build after the run.
- **SC-004**: After a source change, evolve identifies 100% of the pages whose cited material changed and modifies no page outside the affected set and its referencing pages.
- **SC-005**: evolve on the existing SAW guide, moving its SAW baseline to a revision that includes the OpenShell v0.1.2 upgrade, completes with passing checks and an updated baseline.
- **SC-006**: Zero upstream reports or change proposals are posted without explicit approval, and every posted report was re-verified against the current default branch within the same run.
- **SC-007**: Zero commands that change a cluster run without per-command confirmation, and zero run on a cluster not marked disposable.
- **SC-008**: Preview shows the rendered guide within one minute for a guide of 25 pages.
- **SC-009**: With a missing or incompatible companion plugin, the author gets an actionable message when the plugin loads (superpowers missing) or within the first step of a command (incompatible version or contract), before any file is written.
- **SC-010**: The fast profile completes a guide with at most half the review dispatches of the standard profile, and the strict profile produces a claim ledger in which every verifiable statement on every page has an identifier and a source.
- **SC-011**: export produces the PDF of a 25-page guide in under three minutes, and a reader can reach any page from the table of contents in one click.
- **SC-012**: Zero confidential terms or internal pages appear in a PDF exported without the explicit internal option.
- **SC-013**: Every diagram in a guide created by the plugin passes the overlap check with zero findings, was reviewed by the controlling session on the exported image, and went through at most two automated fix rounds before any manual editing.

## Assumptions

- Authors use Claude Code with the superpowers plugin installed; the diagram server is optional and only needed for diagrams; the prose plugin is optional and improves voices and AI-pattern checks.
- Upstream reporting targets GitHub in the first release; GitLab and ticket systems are out of scope for it.
- Source verification is static (reading pinned sources); live validation is the only feature that touches a running system.
- The guide project is a git repository the author controls; the run commits to it locally and pushes only when the author opted in at the start of the run (FR-005c).
- The working state of a run (ledger, briefs, reports) stays local and untracked; what later runs need (baseline, source reference blocks, run summary with rulings and findings) is committed.
- The existing SAW guide serves as the reference project for evolve and for regression testing of the Antora adapter.
- Out of scope for the first release: a Hugo adapter, hosting or publishing the site, export to Google Docs, and screenshot review of text pages.
