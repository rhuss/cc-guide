# Research: cc-guide

Phase 0 findings. Each topic records the decision, the rationale, and the alternatives considered. Sources: the author's plugin repositories under `~/Development/context-engineering/`, the installed superpowers plugin (6.3.0 and 6.4.1), the Excalidraw MCP server clone, the saw-guide reference project, and tool documentation.

## R1. Plugin structure

**Decision**: Follow the real `cc-` plugins over `PLUGIN-ARCHITECTURE.md` where they differ. Repository `cc-guide` with root `.claude-plugin/marketplace.json` (marketplace name `guide-plugin-development`), `Makefile`, and the plugin in `guide/` with `.claude-plugin/plugin.json`, `commands/*.md` (thin wrappers) delegating to `skills/<name>/SKILL.md`, plus `scripts/`, `templates/`, `adapters/`, `toolkit/`, and `docs/`. Command frontmatter: `description`, `argument-hint`. No `hooks.json` or Python venv inside the plugin (cc-prose has neither); the plugin root is resolved from the skill's base directory, which Claude Code provides when a skill loads.

**Rationale**: cc-prose and cc-blog, the closest siblings, use exactly this shape; the architecture document predates them (marketplace naming `<name>-plugin-development` in practice, venv pattern only used by three plugins).

**Alternatives**: A context hook that injects `PLUGIN_ROOT` on every `/guide:` prompt (architecture doc); rejected for v1 because skills already know their base directory, and a hook adds a Python dependency to every prompt.

## R2. Dependency detection

**Decision**: Runtime check of `~/.claude/plugins/installed_plugins.json` (schema version 2: `plugins["<name>@<marketplace>"]` is an array of `{scope, installPath, version, gitCommitSha}`) for `superpowers@*` (required for create and evolve) and `prose@*` (optional). Additionally declare `superpowers` in `plugin.json` `dependencies` if the field accepts a cross-marketplace reference; this is verified in the first implementation task and dropped if not.

**Rationale**: cc-blog already gates on prose at prompt level; a programmatic read of `installed_plugins.json` exists in cc-spex and cc-memory. Claude Code's schema supports a `dependencies` field ("Plugins that must be enabled for this plugin to function"), but none of the author's plugins use it yet.

**Alternatives**: Checking the session's available-skills list only (works for prose, but cannot locate superpowers' scripts on disk).

## R3. Superpowers integration surface and drift (FR-004)

**Decision**: cc-guide drives four superpowers skills (`brainstorming`, `writing-plans`, `subagent-driven-development`, `requesting-code-review`) and calls three scripts from `<installPath>/skills/subagent-driven-development/scripts/` (`sdd-workspace`, `task-brief`, `review-package`), always as `bash <script>`. A contract probe runs before create and evolve: required skills exist, each script without arguments exits 2 with a `usage:` line, and the plugin's own tests check the `wrote <path>:` output format against a fixture. `guide/compat.yaml` lists known-good versions (6.3.0, 6.4.1). cc-guide states its plan and spec locations explicitly in the instructions it injects (superpowers defaults to `docs/superpowers/plans/` and `docs/superpowers/specs/`, overridable only in prose).

**Rationale**: There is no stable entry point or version API; three of four script contracts changed between 6.3.0 and 6.4.1 (`plan-path` marker and slug disambiguation, exit-3 range guards, `bash` invocation because exec bits can be stripped). The `wrote <path>:` output is an implicit API.

**Alternatives**: Vendoring the three scripts into cc-guide (stable, but forks superpowers and drifts from its ledger semantics); rejected because the user asked for superpowers as the dependency.

## R4. Toolkit placement and language

**Decision**: Deterministic logic lives in a **toolkit** that create copies into the guide project as `tools/guide/` with a `VERSION` file; evolve offers to update it when the plugin ships a newer version. Python 3.11+ scripts with PEP 723 inline metadata (`pyyaml` only), run with `uv run`; Node 20+ for Antora, Playwright, and the GFM preview server; Bash only for thin `make` glue.

**Rationale**: The scheduled drift check (FR-025b) runs in CI without Claude Code and without the plugin, so the check, drift, and leak-check logic must live in the guide repository. `uv run` with PEP 723 needs no committed virtual environment, matches the author's uv rule, and works on GitHub runners via `astral-sh/setup-uv`. Python replaces saw-guide's mix of `yq`, `rg`, and shell for parsing, which was the main source of SAW-specific hard-coding.

**Alternatives**: Running scripts from the plugin install path (CI cannot reach it, and the repository is private); a CI step that clones cc-guide at a tag (needs network access to the plugin repository and couples guides to its visibility).

## R5. Antora adapter and PDF

**Decision**: Antora `~3.2` with `@antora/html-single-extension` producing one standalone HTML document per view, printed to PDF by the shared Playwright script. Pin `@antora/cli ~3.2.0`. Port saw-guide's playbook pair (`site.yml`, `site-internal.yml` with a separate `internal` component), attribute injection from `baseline.yaml` through `--attribute`, the experimental partials, and the leak check.

**Rationale**: No Ruby needed: the local system Ruby is 2.6 and Antora Assembler with asciidoctor-pdf requires Ruby 2.7 or later. Playwright Chromium is already part of the stack (`shoot.mjs`).

**Alternatives**: Antora Assembler with asciidoctor-pdf (best typography, but a Ruby tool chain per author machine); Pandoc from the assembled AsciiDoc (loses Antora xrefs). **Risk**: the html-single extension is new (1.0.0); the first adapter task verifies it on saw-guide content and falls back to a toolkit script that assembles the pages in navigation order if it falls short.

## R6. MkDocs Material adapter and PDF

**Decision**: MkDocs Material `>=9.5,<9.8`, `mkdocs-macros-plugin` with `include_yaml: [baseline.yaml]` for baseline values, native admonitions plus a custom `experimental` admonition class, two configs (`mkdocs.yml` and `mkdocs-internal.yml` with `INHERIT:`) for the internal part, `mkdocs serve` for preview, and `mkdocs-print-site-plugin ~=2.8` producing a print page that the shared Playwright script turns into the PDF. Python packages installed with `uv tool` or `uvx`, never pip.

**Rationale**: Covers every adapter contract item with maintained plugins. **Risk**: Material is in maintenance mode (bug fixes only, announced for about one year from November 2025); its successor Zensical is not plugin-compatible yet. The adapter pins versions and documents the risk; a Zensical adapter is a later addition.

**Alternatives**: `mkdocs-with-pdf` (unmaintained), `mkdocs-exporter` (stale since 2024).

## R7. Plain GitHub Markdown adapter and PDF

**Decision**:
- Admonitions: GitHub alerts (`> [!NOTE]`, `> [!TIP]`, `> [!IMPORTANT]`, `> [!WARNING]`, `> [!CAUTION]`), which map one to one to the five types; experimental labels are IMPORTANT alerts with a fixed first line.
- Baseline values: **generated regions** inside the committed pages, `<!-- guide:attr <name> -->value<!-- /guide:attr -->`, rewritten in place by the toolkit. Pages stay the single source and remain readable on GitHub.
- Internal part: `internal/` beside `docs/`; the shareable view is `docs/` only; the leak check forbids links from `docs/` into `internal/`.
- Preview: `markserv` (offline, GitHub CSS, live reload).
- PDF: Pandoc 3 (`--standalone`, GitHub CSS) assembles one HTML document in navigation order (`docs/SUMMARY.md` or the README table of contents), printed by the shared Playwright script.

**Rationale**: Alerts are native GitHub rendering; generated regions avoid a second copy of every page; Pandoc is already installed.

**Alternatives**: `*.md.tmpl` templates rendered into committed `docs/` (two copies of every page, authors edit the wrong one); `grip` preview (needs the GitHub API, not offline); Pandoc with Typst as PDF engine (good output, but a separate engine from the other adapters and an extra install).

## R8. Unified PDF strategy (FR-030a to FR-030f)

**Decision**: Every adapter produces one self-contained print HTML document per view (shareable, internal). One shared toolkit script `print-pdf.mjs` adds the title page (title, baseline date, source revisions from `baseline.yaml`) and a linked table of contents, rewrites inter-page links to in-document anchors, applies print CSS (wrapping code, fitting tables, landscape pages for marked wide elements, admonition styling), and calls Playwright `page.pdf()` with `displayHeaderFooter` for page numbers and the internal marker in the footer. It refuses to run when the content checks or the leak check fail. The PDF has a linked TOC, not TOC page numbers.

**Rationale**: One code path for all formats, already-installed Chromium, searchable text, working links. Chromium lacks `target-counter`, so TOC page numbers would need paged.js; a linked TOC satisfies SC-011 ("reach any page in one click").

**Alternatives**: paged.js polyfill for TOC page numbers and running headers (later enhancement); per-format native PDF tools (three code paths).

## R9. Excalidraw diagrams (FR-022 to FR-024)

**Decision**: Use the configured server `yctimlin/mcp_excalidraw` 1.0.7 (`mcp__excalidraw__*` tools). Mechanics and rules for the diagram skill, refined by a later saw-guide diagram rework:

- **Canvas identification**: several canvases may run (a project `.mcp.json` server and a user-level one, on different ports). Before drawing, query the server's `/health` endpoint (`elements_count`, `websocket_clients`) to confirm which canvas the tools talk to. `export_to_image` and `get_canvas_screenshot` need a browser tab connected to that canvas; when `websocket_clients` is 0, open the canvas URL first.
- **Backup**: `export_scene` to `.guide/canvas-backup/<timestamp>.excalidraw` (read-only) before `clear_canvas` or `import_scene` with mode `replace`; restore with `import_scene` afterwards. `snapshot_scene` is not a backup (in-memory only).
- **Layout first**: plan rows and columns before any arrow. Leave 80 to 100 px channels between rows for arrows and their labels, at least 40 px between boxes, and keep boxes and labels off frame borders. Packed rows caused most crossings.
- **Containers**: a rectangle with a separate text label is not a container; moving it moves neither the label nor the boxes inside. Use real Excalidraw frames or groups (`group_elements`), or move a container together with all its children and its label in one change.
- **Curved arrows**: an `arrow` element with `roundness: {type: 2}` and at least three `points`, bound to box edges through `startElementId` and `endElementId` (unbound straight arrows ended in empty space after boxes moved). `update_element` cannot change `points` or `roundness`: change arrow geometry by editing the scene JSON and re-importing with `import_scene` mode `replace` (after a backup), or by deleting and recreating the arrow with `batch_create_elements`.
- **Arrow labels**: a label bound to an arrow is always rendered at the midpoint of the arrow path; setting its x or y has no effect. Move it by reshaping the arrow, or make it free-standing text placed explicitly.
- **Duplicates**: before export, `query_elements` finds container-bound text duplicates (source `frontend_sync`) and deletes them; the exported file must have exactly one text per container.
- **Palette** (semantic, from saw-guide): platform gray `#e9ecef`/`#495057`, governance orange `#ffe8cc`/`#e8590c`, admin red `#ffe3e3`/`#c92a2a`, user blue `#d0ebff`/`#1971c2`; text and legend use `#495057`, never the default `#1e1e1e`; one entity keeps one color across all diagrams.
- **Overlap gate** (FR-023): `tools/guide/diagram_check.py` parses the `.excalidraw` JSON, samples every arrow path (Catmull-Rom sampling through the points for curved arrows, the polyline otherwise), and reports intersections with text and box bounding boxes the arrow is not bound to, plus labels or boxes that cross a frame border, duplicate bound texts, and unbound arrow ends. Export is blocked until it reports zero findings.
- **Review of the export, by the controller** (FR-023a): the drawing subagent's self-review is not trusted (one subagent reported "all arrows pass" three times while the PNG still had labels on frame borders and arrows through boxes). The canvas render differs from the export, and image readers downscale large PNGs (a 2x export was about 7700 px wide) and hide overlaps. So the controller reviews the exported PNG in tiles at native resolution (`diagram_check.py crops`, with focused crops around each finding) and records the result.
- **Rounds and hand-off** (FR-023b): every round writes to `.guide/diagrams/<name>/round<N>/` (scene, SVG, PNG, check report), so an earlier better round can be restored. At most two automated fix rounds; then hand the canvas to the author ("open for manual edit"), wait for "done", and export, check, and review again. One failed automated round in saw-guide cost 37 minutes and 102 tool calls.
- **Export**: the `.excalidraw` source to `diagrams/`, SVG through `export_to_image`, PNG at 2x through `shoot.mjs`.
- **Permissions**: create checks that `mcp__excalidraw` is allowed in the guide project's `.claude/settings.local.json` and offers to add it (permission prompts stalled a saw-guide task for about three hours).

**Alternatives**: Relying on screenshot review by the drawing subagent (proven unreliable); `update_element` for arrow geometry (does not support `points` or `roundness`); unlimited automated fix rounds (expensive, and they can make a diagram worse).

## R9a. Preview, worktrees, and rendering details (FR-016a, FR-019, FR-022a, FR-030)

**Decision**:
- **Preview loop** (`antora-watch.mjs` for Antora): browser-sync serves `build/site`; chokidar watches the content sources; changes are debounced (300 ms), changes that arrive during a build are queued and trigger one follow-up build, a failed build keeps the last good site and prints the error, and a successful build reloads the browser. browser-sync injects its client only into responses requested with `Accept: text/html`, so the served pages must be HTML documents with that content type (true for Antora output). MkDocs uses `mkdocs serve`, the gfm adapter `markserv`, both with their own reload.
- **Linked worktrees**: Antora cannot use `url: .` inside a linked git worktree, where `.git` is a file. `tools/guide/playbook.py` detects a worktree and generates `build/playbook.yml` and `build/playbook-internal.yml` pointing at the main repository with `branches: <worktree branch>` and `worktrees: <worktree name>`, and an absolute `output.dir`. This matters because the spex worktrees extension places feature work in `.claude/worktrees/`.
- **Click to enlarge**: the Antora scaffold uses the RHDP showroom UI, whose built-in lightbox handles `role=expand` (overlay at 95% of the window) and `role=fullscreen`; every diagram image gets `role=expand`. MkDocs uses `mkdocs-glightbox`. The gfm adapter wraps each diagram in a link to its SVG.
- **Alt texts**: an AsciiDoc `image::` alt text with commas is split into width and height values; the content check requires quoted alt texts (`image::x.svg["Alt, with commas"]`).
- **git in isolated sessions**: background or isolated sessions may refuse `git` commands that a shell hook rewrites (for example `rtk git ...`). Skills tell subagents to fall back to the absolute path (`/usr/bin/git`); toolkit scripts call git through `subprocess` and are not affected.

## R10. Reuse from saw-guide

**Decision**: Generalize and port: `check-content.sh` helpers (`require`, `forbid`, `require_order`) into the Python checker with per-guide rule files; `check-no-internal.sh` into the leak check driven by `guide.yaml`; `check_ledger.py` (strict rigor) with source ids read from `baseline.yaml` and the block parsed only at the page top; `fetch-baseline.sh` (blobless clone plus pinned worktree, never `cd` into the cache) and `baseline-diff.sh` into `drift.py`; `shoot.mjs` as is; the experimental and baseline partials; `page-procedure.md`, `page-review-guide.md`, and the global-constraints template as skill templates. SAW-specific rules (product terms, page rule sets, Helm reference generator) stay in saw-guide. The saw-guide `baseline.yaml` (a SAW-shaped schema) is migrated to the cc-guide schema by the adoption step (FR-028), which SC-005 exercises.

## R11. Evaluation

**Decision**: Two layers. Deterministic tests: `pytest` for the toolkit (parsers, checkers, drift, read-only classifier, redaction, PDF preconditions) and per-adapter smoke tests on a fixture guide (build, check, leak check, PDF produced). Behavioral evals: agent-eval-harness cases (`eval.yaml`, `eval/cases/`, as in cc-prose) for the judgment-heavy skills: the page review catches planted false statements; upstream drops findings that no longer hold on the default branch; validate classifies commands correctly. A full create run on a small fixture project is a manual quickstart scenario, not an automated eval (cost).

**Rationale**: cc-prose uses agent-eval-harness; full create runs cost hours of model time.

## R12. Drift check in CI (FR-025b)

**Decision**: Opt-in GitHub Actions workflow template (`guide/templates/guide-drift.yml`, installed as `.github/workflows/guide-drift.yml`) with a weekly cron: `astral-sh/setup-uv`, `uv run tools/guide/drift.py --check --format markdown`, then `gh issue` to create or update one issue labelled `guide-drift`. Private sources need a read-only token secret (`GUIDE_SOURCES_TOKEN`); sources the job cannot read are reported as unchecked.

## R13. Session recommendations (FR-041, FR-042)

**Decision**: Recommend the most capable model for the controlling session, subagents without a model override (they inherit it), effort `high` for create and evolve and `xhigh` for strict rigor. A command can see its own model identity (stated in the system prompt) but not the effort level, so the preflight states both recommendations and warns only on the model.
