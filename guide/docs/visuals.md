# Captured visuals

A guide can show what the reader will see: screenshots of a tool's web UI and the colored output of its CLI. cc-guide never takes these by hand. A guide project declares them in a recipe, `visuals.yaml`, and `make visuals` produces them in throwaway containers it starts itself, the same way on a laptop and in a CI job. Every image gets a text sidecar, so checks and page reviews verify a visual without looking at it. The design is in `specs/008-captured-visuals/`.

## Files in a guide project

| Path | What it holds |
|---|---|
| `visuals.yaml` | The recipe: environments, seed steps, redaction rules, defaults, visuals |
| `visuals/` | Sidecars (`<name>.visual.yaml`, `<name>-dark.visual.yaml`), seed data (`visuals/seed/`), script steps (`visuals/scripts/`). Outside every published directory, so sidecars never reach a site |
| `visual_dir` of the adapter | The images: `content/modules/ROOT/images/visuals/` (Antora), `docs/assets/visuals/` (MkDocs, gfm). PNG for web visuals, SVG for CLI visuals |
| `.guide/visuals/<run-id>/` | Scratch of one run: results, debug images of failed steps, `report.md` and `report.json`. Ignored by git. A run keeps the ten newest run directories and prunes older ones |
| `tools/guide/capture/` | The capture environment definition (Containerfile, runner, renderer, redaction rules, font licenses) |

`/guide:evolve --visuals` adds the recipe skeleton, `visuals/`, and the make targets to an existing guide. The skeleton (`tools/guide/templates/visuals.yaml`) explains every field in comments.

## Commands

| Command | Behavior | Exit status |
|---|---|---|
| `make visuals` (`VISUALS="a b"` for some) | Capture, write images and sidecars | 0 every visual captured or skipped, 1 a visual or environment failed, 2 recipe or configuration error, podman missing, or a run in progress |
| `make visuals-drift` | Recapture into `.guide/visuals/<run-id>/` and compare; never changes committed files | fails on drift; run `uv run tools/guide/visuals.py drift` for the exact status (0 no drift, 10 drift, 2 environment failure or the errors above) |
| `uv run tools/guide/visuals.py validate` | Schema check of `visuals.yaml`; no podman | 0 clean, 1 problems |
| `uv run tools/guide/visuals.py placeholder <name>...` | Placeholder sidecars for visuals that cannot be captured yet | 0, 1 unknown name |
| `uv run tools/guide/visuals.py version` | The capture environment version | 0 |

GNU make reports any failing recipe as exit 2, so `make visuals-drift` exits 2 on drift as well. Scripts that need the exact status (0, 10, 2) call `uv run tools/guide/visuals.py drift` directly. Without a `visuals.yaml`, capture and drift print `no visuals declared` and exit 0 before they look for podman. `make doctor` lists podman as optional: a missing podman is a warning, never a failure, and nothing but these two targets needs it.

## The recipe

```yaml
schema: 1
defaults:              # all optional
  width: 100           # CLI columns (20 to 300)
  prompt: "$ "
  viewport: {width: 1280, height: 800}
  timeout: 15          # seconds per web step
  tolerance: 16        # per-channel pixel tolerance for drift (0 to 255)
  threshold: 0.5       # percent of differing pixels that counts as drift
redaction:
  rules:
    - {id: tenant, pattern: "acme-[0-9]+", replacement: example-tenant}
environments:
  mlflow:
    kind: web
    image: ghcr.io/mlflow/mlflow:v2.19.0
    source: mlflow     # baseline.yaml source id (optional)
    port: 5000
    command: ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000"]
    ready: /health     # default /
    ready_timeout: 120
    seed:
      - run: python /visuals/seed/runs.py
        files: [seed/runs.py]
  tools:
    kind: cli
    image: ghcr.io/mlflow/mlflow:v2.19.0
visuals:
  mlflow-runs:
    kind: web
    env: mlflow
    variants: [light, dark]
    steps:
      - goto: /#/experiments/1
      - wait: "role=table"
      - highlight: {selector: "role=columnheader[name=accuracy]", label: "1"}
      - crop: "role=table"
    masks:
      - {pattern: "\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}", replacement: "2026-01-01 12:00:00"}
  mlflow-cli-runs:
    kind: cli
    env: tools
    command: mlflow runs list --experiment-id 1
    env_vars: {MLFLOW_TRACKING_URI: "${GUIDE_ENV_MLFLOW_URL}"}
```

Unknown keys are errors, so typos never pass silently. Every problem is reported as `visuals.yaml: <path>: <message>`. Steps and seed steps are numbered from 1, the same way a failed run names them (`visuals.mlflow-runs.step 3`, `environments.mlflow.seed step 1.run`); other lists use a zero-based index (`visuals.mlflow-runs.masks[0]`).

### Environments

- `kind: web` needs `port`, the container port of the UI. `kind: cli` keeps a container running for the length of the run (without a `command`, its entrypoint is replaced by `sleep infinity`). `kind: kind-cluster` is reserved and rejected as "not supported yet".
- `image` must name a tag or a digest; no tag or `:latest` is rejected, because a sidecar records the version it was captured from.
- Names are host names (lower case letters, digits, `-`, starting with a letter). All containers of a run share one internal network the run creates (no route out of it: the tools and pages of a run reach neither the internet nor the author's network, and images are pulled on the host before the run); each environment is reachable by its name, and every container receives `GUIDE_ENV_<NAME>_URL` (`http://<name>:<port>`) for each web environment. `env_vars` of a CLI visual may use `${GUIDE_ENV_<NAME>_URL}`; nothing else is expanded.
- No port is ever published to the host. Readiness is polled from inside the run network: a web environment is ready when `ready` answers below 400; after `ready_timeout` seconds every visual of the environment fails with the last status and the tail of the container log.
- `source` ties the environment to a baseline source. `make drift` then lists the environment's visuals as affected when that source drifts, and a sidecar records the source's pinned commit.

### Seed steps

A seed step is a shell command run in the tool's container (default, where its own client lives) or in the capture container (`in: capture`), after readiness and before the visuals. `visuals/` is mounted read-only at `/visuals` in every container. List the files a step reads under `files:`; their contents feed the recipe fingerprint. Seed data is fictional only and committed with the guide.

The run network is internal: no container of a run has outbound network access, so a seed step cannot download anything (no `pip install`, no `curl` of a dataset, no package mirror). Everything a seed step needs comes from the tool image or from committed files under `visuals/`. When the tool image lacks a client library, pick an image that has it, or write the seed with what the image ships (often the tool's own CLI or `python3` with the standard library).

### Web visuals

Steps run in order: `goto: <path>`, `click: <selector>`, `fill: {selector, text}`, `press: <key>`, `wait: <selector>`, `highlight: {selector, label}`, `crop: <selector>` (at most one), `hide: <selector>`, and `script: scripts/<file>.py`. Selectors are CSS, `text=<text>`, or `role=<role>[name=<name>]` (an exact accessible name). Note that Chromium maps a `<th>` without `scope` to the role `cell`, not `columnheader`.

The capture runs Chromium with a fixed viewport, device scale 2, locale `en-US`, time zone UTC, reduced motion, a fixed clock start, and no animations, transitions, or caret. `highlight` outlines the element, dims the rest of the captured region, and puts the label in a badge next to the element, placed from its live position so it follows layout changes. The badge takes the first of these positions that stays inside the image and covers no other visible text, highlight, or badge: above right, above left, below right, below left, right, left (always outside the outline); when none is free, the one that covers the least. `crop` clips the image to the element plus 16 pixels. A step that fails writes a debug image of the page (already redacted) to `.guide/visuals/<run-id>/debug/` and names the step number and selector; the other visuals still run.

A `script` step imports `visuals/scripts/<file>.py` and calls `run(page, base_url)` with the Playwright page and the environment's base URL. The sidecar lists the scripts a visual ran.

`variants: [light, dark]` captures both color schemes through the browser's preference (`<name>.png` and `<name>-dark.png`). When the dark capture equals the light one (same text, image difference below the threshold), the tool ignores the preference: no dark image is written and the light sidecar records the dark variant as `skipped`.

### CLI visuals

The command runs in the environment's container (a web environment works too) under a pseudo-terminal with `COLUMNS` set to `width` and `TERM=xterm-256color`, so tools that disable colors without a terminal keep them. The SVG shows the prompt, the command, and the output with its colors, bold, dim, italic, underline, and Unicode characters, in DejaVu Sans Mono embedded as WOFF2 subsets; emoji are embedded as bitmaps from Noto Color Emoji. A terminal cell holds a whole grapheme cluster: an emoji ZWJ sequence, a flag, a keycap, a skin tone, or a character followed by U+FE0F is one two-column emoji, drawn from the font's glyph for the whole sequence, and the sidecar keeps every code point. A character without U+FE0F (for example U+26A0 alone) keeps its text presentation. A sequence the font has no glyph for shows its first emoji. The SVG needs no external fonts or styles, so GitHub, the sites, and the PDF show the same thing. An exit status other than `exit` (default 0) fails the visual with the command, the status, and the last lines of output. An SVG over 2 MB fails too.

## Redaction and masks

Before anything is rendered, the run replaces, in the CLI text and in the page text (text nodes, input values, `title`, `alt`, `aria-label`, `aria-valuetext`, `aria-description`, `placeholder`, including open shadow roots and same-origin iframes; a value split across inline elements is matched as one text): the capturing user's home path and user name in path form or as `<user>@`, the host name, IPv4 addresses (except documentation ranges, loopback, `0.0.0.0`, and the run's own network), bearer tokens, API key, OpenShift token, `key: value` credential, private key, and JWT shaped strings, and Kubernetes API server URLs (`https://<host>:6443`). The page text is redacted again right before the screenshot, so text that changes while the run measures the highlights is covered too. Recipe rules add patterns; `disable_redaction` switches default rules off per visual. Masks replace volatile values (times, durations, generated ids) with a fixed value so repeated captures agree. Images and sidecars therefore carry the same text.

Text a web UI draws on a canvas or into an image is not page text and cannot be redacted. Hide or crop around it.

Redaction runs before any image, sidecar, report, or debug image is written. The only unredacted files are the run's own scratch inputs in `.guide/visuals/<run-id>/`: the raw CLI output (`raw/<name>.bin`) and the job file (`job.json`) with the host values the rules resolve to. Both are readable by the owner only and deleted at the end of the run; the next run deletes what a killed run left behind and keeps only the ten newest run directories. Failure messages (seed output, container logs) pass through the same rules before they are printed or written to a report. Sidecars and fingerprints store rule ids and pattern templates.

## Sidecars

A sidecar holds the provenance (environment image, index digest, platform, source commit), the recipe fingerprint, the capture environment version, the capture time, the redaction record (rule ids, disabled rules, replacements per rule, never the replaced values), the mask count, the scripts, the variants, the highlights (label, selector, element text), the CLI style fingerprint, and the text: the ARIA outline of the captured region for a web visual, the command line and output for a CLI visual. See `specs/008-captured-visuals/contracts/sidecar.md`.

## Pages, checks, and reviews

A page that embeds a visual cites it in its source block as `visual:<name>` (`visual:<name>-dark` for the dark variant) and embeds it with the adapter's image markup: Antora `image::visuals/<name>.png["<alt>"]`, MkDocs and gfm `![<alt>](<relative path>/assets/visuals/<name>.png)`. The source id `visual` is reserved.

`make check` never starts a container and needs no podman. Its `visuals` rule family reports:

| Severity | Finding |
|---|---|
| error | an image under the visual directory that no recipe declares |
| error | a declared visual whose image or sidecar is missing (unless the dark variant is recorded `skipped`, or the visual is a placeholder) |
| error | a sidecar without a redaction record |
| error | a `visual:` citation of an undeclared visual, or an embedded visual without its citation |
| error | a confidential term or pattern in a sidecar's text |
| error | a `visuals.yaml` that fails the schema check |
| warning | a placeholder visual, not yet captured |
| warning | a stale visual: its recipe, seed files, rules, a default that applies to it (for example the guide-wide `width` or `threshold`), or the capture environment changed since the capture (a toolkit update marks every visual stale until the next `make visuals`) |
| warning | a visual captured before the last rebaseline of its environment's source |

Warnings never fail the check, also not under `STRICT=1`. The dash rule (no em or en dash characters) skips the files in the visual directory, since images keep tool output verbatim.

The PDF export prints every visual as an ordinary image. Where a page wraps an image in a link to the image file (MkDocs glightbox, the click-to-enlarge links of gfm diagrams and visuals), `print-pdf.mjs` drops the link in the print document and keeps the image; this applies to every image, not only to visuals.

The page review guide treats every caption, alt text, and sentence about a visual as a claim against its sidecar. A reviewer that cannot see images (a text-only model) verifies visuals from the sidecar alone; looking at the image is optional.

## Visual drift

`make visuals-drift` recaptures every visual (or the named ones) and compares it with the committed one:

- the sidecar text and highlights, as a line diff (never provenance fields);
- for CLI visuals the style fingerprint (colors and weights), the image difference is reported as `n/a`;
- for web visuals the share of pixels whose channels differ by more than `tolerance`, against `threshold` (per guide or per visual).

| Status | Meaning |
|---|---|
| `unchanged` | nothing differs beyond the threshold |
| `drifted` | the text, the highlights, the CLI style, or the image changed; a skipped dark variant that now differs from the light one counts too |
| `recapture-failed` | a step or the command failed (with the step and selector or command); counts as drift |
| `environment-failed` | image pull, readiness, or seed step failed; not drift, the command exits 2 |

An image difference between captures from different platforms (an arm64 laptop and an amd64 CI runner) is reported but never counts as drift on its own; the sidecar text still does. The report lists, per visual, the pages that cite it, the image difference, the changed sidecar lines, and the environment image, digest, and platform before and after (`report.md` and `report.json` in the run directory). `/guide:evolve` runs visual drift next to the source drift when podman is available, recaptures drifted visuals, and updates the citing pages through page tasks and reviews.

## CI

`guide/templates/guide-visuals.yml` runs the visual drift command weekly and on manual dispatch on `ubuntu-latest`, with the runner's own podman: the capture environment and the tool environments run as sibling containers, never podman inside podman. It needs no repository secret, reads the repository only, puts the report into the job summary, and fails the job on drift or an environment failure. `/guide:create` and `/guide:evolve --visuals` install it when the author agrees, with `{{GUIDE_DIR}}` set like the drift workflow's.

## The capture environment

`tools/guide/capture/Containerfile` builds on the Playwright 1.49.1 Python image for Ubuntu 24.04, pinned by its index digest, and installs pinned versions of Playwright, pyte, fontTools, Pillow, PyYAML, and Brotli with uv, and pins their dependencies too (wcwidth, which decides how many cells a character takes, zopfli, greenlet, pyee, typing-extensions), plus DejaVu and Noto Color Emoji fonts from the noble release pocket. The font licenses ship in `capture/licenses/`. `visuals.py` builds it locally as `localhost/cc-guide-capture:<version>`, where the version is a hash over the build context, and reuses it while the hash is unchanged. No registry account is needed; a run only pulls images.

Two runs of the same recipe on the same CPU platform produce byte-identical CLI images and web images below the drift threshold. Across platforms rasterization may differ slightly.

Every container and network of a run carries the label `io.cc-guide.capture=1` with the run id, a hash of the guide path, the owning process id, and a hash of the host name. A run removes leftovers only of dead runs on the same host; every podman call has a timeout, and a second interrupt during cleanup is ignored so the cleanup finishes. A lock in `.guide/visuals/` serializes the runs of one guide project.

## Timings

Measured on 2026-11-22 with `tests/adapters/test_visuals.sh` (it prints these durations) on an arm64 Mac with podman 6.2 (applehv machine):

| Step | Time |
|---|---|
| First build of the capture environment | the pull of the 2.4 GB Playwright base image (network bound, a few minutes), then about 20 s for fonts, uv, and the Python packages |
| `make visuals` with a warm image cache: one CLI visual (alpine) and one annotated, cropped web visual (nginx with a seed page) | 4 to 5 s, including network, containers, readiness, seed, and teardown |
| `make visuals-drift` on the same recipe | 4 to 5 s |

Most of a run is container start and teardown; each further visual adds about one to two seconds, so ten visuals stay well under the three-minute goal of the plan. Going from an empty recipe to an embedded, annotated screenshot of a standalone web tool (SC-001) is dominated by writing the recipe and the seed data, not by the capture.

## Limits

- Platform-only UIs (for example a cluster dashboard that cannot run in a standalone container) are out of scope; the create plan proposes no visuals for them.
- Text drawn on a canvas or into images cannot be redacted or masked.
- An emoji sequence that Noto Color Emoji has no glyph for (an unknown ZWJ combination) shows only its first emoji in a CLI image; the sidecar text keeps the whole sequence.
- No animations (filmstrips, terminal playback), no Kubernetes-in-container environments, and no internal-only visuals in this version: all visuals are shareable, and the confidential-term check on sidecar text keeps confidential content out.
- Docker is not supported; captures use podman.
