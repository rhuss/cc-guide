# Learnings

These lessons come from building the first source-verified guide with this method: a persona-split guide for the Secure Agent Workspace (SAW) validated pattern, written from walkthrough transcripts, a ticket board, and two source repositories. Most of them shaped a requirement in `specs/001-cc-guide-plugin/spec.md`; the reference after each lesson names it.

## Process and reviews

- **Per-task reviews are the most valuable gate.** A fresh reviewer checked at least 12 statements per page against the pinned sources and found a factual error in nearly every page. The catches included swapped Route purposes, a configuration key that does not exist, two RBAC tiers collapsed into one, and citations pointing at the wrong file. Keep them in the default profile. (FR-011)
- **Reviewers can be wrong too.** The final review once proposed changing a namespace to `openshift-gitops`; the project's own scripts and charts all use `vp-gitops`. Before applying a finding that changes a fact, the controller checks the pinned source itself. (FR-012)
- **Re-verify upstream findings on the current default branch, and test behavior claims.** Two of four issue candidates did not hold: one version cap was intentional and documented in a comment, and GNU make does pass command-line variables to recipes, which a 10-line Makefile proved. (FR-032)
- **The per-claim ledger was overkill for most runs.** A per-page block of sources keeps most of the value at a fraction of the cost. The claim ledger stays available as the strict profile. (FR-010, FR-021)
- **A prose check ends a subagent's turn.** Resume it with a short "finish" message, and skip the check on table-heavy reference pages and in the final consistency pass. (FR-003a)
- **Record decisions instead of stalling.** A run that hits an ambiguity decides, writes the decision down with what it costs if wrong, and continues; the list goes to the author at the end. (FR-014)
- **The ledger is the recovery map.** After a context compaction, the progress ledger and the commits it names are the truth, not the session's memory. (FR-013a)
- **Transcript quotes are verbatim or not quotes at all.** One cleaned-up quote had to be turned into a paraphrase. (spec edge cases)

## Sources and builds

- **Pin everything by commit SHA.** A `baseline.yaml` with the exact revisions made later updates possible, and the OpenShell upgrade that merged a few hours after the baseline became the trigger for the first evolve run instead of a silent drift. (FR-007, FR-025)
- **Never `cd` into the partial-clone cache, and never run git there.** It stalled subagents repeatedly; run every command from the project root with path arguments. Read pull request heads through `gh api .../compare`. (research R10)
- **Inject versions, never type them.** Listings that use attributes need `subs="attributes+"`, and a `${VAR}` inside such a listing breaks a warn-level build. (FR-018)
- **Make the style rules scripts.** One sentence per line in AsciiDoc, no em or en dashes, no internal links or ticket keys on shareable pages, and a leak check on the built site all ran as `make check` gates. (FR-019)
- **Quote AsciiDoc alt texts.** In an `image::` macro, an alt text that contains commas is split into `width` and `height` values. (FR-019)
- **Antora cannot build `url: .` from a linked git worktree,** because `.git` is a file there. Detect the worktree and generate a playbook that points at the main repository with `branches: <worktree branch>` and `worktrees: <worktree name>`, with an absolute `output.dir`. The spex worktrees extension works in `.claude/worktrees/`, so this case is common. (FR-016a)
- **Isolated or background sessions may refuse `git` commands rewritten by a shell hook** (`rtk git ...`). Calling `/usr/bin/git` directly works. (spec edge cases)
- **Pushes fail while the 1Password SSH agent is locked.** Keep committing locally and retry after the next task. (spec edge cases)

## Excalidraw diagrams

- **Prefer curved arrows, with the right mechanics.** A curved arrow is an `arrow` element with `"roundness": {"type": 2}` and at least three `points`. The MCP's `update_element` cannot set `points` or `roundness`, so change arrow geometry by editing the scene JSON and re-importing it on a cleared canvas (`clear_canvas`, then `import_scene`). Deleting the arrow and recreating it with `batch_create_elements` works only for straight or elbowed arrows (see "Canvas setup"). (FR-022)
- **Arrow labels follow the arrow.** A label bound to an arrow is always drawn at the midpoint of the arrow path; setting its x or y does nothing. Reshape the arrow, or make the label free-standing text and place it explicitly. (FR-022)
- **A rectangle with a text label is not a container.** Moving such a "frame" moves neither its label nor the boxes inside it. One layout change broke a diagram exactly this way: frames moved, labels and legend stayed behind, and arrows ended in empty space. Use real Excalidraw frames or groups, or move a container together with all its children and its label. (FR-022)
- **Plan the layout before drawing arrows.** Leave 80 to 100 px channels between rows for arrows and their labels, at least 40 px between boxes, and keep every box and label off frame borders. Most crossings came from rows packed too tightly to route around anything. (FR-022)
- **Bind arrows to box edges.** Straight two-point arrows whose boxes later moved ended up starting in empty space. (FR-022)
- **Remove duplicate container-bound texts before export.** Canvas sync creates them; one diagram had 54 text elements for 27 containers. (FR-022)
- **Use one semantic palette across all diagrams,** and keep one entity in one color everywhere; the default `#1e1e1e` legend text and stray grays crept in more than once. (FR-022)

## Diagram review

This was the most expensive lesson.

- **A subagent's visual self-review is not reliable for diagrams.** One subagent reported "all arrows pass" three times while the exported PNG still had labels on frame borders, arrows through boxes, and once a broken layout. The controller checks every export itself. (FR-023a)
- **The canvas render differs from the export.** Review the exported SVG or PNG, never only the canvas screenshot. (FR-023a)
- **Large PNGs get downscaled when an agent reads them.** The 2x export was about 7700 px wide, and downscaling hid the overlaps. Review cropped regions at native resolution. (FR-023a)
- **Let a script find overlaps, not eyes.** A checker parses the `.excalidraw` JSON, samples each arrow's path (curves included), and reports every intersection with a text or box it is not bound to, plus every label or box that crosses a frame border. It is a gate before export. (FR-023)
- **Keep every round.** Round 2 overwrote a better round 1, which was lost. Each round now writes to its own versioned directory. (FR-023b)
- **Cap automated fix rounds at two, then hand over.** After two rounds the author edits on the canvas, says when they are done, and the plugin exports, renders, and checks again. Manual editing is a regular step, not an error path. For scale: one unsuccessful automated round cost 37 minutes and 102 tool calls. (FR-023b)

## Canvas setup

- **Know which canvas you are drawing on.** There can be several: a project `.mcp.json` server (port 3000 in the SAW run) and a user-level one (port 3100). The server's `/health` endpoint shows `elements_count` and `websocket_clients`. `export_to_image` needs a browser tab connected to that canvas, so open it when `websocket_clients` is 0. (FR-024)
- **Back up the canvas before replacing the scene,** and restore it afterwards, because the author may have their own drawing there. Server snapshots live only in memory and are not a backup. (FR-024)
- **Pre-approve the Excalidraw tools where the session reads them.** Permission prompts stalled one diagram task for about three hours. In a later run the session ran in a different directory than the guide project. Claude Code reads the session directory's `.claude/settings*.json` and `~/.claude/settings.json`, not the guide project's, and the classifier denied `clear_canvas` and `import_scene` to a subagent. (research R9)

Canvas facts from a later guide run (`yctimlin/mcp_excalidraw`):

- **Clear the canvas before drawing.** The canvas still held the author's old drawing, and restoring it after every diagram meant each new diagram started on top of old content; screenshots and the author's view were confusing. Back up once, `clear_canvas`, confirm `elements_count` 0 on `/health`, draw every diagram on an empty canvas, and restore the author's drawing only at the end of the run. (FR-024)
- **`import_scene` with mode `replace` keeps existing elements.** A clean restore or reload is `clear_canvas` first, then `import_scene`, then a count check. (FR-024)
- **`batch_create_elements` drops custom points on bound arrows.** Curved arrows only worked by generating the scene JSON (boxes, bound texts, arrows with bindings) and loading it with `import_scene`. (FR-022)
- **The server reads and writes files only under its working directory or `EXCALIDRAW_EXPORT_DIR`.** `export_scene` into a guide project elsewhere failed with "Path traversal blocked"; agents had to stage files in an allowed directory and move them. Set `EXCALIDRAW_EXPORT_DIR` in the server's `env` to a directory that contains the guide projects. (FR-024)

## Preview and rendering

- **Click to enlarge.** The RHDP showroom Antora UI has a built-in lightbox for `role=expand` (an overlay at 95% of the window) and `role=fullscreen`. The Antora adapter adds `role=expand` to every diagram. (FR-022a)
- **Preview loop:** serve with browser-sync, watch the content sources, rebuild on change with a debounce, queue changes that arrive during a build, keep the last good site when a build fails, then reload the browser. browser-sync injects its client only into requests that accept `text/html`. (FR-030)

## Building the plugin

Lessons from implementing cc-guide itself (2026-10-01).

- **Antora html-single defaults to Ruby.** `@antora/html-single-extension` converts with the `asciidoctor` command unless its build configuration says `command: false`; then it uses the bundled Asciidoctor.js. The setting lives inline in the playbooks (`config_source`), because the playbook generated for a linked worktree sits in `build/` and would not find a separate `antora-assembler.yml`. (R5, FR-030a)
- **An experimental partial must not set the section id.** A `[#{feature-anchor}]` line inside the partial duplicated the heading's id and failed the warning-level build. The anchor goes on the section heading; the partial only renders the label. Internal pages include the partials as `ROOT:partial$...`. (FR-015)
- **GNU make reports every failing recipe as exit 2.** `make drift` cannot pass drift.py's exit 10 through; scripts and the scheduled workflow call `tools/guide/drift.py --check` directly. (FR-025a)
- **An unreadable source is drift, not silence.** The drift check exits 10 when a source is `unchecked`, so a broken token or a deleted repository opens the drift issue instead of passing as "no change". (FR-025b)
- **Ticket-key patterns are greedy.** `\b[A-Z]{2,}-\d+\b` also matches `UTF-8` in vendor JavaScript and cc-guide's own finding ids (`UF-1`). The leak check scans only the visible text of HTML, and upstream drafts never contain finding ids. (FR-019, FR-035)
- **Generated regions are not typed values.** The gfm adapter writes baseline values into `<!-- guide:attr -->` regions; the typed-version check ignores their content, or every gfm page would fail. (FR-018)
- **Tag-pinned sources drift against the default branch.** A source pinned at a release tag (OpenShell `v0.0.116` in the SAW baseline) shows hundreds of commits against `main`; the useful target is the next tag, which the author names with `--to`. (FR-025)
- **Declaring superpowers as a plugin dependency blocks the whole plugin.** `"dependencies": ["superpowers@claude-plugins-official"]` gives a clear install message, but without superpowers even the commands that do not need it are unavailable. The runtime contract probe stays, because the declaration checks neither versions nor scripts. (FR-003, FR-004)
- **Plausible is not supported.** In the first end-to-end run, 4 of 20 independently sampled statements were unsourced inferences: an invented unit ("seconds"), a side-effect claim, remote-access advice, and an embellishment. Per-page reviews let them through as minors, and the final review left one deferred minor without a fix or a ruling. The review guide now makes unsourced units, side effects, and advice Important, and the controller confirms every deferred finding ends fixed or ruled. (SC-002, FR-011, FR-013)
- **Source-verified is not the same as understandable.** The OpenClaw recipe guide's start page passed its review with every statement sourced, yet a reader learned neither what OpenClaw nor what OpenShell is. The spec had outlined the start page as "what the recipe is" and pointed every fact at the recipe's own README, so the page defined the product by its container ("the kit ships a recipe for running OpenClaw"), repeated the recipe's second-hand description ("an AI coding assistant", where OpenClaw's own README says "an open-source AI assistant ... in the channels you already use"), and named OpenShell without saying what it does. The fix is structural: the spec starts with a why card the author approves, each product is defined from its own pinned source, and overview reviews apply a cold-reader test (`skills/page-task/overview-contract.md`). (FR-043)
- **Never type dash escapes in generated files.** A backslash-u escape for an em dash, written into a file by a tool, came out as the literal character and broke the no-dash rule. Tests build such characters with `chr(0x2014)`.

## Session settings

Use the most capable model for the controlling session and let subagents inherit it. Set the effort to high for create and evolve, and higher for the strict profile. Allow the tools a run needs (`gh`, `make`, `node`, `npx`, `uv`, and the Excalidraw MCP) instead of bypassing all permissions. Details are in `settings.md`. (FR-041, FR-042)
