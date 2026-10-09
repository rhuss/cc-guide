---
name: create
description: Create a source-verified, persona-split guide from source repositories, transcripts, tickets, links, and notes. Interviews the author, scaffolds the guide project with an output adapter (Antora, MkDocs Material, or GitHub Markdown), pins the sources, then drives superpowers brainstorming, writing-plans, and subagent-driven development with per-page reviews against the pinned sources, a final whole-guide review, and a run summary. Resumes an interrupted run. Use for /guide:create.
argument-hint: "[--dir PATH] [--format antora|mkdocs|gfm] [--rigor fast|standard|strict] [--source ID=REPO[@REF]]... [--input PATH]... [--restart] [description]"
allowed-tools: ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Skill", "Agent", "AskUserQuestion", "WebFetch"]
---

# /guide:create

You are the controller of a guide run. You interview the author, set up the guide project, and then orchestrate superpowers to write the guide page by page, each page verified against pinned sources. You never write pages yourself except for small source-verified fixes (ruling R7 of the page-task skill); subagents do.

Paths used below:
- `PLUGIN`: the plugin root, two directories above this skill's base directory.
- `GUIDE`: the guide project directory (absolute).
- `SP`: superpowers `installPath` from the preflight probe.
- `WS`: the superpowers plan workspace for `docs/guide/plan.md`.
- `SESSION`: the directory this Claude Code session was started in (as in the preflight skill). Claude Code reads the session's permissions from there and from `~/.claude/settings.json`.

Run every command from `GUIDE` or with `-C`/`--root`. Never `cd` into `GUIDE/.guide/cache/`.

## Arguments

| Argument | Meaning |
|---|---|
| `--dir PATH` | Target directory; default the current directory |
| `--format antora\|mkdocs\|gfm` | Output adapter; asked in the intake when missing |
| `--rigor fast\|standard\|strict` | Default `standard` |
| `--source ID=REPO[@REF]` | Repeatable; a source to pin (`REPO` is a URL, a local path, or `owner/name`) |
| `--input PATH_OR_URL` | Repeatable; an input to register (never copied) |
| `--restart` | Start a new run even when an unfinished one exists (asks for confirmation) |
| free text | What the guide is about and who reads it |

## 1. Preflight

The `/guide:create` command runs the `guide:preflight` skill first. When its result line is not in this conversation (the skill was invoked directly), invoke `guide:preflight` with `create` and `--dir` now. Stop when it stops. Keep its result (`prose`, `excalidraw`, `excalidraw_allowed`, `excalidraw_allowed_in`, the superpowers installPath and version).

## 2. Resume or new run (FR-013a)

When `GUIDE/guide.yaml` exists:
- When `GUIDE/docs/guide/plan.md` exists, resolve `WS` with `bash "$SP/skills/subagent-driven-development/scripts/sdd-workspace" docs/guide/plan.md` (from `GUIDE`), and run `uv run tools/guide/runs.py resume --workspace "$WS"`.
  - A task number: an unfinished run exists. Without `--restart`, tell the author "Resuming the guide run at task N (tasks 1 to N-1 are complete in the ledger)." and continue at section 7 (Execution) with the existing plan, workspace, and ledger. Trust the commits the ledger names over anything you remember.
  - `done` with no run summary for this plan in `runs/`: continue at section 8 (Final review).
  - `done` with a run summary: the guide exists; suggest `/guide:evolve`, `/guide:preview`, or `/guide:export`, and stop.
- When there is no plan yet, the previous run stopped during setup or spec work: show what exists and continue at the first missing step (guide spec, plan).
- With `--restart`: ask "Start a new run? The existing plan and ledger stay in git history and in the workspace, but the new run will not resume them." Only on yes, move `docs/guide/plan.md` aside (`git mv` to `docs/guide/plan-<date>.md`) and continue at section 5.

## 3. Target directory (FR-005b)

- No `--dir`: the current directory, which must be empty (ignoring `.DS_Store`).
- `--dir PATH`: create it when it does not exist; when it exists it must be empty.
- A non-empty directory that is not a guide project: stop with "`<dir>` is not empty and is not a guide project. Choose an empty directory or a new path with --dir." Write nothing.

## 4. Intake interview (FR-006, FR-005c)

Ask with AskUserQuestion, at most four questions per call, recommended option first. Use the free-text description and the arguments to pre-fill answers, and skip questions they already answer. Collect:

1. **Subject and audience**: one paragraph you will reuse in the guide spec.
2. **Personas**: default `admin` (Administrator) and `user` (User); allow more or fewer.
3. **Scope**: what is in and out (for example installation, day 2, user onboarding; not upstream development).
4. **Output format** (when no `--format`): `antora` (AsciiDoc, Antora site with the RHDP UI, best for large guides), `mkdocs` (Markdown, MkDocs Material), `gfm` (Markdown rendered on GitHub, no build). Recommend antora for guides with more than about 15 pages, gfm for small guides that live next to code.
5. **Branding** (Antora only; do not ask for `mkdocs` or `gfm`, whose adapters support no branding keys): the stock RHDP look (the default) or own branding. For own branding collect:
   - **Logo**: either `logo_text`, a short product name (one line, 1 to 40 characters) shown on the Red Hat logo layout (the Red Hat hat, a divider, and the text), or an own SVG logo file. Tell the author that `logo_text` renders the Red Hat logo and is meant for guides about Red Hat products; a guide about another product uses an own logo file (FR-030).
   - **Alt text**: required for an own logo file, because only the author knows what it shows; optional with `logo_text` (default "Red Hat <logo_text>").
   - **Footer**: `none` (an empty footer, the default with own branding), a text with an optional `http` or `https` link, or `rhdp` (the stock Red Hat Demo Platform footer).
   - **Favicon** (optional): an `.ico`, `.png`, or `.svg` file for the browser tab.
   The accent color (`color`) and the overlay directory `ui/supplemental/` are not part of the intake; they are later edits to the guide project, described in `$PLUGIN/docs/branding.md`.
6. **Sections and voices**: default sections Overview (`concepts`), one per persona (`technical`), Reference (`reference`). With cc-prose present, offer its voice profiles by name instead of the built-in styles.
7. **Rigor**: `standard` (recommended; per-page reviews), `fast` (final review only, about half the review dispatches), `strict` (adds the claim ledger; slower).
8. **Internal part**: whether the guide has internal pages (default no). When yes: the confidential terms (for example customer names) and patterns (for example the ticket key format `\b[A-Z]{2,}-\d+\b`).
9. **Sources**: confirm the `--source` list or ask for repositories and refs. Ask whether any upstream change requests (pull requests) should be documented as experimental content (FR-015): for each, the number and whether it is merged on the default branch (`on-main`) or still open (`in-review`).
10. **Inputs**: confirm the `--input` list or ask for transcripts, tickets, links, and notes. For each input ask whether it is confidential (FR-005).
11. **Cluster connections** (optional): name, kubeconfig path (stored as a reference only), context, disposable (default no).
12. **Scheduled drift check** (FR-025b): offer the weekly GitHub workflow; default no.
13. **Remote repository** (FR-005c): offer to create one, private by default. When yes, ask for the owner/name and visibility, and remember that creating it needs a final confirmation in section 5. Separately, ask once whether to push after each completed task (default no). Without the push opt-in the run only commits locally.

Record the answers in your working notes. Do not write files yet.

## 5. Project setup

Tell the author what you are about to create, then:

1. **Repository**: `git init -b main "$GUIDE"` when it is not a git repository yet.
2. **Scaffold and toolkit**: `bash "$PLUGIN/scripts/scaffold-project.sh" --format <format> --title "<title>" "$GUIDE"`. It copies the adapter scaffold and installs the toolkit as `tools/guide/` (scripts, `VERSION`, `adapter.yaml`, templates, validate allowlist).
3. **Configuration**: write `guide.yaml` from `$PLUGIN/templates/guide.yaml` with the intake answers (title, format, personas with their entry pages, sections and voices, rigor, internal part, confidential terms and patterns, clusters, `drift.schedule`). Write `guide-rules.yaml` with `rules: []` (page tasks add their rules). Write `styleguide.md` from `$PLUGIN/templates/styleguide.md` with the terms you know so far. With own branding (Antora), write the answers as the `branding` block of `guide.yaml` (the template has a commented example) and leave out the keys the author did not set. Copy an own logo or favicon file into `GUIDE/branding/` (for example `branding/logo.svg`), point the block at the copy with a path relative to the guide root, and never move or change the original; the copy is committed with the scaffold in step 9, and step 7 validates the block. Make sure `.gitignore` contains `.guide/`, `.superpowers/`, `node_modules/`, `build/`, and `dist/`.
4. **Tool chain**: run `npm install` in `GUIDE` (every format has a `package.json`: Antora or markserv, plus Playwright and js-yaml for the PDF printer; it installs into `node_modules/`), then `make doctor`. Stop with doctor's hints when a system tool is missing.
5. **Pin the sources** (FR-007): `uv run tools/guide/fetch.py pin --source <id>=<repo>[@<ref>] ...` writes `baseline.yaml` with full commit SHAs. Then `uv run tools/guide/fetch.py fetch`.
   - When a source cannot be fetched (private, unreachable, missing credentials), name it and ask: "Continue without verifying `<id>`? Pages cannot cite it until it is fetched." On yes, run `fetch.py fetch --allow-unverified`, which marks it `status: unverified`; on no, stop.
   - For each change request from the intake, read its head with `gh api repos/<owner>/<name>/pulls/<n> --jq .head.sha` and add it to `baseline.yaml` `change_requests` with `state`, `tier`, and an `anchor` slug for its experimental section (FR-015).
   - Add source `attributes` the author wants on pages (for example a product version), confirmed against the pinned source.
6. **Register the inputs** (FR-005): for each input, refuse a location inside `GUIDE` (raw inputs are never copied or committed) and ask the author to keep it elsewhere; compute `shasum -a 256` for files (leave empty for links you do not fetch); write `inputs.yaml` entries with `id`, `kind`, `location`, `role`, `sha256`, `confidential`, `registered`.
7. **Validate**: `uv run tools/guide/guidecfg.py validate`. Fix and repeat until it passes.
8. **Drift workflow** (when opted in): copy `$PLUGIN/templates/guide-drift.yml` to `.github/workflows/guide-drift.yml` and set `drift.schedule` in `guide.yaml` to its cron expression (weekly by default). Tell the author that private sources need a repository secret `GUIDE_SOURCES_TOKEN` with read access.
9. **Commit**: `chore: scaffold guide project` with the trailer `Assisted-By: 🤖 Claude Code`.
10. **Remote** (when opted in): show the exact command, for example `gh repo create <owner>/<name> --private --source "$GUIDE" --remote origin`, and run it only after the author confirms name and visibility once more. Push only when the author opted into pushes.

## 6. Guide spec and plan (FR-008)

### 6a. Research notes

Get the run id with `uv run tools/guide/runs.py run-id --command create` (`<YYYY-MM-DD>-create[-<n>]`) and keep it for the whole run. Read every registered input. Write research notes to `.guide/runs/<run-id>/research.md` (local and git-ignored): the claims each input makes, with the input id, and for each claim the source locations that could confirm or refute it. Never copy raw input text into a committed file. Mark claims from confidential inputs as internal-only.

### 6b. Guide spec

Invoke the superpowers `brainstorming` skill with these instructions added:

> Write the spec to `docs/guide/spec.md` (not `docs/superpowers/specs/`). The subject, audience, personas, sections, voices, rigor, format, and internal part are already decided: <intake summary>. Research notes are in `.guide/runs/<run-id>/research.md`. The spec describes the guide: purpose, persona journeys, the page list per section with a one-paragraph outline each, the diagrams (name, what it shows, which page uses it), experimental content per change request, what goes into the internal part, and open questions. It never contains confidential terms outside the internal-part section and never quotes inputs.

### 6c. Excalidraw check (FR-003)

When the spec plans diagrams and preflight reported `excalidraw=missing`: warn "Diagrams are planned but the Excalidraw MCP tools are not available in this session. Install the server (`yctimlin/mcp_excalidraw`, see `$PLUGIN/docs/settings.md`) and restart, or continue with placeholder images that name the missing diagrams." Ask whether to continue with placeholders; on yes record a ruling and mark the diagram tasks as placeholder tasks. When the tools are available, check that this session may use them. The allow entry counts only in a file Claude Code reads for this session: `SESSION/.claude/settings.local.json` or `SESSION/.claude/settings.json` (at the git toplevel when `SESSION` is inside a repository), or `~/.claude/settings.json`; the guide project's settings apply only to sessions started in `GUIDE`. When the preflight result is stale or missing, run `bash "$PLUGIN/scripts/deps.sh" --dir "$GUIDE" --session-dir "$SESSION"`. When `excalidraw_allowed` is false, or `excalidraw_allowed_in` lists only files in `GUIDE/.claude/` while `SESSION` is another directory, offer to add `mcp__excalidraw` to `SESSION/.claude/settings.local.json` `permissions.allow` (a permission prompt once stalled a diagram task for hours, and an entry in the wrong file let the classifier deny `clear_canvas` and `import_scene` to a subagent). Mention that adding it to `GUIDE/.claude/settings.local.json` as well covers future sessions started in the guide project. Write only what the author agrees to, merge into an existing file, and never drop entries that are already there.

### 6d. Guide plan

Invoke the superpowers `writing-plans` skill with these instructions added:

> Write the plan to `docs/guide/plan.md` (not `docs/superpowers/plans/`). One task per page or diagram, headed `### Task <N>: <page or diagram>` so `task-brief` can extract it. Diagram tasks come before the pages that show them. Each page task lists: the page path, the outline, the section voice, the facts to verify with source hints (`<source-id>:<path>` candidates from the research notes), the content rules to add to `guide-rules.yaml` for the page (require, forbid, require_order), the persona, and whether it is internal. Each diagram task lists the diagram name, what it shows, the entities and their palette colors, and the page that shows it. Every task's steps follow `page-procedure.md` (pages) or the `guide:diagrams` skill (diagrams); do not restate them. Include this Global Constraints section verbatim: <rendered global constraints>.

Render the Global Constraints from `$PLUGIN/skills/page-task/global-constraints.template.md` with the values from `guide.yaml`, `baseline.yaml`, `inputs.yaml`, and the preflight result (attributes from `uv run tools/guide/attrs.py`, the format rules below, the push opt-in). `{{FORMAT_RULES}}` per format (the page procedure has the full snippets):

| Format | Format rules for the Global Constraints |
|---|---|
| antora | AsciiDoc, one sentence per line; source block as `// Sources:` lines; expectations as `// expect:`; baseline values as `{<name>}` (listings need `subs="attributes+"` and no `${VAR}`); experimental labels through `ROOT:partial$experimental-<tier>.adoc` with the anchor on the section heading; images `image::<name>.svg["<alt>",role=expand]` with quoted alt text; pages under `content/modules/ROOT/pages/`, internal pages under `internal/modules/internal/pages/` |
| mkdocs | Markdown; source block and expectations as HTML comments; baseline values as `{{= attr("<name>") }}`; admonitions `!!! <type>` with a four-space indented body; experimental labels `{{= experimental("<tier>", "<feature>", <n>) }}` under a heading with `{ #<anchor> }`; pages under `docs/`, internal pages under `docs/internal/` |
| gfm | GitHub Markdown; source block and expectations as HTML comments; baseline values as generated regions `<!-- guide:attr <name> -->...<!-- /guide:attr -->` (never inside listings), rewritten by `make site`; GitHub alerts for admonitions; experimental labels as IMPORTANT alerts with the fixed first line after an `<a id>` anchor; diagrams linked to their full-size SVG; pages under `docs/` with the order in `docs/SUMMARY.md`, internal pages under `internal/` |

Commit the spec and the plan (`docs(guide): add guide spec and plan`).

### 6e. Approval gate

Show the author the page list (per section, with personas and voices), the diagrams, the experimental items, the internal pages, the rigor, and the estimated number of review dispatches. Ask for approval. Nothing is written into the content directories before the author approves. On requested changes, update the spec or plan and ask again.

## 7. Execution (FR-009 to FR-012, FR-021 to FR-024)

Invoke the `guide:page-task` skill's setup (workspace files, pre-seeded rulings), then invoke the superpowers `subagent-driven-development` skill on `docs/guide/plan.md` with these additions:

- The dispatch additions and rigor profile from the page-task skill (`fast`: no per-task reviews; `standard`: per-task reviews; `strict`: reviews plus `make check STRICT=1` and claim identifiers).
- The pre-seeded rulings R1 to R8 recorded first in the ledger.
- Implementer reports list Findings (input claims the sources contradict) and Upstream candidates. For each Finding, log `Task <N>: finding rejected-by-source: <input id> claims <claim> (<source-id>:<path>:<lines> says <what>)`. Collect each Upstream candidate for the wrap-up.
- Before applying a reviewer's factual correction, open the cited pinned source yourself (FR-012). Apply it only when the source supports it; otherwise log it as rejected by source with the location.
- **Diagram tasks**: the implementer follows the `guide:diagrams` skill. Before the task counts as complete, you (the controller) run `uv run tools/guide/diagram_check.py check <scene>` on the round's scene, then `uv run tools/guide/diagram_check.py crops <png> --scene <scene> --out .guide/diagrams/<name>/round<N>/crops`, read every tile and finding crop, and write your verdict to `.guide/diagrams/<name>/round<N>/review.md` (FR-023a). At most two automated fix rounds; then hand the diagram to the author on the canvas ("open for manual edit"), wait for "done", and export, check, and review again (FR-023b).
- **Pushes**: when the author opted in, push after each completed task. When a push fails (for example a locked SSH agent), keep committing locally, report the failure once, retry after the next completed task, and keep a list of unpushed commits.
- **Stalls**: when an implementer stalls or ends its turn early, resume it once with "finish"; if it stalls again, re-dispatch the task fresh from the ledger's base commit and record a ruling.

## 8. Final review (FR-013)

Run `make check`, then `uv run tools/guide/check.py --structure` (every persona's entry page exists and every section is in the navigation). Then invoke superpowers `requesting-code-review` for the whole run (base of task 1 to HEAD) with `final-review-addendum.md`, the deferred-minor and parked ledger lines, and the built sites. Apply the fixes in one fix round (re-verify factual corrections against the pinned sources first), run `make check` again, and commit (`docs(guide): final review fixes`). Then walk every deferred minor and parked line in the ledger and confirm each one now has either a fix commit or a recorded ruling; record the missing rulings before the wrap-up (FR-013, FR-014).

## 9. Wrap-up (FR-014, FR-031)

1. **Upstream findings**: for each collected Upstream candidate, add it with `uv run tools/guide/runs.py findings-add --source <id> --kind <kind> --location <path>:<lines> --quote "<text at the pinned commit>" --summary "<one sentence>" --evidence "<what contradicts what>"`. Kinds: `doc-drift`, `stale-reference`, `dead-config`, `missing-doc`, `naming-ux`, `bug`.
2. **Run summary**: `uv run tools/guide/runs.py summary --workspace "$WS" --run-id <run-id> --command create --rigor <rigor> --model "<your model name>" --effort <high|xhigh>`. It writes `runs/<run-id>.md`.
3. **Commit** the findings and the run summary (`docs(guide): run summary <run-id>`), and push when opted in.
4. **Canvas**: when diagram tasks backed up the author's canvas, ask whether to restore the author's drawing now or keep the last diagram on the canvas. Restore as in the `guide:diagrams` skill step 2 (`clear_canvas`, check that `elements_count` is 0, `import_scene` from the backup, check the count), and name the backup path either way.
5. **Report to the author**:
   - the guide location, format, page count per persona, diagrams
   - every ruling from the ledger ("Rulings I made"), in order, each with what it costs if wrong (FR-014)
   - findings rejected by source, and the upstream findings collected (suggest `/guide:upstream`)
   - unpushed commits, if any
   - next steps: `/guide:preview`, `/guide:export`, `/guide:validate` (when clusters are configured)

## Rules

- Every outward action (creating the remote, pushing, filing anything) is shown in full and runs only after the author's explicit approval.
- Raw inputs never enter the guide project; the input register holds references and checksums only.
- Subagents are dispatched without a model override.
- Commit messages end with the trailer `Assisted-By: 🤖 Claude Code`.
- No em dash or en dash characters in anything you write.
