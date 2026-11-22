# Feature Specification: Captured visuals (web UI screenshots and rendered CLI output)

**Feature Branch**: `008-captured-visuals`

**Created**: 2026-11-22

**Status**: Draft

**Input**: User description: "Captured visuals for cc-guide guides: screenshots of web UIs and rendered CLI output, produced unattended from declarative capture recipes in a self-contained container environment, checked through text sidecars so text-only models can review them, with computed visual drift." Authoritative input: `brainstorm/09-captured-visuals.md`.

## Background

A guide created by cc-guide carries text, listings, and Excalidraw diagrams. Guides about tools with a user interface (for example the MLflow UI) or with rich terminal output (colors, Unicode bars, symbols) cannot show what the reader will see. Hand-made screenshots would contradict the guide's model: every page is pinned to source revisions, checked by scripts, and kept current through drift reports and `/guide:evolve`. A hand-made image has no recipe, no recorded version, and goes stale without anyone noticing. Screenshots taken from an author's own machine also leak hostnames, user names, local paths, and cluster identifiers.

This feature adds captured visuals: images that a guide project produces from committed recipes, in a throwaway environment it brings up itself, the same way on a laptop and in a CI job. Every visual has a text sidecar so that checks and reviews never depend on a model that can see images.

## Clarifications

### Session 2026-11-22

- Q: How is a visual tied to the guide's pinned sources, so that source drift also points at the visuals of a changed tool? → A: An environment may name a baseline source id (`source:`); the source drift report then lists the visuals of that environment as affected when the source drifts, and the sidecar records the source's pinned commit next to the image digest.
- Q: Which inputs make up a visual's recipe fingerprint, so that check can tell a stale visual? → A: The visual's own entry, its environment entry, its seed step and the content of every seed file it references, the effective redaction and mask rules, the resolved defaults that apply to the visual (for example the default width or drift threshold it inherits), and the capture environment version; a change to any of them makes the visual stale.
- Q: Is the capture environment pulled from a registry or built locally? → A: Built locally with podman from the definition vendored in `tools/guide/`, tagged with a hash of that definition, and reused while the hash is unchanged; no registry account is needed.
- Q: How does a capture run know that a web tool is ready? → A: It polls an HTTP path on the environment's port (default `/`, configurable as `ready`) until it answers with a status below 400, with a timeout (default 120 seconds, configurable); on timeout every visual of that environment fails with the last status and the tail of the container log.
- Q: What CI runner does the workflow template target, and how does it run podman? → A: GitHub Actions on `ubuntu-latest`, which ships podman; the capture environment and the tool environment run as sibling containers on the runner's podman, never podman inside podman.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Render colored CLI output into a guide page (Priority: P1)

A guide author documents a CLI tool whose output uses colors and Unicode symbols. The author declares a capture of a command in the guide's capture recipe file. Running the capture command produces a scalable image of the command and its output, with a neutral prompt, faithful colors, and no personal details, plus a text sidecar holding the plain output. The page embeds the image like any other image.

**Why this priority**: CLI tools are the most common subject of guides, need no browser or UI, and deliver visible value with the smallest environment. This slice proves the recipe file, the capture run, redaction, and sidecars end to end.

**Independent Test**: In a guide project with one CLI capture declared, run the capture command; the image appears in the guide's visuals directory and its sidecar in `visuals/`, the image shows the colored output with a neutral prompt, and the build and checks pass with the image embedded on a page.

**Acceptance Scenarios**:

1. **Given** a recipe declaring a CLI capture of a command whose output contains ANSI colors, bold text, and Unicode block characters, **When** the author runs the capture command, **Then** a scalable image is written that shows the command after a neutral prompt (`$ `) and its output with the same colors, weights, and characters, and a sidecar is written with the plain text of the command and output.
2. **Given** the command output contains an absolute path under the capturing user's home directory or the capture host's name, **When** the capture runs, **Then** neither appears in the image or the sidecar; the default redaction replaces them before the image or the sidecar is written.
3. **Given** the command exits with a non-zero status that the recipe does not expect, **When** the capture runs, **Then** the capture of that visual fails with the command, the exit status, and the last lines of its error output, no image or sidecar is written for it, and other visuals are still captured.
4. **Given** an Antora, MkDocs, or GitHub Markdown guide, **When** a page embeds a rendered CLI image, **Then** the site build, the PDF export, and the GitHub rendering show it as an image.

---

### User Story 2 - Capture an annotated web UI screenshot from a self-contained environment (Priority: P1)

A guide author documents a tool with a web UI that runs standalone in a container (for example an MLflow tracking server). The recipe declares the tool environment (the container image and its port), a seed step that loads fictional demo data (an experiment with runs and metrics), and one or more visuals as step lists: open a path, click, fill a field, wait for an element, highlight an element with a numbered callout, and crop to an element. One capture command starts the environment, seeds it, replays every visual, and tears everything down, with no access to the author's clusters or credentials.

**Why this priority**: Web UIs are the main reason the author asked for this feature. Annotations and crops are the parts the author called out as most valuable.

**Independent Test**: In a guide project whose recipe declares a standalone web tool, a seed step, and one annotated, cropped visual, run the capture command on a machine with podman and no cluster access; the cropped, annotated image and its sidecar appear, and no container or network from the run remains afterwards.

**Acceptance Scenarios**:

1. **Given** a recipe with a tool environment, a seed step, and a visual that highlights an element with callout `1` and crops to a containing panel, **When** the capture runs, **Then** the image shows only the panel, the highlighted element is outlined with a callout labeled `1` next to it, the rest of the panel is dimmed, and the sidecar lists the visible text and element structure of the panel and records the highlight with its label and the text of the highlighted element.
2. **Given** the highlighted element moves on the page between two tool versions, **When** the capture runs again, **Then** the highlight and callout follow the element, because they are placed by element selector and not by pixel position.
3. **Given** a step's selector matches no element within the step's timeout, **When** the capture runs, **Then** the visual fails with the visual name, the step number, and the selector, a debug image of the page at the time of the failure is written to the run directory (not to the guide's images), and the other visuals are still captured.
4. **Given** the run finished or failed, **When** the author lists containers and networks, **Then** nothing created by the run remains.
5. **Given** a seed step that fails, **When** the capture runs, **Then** no visual of that environment is captured and the error names the seed step.

---

### User Story 3 - Review visuals with a text-only model (Priority: P2)

The guide checks and the page review treat a visual as a claim. The caption and the page sentences that refer to a visual must be supported by its sidecar. A reviewer that cannot see images (for example GLM through a harness without image input) verifies the visual through the sidecar alone. A multimodal reviewer may also look at the image, but no check requires it.

**Why this priority**: The author explicitly requires that nothing in the pipeline depends on a multimodal model. Without this, visuals would be unverified claims in a source-verified guide.

**Independent Test**: Run the check command on a guide with a missing sidecar, an undeclared image, and a stale visual; it reports each mechanically. Separately, give a page whose caption names a value missing from the sidecar to a page review; the review guide instructs the reviewer to rate the caption mismatch from the sidecar text alone.

**Acceptance Scenarios**:

1. **Given** a page embeds a visual whose image file or sidecar is missing, **When** the guide check runs, **Then** it reports the page, the line, and the missing file.
2. **Given** a page embeds an image under the visuals directory that no recipe declares, **When** the guide check runs, **Then** it reports the image as not produced by a recipe.
3. **Given** a visual's recipe changed after the image was captured, **When** the guide check runs, **Then** it warns that the visual is stale (its recorded recipe fingerprint no longer matches) without failing.
4. **Given** a sidecar without a redaction record, **When** the guide check runs, **Then** it reports the visual as unredacted.
5. **Given** the page review of a page with visuals, **When** the reviewer follows the page review guide, **Then** the guide tells it to check each caption and each sentence about a visual against the sidecar text, and to rate a statement the sidecar does not support like any unsupported statement.

---

### User Story 4 - Notice visual drift and recapture (Priority: P2)

When the documented tool changes, the visuals must change with it. A drift run recaptures the visuals into a scratch location and compares them with the committed ones: an image difference above a threshold and any change in the sidecar text (after masking volatile values such as timestamps and run identifiers) become findings in a visual drift report that names what changed. `/guide:evolve` treats these findings like source drift: it recaptures the affected visuals and updates the pages that refer to them.

**Why this priority**: Visual drift keeps the prose honest when the UI changes, and the author called it important. It depends on stories 1 and 2.

**Independent Test**: Capture visuals, then change the seed data or the tool image version in the recipe, and run the visual drift command; it exits with the drift status and reports, per visual, the image difference and the changed sidecar lines, without modifying committed visuals.

**Acceptance Scenarios**:

1. **Given** committed visuals and an unchanged environment, **When** the visual drift command runs twice, **Then** it reports no drift (volatile values are masked and rendering is deterministic).
2. **Given** a tool version change that alters a table column header, **When** the visual drift command runs, **Then** it exits with the drift status and its report for that visual includes the changed sidecar line and the image difference value.
3. **Given** the visual drift command, **When** it runs, **Then** it writes only into the run's scratch directory; committed images and sidecars are unchanged.
4. **Given** a drift report with visual findings, **When** the author runs `/guide:evolve`, **Then** evolve recaptures the visuals, shows the affected pages, and updates the text that refers to changed visuals through the usual page tasks and reviews.

---

### User Story 5 - Plan visuals when creating a guide, and add them to an existing guide (Priority: P3)

During `/guide:create`, the plan proposes visuals per page next to the diagrams: which tool screens or commands a page should show and why. Page tasks write the recipe entries and seed data, the controller runs one capture, and the pages embed the results. For a guide that already exists, `/guide:evolve --visuals` sets up the capture recipe file and the capture targets without a drift run, so the author can add visuals later.

**Why this priority**: The workflow integration makes visuals part of normal guide creation, but the capture, checks, and drift (stories 1 to 4) are usable without it.

**Independent Test**: Run `/guide:evolve --visuals` in an existing guide project without visuals; the recipe file skeleton and the capture targets appear and `make check` still passes. Inspect the create skill's plan instructions; they ask for proposed visuals per page with the same approval step as diagrams.

**Acceptance Scenarios**:

1. **Given** an existing guide without visuals, **When** the author runs `/guide:evolve --visuals`, **Then** the guide gains an empty recipe file with comments explaining each field, the `visuals/` sidecar directory, and the capture targets in its build file; the CI workflow is added only when the author agrees, an ignore entry only when `.guide/` is not already ignored, and the toolkit is refreshed first when `tools/guide/VERSION` predates visuals. Nothing else changes.
2. **Given** a guide plan that proposes visuals, **When** the author approves the plan, **Then** the visual tasks come before the pages that embed them, the same order as diagram tasks.
3. **Given** a guide whose tool runs only inside a platform that cannot be started in a throwaway environment, **When** the plan considers visuals for it, **Then** it proposes none for that tool and notes that platform-only UIs are out of scope.

---

### User Story 6 - Run captures unattended in CI (Priority: P3)

A guide repository runs the capture and the visual drift check in a CI job, using the same commands as on a laptop. A scheduled job reports visual drift; it does not modify the repository.

**Why this priority**: The author wants the capture self-contained enough for a CI pipeline. A workflow template makes that concrete, but the commands themselves (stories 1 and 4) already work unattended.

**Independent Test**: Validate the CI workflow template's syntax and confirm it calls only the documented capture and drift commands, with no secrets and read-only repository permissions.

**Acceptance Scenarios**:

1. **Given** the CI workflow template installed into a guide repository, **When** it runs on its schedule, **Then** it runs the visual drift command and fails the job with the drift report as its summary when visuals drifted.
2. **Given** the workflow template, **When** it is reviewed, **Then** it needs no repository secrets and requests only read access to the repository contents.

---

### Edge Cases

- A recipe declares a visual name twice, or a name with characters unsafe for file names: the schema check rejects the recipe before any environment starts.
- The capture runs on a machine without podman, or podman cannot start containers: the capture command stops before doing anything with a message naming the missing prerequisite (and `make doctor` reports it).
- The tool's container image cannot be pulled: the capture of every visual in that environment fails with the image reference; no partial image is written.
- A port declared by the environment is already in use on the host: a run publishes no host ports (FR-011), so this cannot block a run.
- CLI output is wider than the configured terminal width: the output wraps at the configured width the same way on every run; the default width is 100 columns.
- CLI output contains emoji: the image embeds them as raster images rendered from an emoji font shipped in the capture environment, so the result depends neither on the host's fonts nor on the viewer's (FR-016). An emoji sequence (a ZWJ sequence, a flag, a keycap, a skin tone, or a character followed by U+FE0F) takes one two-column cell and is drawn as the font's glyph for the whole sequence; a character without U+FE0F keeps its text presentation. A sequence the font has no glyph for shows its first emoji. The sidecar keeps every code point of the sequence.
- A command prints a timestamp, duration, or generated identifier: the recipe declares mask patterns with fixed replacement values for that visual; the image and the sidecar show the replacement (FR-018), so repeated captures and drift runs do not differ in those values.
- A visual declares a light and a dark variant, but the tool has no dark theme: the dark capture equals the light one, so the dark variant is recorded as skipped in the light sidecar and check accepts the missing dark image (FR-037, FR-023).
- A recipe needs a step the step language does not cover: a script step runs a committed script file inside the capture environment; the sidecar lists the script files a visual ran (FR-017), so reviewers see that a visual used one.
- The guide has no recipe file: the capture and visual drift commands report "no visuals declared" and exit successfully; check does not require visuals.
- A visual shows something only the internal part should see: all visuals are shareable in this version (there is no internal visuals directory); the confidential-term check on sidecar text (FR-023) catches confidential content, and such a visual is left out.

## Requirements *(mandatory)*

### Functional Requirements

#### Recipe file

- **FR-001**: A guide project MAY contain one capture recipe file, `visuals.yaml`, at the guide project root. It declares environments, seed steps, redaction rules, defaults, and visuals.
- **FR-002**: An environment MUST be declared as one of two kinds: a web environment (image reference, the container port of the web UI, optional environment variables and command, an optional readiness path `ready` (default `/`) and readiness timeout (default 120 seconds)) or a CLI environment (an image reference whose tools the CLI captures run, kept running for the length of the run). A third kind, a local Kubernetes cluster in containers, is reserved in the schema and rejected with "not supported yet" in this version. An environment MAY name a baseline source id (`source:`) that it shows; the schema check rejects an id that `baseline.yaml` does not define. All environments of a run, and the capture environment, share one network the run creates; each container gets the environment name as its fixed host name, so environments reach each other by name, and every container receives `GUIDE_ENV_<NAME>_URL` (the base URL of each web environment; `<NAME>` is the environment name in upper case with `-` replaced by `_`) in its environment. Environment names MUST be valid host names (lower case letters, digits, and `-`, starting with a letter); the schema check rejects other names.
- **FR-002a**: A web environment MUST count as ready when its readiness path answers with an HTTP status below 400. When the timeout passes first, every visual of that environment fails with the last status (or connection error) and the last lines of the container log.
- **FR-003**: Image references in environments MUST name a tag or digest; a reference without either (implicitly `latest`) and a reference with the explicit tag `latest` are both rejected by the schema check, because a visual must record the version it was captured from.
- **FR-004**: A seed step MUST be a list of commands, each run inside the tool environment's container (the default, where the tool's own client lives) or inside the capture environment (`in: capture`), after the environment is ready and before any visual of that environment is captured. Seed data and seed scripts MUST be committed files in the guide project (or come with the tool image) and MUST contain fictional data only; a seed step cannot download anything, because the run network has no outbound access (FR-010).
- **FR-005**: A web visual MUST be declared as a name, an environment, an optional viewport, and an ordered list of steps from this set: `goto <path>`, `click <selector>`, `fill <selector> <text>`, `press <key>`, `wait <selector>`, `highlight <selector> <label>`, `crop <selector>`, `hide <selector>`, `script <path>`. At most one `crop` per visual; `highlight` may appear several times with distinct labels. Selectors are CSS selectors or the `text=<text>` and `role=<role>[name=<name>]` forms. A `script` step runs a committed script file that receives the open browser page and the environment's base URL; its exact interface is fixed in the toolkit contract.
- **FR-006**: A CLI visual MUST be declared as a name, an environment (a CLI environment, or a web environment, in which case the command runs inside the tool's own container, the way seed steps do), the command, an optional expected exit status (default 0), an optional terminal width (default 100 columns), an optional displayed prompt (default `$ `), and optional environment variables. The command MUST run under a pseudo-terminal with `COLUMNS` set to the width and a fixed `TERM` (`xterm-256color`), so tools that disable colors without a terminal still emit them.
- **FR-007**: The toolkit MUST provide a schema check of the recipe file that reports every problem with its location (visual name and step number) and runs without starting any environment. Step numbers start at 1 in schema problems and in run failures alike, so `visuals.<name>.step 3` and a run's "step 3" name the same step.

#### Capture run

- **FR-008**: One command MUST capture all visuals, or the visuals named on the command line, unattended: build or reuse the capture environment, start each needed tool environment, wait until it is ready, run its seed step, replay its visuals, apply redaction, write images and sidecars, and remove every container and network the run created, also when the run fails or is interrupted. Every container and network a run creates MUST carry a label identifying cc-guide captures and the run id; the labels also carry identifiers of the guide project path and of the host (short hashes, so `podman inspect` never shows the raw path or host name) and the owning process id. At start, a run removes only labeled resources whose owning process on this host is no longer alive; under the lock it also deletes the scratch inputs earlier runs left behind (FR-021) and keeps only the ten newest run directories in `.guide/visuals/` (older ones are pruned). Runs of the same guide project are serialized by a lock in `.guide/visuals/`; a second run exits 2 with "capture already running".
- **FR-009**: The capture environment MUST be a container image built locally with podman from a definition vendored in `tools/guide/`, containing the browser, the terminal renderer, and the fonts (including an emoji font). Its definition MUST pin the versions it installs, transitive dependencies included (every package the image's package manager installs, for example the character width table the terminal renderer uses), so two runs of the same recipe on machines of the same CPU platform (for example two linux/amd64 hosts) produce the same images; across platforms (an arm64 laptop and an amd64 CI runner) images may differ slightly in rasterization. The image is tagged with a hash of its definition and reused while the hash is unchanged; no registry account is needed.
- **FR-010**: Captures MUST NOT use the author's clusters, kubeconfig files, credentials, or host network services; the tool environment and the capture environment communicate over a network the run creates. That network is internal: tool containers and the capture container have no outbound network access at all (neither the internet nor the author's network). Container images are pulled, and the capture environment is built, on the host before any container of the run starts; that is the only outbound network access a run needs. Seed data and anything a seed step or a page needs therefore come from the tool image or from committed files under `visuals/`.
- **FR-011**: A run MUST NOT publish any port to the host. The capture environment reaches tool environments over the run network, and readiness (FR-002a) is polled from the capture environment; a run therefore never depends on a free host port.
- **FR-012**: A failure in one visual MUST NOT stop the other visuals of the run, and a failed visual leaves its previously committed image and sidecar unchanged. The capture command prints a summary listing each visual as captured, failed (with reason), or skipped, and exits 0 when every visual was captured or skipped, 1 when any visual or environment failed, and 2 on recipe or configuration errors, a missing podman, or a run already in progress. Without a recipe file it reports "no visuals declared" and exits 0 before checking for podman; the visual drift command does the same.
- **FR-013**: On a web step failure, the run MUST write a debug image of the page and the failing step to the run's scratch directory (`.guide/visuals/<run-id>/`), never into the guide's image directory.
- **FR-014**: Web visuals MUST be captured with animations and transitions disabled and a fixed viewport, device scale, locale, and time zone, so that repeated captures of an unchanged UI are identical or differ only below the drift threshold.

#### Output: images and sidecars

- **FR-015**: Each visual MUST produce an image in the adapter's visuals directory (Antora: `content/modules/ROOT/images/visuals/`; MkDocs and GitHub Markdown: `docs/assets/visuals/`, next to the diagrams directory), declared in each adapter descriptor, named after the visual: PNG for web visuals, SVG for CLI visuals.
- **FR-016**: A CLI visual's image MUST show the displayed prompt followed by the command, then the output with its ANSI foreground and background colors, bold, dim, italic, underline, and Unicode characters preserved, in a fixed monospaced font, and MUST be a self-contained SVG file that needs no external fonts, scripts, or styles: the font is embedded as a subset of the glyphs used, and emoji are embedded as raster images, so GitHub, the sites, and the PDF export show the same result. An SVG larger than 2 MB fails the visual with its size.
- **FR-017**: Each visual MUST produce a sidecar file `<name>.visual.yaml` (the dark variant `<name>-dark.visual.yaml`) in the guide project's `visuals/` directory, next to the recipe file and outside every published content directory, so sidecars never reach a built site. The sidecar records: the visual name, the kind, the environment image reference with the resolved index (manifest list) digest and the platform the capture ran on, the environment's baseline source id and pinned commit when it names one, the recipe fingerprint (over the visual's entry, its environment entry, its seed step and the content of every seed file and script it references, the effective redaction and mask rules by rule id and pattern template, never the host values a default rule resolves to, the resolved defaults that apply to the visual (CLI: width and prompt; web: viewport, step timeout, drift tolerance, and threshold), and the capture environment version), the capture environment version, the capture time, the redaction record (the ids of the rules applied and the number of replacements per rule, never the replaced values or the host values a rule resolved to), the script files the visual ran, the variants (with `skipped` for a declared variant that was not written, FR-037), the highlights (label, selector, text of the element), for CLI visuals a style fingerprint (a hash over the masked text together with its color and weight runs), and the text content: for web visuals the visible text of the captured region as an indented outline of its element structure (roles, labels, headings, table rows); for CLI visuals the plain text of the command and output.
- **FR-018**: Masks MUST work like redaction rules with a fixed replacement: each mask pattern of a visual declares the value that replaces every match (for example a fixed time), and the replacement is applied to the text before rendering (CLI) or to the page text before the screenshot (web), and to the sidecar. Images and sidecars therefore carry the same redacted and masked text, and repeated captures do not differ in masked values.

#### Annotations and crops

- **FR-019**: `highlight` MUST outline the element matched by the selector, place a numbered or labeled callout next to it without covering it, and dim the rest of the captured region. The callout MUST stay inside the captured region and MUST NOT cover other visible text, other highlights, or other callouts: it takes the first free position of above right, above left, below right, below left, right, and left (all outside the outline), and only when none is free the position that covers the least; `crop` MUST restrict the image to the bounding box of the matched element plus a fixed margin.
- **FR-020**: Annotations MUST be placed from the element's position at capture time, so they follow layout changes without editing the recipe.

#### Redaction

- **FR-021**: Redaction MUST run on every visual before any image, sidecar, report, or debug image is written. The only unredacted files a run writes are its own scratch inputs under `.guide/visuals/<run-id>/`: the raw CLI output (`raw/<name>.bin`) and the job file (`job.json`, which holds the host values the default rules resolve to). They MUST be readable by the owner only (mode 0600, `raw/` mode 0700), deleted at the end of the run (also when it fails or is interrupted), and swept by the next run of the guide project when a crash left them behind. Default rules MUST replace: the capturing user's home directory path and the user name where it appears in path form (`/home/<user>`, `/Users/<user>`) or as `<user>@`, the capture host's name, IPv4 addresses (exempt: the documentation ranges, loopback `127.0.0.0/8`, the unspecified address `0.0.0.0`, and the address range of the network the run created), strings shaped like bearer tokens, API keys, or JWTs, and Kubernetes API server URLs (`https://api.<host>:6443` and any `https://<host>:6443`). Text that a web UI draws on a canvas or into an image is not page text and cannot be redacted or masked; recipes hide or crop around such regions. For CLI visuals redaction applies to the text before rendering; for web visuals it applies to the page text in the browser before the screenshot, and to the sidecar.
- **FR-022**: The recipe MAY add redaction rules (a pattern and a replacement) and MAY disable named default rules per visual; disabling a default rule is recorded in the sidecar's redaction record.

#### Checks and review

- **FR-023**: The guide check MUST report as errors (failing `make check`): an embedded image under the visuals directory without a recipe entry; a declared visual whose image or sidecar is missing, unless its sidecar records the variant as `skipped` or the visual as a placeholder (FR-031a); a sidecar without a redaction record; a `visual:` reference to an undeclared visual; a page that embeds an image from the visuals directory without citing `visual:<name>` for it; a confidential term or pattern (the existing confidential-term configuration) in a sidecar's text content; and a recipe that fails the schema check. It MUST report as warnings (not failing, also under `STRICT=1`): a visual whose recorded recipe fingerprint differs from the current recipe (stale), because a toolkit update that changes the capture environment version marks every visual stale until the next capture; and a visual whose sidecar records a source commit that differs from the current `baseline.yaml` pin of its environment's source (captured before the last rebaseline). The guide check's dash rule (no em or en dash characters) skips files in the adapter's visuals directory, because generated images keep tool output verbatim.
- **FR-024**: The guide check MUST NOT start any environment, pull any image, or require podman; it reads only committed files.
- **FR-025**: The page review guide MUST instruct reviewers to verify each caption, alt text, and sentence that refers to a visual against its sidecar, and to treat a statement the sidecar does not support as an unsupported statement. Reviews MUST be completable without viewing the image; viewing it is optional for reviewers that can.
- **FR-026**: A page that embeds a visual MUST cite it in its source block with the reference form `visual:<name>`, next to the existing `<source-id>:<path>:<lines>` and `input:<id>` forms. The check resolves it to the declared visual and its sidecar (FR-023); the source id `visual` is reserved, like `self`, and guide validation rejects a baseline source with that id; the visual drift report and `/guide:evolve` use these references to find the pages that depend on a visual.

#### Visual drift

- **FR-027**: A visual drift command MUST recapture the declared visuals (or the named ones) into the run's scratch directory and compare each with the committed visual: for web visuals the image difference as the share of pixels that differ by more than a per-channel tolerance (default 16 of 255); for CLI visuals the style fingerprint (FR-017) instead of an image difference (the image difference value is reported as `n/a`); and for every visual a line diff of the sidecar's text content and highlights only (never the capture time, digests, or other provenance fields).
- **FR-028**: A visual counts as drifted when its sidecar text content or highlights differ, when its CLI style fingerprint differs, or when its image difference exceeds the threshold (default 0.5 percent of pixels, configurable per guide and per visual). A visual whose recapture fails at a step during a drift run (for example a selector that no longer matches) counts as drifted with the status "recapture failed", the step number, and the selector or command. When the committed visual was captured on a different platform than the current run (FR-017), the image difference is reported but does not count as drift on its own; the sidecar text still does. A failure of the environment itself (image pull, readiness timeout, seed step) is not drift: it is reported with the status "environment failed". The command MUST exit 10 when any visual drifted and no environment failed, 0 when nothing drifted, and 2 on environment failures, recipe or configuration errors, and when podman is missing. `make visuals-drift` fails on drift too, but GNU make reports every failing recipe as 2; callers that need the exact status run `uv run tools/guide/visuals.py drift`.
- **FR-029**: The visual drift report MUST list per drifted visual: the name, the pages citing it, the status (drifted or recapture failed), the image difference value (`n/a` for CLI visuals), the changed sidecar lines, and the environment image reference, index digest, and platform before and after. It MUST be available as Markdown and JSON.
- **FR-030**: The visual drift command MUST NOT modify committed images or sidecars. Replacing them is the job of the capture command or of `/guide:evolve`.
- **FR-030a**: The source drift report (`drift.py --check`) MUST list, for a drifted source that an environment names, the visuals of that environment as affected, so that a tool upgrade points at its visuals even before they are recaptured. This needs no podman.

#### Workflow integration

- **FR-031**: The `/guide:create` plan instructions MUST ask for proposed visuals per page (name, kind, what it shows, why the page needs it), presented for approval together with the diagrams. Visual tasks come before the pages that embed them. Page tasks that embed a visual cite its sidecar.
- **FR-031a**: Preflight MUST report whether podman is available. Without podman, the plan proposes visuals only when the author agrees to placeholders (recorded as a ruling, like diagram placeholders); a placeholder visual has a recipe entry and a sidecar marked `placeholder: true` and no image, and check reports it as a warning (not a missing image) until the first capture. When the author declines, the plan proposes no visuals and notes why.
- **FR-032**: The plan MUST NOT propose visuals for tools that cannot run in a standalone container or as a CLI in the capture environment (platform-only UIs); it notes the omission instead.
- **FR-033**: `/guide:evolve` MUST include visual drift findings in its drift report when the guide has a recipe file and podman is available, recapture the drifted visuals, and update the pages that cite them through its usual page tasks and reviews. When podman is not available, evolve reports that visual drift was not checked and continues.
- **FR-034**: `/guide:evolve --visuals` MUST add visuals to an existing guide: refresh the vendored toolkit first when `tools/guide/VERSION` predates visuals (the same toolkit refresh evolve already offers), then add an empty recipe file with explanatory comments, the `visuals/` sidecar directory, the capture and visual drift targets in the guide's build file when missing, the visual drift CI workflow (FR-036) when the author agrees, and an ignore entry for `.guide/visuals/` only when the guide's ignore file does not already cover `.guide/`, without a drift run.
- **FR-035**: Each adapter scaffold MUST provide `make visuals` (capture all, or `VISUALS=<names>`) and `make visuals-drift`, with identical semantics across adapters, and `make doctor` MUST report podman as an optional tool needed only for these targets.
- **FR-036**: The plugin MUST ship a CI workflow template for GitHub Actions on `ubuntu-latest` that runs the visual drift command on a schedule and on manual dispatch, needs no secrets, requests read-only repository permissions, and puts the drift report into the job summary. Like the existing drift workflow template, it carries the guide directory placeholder so it works for an embedded guide in a subdirectory. The capture environment and tool environments run as sibling containers on the runner's podman, never podman inside podman.

#### Variants

- **FR-037**: A web visual MAY declare color scheme variants (`light`, `dark`); each declared variant produces its own image (`<name>-dark.png` for the dark variant) and sidecar (`<name>-dark.visual.yaml`). Variants are optional; a visual without the declaration produces one image in the tool's default scheme. The run requests the scheme through the browser's color scheme preference; when the dark capture equals the light one (same sidecar text and an image difference below the drift threshold, because the tool ignores the preference), no dark image is written and the light sidecar records the dark variant as `skipped`. The schema check rejects a visual named `<x>-dark` when a visual `<x>` declares a dark variant. A visual that declares only `dark` writes `<name>-dark.png` and `<name>-dark.visual.yaml` and no `<name>.png`. When the committed sidecar records the dark variant as `skipped` but a drift run's dark capture now differs from the light one (the tool gained a dark theme), the visual counts as drifted.

### Key Entities

- **Capture recipe file**: the guide's declaration of environments, seed steps, redaction rules, defaults, and visuals. Committed; its per-visual fingerprint ties images to the recipe that made them.
- **Environment**: a throwaway tool instance (standalone web container, or CLI tool image) started per capture run, identified by an image reference with tag or digest.
- **Seed step**: committed commands and fictional data that put the tool into the state the visuals show.
- **Visual**: one named capture (web or CLI) with its steps or command, producing one image per variant and one sidecar.
- **Sidecar**: the text record of a visual, kept in the guide's `visuals/` directory outside the published content: provenance (image digest and platform, source commit, recipe fingerprint, capture environment version), redaction record, scripts, variants, highlights, style fingerprint (CLI), and the redacted and masked text content used by checks, reviews, and drift.
- **Capture environment**: the pinned container image with browser, renderer, and fonts in which every capture runs.
- **Visual drift report**: the per-visual comparison of a fresh capture with the committed visual.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a machine with podman and network access to container registries, an author can go from an empty recipe file to an embedded, annotated, cropped screenshot of a standalone web tool with seed data in under 30 minutes, without access to any cluster.
- **SC-002**: Two consecutive capture runs of an unchanged recipe on the same CPU platform, with every volatile value covered by a mask, produce CLI images that are byte-identical and web images whose difference is below the drift threshold for 100 percent of visuals; the visual drift command reports no drift.
- **SC-003**: A change of a visible label in the tool's UI is reported by the visual drift command for every visual showing it, with the changed label text in the report.
- **SC-004**: No captured image or sidecar in the plugin's test fixtures contains the capturing user's name, home path, host name, or a token-shaped string, verified by an automated test that captures with known values present.
- **SC-005**: Every check and review step for visuals completes with a reviewer that has no image input; the review guide never asks for image inspection as a required step.
- **SC-006**: After any capture or drift run, including one interrupted by a failure, no container or network created by the run remains on the host.

## Assumptions

- Podman is available on the author's machine and in the CI runner for captures and visual drift; it is not needed for building, checking, or exporting a guide. Docker is not supported (project rule).
- Tools that run standalone (for example an `mlflow server` container) are acceptable stand-ins for their platform-embedded versions; the author agreed that screenshots may show the standalone look.
- Platform-only UIs (for example the OpenShift AI dashboard), pluggable capture providers supplied by the documented project, animations (filmstrips, terminal playback), and Kubernetes-in-container environments are out of scope for this version.
- The PDF export embeds visuals as ordinary images; no interactive content is needed.
- The SVG produced for CLI visuals renders on GitHub, in Antora and MkDocs sites, and in the PDF export as an image.
- Fonts in the capture environment are open licensed and their licenses ship with the capture environment definition.
- Recipes are written by page tasks (an AI session) or by the author; the capture, check, and drift commands need no AI session.

## Revision Notes

- 2026-11-22: FR-008 labels identify the guide project path and the host by short hashes instead of raw values (found in code review; keeps host values out of `podman inspect` output). No behavior change for cleanup, which needs only host identity and process id.
- 2026-11-22: FR-009 pins transitive dependencies too: the Containerfile pins every package uv installs (wcwidth, zopfli, greenlet, pyee, typing-extensions were unpinned), and a test fails on an unpinned one.
- 2026-11-22: FR-021 names the run's unredacted scratch inputs (`raw/<name>.bin`, `job.json`): owner-only, deleted at teardown, swept after a crash. Redaction runs before any image, sidecar, report, or debug image is written, not before any file. The raw CLI output is now written with mode 0600 (it had the default mode).
- 2026-11-22: FR-007 numbers steps from 1 in schema problems too (they used zero-based `steps[2]` while run failures said "step 3"); seed steps likewise (`seed step 1`).
- 2026-11-22: FR-010 and FR-004 state that the run network is internal: tool containers have no outbound network access at all, so seed data comes from the tool image or committed files under `visuals/` (the code used `--internal` from the start; the spec said only what a run needs).
- 2026-11-22: FR-003 says that an explicit `:latest` tag is rejected as well as an implicit one (the schema check always did).
- 2026-11-22: The fingerprint clarification and FR-017 list the resolved defaults that apply to a visual (width, prompt, viewport, timeout, tolerance, threshold), which the fingerprint always covered.
- 2026-11-22: FR-023 states that the dash rule of the guide check skips the adapter's visuals directory (check.py always did).
- 2026-11-22: The PDF printer (`print-pdf.mjs`) drops the link of every image link in the print document (click-to-enlarge wrappers of MkDocs glightbox and of gfm diagram and visual links), not only of visuals; the image stays. Documented in `guide/docs/adapters.md` and `guide/docs/visuals.md`.
- 2026-11-22: FR-008 states that a run keeps only the ten newest run directories in `.guide/visuals/` (the code always pruned older ones).
- 2026-11-22: FR-028 notes that `make visuals-drift` reports a failing run as 2 (GNU make), so the exact status (0, 10, 2) comes from `uv run tools/guide/visuals.py drift`; the scaffold Makefiles' help text no longer claims exit 10.
- 2026-11-22: FR-019 fixes where a callout badge goes: the first of six positions around the outline that stays in the captured region and covers no visible text, other highlight, or other badge, else the least covering one (the badge of the smoke test covered part of the neighboring column header).
- 2026-11-22: Edge case on emoji: the renderer keeps grapheme clusters together and draws an emoji sequence (ZWJ, flag, keycap, skin tone, U+FE0F) from the emoji font's ligature glyph; it used to drop format characters, so a ZWJ sequence showed as separate emoji, U+FE0F had no effect, and the sidecar lost the joiners. A sequence without a ligature shows its first emoji.
