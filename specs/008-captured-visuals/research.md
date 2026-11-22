# Research: Captured visuals

All decisions below resolve the open questions of `brainstorm/09-captured-visuals.md` and the technical unknowns of the plan. Spikes were run on 2026-11-22 on macOS with podman 6.2.0 (applehv machine).

## R1. Where the work runs: host orchestrator plus a capture container

- **Decision**: A host script `tools/guide/visuals.py` (PEP 723, run with `uv run`) parses the recipe, talks to podman through `subprocess`, writes sidecars, computes fingerprints, and compares drift results. Everything that needs a browser, fonts, or image libraries runs inside the capture container through `tools/guide/capture/runner.py`, called with `podman exec`.
- **Rationale**: The host side stays testable with pytest and needs no browser or image library. Rendering inside one pinned image is what makes images reproducible (FR-009). The toolkit rule "nothing imported from outside its own directory" holds, because the capture image is built from files in `tools/guide/capture/`.
- **Alternatives considered**: Everything inside the container (the host would still need podman orchestration, and pytest could not reach most logic); Playwright on the host via the scaffold's existing Node dependency (fonts and browser versions then depend on the host, which breaks FR-009 and SC-002).

## R2. Capture container base image and pinning

- **Decision**: `tools/guide/capture/Containerfile` starts `FROM mcr.microsoft.com/playwright/python:v1.49.1-noble` pinned by its index digest (recorded in the Containerfile next to the tag, resolved once at implementation time with `podman manifest inspect`). It installs uv from `ghcr.io/astral-sh/uv:<pinned>` and then pinned Python packages with `uv pip install --system`: `pyte==0.8.2`, `fonttools[woff]==4.67.0` (the version `playbook.py` already uses), `pillow` (pinned), `pyyaml` (pinned). Fonts: DejaVu Sans Mono (regular and bold from `fonts-dejavu-core`, oblique faces from `fonts-dejavu-extra`) and Noto Color Emoji from the Ubuntu noble archive, installed with apt at versions pinned to the noble release pocket (updates-pocket versions disappear when superseded); `uv pip install --system --break-system-packages` because the noble Python is externally managed; the image digest of the base plus the apt versions pin the result.
- **Rationale**: The image is multi-arch (`linux/amd64`, `linux/arm64`, verified with `podman manifest inspect`), ships Chromium matched to the Playwright version and the system libraries it needs. Python in the container lets the runner share code with the host (`render_cli.py` is pure Python). uv instead of pip is a project rule.
- **Alternatives considered**: The Node Playwright image (the CLI renderer would then be JavaScript, duplicated logic, no host tests); building Chromium ourselves (no benefit).

## R3. Capture environment identity

- **Decision**: The capture environment version is the first 12 hex characters of a SHA-256 over the sorted relative paths and contents of the files in `tools/guide/capture/`, excluding `__pycache__/`, `*.pyc`, and dotfiles other than `.containerignore` (importing `redact.py` on the host writes bytecode there). The image tag is `localhost/cc-guide-capture:<version>`; `visuals.py` builds it with `podman build` when `podman image exists` fails, and otherwise reuses it.
- **Rationale**: FR-009 clarification (built locally, tagged by a definition hash, reused). The same function feeds the fingerprint (FR-017), so `check.py` computes it without podman (FR-024).

## R4. CLI capture: host pseudo-terminal plus `podman exec -t`

- **Decision**: For a CLI visual, the host opens a pseudo-terminal (`pty.openpty()`), runs `podman exec -t -e COLUMNS=<w> -e LINES=200 -e TERM=xterm-256color [-e ...] <container> sh -c '<command>'` with stdin, stdout, and stderr on the pty's slave side, reads raw bytes from the master until EOF, and records the exit status. The raw bytes go to the run's scratch directory and are deleted when the run ends.
- **Rationale**: Spike: the output kept `ESC[1;32m` and truecolor `ESC[38;2;...m` sequences and `[ -t 1 ]` was true inside the container. `podman exec -t` without a terminal on stdin does not give the container a tty in every podman version; running it under a host pty does.
- **Alternatives considered**: `script -qc` inside the tool image (not present in every image); forcing colors through `FORCE_COLOR` and similar variables (tool specific; still allowed through per-visual environment variables).

## R5. ANSI to SVG rendering

- **Decision**: `tools/guide/capture/render_cli.py` feeds the bytes into a `pyte` screen of the visual's width (height grown to fit), redacts and masks per line (R7), and writes an SVG: one `<text>` row per line with `<tspan>` runs per style, background rectangles per run, a 16-color palette plus 256-color and truecolor values, bold, dim (opacity), italic (oblique face), underline. The monospace font is embedded as WOFF2 subsets (one per face actually used, `fontTools.subset` on the glyphs present) in an `@font-face` with a `data:` URL. Emoji (wide characters with an emoji presentation) are drawn as `<image>` elements whose `data:image/png` comes from the Noto Color Emoji `CBDT` bitmap of the glyph, scaled to two cells. Output is deterministic: no timestamps, sorted attributes, fixed number formatting.
- **Rationale**: Spike: `pyte 0.8.2` keeps fg as names or 6-digit hex for truecolor, bold per cell, and stores a wide emoji in one cell. A terminal emulator (not a plain SGR parser) handles `\r` progress output and cursor moves correctly. Embedded subsets and raster emoji meet FR-016 (self-contained, same rendering on GitHub, sites, and PDF). Size stays well under 2 MB for normal output.
- **Alternatives considered**: `rich`'s SVG export (links external web fonts, styles a terminal window frame we do not want); rendering HTML in Chromium and screenshotting it (gives PNG, not SVG); `aha` or `ansi2html` (HTML, not SVG).

## R6. Web capture with Playwright Python

- **Decision**: `tools/guide/capture/web.py` uses the sync Playwright API with Chromium: viewport from the visual (default 1280x800), `device_scale_factor` 2, `locale` `en-US`, `timezone_id` `UTC`, `reduced_motion` `reduce`, `color_scheme` per variant, a CSS injection that sets `animation: none !important; transition: none !important; caret-color: transparent`, and `page.clock.install(time=<fixed>)` so client side clocks are fixed. Steps map to Playwright calls: `goto` (`page.goto(base + path, wait_until="load")`, with explicit `wait` steps for late content; `networkidle` hangs on UIs that poll), `click`, `fill`, `press`, `wait` (`locator.wait_for(state="visible")`), `hide` (inject `visibility:hidden`). Selectors: CSS by default; `text=` and `role=<role>[name=<name>]` map to `get_by_text` and `get_by_role`. Default step timeout 15 seconds.
- **Highlights and crops**: After all interaction steps and redaction, the runner computes bounding boxes of highlight targets and the crop target, injects one absolutely positioned SVG overlay covering the document with a dimming mask that has holes for highlighted boxes, an outline per box, and a numbered badge placed above-right of the box (moved below or left when it would leave the crop area). Then `page.screenshot(clip=crop_box + 16px margin)` or the full viewport.
- **Sidecar text**: `locator.aria_snapshot()` of the crop element (or `body`), taken before the overlay is injected (the overlay is `aria-hidden`), gives an indented role outline with names and text, which is the FR-017 web text content. Highlight records hold the label, the selector, and `inner_text()` of the element.
- **Rationale**: Playwright ships matching browsers in the base image; `aria_snapshot` exists since 1.49 and produces exactly the outline a text-only reviewer needs. Overlays placed from live bounding boxes follow layout changes (FR-020).
- **Alternatives considered**: Annotating the PNG afterwards with Pillow (loses the dimming of page content behind badges, and coordinates would need a second pass anyway); Puppeteer (Node).

## R7. Redaction and masks on text before rendering

- **Decision**: One rule engine (`tools/guide/capture/redact.py`, pure Python with no third-party imports, used by the runner in the container and imported by the host through the toolkit directory) holds the default rules (`home-path`, `user-path`, `user-at`, `hostname`, `ipv4`, `bearer`, `api-key`, `jwt`, `k8s-api`) as pattern templates with placeholders (`{user}`, `{home}`, `{host}`), plus recipe rules and masks. The host resolves the templates with the real values into the run's job file (scratch only); sidecars and fingerprints store rule ids and templates only. For CLI, redaction runs per screen line on the plain text, with replacements taking the style of the first replaced cell. For web, the runner walks text nodes, input values, `title` and `alt` attributes in the page and replaces matches before overlays, snapshot, and screenshot. Replacement counts per rule go into the redaction record.
- **IPv4 exemptions**: `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`, `127.0.0.0/8`, `0.0.0.0`, and the run network's subnet (read with `podman network inspect`).
- **Rationale**: FR-018, FR-021, FR-022. Text level redaction keeps images sharp and the sidecar identical to what the image shows.
- **Alternatives considered**: Pixel blurring (cannot be checked as text, fails for text-only review).
- **Note**: `redact.py` and `render_cli.py` live in `tools/guide/capture/`, the build context of the capture image, so the hash in R3 covers them; host scripts import `redact` by adding `tools/guide/capture` to `sys.path` (still inside the toolkit directory).

## R8. Image difference

- **Decision**: `runner.py diff <a.png> <b.png> --tolerance 16` (Pillow in the container): different sizes count as 100 percent; otherwise the share of pixels where any channel differs by more than the tolerance. The host never decodes images.
- **Rationale**: FR-027 defaults. Keeping image code in the container keeps the host dependency free.

## R9. Run lifecycle and cleanup

- **Decision**: Run id `YYYYMMDD-HHMMSS-<4 hex>`. Labels on every container and network: `io.cc-guide.capture=1`, `io.cc-guide.run=<id>`, `io.cc-guide.guide=<sha1 of the guide root path, 12 hex>`, `io.cc-guide.pid=<pid>`, `io.cc-guide.host=<hostname hash>`. At start: take an exclusive `fcntl.flock` on `.guide/visuals/.lock` (non-blocking; held means exit 2 "capture already running"); then list labeled resources (`podman ps -a --filter label=io.cc-guide.capture=1`) and remove those whose host label is this host and whose pid is not alive (`os.kill(pid, 0)`). Teardown in `finally` plus `SIGINT`/`SIGTERM` handlers: `podman rm -f` every container of the run, then `podman network rm`. Containers run with `--rm` is not used, so a failed container's log can be read before removal.
- **Name resolution**: podman's DNS (aardvark-dns with netavark) resolves container names and network aliases, not `--hostname`; every tool container gets `--network-alias <env>` plus `--hostname <env>` (the latter only for what the tool prints about itself).
- **Mounts**: `--security-opt label=disable` on every container so the read-only `visuals/` mount and the `/work` mount work on SELinux hosts without relabeling the author's files.
- **CLI environments**: without a declared `command`, `--entrypoint sleep <image> infinity` keeps the container up regardless of the image's own entrypoint.
- **Network**: `podman network create --label ... ccg-<run-id>` (bridge, not `--internal`, because tool images may need outbound access during seed steps such as `pip install`; no ports are published, FR-011).
- **Rationale**: FR-008, FR-011, SC-006, and the final review's process ownership finding.

## R10. Readiness

- **Decision**: The capture container starts first (`sleep infinity` entry), then tool containers. For a web environment, `podman exec <capture> python3 /opt/ccg/runner.py ready --url http://<env>:<port><ready> --timeout <s>` polls every 0.5 seconds with `urllib.request`; status below 400 means ready. On timeout the host adds `podman logs --tail 40 <env container>` to the error.
- **Rationale**: FR-002a; polling from inside the run network needs no published port.

## R11. Fingerprint

- **Decision**: SHA-256 (first 16 hex) over a canonical JSON document: the visual entry, its environment entry, its seed list with the SHA-256 of each referenced seed file and script, the effective redaction and mask rules as `{id, template, replacement}` (defaults plus recipe rules minus disabled ones), the resolved defaults that apply to the visual (width, prompt, viewport, tolerance, threshold), and the capture environment version (R3). Canonical JSON: `json.dumps(sort_keys=True, separators=(",", ":"))`.
- **How seed files are found**: Seed commands reference files under `visuals/seed/`; the recipe lists them explicitly per seed step (`files:`), so the fingerprint does not parse shell commands.
- **Rationale**: FR-017 clarification; `check.py` recomputes it with no podman (FR-024).

## R12. Where things live in a guide project

- **Decision**: `visuals.yaml` at the guide root; `visuals/` at the guide root holds sidecars (`*.visual.yaml`), `visuals/seed/` seed data, `visuals/scripts/` script steps. Images go to the adapter's `visual_dir`: Antora `content/modules/ROOT/images/visuals`, MkDocs and gfm `docs/assets/visuals`. Scratch: `.guide/visuals/<run-id>/` (already ignored through `.guide/`).
- **Embedding**: Antora `image::visuals/<name>.png["<alt>"]`; MkDocs and gfm `![<alt>](<relative path>/assets/visuals/<name>.png)`.
- **Rationale**: FR-015, FR-017 (sidecars outside published content: MkDocs copies every non-Markdown file under `docs/`, Antora publishes the images folder).

## R13. Integration points in the existing toolkit

- **Decision**:
  - `sources.py`: `visual:<name>` becomes a reference kind like `input:`; `<name>` must match the visual name pattern.
  - `guidecfg.py`: reserve the source id `visual` next to `self`.
  - `check.py`: new rule family `visuals` (FR-023), reading `visuals.yaml`, sidecars, page image embeds per adapter, the confidential configuration already used by the `confidential` rule.
  - `drift.py`: FR-030a, add `affected_visuals` per drifted source by reading `visuals.yaml` environments with `source:`.
  - `doctor.py`: a separate `optional` mapping in the adapter descriptor (podman there, built-in check `podman --version`); missing or failing optional tools are warnings that never fail `make doctor`.
  - Adapters: `visual_dir` key; Makefile targets `visuals` and `visuals-drift`.
  - Templates: `guide/templates/guide-visuals.yml` (CI), `guide/templates/visuals.yaml` (commented skeleton).
  - Skills: create (plan instructions, preflight podman, placeholders), page-task (procedure and review guide), evolve (visual drift, `--visuals`), preflight and `scripts/deps.sh` (podman detection), commands/evolve.md (argument hint).
- **Rationale**: Follows the existing structure of specs 001 to 007; every change has a home that already exists.

## R14. Test strategy

- **Decision**: pytest for host logic (`tests/toolkit/test_visualcfg.py`, `test_visuals.py`, `test_runner.py`, `test_redact.py`, `test_render_cli.py`, plus additions to `test_check.py`, `test_sources.py`, `test_guidecfg.py`, `test_drift.py`, `test_doctor.py`). `test_render_cli.py` imports `render_cli.py` in the `make test` environment (the root `Makefile` adds `--with pyte==0.8.2 --with brotli`) and the vendored Red Hat Mono fonts from `guide/adapters/antora/branding/fonts/` as a fixture font, skipping emoji cases when no emoji font is found. A podman smoke test `tests/adapters/test_visuals.sh` builds the capture image, captures one CLI visual (alpine `printf` with colors and the machine's real home path, user, and host name substituted into the scratch recipe by the script) and one web visual (a pinned `nginx:1.27-alpine` serving a seeded HTML page with a table, highlight, crop), runs `make check`, runs drift twice (expect 0), changes the seed (expect 10), and checks that no labeled container or network remains; it skips when podman is not available.
- **Rationale**: SC-002, SC-004, SC-006 need a real run; everything else is fast and deterministic in pytest.
