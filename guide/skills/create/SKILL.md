---
name: create
description: Create a source-verified, persona-split guide from source repositories, transcripts, tickets, links, and notes. Interviews the author, scaffolds the guide project with an output adapter (Antora, MkDocs Material, or GitHub Markdown) in its own repository or embedded in the repository it documents (the README becomes the guide's front page), pins the sources, then drives superpowers brainstorming, writing-plans, and subagent-driven development with per-page reviews against the pinned sources, a final whole-guide review, and a run summary. Resumes an interrupted run. Use for /guide:create.
argument-hint: "[--dir PATH] [--embedded] [--format antora|mkdocs|gfm] [--rigor fast|standard|strict] [--source ID=REPO[@REF]]... [--input PATH]... [--restart] [description]"
allowed-tools: ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Skill", "Agent", "AskUserQuestion", "WebFetch"]
---

# /guide:create

You are the controller of a guide run. You interview the author, set up the guide project, and then orchestrate superpowers to write the guide page by page, each page verified against pinned sources. You never write pages yourself except for small source-verified fixes (ruling R7 of the page-task skill); subagents do.

Paths used below:
- `PLUGIN`: the plugin root, two directories above this skill's base directory.
- `GUIDE`: the guide project directory (absolute).
- `WS`: the subagent-driven-development plan workspace for `docs/guide/plan.md`, resolved with the vendored helper `bash tools/guide/sdd/sdd-workspace docs/guide/plan.md` (run from `GUIDE`). cc-guide ships its own copies of the SDD helper scripts under `tools/guide/sdd/`; never read or run scripts from another plugin's install directory (FR-006).
- `SESSION`: the directory this Claude Code session was started in (as in the preflight skill). Claude Code reads the session's permissions from there and from `~/.claude/settings.json`.
- `HOST` (embedded mode only): the root of the repository the guide documents. The guide project `GUIDE` is one subdirectory of it (default `HOST/guide`), and `HOST/README.md` is the guide's front page (specs/005-embedded-guide).

Run every command from `GUIDE` or with `-C`/`--root`. Never `cd` into `GUIDE/.guide/cache/`.

## Arguments

| Argument | Meaning |
|---|---|
| `--dir PATH` | Target directory; default the current directory |
| `--embedded` | Embed the guide in the existing repository at the target (gfm only; see section 3) |
| `--format antora\|mkdocs\|gfm` | Output adapter; asked in the intake when missing |
| `--rigor fast\|standard\|strict` | Default `standard` |
| `--source ID=REPO[@REF]` | Repeatable; a source to pin (`REPO` is a URL, a local path, or `owner/name`) |
| `--input PATH_OR_URL` | Repeatable; an input to register (never copied) |
| `--restart` | Start a new run even when an unfinished one exists (asks for confirmation) |
| free text | What the guide is about and who reads it |

## 1. Preflight

The `/guide:create` command runs the `guide:preflight` skill first. When its result line is not in this conversation (the skill was invoked directly, as it is on harnesses with no command layer), invoke `guide:preflight` with `create` and `--dir` now. Stop when it stops. Keep its result (`harness`, `prose`, `excalidraw`, `excalidraw_allowed`, `excalidraw_allowed_in`, `multi_agent`, and the superpowers version).

## 2. Resume or new run (FR-013a)

When `GUIDE/guide.yaml` exists:
- When `GUIDE/docs/guide/plan.md` exists, resolve `WS` with `bash tools/guide/sdd/sdd-workspace docs/guide/plan.md` (from `GUIDE`), and run `uv run tools/guide/runs.py resume --workspace "$WS"`.
  - A task number: an unfinished run exists. Without `--restart`, tell the author "Resuming the guide run at task N (tasks 1 to N-1 are complete in the ledger)." and continue at section 7 (Execution) with the existing plan, workspace, and ledger. Trust the commits the ledger names over anything you remember.
  - `done` with no run summary for this plan in `runs/`: continue at section 8 (Final review).
  - `done` with a run summary: the guide exists; suggest `/guide:evolve`, `/guide:preview`, or `/guide:export`, and stop.
- When there is no plan yet, the previous run stopped during setup or spec work: show what exists and continue at the first missing step (guide spec, plan).
- With `--restart`: ask "Start a new run? The existing plan and ledger stay in git history and in the workspace, but the new run will not resume them." Only on yes, move `docs/guide/plan.md` aside (`git mv` to `docs/guide/plan-<date>.md`) and continue at section 5.

## 3. Target directory (FR-005b, FR-001, FR-031)

Run `uv run "$PLUGIN/toolkit/guidecfg.py" discover --dir <target>` first (target: `--dir PATH` or the current directory).

- Exit 0 and the printed directory holds `guide.yaml`: an existing guide project (in its own repository or embedded in a host). Resume it as in section 2 with `GUIDE` set to the printed directory.
- Exit 3 (several embedded guides in the immediate subdirectories): list them and ask which one to use (`--dir`). Write nothing.
- Exit 4 (no guide project), then by target:
  - **Empty directory** (ignoring `.DS_Store`), or a `--dir PATH` that does not exist yet (create it): a guide in its own repository. This is the flow below; never offer embedded mode here.
  - **The root of an existing git repository** (`git -C <target> rev-parse --show-toplevel` prints the target itself) that is not a guide project: offer embedded mode (recommended): "This is the root of an existing repository. cc-guide can embed the guide in a subdirectory here and make the README the guide's front page (gfm only). Embed the guide here?" `--embedded` answers yes without asking. On yes, `HOST` is the target and the embedded steps below apply. On no, stop as for a non-empty directory.
  - **A subdirectory of a git repository** (for example a package in a monorepo): stop with "`<dir>` is inside the repository `<toplevel>` but not its root. Embedded guides live at the root of the repository they document in this release; run create from `<toplevel>`, or choose an empty directory for a separate guide." Write nothing.
  - **A non-empty directory that is not a git repository**: stop with "`<dir>` is not empty and is not a guide project. Choose an empty directory or a new path with --dir." Write nothing.
- `--embedded` with an empty or non-git target: explain that embedded mode needs the root of an existing repository and stop.
- `--embedded` together with `--format antora` or `--format mkdocs`: explain that embedded guides use GitHub Markdown only in this release (the front page is the README GitHub renders; Antora and MkDocs guides live in their own repository) and ask whether to continue with gfm or stop.
- A separate guide (empty target) keeps the full intake, including the format choice and the remote repository offer.

### Embedded preconditions (before the intake)

Only in embedded mode. `HOST` is the repository root.

1. **Clean tree**: `git -C "$HOST" status --porcelain` must be empty. When it is not, stop: "The repository has uncommitted changes. Commit them or set them aside first, so the guide's commits contain only guide work." Write nothing.
2. **Branch**: when the current branch is the default branch (`origin/HEAD`, else `main`, else `master`), ask: "You are on `<branch>`. Create a working branch for the guide (recommended), or commit the guide directly to `<branch>`?" Offer `guide/<slug>` as the branch name; create it with `git -C "$HOST" switch -c <name>` only after the answer. Every later commit goes to the branch the author approved.

## 4. Intake interview (FR-006, FR-005c)

Ask with AskUserQuestion, at most four questions per call, recommended option first. Use the free-text description and the arguments to pre-fill answers, and skip questions they already answer. Collect:

1. **Subject and audience**: one paragraph you will reuse in the guide spec.
2. **Personas**: default `admin` (Administrator) and `user` (User); allow more or fewer.
3. **Scope**: what is in and out (for example installation, day 2, user onboarding; not upstream development).
4. **Output format** (when no `--format`): `antora` (AsciiDoc, Antora site with the RHDP UI, best for large guides), `mkdocs` (Markdown, MkDocs Material), `gfm` (Markdown rendered on GitHub, no build). Recommend antora for guides with more than about 15 pages, gfm for small guides that live next to code.
5. **Branding** (Antora only; do not ask for `mkdocs` or `gfm`, whose adapters support no branding keys). Every new Antora guide gets the neutral theme: the vendored Red Hat fonts, a red rule under the header, and an empty footer (`theme: neutral`, `footer: none`). Ask one question: **"Is this guide about a Red Hat product?"**
   - **Yes**: ask for the short product name (one line, 1 to 40 characters), stored as `logo_text`. The header shows the Red Hat logo layout (the Red Hat hat, a divider, and the name). The default alt text is "Red Hat <name>".
   - **No**: the header shows a text logo without the Red Hat hat (`wordmark`). Propose the guide title when it has at most 40 characters; otherwise ask for a shorter text. The alt text is the wordmark itself.
   Then offer the follow-ups, each optional:
   - **Own logo** instead of the text logo: an SVG file made for a dark background (`logo`), with its alt text (`logo_alt`, required, because only the author knows what it shows).
   - **Footer**: a text with an optional `http` or `https` link instead of the empty footer.
   - **Favicon**: an `.ico`, `.png`, or `.svg` file for the browser tab.
   Do not offer the Red Hat Demo Platform look; an author who asks for it finds the steps in `$PLUGIN/docs/branding.md`. The accent color (`color`) and the overlay directory `ui/supplemental/` are not part of the intake either; they are later edits described there (FR-021 to FR-023).
6. **Sections and voices**: default sections Overview (`concepts`), one per persona (`technical`), Reference (`reference`). With cc-prose present, offer its voice profiles by name instead of the built-in styles.
7. **Rigor**: `standard` (recommended; per-page reviews), `fast` (final review only, about half the review dispatches), `strict` (adds the claim ledger; slower).
8. **Internal part**: whether the guide has internal pages (default no). When yes: the confidential terms (for example customer names) and patterns (for example the ticket key format `\b[A-Z]{2,}-\d+\b`).
9. **Sources**: confirm the `--source` list or ask for repositories and refs. For every product the guide will name (the subject and each product it builds on), make sure the list includes that product's own repository or documentation URL, so the guide can define it from its own source (FR-043); propose the missing ones. Ask whether any upstream change requests (pull requests) should be documented as experimental content (FR-015): for each, the number and whether it is merged on the default branch (`on-main`) or still open (`in-review`).
10. **Inputs**: confirm the `--input` list or ask for transcripts, tickets, links, and notes. For each input ask whether it is confidential (FR-005).
11. **Cluster connections** (optional): name, kubeconfig path (stored as a reference only), context, disposable (default no).
12. **Scheduled drift check** (FR-025b): offer the weekly GitHub workflow; default no.
13. **Remote repository** (FR-005c): offer to create one, private by default. When yes, ask for the owner/name and visibility, and remember that creating it needs a final confirmation in section 5. Separately, ask once whether to push after each completed task (default no). Without the push opt-in the run only commits locally.

Record the answers in your working notes. Do not write files yet.

### Embedded intake (FR-002, FR-005, FR-006, FR-007)

In embedded mode the intake changes as follows; everything else stays as above.

- **Guide subdirectory**: default `guide`; the author may choose another name. When `HOST/<name>` exists, is not empty, and is not a guide project, ask for another name (never merge into an unrelated directory). `GUIDE` is `HOST/<name>`.
- **Developer README**: default `DEVELOPMENT.md` at the repository root; the author may choose another path. It receives the development material of the old README (section 5a).
- **Format**: fixed to `gfm`; do not ask question 4. When the author asks for Antora or MkDocs, explain: "Embedded guides use GitHub Markdown in this release, because the front page is the README that GitHub renders. A guide in Antora or MkDocs lives in its own repository." Offer to continue with gfm or to stop.
- **Branding**: not asked (gfm).
- **Internal part**: not asked. When the author asks for internal pages, explain: "An embedded guide has no internal part, because everything in the repository is visible to its readers. A guide with internal pages must be a separate repository." Confidential terms and patterns are still asked when inputs are confidential; they go to `confidential.local.yaml` in `GUIDE` (git-ignored), never into `guide.yaml`.
- **Inputs**: a confidential input is registered as `location: local:<id>` in `inputs.yaml`; its real location is written only to the `inputs` map of `confidential.local.yaml`. Committed files, run summaries, and findings never name it.
- **Pull request check** (FR-025): offer "Check every pull request for changes to files the guide cites? (default no)". Explain the `guide-skip` label that maintainers use when a change does not touch documented behavior.
- **Scheduled drift check**: offered as today.
- **Remote repository**: not offered (question 13 is skipped); the guide lives in the host repository. Ask only whether to push after each completed task (default no).

## 5. Project setup

Tell the author what you are about to create, then:

1. **Repository**: `git init -b main "$GUIDE"` when it is not a git repository yet.
2. **Scaffold and toolkit**: `bash "$PLUGIN/scripts/scaffold-project.sh" --format <format> --title "<title>" "$GUIDE"`. It copies the adapter scaffold and installs the toolkit as `tools/guide/` (scripts, `VERSION`, `adapter.yaml`, templates, validate allowlist).
3. **Configuration**: write `guide.yaml` from `$PLUGIN/templates/guide.yaml` with the intake answers (title, format, personas with their entry pages, sections and voices, rigor, internal part, confidential terms and patterns, clusters, `drift.schedule`). Write `guide-rules.yaml` with `rules: []` (page tasks add their rules). Write `styleguide.md` from `$PLUGIN/templates/styleguide.md` with the terms you know so far. For every Antora guide, write the branding answers as the `branding` block of `guide.yaml` (the template has a commented example): exactly one of `logo_text`, `wordmark`, or `logo` (with `logo_alt`), then `theme: neutral`, then `footer: none` unless the author gave a footer text, then `favicon` when given; leave out the other keys. Copy an own logo or favicon file into `GUIDE/branding/` (for example `branding/logo.svg`), point the block at the copy with a path relative to the guide root, and never move or change the original; the copy is committed with the scaffold in step 9, and step 7 validates the block. Make sure `.gitignore` contains `.guide/`, `.superpowers/`, `.opencode/` (OpenCode writes an in-project plugins dir there when cc-guide is installed for OpenCode in the guide project), `node_modules/`, `build/`, and `dist/`.
4. **Tool chain**: run `npm install` in `GUIDE` (every format has a `package.json`: Antora or markserv, plus Playwright and js-yaml for the PDF printer; it installs into `node_modules/`), then `make doctor`. Stop with doctor's hints when a system tool is missing.
5. **Pin the sources** (FR-007): `uv run tools/guide/fetch.py pin --source <id>=<repo>[@<ref>] ...` writes `baseline.yaml` with full commit SHAs. Then `uv run tools/guide/fetch.py fetch`.
   - When a source cannot be fetched (private, unreachable, missing credentials), name it and ask: "Continue without verifying `<id>`? Pages cannot cite it until it is fetched." On yes, run `fetch.py fetch --allow-unverified`, which marks it `status: unverified`; on no, stop.
   - For each change request from the intake, read its head with `gh api repos/<owner>/<name>/pulls/<n> --jq .head.sha` and add it to `baseline.yaml` `change_requests` with `state`, `tier`, and an `anchor` slug for its experimental section (FR-015).
   - Add source `attributes` the author wants on pages (for example a product version), confirmed against the pinned source.
6. **Register the inputs** (FR-005): for each input, refuse a location inside `GUIDE` (raw inputs are never copied or committed) and ask the author to keep it elsewhere; compute `shasum -a 256` for files (leave empty for links you do not fetch); write `inputs.yaml` entries with `id`, `kind`, `location`, `role`, `sha256`, `confidential`, `registered`.
7. **Validate**: `uv run tools/guide/guidecfg.py validate`. Fix and repeat until it passes.
8. **Drift workflow** (when opted in): render `$PLUGIN/templates/guide-drift.yml` to `.github/workflows/guide-drift.yml` as in section 11 (`{{GUIDE_DIR}}` becomes `.`) and set `drift.schedule` in `guide.yaml` to its cron expression (weekly by default). Tell the author that private sources need a repository secret `GUIDE_SOURCES_TOKEN` with read access.
9. **Commit**: `chore: scaffold guide project` with the trailer `Assisted-By: 🤖 Claude Code`.
10. **Remote** (when opted in): show the exact command, for example `gh repo create <owner>/<name> --private --source "$GUIDE" --remote origin`, and run it only after the author confirms name and visibility once more. Push only when the author opted into pushes.

### Embedded setup (FR-002, FR-003, FR-007, FR-011)

In embedded mode, section 5 changes as follows. Until the move plan is approved (section 5a), nothing outside `GUIDE` changes.

1. **Repository**: no `git init`; the host repository holds the guide. No remote is created.
2. **Scaffold**: `bash "$PLUGIN/scripts/scaffold-project.sh" --format gfm --title "<title>" --embedded "$GUIDE"`. It skips `internal/`, installs the pointer page `docs/README.md` (the front page replaces the table of contents), and adds `confidential.local.yaml` to the guide's `.gitignore`.
3. **Configuration**: write `guide.yaml` as above with `format: gfm`, `internal.enabled: false`, empty `confidential_terms` and `confidential_patterns`, and the `embedded` block (the template has a commented example): `front_page: ../README.md`, `developer_readme` only after section 5a moved something, `stubs: []`, `pr_check: on|off` from the intake. Write `confidential.local.yaml` (from `$PLUGIN/templates/confidential.local.yaml`) when there are confidential terms, patterns, or inputs.
4. **Tool chain**: `npm install` and `make doctor` in `GUIDE`, as above.
5. **Pin the sources**: `uv run tools/guide/fetch.py pin --source self=.. --source <id>=<repo>[@<ref>] ...`. `self` is the host repository: the committed HEAD of the current branch, `ref` the default branch, `web` from a GitHub `origin`. It is read in place and exported outside the repository (`uv run tools/guide/fetch.py where self` prints the snapshot); it is never cloned into `.guide/cache/`. Then `uv run tools/guide/fetch.py fetch`.
6. **Inputs**: register them as above (`local:<id>` for confidential ones).
7. **Validate**: `uv run tools/guide/guidecfg.py validate --allow-missing-front-page` (the front page does not exist in its final form yet).
8. **Session files**: when the author approves a session settings file at the host root (for example `.claude/settings.local.json` for an Excalidraw permission), add its path to `HOST/.git/info/exclude` (untracked), never to the host's `.gitignore`.
9. **No commit yet**: the guide subdirectory stays uncommitted until the author approves the move plan, so a declined plan leaves the branch exactly as it was (section 5a commits the scaffold and the consolidation together). The host's own files are untouched.

Workflows (section 5 step 8 and the pull request check) are installed after section 5a, see "Workflows" below.

## 5a. Consolidation (embedded mode only, FR-016 to FR-024)

Consolidation runs only here, never in evolve (FR-032). Nothing outside `GUIDE` changes before the author approves the move plan (FR-018).

1. **Inventory**: `uv run tools/guide/embed.py inventory --format yaml`. It lists the documentation the host has at HEAD (root README in any format, `.github/README*`, `docs/README*`, `CONTRIBUTING*`, `CODE_OF_CONDUCT*`, `SECURITY*`, `SUPPORT*`, `INSTALL*`, `USAGE*`, `CHANGELOG*`, `LICENSE*`, `docs/`, `doc/`, `documentation/`, documentation sites), the headings of README-like files, and the package manifests that publish the README.
2. **Classify** every file, or every section of a file that mixes audiences (use the headings), into one destination:
   - `input`: instructional user-facing material (how to install, configure, and use). It is registered as guide input and verified like any input; only verified facts reach the pages, never copied text. A non-Markdown root README (`README.rst`, `README.adoc`) is `input` plus `remove` or `relocate`, so there is never a second root README; explain that the front page replaces it with a Markdown README.
   - `author-region`: landing-oriented sections of the root Markdown README (pitch, context, usage examples). The default for landing material (specs/006 FR-012): the section stays in place as author-owned text above the guide region, byte-identical, and nothing in it is registered, verified, rewritten, or dropped. The author can change any destination before approval, as today.
   - `developer`: development material (contributing, building from source, running tests, releasing). It moves to the developer README with its text unchanged except heading levels and relative links (FR-021).
   - `keep`: `LICENSE*` (always kept where it is), community health files where GitHub detects them (`CONTRIBUTING`, `CODE_OF_CONDUCT`, `SECURITY`, `SUPPORT` at the root, in `.github/`, or in `docs/`; link them from the developer README instead of merging them), and the changelog.
   - `remove` (always with `stub: true`, except a root or `.github` README): documentation absorbed into the guide (for example `docs/install.md`, `USAGE.md`). Mark it `input` with `stub: true`: it is read as input, then replaced by a stub that keeps old links working (FR-023).
   - An existing documentation site (a generator configuration with its content directory) defaults to `keep`, with its pages as `input` entries; it is removed with stubs only when the author changes that destination (FR-017).
   - `.github/README*`: GitHub shows it in place of the root README, so it is `remove` or `relocate` (never a stub).
   - A host without a README gets a new front page and no developer README unless there is development material elsewhere to move.
3. **Write the move plan** to `.guide/runs/<run-id>/move-plan.yaml` (data-model in the plugin's embedded docs): `self_revision` (the inventory's `self_revision`), `developer_readme` (`../DEVELOPMENT.md` or the intake path), `developer_readme_exists`, `entries` (path relative to the guide root, `section` or null, `destination`, `stub`, `to`), `manifests`, and `absolute_links` (true when a manifest publishes the README, so the front page renders outside GitHub; ask the author).
4. **Show the plan** as a table (path, section, destination, stub, relocation target), then the list of every removal and stub, the flagged manifests, and where the developer sections go (appended under `## Moved from the README` when the developer README exists). Let the author change any destination; update the plan file and show it again.
5. **Approval**: ask "Apply this move plan?" Run `uv run tools/guide/embed.py apply --plan .guide/runs/<run-id>/move-plan.yaml --dry-run` first and show its operations, then run it without `--dry-run`. `apply` refuses a dirty host tree, missing paths, removals of `LICENSE` or non-documentation files, stubs on a root or `.github` README, and unknown sections; fix the plan and ask again.
6. **Decline**: when the author declines, stop. Nothing outside `GUIDE` has changed and nothing was committed. Offer to remove the uncommitted guide subdirectory (`git -C "$HOST" status --porcelain -- <guide dir>` shows what would go); remove it only on yes.
7. **Commit** the guide subdirectory (the scaffold, configuration, and `inputs.yaml`) with the developer README, the stubs, and the relocations and removals: stage exactly those paths (`git -C "$HOST" add -- <guide dir> <paths apply reported>`) and commit `chore: add the embedded guide and consolidate documentation` with the trailer. Without `author-region` entries the old README stays until the front page task replaces it; with them, `apply` already rewrote it (markers below the retained landing text) and the front page task fills the region between the markers.

## 6. Guide spec and plan (FR-008)

### 6a. Research notes

Get the run id with `uv run tools/guide/runs.py run-id --command create` (`<YYYY-MM-DD>-create[-<n>]`) and keep it for the whole run. Read every registered input. Write research notes to `.guide/runs/<run-id>/research.md` (local and git-ignored): the claims each input makes, with the input id, and for each claim the source locations that could confirm or refute it. Never copy raw input text into a committed file. Mark claims from confidential inputs as internal-only.

### 6b. Guide spec

Invoke the superpowers `brainstorming` skill with these instructions added:

> Write the spec to `docs/guide/spec.md` (not `docs/superpowers/specs/`). The subject, audience, personas, sections, voices, rigor, format, and internal part are already decided: <intake summary>. Research notes are in `.guide/runs/<run-id>/research.md`. The spec starts with a `## Why` section, the why card from `$PLUGIN/skills/page-task/overview-contract.md`: all six slots, written for a reader who knows none of the products, each factual sentence with its source, and each product defined from its own pinned source. Purpose describes the reader's outcome, not the guide's method. The start page outline follows the contract's start page shape and carries the card's content; repository layout and implementation detail go to the architecture or reference pages. The spec then describes the guide: purpose, persona journeys, the page list per section with a one-paragraph outline each, the diagrams (name, what it shows, which page uses it), experimental content per change request, what goes into the internal part, and open questions. It never contains confidential terms outside the internal-part section and never quotes inputs.

### 6c. Excalidraw check (FR-003)

When the spec plans diagrams and preflight reported `excalidraw=missing`: warn "Diagrams are planned but the Excalidraw MCP tools are not available in this session. Install the server (`yctimlin/mcp_excalidraw`, see `$PLUGIN/docs/settings.md`) and restart, or continue with placeholder images that name the missing diagrams." Ask whether to continue with placeholders; on yes record a ruling and mark the diagram tasks as placeholder tasks. The Excalidraw permission wiring in the rest of this subsection is Claude Code only (FR-010): when `harness` is not `claude` there is no settings file to check, so if the tools are available use them and if they are absent fall back to placeholders as above, then skip the rest of this subsection. On Claude Code, when the tools are available, check that this session may use them. The allow entry counts only in a file Claude Code reads for this session: `SESSION/.claude/settings.local.json` or `SESSION/.claude/settings.json` (at the git toplevel when `SESSION` is inside a repository), or `~/.claude/settings.json`; the guide project's settings apply only to sessions started in `GUIDE`. When the preflight result is stale or missing, run `bash "$PLUGIN/scripts/deps.sh" --harness claude --dir "$GUIDE" --session-dir "$SESSION"`. When `excalidraw_allowed` is false, or `excalidraw_allowed_in` lists only files in `GUIDE/.claude/` while `SESSION` is another directory, offer to add `mcp__excalidraw` to `SESSION/.claude/settings.local.json` `permissions.allow` (a permission prompt once stalled a diagram task for hours, and an entry in the wrong file let the classifier deny `clear_canvas` and `import_scene` to a subagent). Mention that adding it to `GUIDE/.claude/settings.local.json` as well covers future sessions started in the guide project. Write only what the author agrees to, merge into an existing file, and never drop entries that are already there.

### 6d. Guide plan

Invoke the superpowers `writing-plans` skill with these instructions added:

> Write the plan to `docs/guide/plan.md` (not `docs/superpowers/plans/`). One task per page or diagram, headed `### Task <N>: <page or diagram>` so `task-brief` can extract it. Diagram tasks come before the pages that show them. Each page task lists: the page path, the outline, the section voice, the facts to verify with source hints (`<source-id>:<path>` candidates from the research notes), the content rules to add to `guide-rules.yaml` for the page (require, forbid, require_order), the persona, and whether it is internal. The start page task and each section overview task also say "follows `overview-contract.md`" and give, for every product the page names, the source hint of that product's own definition. Each diagram task lists the diagram name, what it shows, the entities and their palette colors, the page that shows it, and source hints for where each entity runs and what it connects to (the product's own architecture documentation for its parts). Every task's steps follow `page-procedure.md` (pages) or the `guide:diagrams` skill (diagrams); do not restate them. Include this Global Constraints section verbatim: <rendered global constraints>.

Render the Global Constraints from `$PLUGIN/skills/page-task/global-constraints.template.md` with the values from `guide.yaml`, `baseline.yaml`, `inputs.yaml`, and the preflight result (attributes from `uv run tools/guide/attrs.py`, the format rules below, the push opt-in, and `{{EMBEDDED_RULES}}`: empty for a guide in its own repository, the embedded rules in the template's comment for an embedded guide). `{{FORMAT_RULES}}` per format (the page procedure has the full snippets):

| Format | Format rules for the Global Constraints |
|---|---|
| antora | AsciiDoc, one sentence per line; source block as `// Sources:` lines; expectations as `// expect:`; baseline values as `{<name>}` (listings need `subs="attributes+"` and no `${VAR}`); experimental labels through `ROOT:partial$experimental-<tier>.adoc` with the anchor on the section heading; images `image::<name>.svg["<alt>",role=expand]` with quoted alt text; pages under `content/modules/ROOT/pages/`, internal pages under `internal/modules/internal/pages/` |
| mkdocs | Markdown; source block and expectations as HTML comments; baseline values as `{{= attr("<name>") }}`; admonitions `!!! <type>` with a four-space indented body; experimental labels `{{= experimental("<tier>", "<feature>", <n>) }}` under a heading with `{ #<anchor> }`; pages under `docs/`, internal pages under `docs/internal/` |
| gfm | GitHub Markdown; source block and expectations as HTML comments; baseline values as generated regions `<!-- guide:attr <name> -->...<!-- /guide:attr -->` (never inside listings), rewritten by `make site`; GitHub alerts for admonitions; experimental labels as IMPORTANT alerts with the fixed first line after an `<a id>` anchor; diagrams linked to their full-size SVG; pages under `docs/` with the order in `docs/SUMMARY.md`, internal pages under `internal/` |

Commit the spec and the plan (`docs(guide): add guide spec and plan`).

### 6e. Approval gate

Show the author the spec's `## Why` card first, in full, and ask whether a reader who knows none of the products would understand what they get and why; the card is what the start page will say. Then show the page list (per section, with personas and voices), the diagrams, the experimental items, the internal pages, the rigor, and the estimated number of review dispatches. Ask for approval. Nothing is written into the content directories before the author approves. On requested changes, update the spec or plan and ask again.

## 7. Execution (FR-009 to FR-012, FR-021 to FR-024)

Invoke the `guide:page-task` skill's setup (workspace files, pre-seeded rulings), then invoke the superpowers `subagent-driven-development` skill on `docs/guide/plan.md` with these additions:

- The dispatch additions and rigor profile from the page-task skill (`fast`: no per-task reviews; `standard`: per-task reviews; `strict`: reviews plus `make check STRICT=1` and claim identifiers).
- The pre-seeded rulings R1 to R8 recorded first in the ledger.
- Implementer reports list Findings (input claims the sources contradict) and Upstream candidates. For each Finding, log `Task <N>: finding rejected-by-source: <input id> claims <claim> (<source-id>:<path>:<lines> says <what>)`. Collect each Upstream candidate for the wrap-up.
- Before applying a reviewer's factual correction, open the cited pinned source yourself (FR-012). Apply it only when the source supports it; otherwise log it as rejected by source with the location.
- **Diagram tasks**: the implementer follows the `guide:diagrams` skill, including its claims file (FR-044). Before the task counts as complete, you (the controller) run `uv run tools/guide/diagram_check.py check <scene>` and `uv run tools/guide/diagram_check.py claims <scene> --claims <round>/claims.yaml` on the round's files, verify the claims against their sources (diagrams skill step 8), then `uv run tools/guide/diagram_check.py crops <png> --scene <scene> --out .guide/diagrams/<name>/round<N>/crops`, read every tile and finding crop, and write your verdict to `.guide/diagrams/<name>/round<N>/review.md` (FR-023a). At most two automated fix rounds; then hand the diagram to the author on the canvas ("open for manual edit"), wait for "done", and export, check, and review again (FR-023b).
- **Pushes**: when the author opted in, push after each completed task. When a push fails (for example a locked SSH agent), keep committing locally, report the failure once, retry after the next completed task, and keep a list of unpushed commits.
- **Stalls**: when an implementer stalls or ends its turn early, resume it once with "finish"; if it stalls again, re-dispatch the task fresh from the ledger's base commit and record a ruling.

## 8. Final review (FR-013)

Run `make check`, then `uv run tools/guide/check.py --structure` (every persona's entry page exists and every section is in the navigation; for an embedded guide the navigation is the front page, see section 10). Then invoke superpowers `requesting-code-review` for the whole run (base of task 1 to HEAD) with `final-review-addendum.md`, the deferred-minor and parked ledger lines, and the built sites. Apply the fixes in one fix round (re-verify factual corrections against the pinned sources first), run `make check` again, and commit (`docs(guide): final review fixes`). Then walk every deferred minor and parked line in the ledger and confirm each one now has either a fix commit or a recorded ruling; record the missing rulings before the wrap-up (FR-013, FR-014).

## 9. Wrap-up (FR-014, FR-031)

1. **Upstream findings**: for each collected Upstream candidate, add it with `uv run tools/guide/runs.py findings-add --source <id> --kind <kind> --location <path>:<lines> --quote "<text at the pinned commit>" --summary "<one sentence>" --evidence "<what contradicts what>"`. Kinds: `doc-drift`, `stale-reference`, `dead-config`, `missing-doc`, `naming-ux`, `bug`.
2. **Run summary** (an embedded guide adds the dropped claims and keeps `local:` inputs to their ids, see section 10): `uv run tools/guide/runs.py summary --workspace "$WS" --run-id <run-id> --command create --rigor <rigor> --model "<your model name>" --effort <high|xhigh>`. It writes `runs/<run-id>.md`.
3. **Commit** the findings and the run summary (`docs(guide): run summary <run-id>`), and push when opted in.
4. **Canvas**: when diagram tasks backed up the author's canvas, ask whether to restore the author's drawing now or keep the last diagram on the canvas. Restore as in the `guide:diagrams` skill step 2 (`clear_canvas`, check that `elements_count` is 0, `import_scene` from the backup, check the count), and name the backup path either way.
5. **Report to the author**:
   - the guide location, format, page count per persona, diagrams
   - every ruling from the ledger ("Rulings I made"), in order, each with what it costs if wrong (FR-014)
   - findings rejected by source, and the upstream findings collected (suggest `/guide:upstream`)
   - unpushed commits, if any
   - next steps: `/guide:preview`, `/guide:export`, `/guide:validate` (when clusters are configured)

## 10. Embedded guides: additions to sections 6 to 9

- **6b spec**: the front page (`../README.md`, the host README) is the start page and the navigation (FR-008a); its outline follows `$PLUGIN/skills/page-task/front-page-contract.md` and `overview-contract.md`. Old README statements are claims to verify; list the ones the pinned code contradicts under open questions with the contradicting location.
- **6d plan**: the front page task is the first page task, says "follows `front-page-contract.md` and `overview-contract.md`", and names the badges and logo to keep (when the move plan kept landing sections as the author region, they stay in the author text above the markers, and the task fills the region between the markers instead of rewriting the file). The page plan maps every stubbed path from the move plan to the page that covers its content (or to the front page when nothing does). Add to the format rules: "Embedded guide: the front page is `../README.md`; links into the guide use host-relative paths `<guide dir>/docs/...` (absolute `<web>/blob/<ref>/...` links when the move plan set `absolute_links`); `self:` citations never name files inside `<guide dir>/`, the front page, the developer README, or a stub; read the `self` source in the directory printed by `uv run tools/guide/fetch.py where self`."
- **7 execution**: the front page task and its review use the front page contract (page-task dispatch additions). After the last page task, run `uv run tools/guide/embed.py retarget <old path>=<new page> ...` with the plan's map, then `make check`. Both paths are relative to the host repository root, not to the guide root as in the move plan (for example `docs/install.md=guide/docs/admin/install.md`).
- **8 final review**: `make check` and `uv run tools/guide/check.py --structure` cover the front page (ownership comment, persona links, section titles), the stubs (marker and link), and the developer README links. After the last check: `uv run tools/guide/fetch.py rebaseline --to self=HEAD` (fingerprints of every cited host file and the front page blob), then `uv run tools/guide/embed.py front-page-status --record`, and commit `baseline.yaml` (`chore(baseline): record the embedded guide baseline`).
- **9 wrap-up**: the run summary lists dropped claims (old documentation statements the pinned sources contradict) with their source locations; log each in the ledger as `Task <N>: claim dropped: <input id> claims <claim> (<source-id>:<path>:<lines> says <what>)`. Offer upstream findings only for material that stays in place (kept files, the documentation site), never for files consolidation removed or rewrote. Run summaries and findings name `local:` inputs by id only. Mention the `guide-skip` label when the pull request check was installed.

## 11. Workflows

Both workflow templates contain `{{GUIDE_DIR}}`, the working directory of their steps. Render it to `.` for a separate guide (the result equals the previous template) and to the guide subdirectory name for an embedded guide.

- **Scheduled drift check** (when opted in): render `$PLUGIN/templates/guide-drift.yml` to `.github/workflows/guide-drift.yml` at the repository root (the host root in embedded mode; GitHub reads workflows only there).
- **Pull request check** (embedded, when opted in, FR-025 to FR-028): render `$PLUGIN/templates/guide-pr-check.yml` to `HOST/.github/workflows/guide-pr-check.yml` and set `embedded.pr_check: on`. It runs `drift.py --pr` for the `self` source only, with read-only permissions, and passes for pull requests labelled `guide-skip`.
- Before writing either file, check that the target path does not exist; when it does, stop and ask for another file name. Never overwrite a workflow.

## Rules

- Every outward action (creating the remote, pushing, filing anything) is shown in full and runs only after the author's explicit approval.
- Raw inputs never enter the guide project; the input register holds references and checksums only.
- Subagents are dispatched without a model override.
- Commit messages end with the trailer `Assisted-By: 🤖 Claude Code`.
- No em dash or en dash characters in anything you write.
