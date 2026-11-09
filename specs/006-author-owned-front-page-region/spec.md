# Feature Specification: Author-owned region on the generated front page

**Feature Branch**: `006-author-owned-front-page-region`

**Created**: 2026-11-09

**Status**: Draft

**Input**: User description: "Add a general marker-region publishing mechanism: any gfm guide can publish a designated page into an author-owned README, and the embedded front page carries an author-owned region that the guide never rewrites or verifies line by line." Authoritative input: `brainstorm/06-author-owned-front-page-region.md`.

## Clarifications

### Session 2026-11-09

- Q: What is the exact marker spelling? → A: `<!-- guide:region -->` opens and `<!-- /guide:region -->` closes the guide-owned region, mirroring the existing `guide:attr` open/close comment pair.
- Q: What does the publish declaration look like in the guide configuration? → A: A single `publish` block in `guide.yaml` with a `page` key (the source page inside the content root) and a `target` key (the README to write); one target per guide in v1.
- Q: How does an author bootstrap the markers in an existing README? → A: By hand: the publish command stops with an error when the markers are missing, and the author inserts the two comment lines where the guide content should appear. Embedded create is the exception: it writes the markers as part of the approved move plan.
- Q: How is a stale published region detected? → A: The region comparison runs in the standard check flow, so a region out of date with its source page fails the checks; when evolve updates the source page, the region is refreshed with it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Publish a guide page into an author-owned README region (Priority: P1)

An author maintains a standalone gfm guide in its own repository. The repository's root `README.md` is the landing page visitors see on GitHub. The author wants a hand-written pitch, context, and short usage examples at the top, and the guide's introduction below it, kept current by the guide. They declare a publish target in the guide configuration (a source page and the target README), place two markers in the README where the guide content should appear, and run the publish command. The guide renders the source page with links rebased for the new location and writes only the text between the markers. Hand-written text above and below the markers is untouched. The check command compares only the region and passes while the author text stays as written.

**Why this priority**: This is the general mechanism every other story builds on. Without it there is no region machinery to narrow or migrate onto.

**Independent Test**: Run the publish command on a fixture gfm guide with a README that has hand-written text around the markers; confirm the region is updated, the author text is byte-identical, and `--check` passes; edit author text, confirm `--check` still passes; edit region text, confirm `--check` fails.

**Acceptance Scenarios**:

1. **Given** a gfm guide with a publish declaration naming a source page and a target README outside the content root, **When** the publish command runs, **Then** the guide renders the source page with relative links rebased to resolve from the README's location and writes only the region between the markers.
2. **Given** a README with author text before and after the region, **When** the publish command runs, **Then** every byte outside the markers is unchanged.
3. **Given** a published README, **When** the check command runs, **Then** it compares only the rendered region against the source page and reports differences only there.
4. **Given** a guide with no publish declaration, **When** any guide command runs, **Then** no README outside the content root is read, written, or checked (behavior unchanged from today).
5. **Given** a README with no markers, **When** the publish command runs, **Then** it stops with an error that names the missing markers and the file, and changes nothing.

---

### User Story 2 - Author-owned region on the embedded front page (Priority: P1)

An author runs an embedded guide (spec 005) where the root README is the guide's front page. They want the same author-owned landing section there: pitch and context in their own voice above the guide's front page content. They add the markers to the front page, with the guide-owned content between them. The guide's page task, per-page review, final review, structure checks, sources block, and drift detection all operate on the region only. The author edits their section freely on GitHub; when `evolve` next updates the front page, it rewrites only the region and never reports or discards the author's edits. The ownership comment the front page carries (spec 005 FR-009a) states that the text between the markers is guide-owned and the rest belongs to the author.

**Why this priority**: Embedded mode is the highest-impact consumer: its front page is the whole repository landing page, and today every hand-written line is at risk from the next update.

**Independent Test**: In a fixture repository with an embedded guide, add markers and author text to the front page; run the checks (pass), edit author text and run `evolve` (author text preserved, no hand-edit report for it), and change a cited source file and run `evolve` (region updated through the normal page flow).

**Acceptance Scenarios**:

1. **Given** an embedded front page with markers, **When** any guide command reads, writes, checks, or reviews the front page, **Then** it does so only for the region between the markers (the whole-file link check of FR-008 excepted).
2. **Given** author text outside the region, **When** `evolve` updates the front page, **Then** the author text is preserved byte-for-byte and is not reported as a hand edit.
3. **Given** hand edits inside the region, **When** `evolve` runs, **Then** they are reported before the region is rewritten, exactly as spec 005 FR-009a requires for the whole file today.
4. **Given** a front page without markers, **When** any guide command runs, **Then** the whole file is guide-owned and every spec 005 behavior applies unchanged.
5. **Given** the front page, **When** the PDF and site exports run, **Then** the front page prints first with the whole file including author text, as today.

---

### User Story 3 - Embedded create keeps landing material as the author region (Priority: P2)

An author runs embedded create on a repository whose hand-written README has a pitch, context, and usage examples above its instructional content. The inventory and move plan (spec 005 FR-016 through FR-019) offer "stays as the author region" as the default destination for the landing-oriented sections, while instructional material is still verified as guide input. The author approves. create places the markers below the landing material and writes the generated front page region under it. The author's voice survives the conversion without any of its claims being verified, rewritten, or dropped.

**Why this priority**: This is the moment the author region is most valuable (the repository already has landing text worth keeping), but the region mechanism from stories 1 and 2 must exist first.

**Independent Test**: Run embedded create on a fixture repository with a pitch-style README; approve the move plan; confirm the landing sections remain as author text above the markers, unverified and unrewritten, and the generated front page region follows below.

**Acceptance Scenarios**:

1. **Given** an existing README with landing-oriented sections (pitch, context, usage examples), **When** embedded create inventories it, **Then** the move plan proposes "stays as the author region" as the default destination for those sections.
2. **Given** the approved move plan, **When** create finishes, **Then** the landing text stands above the markers unchanged except for placement, and the generated front page region follows below it.
3. **Given** instructional material in the same README, **When** create finishes, **Then** that material went through verification as guide input exactly as spec 005 FR-019 requires; only the landing sections were exempted.
4. **Given** a README section the author reclassifies in the move plan, **When** create finishes, **Then** the author's chosen destination applies, as today.

---

### User Story 4 - The guide notices contradictions without blocking (Priority: P3)

Over time the author's landing text drifts from the guide region (an example that no longer matches the tool's behavior). When a page task or review touches the front page or the published region's source page, the reviewer brief directs the reviewer to read the author region alongside it and flag contradictions as non-blocking findings in the run summary. The author decides what to do; nothing in the author region fails a build or a check, except an unresolvable link (FR-008).

**Why this priority**: This is the safety net for the silent-drift failure mode; the region mechanism is useful without it, so it ranks last.

**Independent Test**: In a fixture with a published front page, make the author region contradict a verified fact in the guide region; run the review flow for that page; confirm the contradiction appears as an advisory finding and no check or gate fails.

**Acceptance Scenarios**:

1. **Given** a front page or published region under review, **When** the page task or review runs, **Then** the reviewer brief includes reading the author region and flagging contradictions with the guide region or the sources.
2. **Given** a flagged contradiction, **When** the run completes, **Then** it is listed in the run summary as a non-blocking finding and no check, gate, or build fails because of author text, except the whole-file link check (FR-008).
3. **Given** author text of any content, **When** the guide checks run, **Then** no claim verification or code-block validation is applied to it.

---

### Edge Cases

- What happens when the markers are unbalanced (a begin without an end, or the reverse)? The check fails with an error naming the file and the unmatched marker; nothing is written.
- What happens when a file contains more than one marker pair? The check fails with an error naming the file and the count; the mechanism defines exactly one region per file.
- What happens when markers appear inside a fenced code block in the author text? They are treated as author text, not as region delimiters; the region parser must not be fooled by fences inside the region or the author text.
- What happens when the publish declaration names a target that has markers but the source page is deleted or renamed? The check fails with an error naming the missing source page.
- What happens when the author deletes the markers between two publish runs? The publish command stops with the missing-markers error (story 1, scenario 5) instead of writing the whole file. The author re-inserts the two marker lines by hand; no command ever inserts markers into an existing file outside an approved embedded create move plan.
- What happens when the author region contains links into the guide that do not resolve? The whole-file link check fails, because author links into the guide must resolve.
- What happens when a package registry publishes the README (spec 005 FR-010a inventory)? The guide region uses absolute links as FR-010a requires; relative links in the author region are the author's responsibility and produce no warning.
- What happens when the region is empty or the guide content is shorter than the author text? The front page contract (why card, cold-reader test, navigation) still holds for the region on its own, so the guide region reads correctly when the author section is short, long, or missing.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A README subject to guide publishing MUST carry at most one guide-owned region, delimited by `<!-- guide:region -->` (begin) and `<!-- /guide:region -->` (end), mirroring the existing generated-region comment convention (`guide:attr`); everything outside the markers is author-owned.
- **FR-002**: When no markers are present in a file the guide already owns (the embedded front page), behavior MUST be unchanged: the whole file is guide-owned and every spec 005 guarantee applies to the whole file. A declared publish target without markers MUST instead be an error (story 1, scenario 5), never a whole-file rewrite.
- **FR-003**: When markers are present, every guide command MUST operate on the region only: the publish writer and the embedded front-page page task write only the region, the checks validate only the region, drift and hand-edit detection compare only the region, and no command modifies, reports, or verifies author text outside the markers. The whole-file link check (FR-008) is the single exception: it reads the entire file.
- **FR-004**: The checks MUST fail with a clear error, and nothing MUST be written, when markers are unbalanced, duplicated, or otherwise malformed; the error names the file and the problem.
- **FR-005**: The region parser MUST NOT treat marker text inside fenced code blocks as delimiters.
- **FR-006**: A gfm guide MUST be able to declare a publish target in its guide configuration: a single `publish` block in `guide.yaml` with a `page` key naming the source page inside the content root and a `target` key naming the README to write; one target per guide in v1. Without the declaration, no command reads, writes, or checks any README outside the content root.
- **FR-007**: The publish writer MUST render the source page with relative links rebased to resolve from the target README's location, and MUST write only the region. The region comparison MUST run in the standard check flow, so a region out of date with its source page fails the checks, and when evolve updates the source page the region MUST be refreshed with it.
- **FR-008**: Link checks MUST cover the whole file, including author text, so author links into the guide must resolve.
- **FR-009**: The sources block and the front page contract (why card, cold-reader test, navigation, developer README link) MUST sit inside the region and MUST hold on their own, so the guide region reads correctly when the author section is short or missing.
- **FR-010**: In embedded mode, the front page machinery of spec 005 MUST narrow to the region when markers are present: the page task, per-page review, final review, structure checks, sources block validation, and drift detection operate on the region; FR-009a's hand-edit reporting applies to the region; FR-010a's badge and logo handling becomes ordinary author text outside the region.
- **FR-011**: The front page ownership comment MUST sit inside the region (it is guide-written) and MUST state, when markers are present, that the text between the markers is guide-owned and how to change it, and that the rest of the file belongs to the author.
- **FR-012**: Embedded create's inventory and move plan MUST offer "stays as the author region" as the default destination for landing-oriented sections of an existing README (pitch, context, usage examples), while instructional material continues through verification as guide input. The author can change each destination before approving, as today.
- **FR-013**: Author text MUST NOT be claim-verified, code-block-validated, or rewritten by any guide command. No check or build fails because of author text content, with one exception: the whole-file link check (FR-008), where an author link that does not resolve fails the check.
- **FR-014**: Reviewer briefs for front-page and published-region work MUST direct the reviewer to read the author region and flag contradictions with the guide region or the sources as non-blocking findings in the run summary.
- **FR-015**: Exports MUST behave as today: the embedded front page prints first in PDF and site with the whole file including author text; a plain guide's author region exists only in the README and never enters the guide's own exports.
- **FR-016**: The mechanism MUST ship for the gfm adapter first; other adapters are out of scope for this feature.

### Key Entities

- **Guide-owned region**: The text between the begin and end markers in a published README or embedded front page; the only part of the file any guide command generates, checks, reviews, or drift-detects.
- **Author-owned text**: Everything in the file outside the markers; owned by the repository author, never modified or verified by guide commands, covered only by whole-file link checks and advisory contradiction flags.
- **Publish declaration**: A guide configuration entry naming a source page and a target README; opts a gfm guide into README publishing.
- **Publish writer**: The command that renders the source page with rebased links into the target's region; the check mode compares the region only.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An author can add, edit, or delete any author text in a published README and no guide check, build, or update fails or reverts it, except an unresolvable link (FR-008) (verifiable with the fixture from story 1).
- **SC-002**: Every guide command that touches a file with markers changes bytes only inside the region (verifiable by byte comparison before and after each command in the test fixture).
- **SC-003**: A guide page published into a README region renders with all relative links resolving from the README's location, both on GitHub and in the whole-file link check.
- **SC-004**: An embedded create run on a repository with landing-oriented README sections preserves those sections verbatim as author text, with zero claims from them verified, rewritten, or dropped.
- **SC-005**: A reviewer run on a front page with a planted contradiction reports the contradiction as an advisory finding while all checks and gates pass.

## Assumptions

- The exact marker spelling is `<!-- guide:region -->` and `<!-- /guide:region -->`, mirroring the existing `guide:attr` generated-region comment pair (resolved in Clarifications).
- The publish declaration is a single `publish` block in `guide.yaml` with `page` and `target` keys, one target per guide in v1 (resolved in Clarifications).
- gfm-only in v1 (FR-016); the adapter contract may generalize the capability later.
- aprofile's migration (replacing its project-local `sync-readme.py` with this mechanism) happens after the feature lands, as a separate adoption step, not as part of this feature.
- Package-registry README publishing keeps spec 005 FR-010a's absolute-link rule for the guide region; relative links in author text are the author's responsibility without warnings.
- The region markers are visible in the raw file; no attempt is made to hide them beyond normal HTML comment rendering.
