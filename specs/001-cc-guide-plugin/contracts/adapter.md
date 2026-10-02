# Contract: Output Adapter

An adapter turns the format-neutral guide model into one output format. Each adapter lives in the plugin at `guide/adapters/<format>/` and consists of a descriptor and a scaffold. Skills never call format tools directly; they call the guide project's `make` targets, which every adapter must provide with identical names and semantics.

## Descriptor (`adapter.yaml`)

| Field | Meaning |
|---|---|
| `format` | `antora`, `mkdocs`, or `gfm` |
| `requires` | Tool chain with version constraints, checked by `tools/guide/doctor` (for example `node >=20`, `@antora/cli ~3.2.0`, `pandoc >=3`) |
| `content_root` | Shareable content directory |
| `internal_root` | Internal content directory |
| `page_glob` | Pages subject to page conventions |
| `comment` | Syntax for source blocks and expectations (`line://` or `html`) |
| `admonitions` | Mapping of the five types to the format's syntax |
| `experimental` | How the two experimental tiers are rendered (partial, snippet, or alert template) |
| `attributes` | How baseline values reach pages (`antora-attribute`, `mkdocs-macros`, `generated-region`) |
| `preview_port` | Default preview port |

## Scaffold

Files copied into a new guide project by create: build configuration, navigation file, an index page per persona, the experimental and baseline snippets for the format, the `Makefile` targets below, `package.json` or tool pins, and `.gitignore` entries. The toolkit (`tools/guide/`) is copied separately and is format-neutral.

## Make targets (identical across adapters)

| Target | Behavior | Exit status |
|---|---|---|
| `make doctor` | Check the tool chain against `adapter.yaml` | non-zero with install hints when something is missing |
| `make fetch-baseline` | Fetch pinned sources into `.guide/cache/` | non-zero when a source cannot be fetched |
| `make site` | Build the shareable view into `build/site` | non-zero on build warnings |
| `make site-internal` | Build the internal view into `build/site-internal` (no-op when `internal.enabled: false`) | as above |
| `make check` | `site`, `site-internal`, page-convention checks, content checks, leak check on the shareable build; `STRICT=1` adds the claim ledger check (strict rigor) and forbids stubs | non-zero on any violation |
| `make preview [VIEW=internal]` | Build and serve with live reload, open the browser | runs until stopped |
| `make pdf [VIEW=internal]` | Produce the print HTML, then `tools/guide/print-pdf.mjs`; refuses when `make check` fails | non-zero, no file written, on failure |
| `make dist` | Shareable tarball and, when enabled, full tarball, plus the PDF(s) | non-zero on failure |
| `make drift` | `tools/guide/drift.py --check` | drift.py exits 0 no drift, 10 drift found, other non-zero on errors; `make drift` fails on anything but 0 (GNU make reports a failing recipe as 2), so callers that need the exact status run drift.py directly |

## Behavioral requirements

- Baseline values are injected at build or render time; pages never contain typed versions or commits (FR-018).
- The shareable view contains nothing from the internal root and no links into it (FR-019, FR-030e).
- Builds fail on warnings, including unresolved attributes or macros, so a missing baseline value cannot slip through.
- The print HTML contains every page in navigation order, each page's anchors made unique, and diagrams as SVG (FR-030a, FR-030c).
- Every target works when the guide project is a linked git worktree (FR-016a).
- Preview rebuilds on change with a debounce, queues changes that arrive during a build, keeps the last good site on failure, and reloads the browser after a successful build (FR-030).
- Diagrams open enlarged on click in the HTML output (FR-022a).

## Initial adapters

| Format | Build | Baseline values | Internal part | Preview | Print HTML |
|---|---|---|---|---|---|
| `antora` | Antora `~3.2`, two playbooks (generated from the main repository when the project is a linked worktree), RHDP showroom UI | `--attribute` from `baseline.yaml` | separate `internal` component | `antora-watch.mjs`: browser-sync, debounced rebuild, queued changes, last good site kept | `@antora/html-single-extension` |
| `mkdocs` | MkDocs Material `>=9.5,<9.8`, `mkdocs-glightbox` | `mkdocs-macros-plugin` reading `baseline.yaml` | `mkdocs-internal.yml` with `INHERIT:` | `mkdocs serve` | `mkdocs-print-site-plugin ~=2.8` |
| `gfm` | none (renders on GitHub) | generated regions rewritten by the toolkit | `internal/` beside `docs/` | `markserv` | Pandoc 3 standalone HTML in navigation order |
