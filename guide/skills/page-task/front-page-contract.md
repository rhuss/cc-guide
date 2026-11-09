# Front page contract: the host README of an embedded guide

An embedded guide lives in one subdirectory of the repository it documents, and the repository's root `README.md` is the guide's front page (specs/005-embedded-guide). A visitor to the repository lands on it, so it is the guide's start page and its navigation at once.

The front page may carry the author-region markers (specs/006-author-owned-front-page-region):

```markdown
author text (the author's, never touched by the guide)
<!-- guide:region -->
guide-owned content
<!-- /guide:region -->
more author text
```

With markers, everything between them is guide-owned and everything outside is the author's: the page task, the reviews, the checks, and hand-edit detection read and write the region only. Without markers, the whole file is guide-owned and every rule below applies to the whole file (specs/005 behavior). This contract extends `overview-contract.md`; both apply to the front page task, to its review, and to the final review.

## The nine rules

1. **Ownership comment first in the region.** The first line of the guide-owned region is exactly:

   ```markdown
   <!-- guide: front page. The text between the guide:region markers is generated and maintained by cc-guide; change it with /guide:evolve. Text outside the markers belongs to the author. -->
   ```

   (Without markers, the first line of the file is the specs/005 comment: `<!-- guide: front page. This file is generated and maintained by cc-guide; change it with /guide:evolve. -->`.) Nothing guide-owned comes above it. `make check` fails without it.

2. **A Markdown title.** A `#` title follows the comment. Raw HTML titles (`<h1>`, a centered `<p>` with a heading) are not allowed; the PDF printer and the checks read the `#` title.

3. **Author text outside the region.** Badges, a logo, a pitch, anything the author keeps outside the markers is the author's: copied verbatim, never verified, never rewritten, never reported. There is no badge rule of the guide's own; when the guide creates the region (embedded create), badges and logo from the old README stay in the author text above the markers, unchanged.
4. **The source block.** The source block follows the title inside the region. It cites `self:<path>` files of the host repository and other sources like any page. It never cites files inside the guide subdirectory, the front page itself, the developer README, or a stub; `make check` rejects such citations (rule `self-citation`), because the guide must not verify itself against its own text.
5. **The why.** The why card and the overview body follow `overview-contract.md`, inside the region. The cold-reader test applies to the front page as it applies to a start page. The region must hold on its own: it reads correctly when the author section is short or missing.
6. **Persona navigation.** One link per persona entry page, in section order, plus the reference section, inside the region. Each section of `guide.yaml` appears as a heading or a list entry with its exact title, because `check.py --structure` reads the section titles from the region (never from author text).
7. **Closing links.** A short closing section inside the region links to the developer README (when it exists), `LICENSE`, and `CONTRIBUTING` (wherever it lives: the root, `.github/`, or `docs/`).
8. **Link form.** Links into the guide use host-relative paths (`guide/docs/admin/install.md` when the guide subdirectory is `guide`). When the move plan set `absolute_links: true` (a package manifest publishes the README to a registry), use absolute URLs at the tracked branch instead, built from the `self` source's `web` URL: `<web>/blob/<ref>/guide/docs/admin/install.md`. Links are checked in the whole file, author text included: an author link that does not resolve fails `make check` (the single exception to region-only checking).
9. **Shareable only.** An embedded guide has no internal part. No internal content, no confidential term or pattern, and no `input:` references in the region.

## What the page task does differently

- The page lives at `../README.md` from the guide root. Edit it there; there is no copy in `docs/`. `docs/README.md` stays a one-line pointer to it.
- Edit the region only. Author text outside the markers is never modified, even to fix a link or a typo: report a problem in the run summary instead. `region.splice` (via the toolkit) is the only legal write.
- Verify facts in the `self` snapshot printed by `uv run tools/guide/fetch.py where self` (the host at the pinned commit, outside the repository), never in the working tree, which may hold uncommitted changes.
- Statements from the old README that moved into the region are claims to verify like any input. A statement the pinned code contradicts is dropped from the region, and the report lists it under Findings with the contradicting source location (the run summary lists it under Dropped claims). Statements that stayed in the author text are not verified at all.
- `make check` builds the site and the PDF from a staged copy of `docs/` with the whole front page (author text included) in place of the pointer page (`tools/guide/embed.py stage`), so exports are unchanged.

## Review additions

The reviewer of the front page applies checks 1 to 9 of `page-review-guide.md` and these:

- The first line of the region is the ownership comment, the title is a Markdown `#` title, and nothing guide-owned sits above the begin marker.
- Every link to a persona entry page and to the developer README resolves from the repository root (as GitHub renders it), in the region and in the author text alike.
- Read the author text outside the `guide:region` markers and flag contradictions with the guide region or the pinned sources as non-blocking findings in the run summary; never fail a check over author text (FR-014, FR-013).
- No citation of guide material in the source block.
- The cold-reader test answers are in the review output.
