# Output adapters

An adapter turns the format-neutral guide model into one output format. Each lives in `guide/adapters/<format>/` as a descriptor (`adapter.yaml`, copied into a guide project as `tools/guide/adapter.yaml`) and a scaffold (copied by `/guide:create` through `scripts/scaffold-project.sh`). The descriptor's `branding` list names the branding keys the adapter supports. An optional `branding/` directory (the Antora logo template, UI bundle contract, and vendored Red Hat fonts) is vendored next to the toolkit as `tools/guide/branding/`. Skills never call format tools directly; they run the guide project's `make` targets, which every adapter provides with the same names and meaning (`specs/001-cc-guide-plugin/contracts/adapter.md`).

## Capabilities

| | antora | mkdocs | gfm |
|---|---|---|---|
| Pages | AsciiDoc, one sentence per line | Markdown | Markdown rendered by GitHub |
| Site | Antora 3.2 with the RHDP showroom UI | MkDocs Material | no build needed; Pandoc HTML in `build/` for checks and tarballs |
| Baseline values | `--attribute` from `tools/guide/attrs.py export` | `{{= attr("<name>") }}` through `tools/guide/mkdocs_macros.py` | generated regions rewritten by `attrs.py regions --write` |
| Admonitions | `[NOTE]` ... `[CAUTION]` blocks | `!!! note` ... `!!! caution` (important and caution styled by `experimental.css`) | GitHub alerts `> [!NOTE]` ... `> [!CAUTION]` |
| Experimental labels | `ROOT:partial$experimental-<tier>.adoc` | `{{= experimental("<tier>", "<feature>", <n>) }}` | IMPORTANT alert with a fixed first line |
| Internal part | separate `internal` module (`internal/`) in the same component | `docs/internal/`, excluded from `mkdocs.yml`, included by `mkdocs-internal.yml` | `internal/` beside `docs/` |
| Click to enlarge | `role=expand` lightbox of the UI | glightbox | image links to its SVG |
| Preview | `tools/guide/preview-watch.mjs` (debounce, queue, last good site, reload) | the same watcher with `mkdocs build --strict` | `markserv` (no build, so nothing can break) |
| Print HTML for the PDF | html-single export `build/site/guide/_exports/index.html` | print-site page `build/site/print_page.html` | Pandoc assembly in `docs/SUMMARY.md` order |
| Linked git worktrees | generated playbooks (`tools/guide/playbook.py`) | works as is | works as is |
| Branding (`guide.yaml` `branding`) | all eight keys: `logo_text`, `wordmark`, `logo`, `logo_alt`, `footer`, `favicon`, `color`, `theme`, plus the overlay directory `ui/supplemental/` ([branding.md](branding.md)) | none (a branding block fails validation) | none (a branding block fails validation) |

## Make targets

| Target | Behavior |
|---|---|
| `make doctor` | Check the tool chain from `requires` in `adapter.yaml`; prints one install hint per missing tool |
| `make fetch-baseline` | Blobless clones and pinned worktrees under `.guide/cache/` |
| `make site`, `make site-internal` | Build the views into `build/site` and `build/site-internal`; warnings fail the build |
| `make check` | Builds, `guidecfg.py validate`, `check.py` (page conventions and `guide-rules.yaml`), the leak check on the shareable build; `STRICT=1` adds the claim ledger and forbids stub pages |
| `make preview [VIEW=internal] [PORT=n]` | Serve with live reload |
| `make pdf [VIEW=internal]` | `make check`, then the print HTML, then `tools/guide/print-pdf.mjs`; the shareable PDF is leak-checked and deleted on a leak |
| `make dist` | Shareable tarball, the internal one when enabled, and the PDFs |
| `make drift` | `tools/guide/drift.py --check`; drift makes the target fail. GNU make reports any failing recipe as exit 2, so scripts that need the exact status (0 no drift, 10 drift) call `uv run tools/guide/drift.py --check` directly |

## Version pins

| Adapter | Pins | Where |
|---|---|---|
| antora | `@antora/cli ~3.2.0`, `@antora/site-generator ~3.2.0`, `@antora/html-single-extension ^1.0.0`, RHDP showroom UI bundle v2.0.3, `chokidar`, `browser-sync`, `playwright ^1.48`, `js-yaml` | scaffold `package.json`, `site.yml` |
| mkdocs | `mkdocs 1.6.1`, `mkdocs-material 9.7.7` (kept below 9.8), `mkdocs-macros-plugin 1.5.0`, `mkdocs-print-site-plugin 2.8`, `mkdocs-glightbox 0.5.2`, `pymdown-extensions 10.21.3` (run through `uvx`, never pip), `playwright`, `js-yaml` | scaffold `requirements.txt`, `package.json` |
| gfm | `markserv 1.20.0` (1.20.2 fails `npm install`), Pandoc 3, `playwright`, `js-yaml` | scaffold `package.json` |

## MkDocs Material is in maintenance mode

MkDocs Material announced maintenance mode in November 2025: bug fixes only, for about a year. Its successor, Zensical, is not compatible with the MkDocs plugins this adapter needs (macros, print-site, glightbox). The adapter pins `mkdocs-material` below 9.8 so a later release cannot change the build silently. A Zensical adapter is a planned addition once it supports the equivalent features; until then, new guides that need a long life should prefer the antora or gfm format (research R6).

## PDF printing

All three formats print through one script, `tools/guide/print-pdf.mjs` (Playwright Chromium):

```text
node tools/guide/print-pdf.mjs --html <print html> --guide-root . --view shareable|internal --out <pdf>
    [--page-heading CSS] [--section-heading CSS] [--hide CSS] [--allow-broken-links]
```

It adds the title page (title, baseline date, every source with its commit) and a linked table of contents, rewrites links between pages to in-document anchors, applies the print CSS (wrapped listings, tables at full width, landscape pages for `.guide-wide` elements, distinct admonitions), prints page numbers and the INTERNAL footer marker, and writes the PDF atomically. It fails, leaving no file, on unresolved links, broken images, or missing packages. Chromium cannot print table-of-contents page numbers, so the table of contents is linked instead (research R8).

The Antora html-single export was verified on the SAW guide's content: all 19 navigation pages in order, its four SVG diagrams, every admonition type, and tabs degraded to definition lists. Three anchors that are broken in the SAW guide's own source make a strict PDF fail; `--allow-broken-links` prints it anyway.

## Adding an adapter

1. Create `guide/adapters/<format>/adapter.yaml` with every descriptor field and `guide/adapters/<format>/scaffold/` with a `Makefile` that implements every target above.
2. Add the format to `FORMATS` in `guide/toolkit/guidecfg.py`.
3. Add a target to `tests/adapters/convert.py` and a smoke test `tests/adapters/test_<format>.sh` with the same assertions as the existing ones; `make test-adapters` picks it up.
4. Add the format's snippets to `guide/skills/page-task/page-procedure.md` and its format rules to the create skill.
