---
name: diagrams
description: Draw, check, export, and review Excalidraw diagrams for a cc-guide guide project. Used by create and evolve for every diagram task. Covers canvas identification, the server's file paths, backup, clearing and restore, layout and curved-arrow rules, the claims file with a source for every label, arrow, and frame, the drawer's screenshot self-check, the overlap and claims gates (diagram_check.py), versioned export rounds, the controller's layout and fact review at native resolution, the two-round cap with manual hand-off, permissions, and the placeholder path when the Excalidraw tools are missing.
argument-hint: "<diagram-name> [--round N]"
allowed-tools: ["Bash", "Read", "Write", "Edit", "mcp__excalidraw__*"]
---

# Diagrams

Every diagram in a guide is an Excalidraw scene drawn through the `mcp__excalidraw__*` tools of the configured server (`yctimlin/mcp_excalidraw`), checked by a script, exported in versioned rounds, and reviewed by the controlling session on the exported image. Follow the steps in order. The reasons behind each rule are in `docs/learnings.md` ("Excalidraw diagrams", "Diagram review", "Canvas setup").

Paths below are relative to the guide project root. Toolkit scripts live in `tools/guide/`. Run every command from the guide project root; never `cd` into `.guide/`.

## Roles

- **Drawing subagent** (the implementer of a diagram task): steps 1 to 7 (with the self-check of step 5a) and the automated fix rounds of step 9.
- **Controller** (the session that runs the plan): step 8 always, the round count and hand-off of step 9, the final acceptance, and the restore of the author's drawing at the end of the run (step 2). A drawing subagent's own visual review never counts as the review (FR-023a): one subagent reported "all arrows pass" three times while the export still had arrows through boxes.

## 1. Canvas: know which canvas the tools talk to (FR-024)

Several canvases may run at once (a project `.mcp.json` server and a user-level one on different ports).

1. Collect candidate canvas URLs: the `EXPRESS_SERVER_URL` of every `excalidraw` server entry in the project's `.mcp.json` and in `~/.claude.json` (`mcpServers.excalidraw.env`). Read only that value; never print other configuration (it may hold tokens).
2. Query each candidate: `curl -s <url>/health` returns `elements_count` and `websocket_clients`.
3. Call `mcp__excalidraw__describe_scene` (or `query_elements`) and compare its element count with each candidate's `elements_count`. When two candidates show the same count, create one small marker rectangle with `create_element`, see which `/health` count goes up, then delete the marker with `delete_element`.
4. Tell the author which canvas URL the diagram is drawn on.
5. `export_to_image` needs a browser connected to that canvas. When its `websocket_clients` is 0, open the URL (`open <url>` on macOS) or ask the author to, and check `/health` again before any export.

## 1a. Files: where the server can read and write

The server reads and writes files only under its own working directory (for a server that Claude Code starts, usually the directory the session was started in), or under `EXCALIDRAW_EXPORT_DIR` when that is set in the server's `env`. Any other `filePath` of `export_scene`, `export_to_image`, or `import_scene` fails with "Path traversal blocked ... Set EXCALIDRAW_EXPORT_DIR". When the guide project lies outside that directory:

1. Recommend that the author set `EXCALIDRAW_EXPORT_DIR` in the server's `env` to a directory that contains their guide projects and restart Claude Code (see `docs/settings.md`). Until then, stage.
2. Staging: use a dedicated directory the server allows, for example `<EXCALIDRAW_EXPORT_DIR or the server's working directory>/.guide-staging/<name>/` (create it with `mkdir -p`). Export into it with an absolute `filePath`, then move each file into its place in the guide project (`mv`) right away. For an import, copy the file into the staging directory first and import from there (a small scene can also go to `import_scene` as `data`).
3. Remove the staging files and the staging directory when the step is done, and check that nothing is left behind in the author's checkout.

The paths below name the final location in the guide project; with staging, that is where the file must end up.

## 2. Backup, clear, and restore the canvas (FR-024)

Every diagram is drawn on an empty canvas, never on top of the author's drawing or an earlier diagram.

**Backup.** Before the first `clear_canvas` of a run, when the canvas has elements (and again before any later clear, when the canvas holds elements that are not a diagram of this run already saved in its round directory):

```bash
mkdir -p .guide/canvas-backup
```

1. `mcp__excalidraw__export_scene` with `filePath: <guide>/.guide/canvas-backup/<YYYYMMDD-HHMMSS>.excalidraw` (absolute path; stage it as in step 1a when the path is blocked).
2. `chmod a-w` the backup file and check that it is non-empty JSON with the expected element count.
3. `snapshot_scene` is not a backup (it lives only in the server's memory).

**Clear.** Before drawing each diagram (and before loading a scene for it, steps 4 and 9): `mcp__excalidraw__clear_canvas`, then `curl -s <url>/health` and confirm that `elements_count` is 0. When it is not, clear again and check again; never draw while old elements are left.

**Keep the result.** When a diagram is accepted (or handed off), leave it on the canvas so the author sees it. The next diagram task clears it; its scene is already saved (step 7).

**Restore.** Restore the author's drawing only at the end of the run (the controller does it in the wrap-up) or earlier when the author asks for it, and only after the last scene has been saved (step 7). Always in this order:

1. `clear_canvas`, and check that `elements_count` is 0. `import_scene` with `mode: "replace"` does not remove the elements already on the canvas; without the clear, the backup lands on top of the last diagram.
2. `import_scene` with the backup's `filePath` (staged as in step 1a when needed) and `mode: "replace"`.
3. `curl -s <url>/health` and check that `elements_count` equals the backup's element count. Tell the author the backup path.

## 3. Layout plan before any arrow (FR-022)

Write the plan as a short table in the task notes before drawing:

- rows and columns of boxes, with coordinates
- 80 to 100 px channels between rows for arrows and their labels, at least 40 px between boxes
- frames: real Excalidraw frames, or groups (`group_elements`) that hold the frame rectangle, its label, and all its children; a rectangle with a separate text is not a container, and moving it leaves its label and children behind
- every box and every label at least 20 px away from any frame border
- the legend position (bottom or right edge, outside all frames)

Create boxes with `batch_create_elements`, each box with its label as bound text (one text per container).

## 3a. Claims file: what the diagram asserts, with sources (FR-044)

A diagram makes factual claims with every label, every arrow, and every box drawn inside another. Write them down before drawing, in `.guide/diagrams/<name>/claims.yaml`, and keep it in step with the scene (element ids are the scene's ids):

```yaml
diagram: sandbox-flow
claims:
  - id: supervisor-pod
    kind: contains            # contains | connects | label | legend
    elements: [ns, supervisor]
    text: The supervisor runs in its own pod in the sandbox namespace, not in the workload pod.
    sources: ["openshell:docs/kubernetes/setup.mdx:20-25"]
  - id: egress
    kind: connects
    elements: [a_egress]
    text: Workload traffic leaves only through the supervisor service.
    sources: ["openshell:docs/about/architecture.mdx:100-104"]
  - id: legend
    kind: legend
    elements: [lg_title, lg_user]
```

- `contains`: a frame or group-frame and what it holds. Every frame needs one. Placement is a claim: drawing a process inside a pod says it runs there.
- `connects`: an arrow, what talks to what, and in which direction. Every arrow needs one.
- `label`: a box or free text; the claim covers the box's bound text. Every text needs a claim (an arrow's label is covered by its `connects` claim).
- `legend`: legend texts and swatches; no source.
- Sources are `<source-id>:<path>[:<lines>]`, `url:<url>`, or `live:<what was run, where, when>` for a recorded live check. Where a product runs its parts (pods, containers, processes, sidecars) comes from that product's own architecture documentation at the pinned version, or a live check, never from the integrating repository, an older release, or memory. When the product's docs and the integrating repository disagree, follow the product's docs and report the pair as an Upstream candidate.
- A label states only what its source states. A claim without a source does not go into the diagram. When the diagram has curved arrows, generate the whole scene instead, boxes included (step 4), so that boxes and arrows reference each other consistently.

## 4. Arrows (FR-022)

- Curved arrows are preferred: an `arrow` element with `roundness: {type: 2}` and at least three points, bound to box edges (in scene JSON: `startBinding` and `endBinding` with the box ids, and the arrow listed in each box's `boundElements`). Unbound arrows end in empty space as soon as a box moves.
- `batch_create_elements` drops custom points on bound arrows (`startElementId`, `endElementId`), so it cannot draw curved arrows. Build curved arrows in scene JSON: a small generator script in `.guide/diagrams/<name>/` (for example `scene.py`, run from the guide root with `uv run .guide/diagrams/<name>/scene.py`) writes `.guide/diagrams/<name>/scene.excalidraw` with the boxes, their bound texts, and the arrows. Load it with `import_scene` (`mode: "replace"`) on the canvas cleared as in step 2 (staged as in step 1a when the path is blocked).
- Never change arrow geometry with `update_element`: it cannot set `points` or `roundness`. Change the generator (or the scene JSON exported with `export_scene`), clear the canvas and check the count (step 2), and load it again with `import_scene`. Deleting an arrow and recreating it with `batch_create_elements` only works for straight or elbowed arrows.
- A label bound to an arrow is always drawn at the midpoint of the arrow path; setting its x or y has no effect. Move it by reshaping the arrow, or make it free-standing text placed explicitly in a channel.
- Route arrows through the channels; keep them clear of notes, labels, and unrelated boxes.
- First diagram of a run: after drawing the first curved arrow, call `get_element` on it (expect `roundness.type == 2` and three or more points) and export a test image. If curves do not render, fall back to `elbowed: true` arrows for the run and record a ruling.

## 5. Palette (FR-022)

One semantic palette for the whole guide; one entity keeps one color in every diagram.

| Meaning | Fill | Stroke |
|---|---|---|
| Platform, shared infrastructure | `#e9ecef` | `#495057` |
| Governance, policy | `#ffe8cc` | `#e8590c` |
| Admin-owned | `#ffe3e3` | `#c92a2a` |
| User-owned | `#d0ebff` | `#1971c2` |

Text and legend text use `#495057`, never the default `#1e1e1e`. When a guide needs another meaning, add a row to the guide's `styleguide.md` and use it everywhere.

## 5a. Self-check on the canvas screenshot (drawing subagent)

After each layout pass (the first drawing of steps 3 to 5, and every fix pass of step 9):

1. Call `mcp__excalidraw__get_canvas_screenshot` and look at the image.
2. Look for overlapping boxes, clipped or overflowing labels, arrows through boxes or labels, arrows ending in empty space, labels on frame borders, wrong palette colors, and missing legend entries.
3. Fix what you see on the canvas, then take a new screenshot.

At most two self-check passes per layout pass; then continue with step 6 and name what still looks wrong in your report. This is the drawer's own check, to catch obvious problems before the gate. It never replaces the controller's review of the exported image (step 8, FR-023a): the canvas render differs from the export, and drawers have reported clean diagrams that were not.

## 6. Before export: dedupe and the overlap gate (FR-022, FR-023)

1. `query_elements` for text elements; for every container with more than one bound text (canvas sync creates copies), keep one and `delete_element` the rest.
2. Save the scene: `export_scene` with `filePath: <guide>/.guide/diagrams/<name>/round<N>/<name>.excalidraw`.
3. Run the gate:

   ```bash
   uv run tools/guide/diagram_check.py check .guide/diagrams/<name>/round<N>/<name>.excalidraw \
     | tee .guide/diagrams/<name>/round<N>/check.txt
   ```

   Exit 0 means zero findings. Exit 1 lists findings (`arrow-crosses-text`, `arrow-crosses-box`, `crosses-frame-border`, `duplicate-bound-text`, `unbound-arrow-end`) as text lines followed by one JSON line. Export only at zero findings; otherwise fix and re-run (the fixes before the first export do not count as fix rounds).
4. Copy the claims file into the round directory and run the claims gate on the saved scene:

   ```bash
   cp .guide/diagrams/<name>/claims.yaml .guide/diagrams/<name>/round<N>/claims.yaml
   uv run tools/guide/diagram_check.py claims .guide/diagrams/<name>/round<N>/<name>.excalidraw \
     --claims .guide/diagrams/<name>/round<N>/claims.yaml | tee .guide/diagrams/<name>/round<N>/claims.txt
   ```

   It reports every text, arrow, and frame that no claim names (`claim-missing-label`, `claim-missing-arrow`, `claim-missing-frame`), claims without a well-formed source (`claim-no-source`), and claims that name elements the scene lacks (`claim-unknown-element`). Export only when both gates report zero findings.

## 7. Export a round (FR-023b)

Every round writes to its own directory and is never overwritten:

```text
.guide/diagrams/<name>/round<N>/
  <name>.excalidraw   scene (step 6)
  check.txt           overlap gate report (step 6)
  claims.yaml         the claims of this round (step 3a)
  claims.txt          claims gate report (step 6)
  <name>.svg          export_to_image, format svg
  <name>.png          2x PNG rendered from the SVG
  crops/              controller review tiles (step 8)
  review.md           controller verdict (step 8)
```

1. `mcp__excalidraw__export_to_image` with `format: "svg"` and `filePath: <guide>/.guide/diagrams/<name>/round<N>/<name>.svg`.
2. `node tools/guide/shoot.mjs svg .guide/diagrams/<name>/round<N>/<name>.svg .guide/diagrams/<name>/round<N>/<name>.png --scale 2`
3. Only after the controller accepts the round (step 8): copy `<name>.excalidraw` to `diagrams/<name>.excalidraw`, `claims.yaml` to `diagrams/<name>.claims.yaml` (reviewers of the pages that show the diagram read it there), and the SVG and PNG to the adapter's image directory:

| Format | Image directory | Page markup |
|---|---|---|
| antora | `content/modules/ROOT/images/` | `image::<name>.svg["<alt text>",role=expand]` (quoted alt text, `role=expand` opens the lightbox) |
| mkdocs | `docs/assets/diagrams/` | `![<alt text>](assets/diagrams/<name>.svg)` (glightbox enlarges on click; adjust the relative path to the page) |
| gfm | `docs/assets/diagrams/` | `[![<alt text>](assets/diagrams/<name>.svg)](assets/diagrams/<name>.svg)` (a click opens the full-size SVG) |

## 8. Controller review at native resolution (FR-023a)

The controlling session does this itself, never a subagent, and never from the canvas screenshot (the canvas render differs from the export):

```bash
uv run tools/guide/diagram_check.py crops .guide/diagrams/<name>/round<N>/<name>.png \
  --scene .guide/diagrams/<name>/round<N>/<name>.excalidraw --out .guide/diagrams/<name>/round<N>/crops
```

1. Read every `tile-r<R>-c<C>.png` (at most 1600 x 1200 px, so nothing is downscaled) and every `finding-<NN>-<kind>.png`.
2. Look for arrows through boxes or labels, labels on frame borders, clipped or overlapping text, wrong colors, missing legend entries, and arrows ending in empty space.
3. Check the facts. Read `claims.yaml` and open the cited source of every `contains` and `connects` claim, and of every label that names a product part, a location, a port, or a command. A claim its source does not state, or a box drawn where the product's own architecture documentation does not place it, makes the round `needs fixes`, however clean the layout is. A clean layout review once accepted a diagram that placed a process in the wrong pod; layout and facts are separate checks.
4. Write `review.md` in the round directory: one line per tile with what you saw, one line per checked claim with the source read and the verdict, the list of problems with tile or claim references, and the verdict `accepted` or `needs fixes`.

The page reviewer of every page that shows the diagram checks the claims again, independently (`page-review-guide.md`, check 8).

## 9. Fix rounds and manual hand-off (FR-023b)

- At most two automated fix rounds per diagram. A fix round = one fix pass by the drawing subagent on the canvas (with the self-check of step 5a), then steps 6 to 8 into the next round directory.
- If round 2 is still not accepted (or the author declines the result), stop fixing and hand over:
  > Diagram `<name>` is open for manual edit on <canvas URL>. Round <N> is in `.guide/diagrams/<name>/round<N>/` with the review notes. Edit it on the canvas and tell me "done" when you are finished.
- Wait for the author's "done". Then export, check, and review again (steps 6 to 8) into a new round directory. Manual editing is a regular step of the flow, not an error.
- If an earlier round was better, load it from its round directory instead of fixing forward: `clear_canvas`, check that `elements_count` is 0 (step 2), then `import_scene` with `mode: "replace"`.
- Record every round in the ledger: `Task <N>: diagram <name> round <R> (<findings> findings, review <verdict>)`.

## 10. Permissions

Permission prompts stalled one diagram task for about three hours, and an allow entry in the wrong file let the permission classifier deny `clear_canvas` and `import_scene` to a drawing subagent. The allow entry `mcp__excalidraw` (or `mcp__excalidraw__*`) must be in the settings Claude Code reads for the controlling session, which its subagents share:

- `.claude/settings.local.json` (or `.claude/settings.json`) of the directory the session runs in (its git toplevel inside a repository), or
- `~/.claude/settings.json`.

The guide project's own `.claude/settings*.json` only apply to sessions started in the guide project. Before the first diagram task, run `bash "$PLUGIN/scripts/deps.sh" --dir <guide> --session-dir <session directory>` (`PLUGIN` is the plugin root, two directories above this skill's base directory; the session directory is the one the session was started in). It reports `excalidraw_allowed` and, in `excalidraw_allowed_in`, the files that hold the entry. When the entry is missing, or it is only in the guide project's files while the session runs elsewhere, offer to add it to `<session directory>/.claude/settings.local.json` (and, as an option for future sessions started there, to the guide project's), and add it only after the author agrees:

```json
{ "permissions": { "allow": ["mcp__excalidraw"] } }
```

Merge into an existing file; never drop entries that are already there.

## 11. When the Excalidraw tools are unavailable (FR-003)

When the session has no `mcp__excalidraw__*` tools, or the canvas cannot be reached:

1. Warn with the install hint: install `yctimlin/mcp_excalidraw`, register it as an MCP server named `excalidraw` with `EXPRESS_SERVER_URL`, start its canvas, and restart Claude Code.
2. Ask the author whether to continue with placeholders. Never produce a guide silently without the requested diagrams.
3. On yes, write a placeholder block that names the missing diagram where the image would go (for example an Antora `[NOTE]` with "Diagram `<name>` (<alt text>) is not drawn yet: the Excalidraw tools were unavailable."), skip the diagram task, and record a ruling: `Ruling R<n>: diagram <name> replaced by a placeholder; Excalidraw tools unavailable; the guide lacks this diagram until a later run draws it.`
4. On no, stop the run before the diagram task and say how to resume.
