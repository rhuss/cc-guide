# Front page contract: the host README of an embedded guide

An embedded guide lives in one subdirectory of the repository it documents, and the repository's root `README.md` is the guide's front page (specs/005-embedded-guide). A visitor to the repository lands on it, so it is the guide's start page and its navigation at once. This contract extends `overview-contract.md`; both apply to the front page task, to its review, and to the final review.

## The nine rules

1. **Ownership comment first.** The first line is exactly:

   ```markdown
   <!-- guide: front page. This file is generated and maintained by cc-guide; change it with /guide:evolve. -->
   ```

   Nothing comes above it. `make check` fails without it.
2. **A Markdown title.** A `#` title follows the comment. Raw HTML titles (`<h1>`, a centered `<p>` with a heading) are not allowed; the PDF printer and the checks read the `#` title.
3. **Badges and logo stay.** Badges and a project logo from the old README come right after the title, unchanged and unverified. They are the only unverified content on the page. Do not add new badges.
4. **The source block.** The source block follows the badges. It cites `self:<path>` files of the host repository and other sources like any page. It never cites files inside the guide subdirectory, the front page itself, the developer README, or a stub; `make check` rejects such citations (rule `self-citation`), because the guide must not verify itself against its own text.
5. **The why.** The why card and the overview body follow `overview-contract.md`. The cold-reader test applies to the front page as it applies to a start page.
6. **Persona navigation.** One link per persona entry page, in section order, plus the reference section. Each section of `guide.yaml` appears as a heading or a list entry with its exact title, because `check.py --structure` reads the section titles from the front page.
7. **Closing links.** A short closing section links to the developer README (when it exists), `LICENSE`, and `CONTRIBUTING` (wherever it lives: the root, `.github/`, or `docs/`).
8. **Link form.** Links into the guide use host-relative paths (`guide/docs/admin/install.md` when the guide subdirectory is `guide`). When the move plan set `absolute_links: true` (a package manifest publishes the README to a registry), use absolute URLs at the tracked branch instead, built from the `self` source's `web` URL: `<web>/blob/<ref>/guide/docs/admin/install.md`.
9. **Shareable only.** An embedded guide has no internal part. No internal content, no confidential term or pattern, and no `input:` references on the front page.

## What the page task does differently

- The page lives at `../README.md` from the guide root. Edit it there; there is no copy in `docs/`. `docs/README.md` stays a one-line pointer to it.
- Verify facts in the `self` snapshot printed by `uv run tools/guide/fetch.py where self` (the host at the pinned commit, outside the repository), never in the working tree, which may hold uncommitted changes.
- Statements from the old README are claims to verify like any input. A statement the pinned code contradicts is dropped, and the report lists it under Findings with the contradicting source location (the run summary lists it under Dropped claims).
- `make check` builds the site and the PDF from a staged copy of `docs/` with the front page in place of the pointer page (`tools/guide/embed.py stage`), so links are checked both on GitHub and in the built site.

## Review additions

The reviewer of the front page applies checks 1 to 7 of `page-review-guide.md` and these:

- The first line is the ownership comment, the title is a Markdown `#` title, and only badges and a logo sit between the title and the source block.
- Every link to a persona entry page and to the developer README resolves from the repository root (as GitHub renders it).
- No citation of guide material in the source block.
- The cold-reader test answers are in the review output.
