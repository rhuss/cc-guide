---
name: evolve
description: Evolve a source-verified guide after its sources changed (a guide in its own repository, or a guide embedded in the repository it documents, whose README is the front page). Reports drift against the recorded baseline (check-only mode needs no AI and no superpowers), re-evaluates documented change requests, registers new inputs, updates only the affected pages through superpowers with the same per-page reviews as create, and writes the new baseline last, after the checks pass. Also adopts guides that were not created by cc-guide. Use for /guide:evolve.
argument-hint: "[--check] [--adopt] [--to ID=REF]... [--input PATH]... [--rigor fast|standard|strict] [--dir PATH]"
allowed-tools: ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Skill", "Agent", "AskUserQuestion"]
---

# /guide:evolve

Paths and conventions are those of the create skill (`PLUGIN`, `GUIDE`, `WS`). `WS` is resolved with the vendored helper `bash tools/guide/sdd/sdd-workspace <plan>` (the evolve plan is `docs/guide/plans/<run-id>.md`); never read or run scripts from another plugin's install directory (FR-006). Run every command from `GUIDE` or with `--root`; never `cd` into `.guide/cache/`.

## Arguments

| Argument | Meaning |
|---|---|
| `--check` | Report drift only (FR-025a); change nothing; no superpowers needed |
| `--adopt` | Adopt a guide without a cc-guide baseline or source blocks (FR-028) |
| `--to ID=REF` | Repeatable; target revision per source (default: each source's tracked branch head) |
| `--input PATH_OR_URL` | Repeatable; new inputs to register |
| `--rigor fast\|standard\|strict` | Default from `guide.yaml` |
| `--dir PATH` | Guide project; default the current directory (from the root of a repository with an embedded guide, the guide subdirectory is found automatically) |

## 1. Preflight

The `/guide:evolve` command runs `guide:preflight` first. When its result line is not already in this conversation (the skill was invoked directly, as it is on harnesses with no command layer), invoke `guide:preflight` with `evolve` (and `--check` when given, with `--dir`) now. Stop when it stops. superpowers is required only without `--check`.

## 2. Check-only mode (`--check`)

Preflight resolved `GUIDE` with `guidecfg.py discover`, so `--check` works from the root of a repository with an embedded guide. Run `make drift` (it runs `uv run tools/guide/drift.py --check`). Show the report and interpret the exit status: 0 no drift, 10 drift found (list the affected pages and suggest `/guide:evolve`), anything else an error (show it). Change nothing, commit nothing, and stop here. The scheduled workflow (`.github/workflows/guide-drift.yml`) runs the same check without Claude Code.

## 3. Adoption (`--adopt`, FR-028)

For a guide that has no cc-guide `baseline.yaml` or no source blocks. Regular evolve refuses such a guide and points here.

1. Ask for the format (antora, mkdocs, gfm) and confirm the content and internal directories match the adapter layout (`$PLUGIN/adapters/<format>/adapter.yaml`); stop and explain when they do not.
2. Install the toolkit only: `bash "$PLUGIN/scripts/scaffold-project.sh" --format <format> --toolkit-only "$GUIDE"`. Never overwrite the guide's existing build files. When its `Makefile` lacks targets from the adapter contract (`check`, `drift`, `fetch-baseline`, `doctor`), show the targets from `$PLUGIN/adapters/<format>/scaffold/Makefile` you would add and add them only after the author approves.
3. Migrate the baseline: when a foreign `baseline.yaml` exists, write a mapping file starting from `$PLUGIN/templates/adopt-map.example.yaml` (it maps the SAW schema), show it to the author, and run `uv run tools/guide/adopt.py migrate --map <file>`. It keeps the original as `baseline.foreign.yaml`. Without a baseline, pin the sources with `fetch.py pin` as in create. Then `uv run tools/guide/fetch.py fetch`.
4. Write `guide.yaml` and `inputs.yaml` through the intake subset of the create skill (title, format, personas, sections and voices, rigor, internal part and confidential terms, inputs with the confidential question). Validate with `guidecfg.py validate`.
5. `uv run tools/guide/adopt.py report` lists the pages without source blocks. Plan one task per page ("add the source block and verify every statement against the pinned sources"), get the author's approval, and execute it with the page-task setup and superpowers `subagent-driven-development` exactly as in create sections 6d to 8 (same reviews, same rulings).
6. Run `make check`, commit the first cc-guide baseline (`chore(baseline): adopt guide into cc-guide`), and write the run summary with `--command adopt`. Regular evolve runs only after adoption completed.

## 4. Drift and impact (FR-025 to FR-027, FR-005a)

0. **Adoption gate (FR-028)**: run `uv run tools/guide/guidecfg.py validate` and `uv run tools/guide/adopt.py report`. When the guide has no valid cc-guide baseline, or pages lack source blocks, stop and offer `/guide:evolve --adopt`; the regular evolve runs only on an adopted guide.
1. **Toolkit version**: compare `tools/guide/VERSION` with `$PLUGIN/toolkit/VERSION`. When the plugin's is newer, offer `bash "$PLUGIN/scripts/scaffold-project.sh" --format <format> --toolkit-only "$GUIDE"` and commit it separately (`chore: update guide toolkit to <version>`). From toolkit 0.2.0 on, an Antora guide can carry its own branding: a `branding` block in `guide.yaml` (logo text or own logo, alt text, footer, favicon, accent color) and the overlay directory `ui/supplemental/`, with no change to the Makefile or the playbooks (see `$PLUGIN/docs/branding.md`). Mention this when the author asks about the guide's look. A `branding` block added before the refresh fails validation with `guide.yaml:branding: unknown key`; the refresh resolves it. Toolkit 0.3.0 adds the claims gate (`diagram_check.py claims`, FR-044); after the refresh, diagrams without a `diagrams/<name>.claims.yaml` get one in their next task. Toolkit 0.4.0 adds the neutral theme for Antora guides: `theme: neutral` (vendored Red Hat fonts, a red rule under the header, no Google Fonts request) and `wordmark` (a text logo without the Red Hat hat). When a refresh moves an Antora guide from below 0.4.0 to 0.4.0 or later, name both keys in the summary and point to `$PLUGIN/docs/branding.md`; never edit the guide's `branding` block yourself, the author decides (specs/003-neutral-branding FR-025).
2. **Drift report**: `uv run tools/guide/drift.py --check --format json` (exit 10 means drift). Show the Markdown form to the author. An embedded guide's `self` source is reported in fingerprint mode and never as `pin-missing` (section 8); before planning, also run the front page check of section 8 (hand edits). Sources reported `unchecked` cannot be verified: name them and ask whether to continue without updating them. A `pin-missing` source needs a new pin before anything else: ask for the revision and use it as that source's target.
3. **Targets**: `--to` values, or each source's tracked branch head from the report. Resolve each to a full SHA.
4. **Change requests (FR-027)**: for every recorded change request, decide with the author from the report:
   - merged, and the target revision contains the merge: the feature is now part of the baseline; remove its experimental label and describe it as current
   - merged, target does not contain it yet: move it to tier `on-main`
   - still open with a new head: re-verify the experimental content at the new head and record the head
   - closed without merge: remove or rework the content and record a ruling
5. **Inputs**: register `--input` entries as in create (location outside the project, checksum, confidential question). Report inputs whose checksum changed or that are unreadable; ask whether their new content should be considered.
6. **Impact set (FR-026, FR-040, FR-044)**: the affected pages from the report (pages citing changed files plus pages linking to them), plus the diagrams whose claims file (`diagrams/<name>.claims.yaml`) cites a changed file and the pages that show them, plus pages touched by change-request decisions, plus new material from new or changed inputs, plus the pages with mismatches listed under "Review findings" in the latest `.guide/runs/*-validate*/validation.md` (each such page task must address its mismatches: fix the command or the expectation after re-verifying against the source, or record why the guide stands). Every renamed or deleted cited file must be resolved in its page task (update the reference or remove the statement), never silently dropped (spec User Story 2, scenario 3).
7. **Why card (FR-043)**: when `docs/guide/spec.md` has no `## Why` section (a guide created before the card existed, or an adopted guide), write the card as in create section 6b from `$PLUGIN/skills/page-task/overview-contract.md`, show it to the author, and add it to the spec only after approval. Then add the start page and the section overview pages to the impact set. Do the same for an existing card when a changed source alters what a product on the card is or does.
8. **Target checkouts**: for each source with a new target, add a second worktree at the target from the guide root, `git -C .guide/cache/<id>.git worktree add --detach "$GUIDE/.guide/cache/<id>-next" <target-sha>`. Page tasks verify facts there; `baseline.yaml` still pins the old commits until step 6. The `self` source of an embedded guide has no worktree: its target is the committed HEAD of the current branch, exported with `uv run tools/guide/fetch.py where self --commit <sha>` (section 8).

## 5. Plan and execution

1. Get the run id with `uv run tools/guide/runs.py run-id --command evolve`.
2. Invoke superpowers `writing-plans` with the plan location `docs/guide/plans/<run-id>.md`, limited to the impact set: one task per affected page (and per diagram whose content changed), each listing the changed source files with old and new locations, the change-request decisions that apply, and the facts to re-verify. Add to every page task: "Verify facts against `.guide/cache/<id>-next/` (the target revision), not `.guide/cache/<id>/` (for an embedded guide's `self`: the directory printed by `uv run tools/guide/fetch.py where self --commit <target-sha>`); source block line ranges refer to the target revision." Include the Global Constraints rendered as in create, with the target commits as the baseline being verified.
3. Show the plan and the impact set; continue only after the author approves. Pages outside the impact set are not modified (SC-004).
4. Execute with the `guide:page-task` setup and superpowers `subagent-driven-development`, with the same dispatch additions, rigor profile, pre-seeded rulings, diagram rules, push handling, and stall handling as create section 7.
5. Final review as in create section 8, limited to the changed pages and their persona journeys.

## 6. New baseline, last (FR-029)

1. `uv run tools/guide/fetch.py rebaseline --to <id>=<target-sha> ...`. It writes the new commits, `captured: today`, and the change-request states, and moves `.guide/cache/<id>/` to the target.
2. Update `baseline.yaml` `change_requests` for the decisions of section 4 (tiers, heads, removed entries).
3. `make check`, then `uv run tools/guide/check.py --structure` (for an embedded guide, then `uv run tools/guide/embed.py front-page-status --record` after the last check). When either fails, fix the pages (a fix dispatch or a source-verified controller fix) and run it again. Never commit a baseline whose checks fail; when the run has to stop, restore the old baseline with `git checkout baseline.yaml` and say so.
4. Commit the baseline alone: `chore(baseline): rebaseline <id> to <short-sha>, ...`. The previous baseline stays in git history.
5. Remove the target worktrees: `git -C .guide/cache/<id>.git worktree remove --force "$GUIDE/.guide/cache/<id>-next"` (there is none for `self`).

## 7. Wrap-up

1. Upstream findings found during the run go through `uv run tools/guide/runs.py findings-add` as in create (FR-031).
2. `uv run tools/guide/runs.py summary --workspace "$WS" --run-id <run-id> --command evolve --rigor <rigor> --model "<model>" --effort <high|xhigh> --baseline-before "<old pins>" --baseline-after "<new pins>"`.
3. When diagram tasks backed up the author's canvas, offer the restore as in create section 9 (Canvas).
4. Commit, push when opted in, and report: pages changed (and that no other page changed), change-request decisions, rulings with their cost if wrong, findings, and next steps.

## 8. Embedded guides (specs/005-embedded-guide)

An embedded guide lives in a subdirectory of the repository it documents; the host README is its front page and the host repository is the source `self`. Everything above applies, with these additions:

- **Resolve the guide** with `uv run "$PLUGIN/toolkit/guidecfg.py" discover --dir <dir>` (preflight does this): from the host root it finds the one embedded guide subdirectory. Several: ask which. None: stop and ask for the guide directory.
- **Reading sources**: read every source in the directory printed by `uv run tools/guide/fetch.py where <id>`; for `self` it is a snapshot of the host at the pinned commit, outside the repository. Never read the host's working tree as a source.
- **Drift for `self`** uses fingerprints (`mode: fingerprint` in the report): only cited host files count, so commits that change only guide files are never drift, and squash merges never cause a `pin-missing`. `self:` inputs are reported as `recorded` (read at a revision; never changed or unreadable).
- **Hand edits** (FR-009a): before planning, run `uv run tools/guide/embed.py front-page-status`. Exit 10 (`edited`) prints a diff of the front page against the blob recorded at the last baseline: show it to the author as hand edits and ask whether to keep them (they become part of the front page task's input and are verified like any statement) or replace them. Never overwrite them silently.
- **Impact set**: add the front page when the report lists `../README.md`, and every stub or front page link whose target page is renamed or removed in this run.
- **Target revision for `self`**: the committed HEAD of the current branch. Export it with `uv run tools/guide/fetch.py where self --commit <sha>` and tell page tasks to verify facts in that directory (there is no `-next` worktree for `self` under `.guide/cache/`).
- **Outside the guide subdirectory**, evolve changes only the front page and, when a page that a stub or the front page links to is renamed or removed, the link targets in those stubs (`uv run tools/guide/embed.py retarget <old>=<new> ...`, both paths relative to the host repository root, for example `guide/docs/admin/setup.md=guide/docs/admin/install.md`). It never creates, moves, or removes host files, and it never repeats the consolidation (FR-032).
- **New baseline**: `uv run tools/guide/fetch.py rebaseline --to self=<sha> ...` recomputes the fingerprints and stores the front page blob. After the final `make check`, run `uv run tools/guide/embed.py front-page-status --record`, then commit `baseline.yaml`.

## Resume

Rerunning `/guide:evolve` while a ledger for `docs/guide/plans/<run-id>.md` has an unfinished task resumes at that task, exactly as in create section 2 (`runs.py resume --workspace <WS>`). A run whose tasks are complete but whose baseline is not yet written continues at section 6.

## Rules

As in create: approval before outward actions, raw inputs never enter the project, no model override for subagents, the commit trailer, no em or en dash characters.
