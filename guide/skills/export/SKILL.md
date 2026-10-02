---
name: export
description: Export the whole guide as one PDF in navigation order, with a title page stating the baseline, a linked table of contents, page numbers, print-quality diagrams, and working cross-references. Shareable by default and leak-checked; the internal part only on explicit request, then marked on every page. Fails without writing a file when checks fail or the tool chain is missing. Use for /guide:export.
argument-hint: "[--internal] [--out PATH] [--dir PATH]"
allowed-tools: ["Bash", "Read", "AskUserQuestion"]
---

# /guide:export

One PDF of the guide, built from the same content as the site (FR-030a to FR-030f).

## Steps

1. The command wrapper runs `guide:preflight` with `export`; it stops when `make doctor` fails (the PDF printer needs Playwright Chromium; the gfm adapter also needs Pandoc). Stop with doctor's hint.
2. View:
   - Default: the shareable view.
   - `--internal`: only when `guide.yaml` has `internal.enabled: true`. Warn first and ask for confirmation:
     > The internal PDF contains internal content (confidential notes, ticket references, customer context). Its file name and every page footer are marked INTERNAL. Do not share it outside the internal audience. Continue?
3. Build: from the guide project root run

   ```bash
   make pdf VIEW=<shareable|internal>
   ```

   The target runs `make check` first and refuses to print when any content check or the leak check fails; it then produces the adapter's print HTML (Antora html-single export, the MkDocs print-site page, or a Pandoc assembly of the gfm pages in `docs/SUMMARY.md` order) and prints it with `tools/guide/print-pdf.mjs`. For the shareable view it leak-checks the PDF and deletes it on a leak. The file is `dist/<guide-slug>-<baseline-date>.pdf` (`-INTERNAL` added for the internal view).
4. On failure, no PDF remains (the printer writes to a temporary file and renames it only on success). Name the cause from the output: the failing check with page and line, the leaked term, or the missing tool and its install hint. Never hand out a partial PDF.
5. `--out PATH`: after a successful build, move the PDF there (keep the `-INTERNAL` marker in the name for the internal view; add it when the given name lacks it).
6. Report the path, the page count (`uv run --with pypdf python -c "import pypdf,sys; print(len(pypdf.PdfReader(sys.argv[1]).pages))" <pdf>`), the view, and for the internal view repeat the sharing warning.

## What the PDF contains (FR-030b to FR-030d)

- A title page with the guide title, the baseline capture date, and every pinned source with its commit.
- A linked table of contents (one click to any page) and page numbers on every page.
- Every page of the view in navigation order; diagrams as SVG; admonitions and experimental labels as distinct blocks; code listings wrapped, tables within the page width, and wide elements on landscape pages.
- Cross-references between pages as links inside the PDF; source links pointing at the pinned revisions; searchable text.
