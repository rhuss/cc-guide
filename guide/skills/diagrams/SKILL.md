---
name: diagrams
description: Draw, check, export, and review Excalidraw diagrams for a cc-guide guide project. Used by create and evolve for every diagram task. Covers canvas identification and backup, layout and curved-arrow rules, the overlap gate (diagram_check.py), versioned export rounds, the controller's review at native resolution, the two-round cap with manual hand-off, permissions, and the placeholder path when the Excalidraw tools are missing.
argument-hint: "<diagram-name> [--round N]"
allowed-tools: ["Bash", "Read", "Write", "Edit", "mcp__excalidraw__*"]
---

# Diagrams

Every diagram in a guide is an Excalidraw scene drawn through the `mcp__excalidraw__*` tools of the configured server (`yctimlin/mcp_excalidraw`), checked by a script, exported in versioned rounds, and reviewed by the controlling session on the exported image. Follow the steps in order. The reasons behind each rule are in `docs/learnings.md` ("Excalidraw diagrams", "Diagram review", "Canvas setup").

Paths below are relative to the guide project root. Toolkit scripts live in `tools/guide/`. Run every command from the guide project root; never `cd` into `.guide/`.

## Roles

- **Drawing subagent** (the implementer of a diagram task): steps 1 to 7 and the automated fix rounds of step 9.
- **Controller** (the session that runs the plan): step 8 always, the round count and hand-off of step 9, and the final acceptance. A drawing subagent's own visual review never counts as the review (FR-023a): one subagent reported "all arrows pass" three times while the export still had arrows through boxes.

## 1. Canvas: know which canvas the tools talk to (FR-024)

Several canvases may run at once (a project `.mcp.json` server and a user-level one on different ports).

1. Collect candidate canvas URLs: the `EXPRESS_SERVER_URL` of every `excalidraw` server entry in the project's `.mcp.json` and in `~/.claude.json` (`mcpServers.excalidraw.env`). Read only that value; never print other configuration (it may hold tokens).
2. Query each candidate: `curl -s <url>/health` returns `elements_count` and `websocket_clients`.
3. Call `mcp__excalidraw__describe_scene` (or `query_elements`) and compare its element count with each candidate's `elements_count`. When two candidates show the same count, create one small marker rectangle with `create_element`, see which `/health` count goes up, then delete the marker with `delete_element`.
4. Tell the author which canvas URL the diagram is drawn on.
5. `export_to_image` needs a browser connected to that canvas. When its `websocket_clients` is 0, open the URL (`open <url>` on macOS) or ask the author to, and check `/health` again before any export.

## 2. Backup the author's canvas (FR-024)

Before `clear_canvas`, or `import_scene` with `mode: "replace"`, and before drawing on a canvas that has elements:

```bash
mkdir -p .guide/canvas-backup
```

1. `mcp__excalidraw__export_scene` with `filePath: <guide>/.guide/canvas-backup/<YYYYMMDD-HHMMSS>.excalidraw` (absolute path).
2. `chmod a-w` the backup file and check that it is non-empty JSON with the expected element count.
3. `snapshot_scene` is not a backup (it lives only in the server's memory).
4. When the diagram work is done (accepted or handed off), restore the author's drawing with `import_scene` (`filePath` of the backup, `mode: "replace"`), after the accepted scene has been saved (step 7). Tell the author the backup path.

## 3. Layout plan before any arrow (FR-022)

Write the plan as a short table in the task notes before drawing:

- rows and columns of boxes, with coordinates
- 80 to 100 px channels between rows for arrows and their labels, at least 40 px between boxes
- frames: real Excalidraw frames, or groups (`group_elements`) that hold the frame rectangle, its label, and all its children; a rectangle with a separate text is not a container, and moving it leaves its label and children behind
- every box and every label at least 20 px away from any frame border
- the legend position (bottom or right edge, outside all frames)

Create boxes with `batch_create_elements`, each box with its label as bound text (one text per container).

## 4. Arrows (FR-022)

- Curved arrows are preferred: an `arrow` element with `roundness: {type: 2}` and at least three points, bound to box edges with `startElementId` and `endElementId`. Unbound arrows end in empty space as soon as a box moves.
- Never change arrow geometry with `update_element`: it cannot set `points` or `roundness`. Either edit the scene JSON (exported with `export_scene`) and re-import it with `import_scene` mode `replace` after a backup (step 2), or delete the arrow and recreate it with `batch_create_elements`.
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

## 6. Before export: dedupe and the overlap gate (FR-022, FR-023)

1. `query_elements` for text elements; for every container with more than one bound text (canvas sync creates copies), keep one and `delete_element` the rest.
2. Save the scene: `export_scene` with `filePath: <guide>/.guide/diagrams/<name>/round<N>/<name>.excalidraw`.
3. Run the gate:

   ```bash
   uv run tools/guide/diagram_check.py check .guide/diagrams/<name>/round<N>/<name>.excalidraw \
     | tee .guide/diagrams/<name>/round<N>/check.txt
   ```

   Exit 0 means zero findings. Exit 1 lists findings (`arrow-crosses-text`, `arrow-crosses-box`, `crosses-frame-border`, `duplicate-bound-text`, `unbound-arrow-end`) as text lines followed by one JSON line. Export only at zero findings; otherwise fix and re-run (the fixes before the first export do not count as fix rounds).

## 7. Export a round (FR-023b)

Every round writes to its own directory and is never overwritten:

```text
.guide/diagrams/<name>/round<N>/
  <name>.excalidraw   scene (step 6)
  check.txt           overlap gate report (step 6)
  <name>.svg          export_to_image, format svg
  <name>.png          2x PNG rendered from the SVG
  crops/              controller review tiles (step 8)
  review.md           controller verdict (step 8)
```

1. `mcp__excalidraw__export_to_image` with `format: "svg"` and `filePath: <guide>/.guide/diagrams/<name>/round<N>/<name>.svg`.
2. `node tools/guide/shoot.mjs svg .guide/diagrams/<name>/round<N>/<name>.svg .guide/diagrams/<name>/round<N>/<name>.png --scale 2`
3. Only after the controller accepts the round (step 8): copy `<name>.excalidraw` to `diagrams/<name>.excalidraw` and the SVG and PNG to the adapter's image directory:

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
3. Write `review.md` in the round directory: one line per tile with what you saw, the list of problems with tile references, and the verdict `accepted` or `needs fixes`.

## 9. Fix rounds and manual hand-off (FR-023b)

- At most two automated fix rounds per diagram. A fix round = one fix pass by the drawing subagent on the canvas, then steps 6 to 8 into the next round directory.
- If round 2 is still not accepted (or the author declines the result), stop fixing and hand over:
  > Diagram `<name>` is open for manual edit on <canvas URL>. Round <N> is in `.guide/diagrams/<name>/round<N>/` with the review notes. Edit it on the canvas and tell me "done" when you are finished.
- Wait for the author's "done". Then export, check, and review again (steps 6 to 8) into a new round directory. Manual editing is a regular step of the flow, not an error.
- If an earlier round was better, restore it from its round directory with `import_scene` (`mode: "replace"`, after a backup) instead of fixing forward.
- Record every round in the ledger: `Task <N>: diagram <name> round <R> (<findings> findings, review <verdict>)`.

## 10. Permissions

Permission prompts stalled one diagram task for about three hours. Before the first diagram task, check the guide project's `.claude/settings.local.json` (and `.claude/settings.json`) for an allow entry `mcp__excalidraw` (or `mcp__excalidraw__*`). `scripts/deps.sh` reports it as `excalidraw_allowed`. When it is missing, offer to add it and add it only after the author agrees:

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
