# Brainstorm: Antora guides that document the repository they live in

**Date:** 2026-11-23
**Status:** parked
**Source:** conversation, following #08 (GitHub Pages deploy and `/guide:evolve --pages`)

## Problem Framing

`/guide:create` can embed a guide in an existing repository only as gfm: the guide lives in a subdirectory, the host README is its front page, existing docs are consolidated into it with redirect stubs, the host is pinned as the source `self` (fingerprint drift, optional pull request check). Antora guides must live in their own repository (`guidecfg.py` rejects an `embedded` block for any other format, `scaffold-project.sh --embedded` refuses other formats, create section 3 refuses `--embedded --format antora`).

Since #08 an Antora guide in a repository subdirectory builds (`playbook.py` points the content source at the git root) and can publish with GitHub Pages. The author wants create to set up an Antora guide inside an existing repository that **documents that repository** (option B below), not one that merely lives there.

## Decisions Made

1. **Scope: the guide documents its host repository** (the embedded semantics), not only a guide stored in a subdirectory whose sources are elsewhere. Considered and set aside: "A, the guide only lives there" (create's separate-guide flow aimed at a subdirectory, no `self` source).
2. **README: the guide owns one section of it.** A marker-delimited Markdown region in the host README, written and verified by the guide like a page (what the project is, who it is for, links into the site per persona); the rest of the README stays the author's. Hand edits and drift are detected as for the gfm front page. The region is authored directly in Markdown: `publish.py` only relinks Markdown and there is no AsciiDoc to Markdown rendering. Set aside: README untouched except a link (drifts from the guide); README fully guide-owned as in gfm mode (takes the README from the author, Markdown front page for an AsciiDoc guide).
3. **Links from host files into the guide point at the published site.** Stubs for consolidated docs and the README region link to `<site URL>/<component>/<page>.html`; Antora's output paths are deterministic, so checks verify these links offline against the page list. A site URL is required, but not GitHub Pages: a repository that already serves its project website with Pages enters another host's URL and skips the Pages workflow. Set aside: links to `.adoc` blobs on GitHub (xrefs, includes, attributes do not resolve there); both forms (doubles every link and check).

## Approaches (not yet chosen)

- **A: one embedded mode with two front page kinds (recommended).** The `embedded` block gains a front page kind (whole README for gfm, README region for Antora). A separate `is_embedded()` replaces the seven call sites that use "has a front page" as the embedded test. Format-specific behavior sits behind one front page layer, as FR-005 of `specs/005-embedded-guide` already required: region vs whole README, ownership check, stubs with site URLs, retargeting, structure checks that keep `nav.adoc`. Reused unchanged: `self` source and fingerprint drift, pull request check, move plan, `confidential.local.yaml`, Pages setup. Existing gfm tests stay green.
- **B: standalone subdirectory guide plus a `self` source.** No `embedded` block; any guide in a host repository can pin it as `self` and use the pull request check; the README region comes from the publish mechanism. Touches less gfm code, but consolidation, stubs, and retargeting would be rebuilt outside embedded mode, and "documents its own repository" would mean two things in the code.
- **C: a separate Antora embed module.** Dropped: duplicates the move plan, stubs, and drift code.

Size: comparable to `specs/005-embedded-guide`. Run it through the full brainstorm and spec flow.

## Code Map (read-only inventory, 2026-11-23)

Classes: N works for Antora as is, S gfm-only and can be skipped, C needs an Antora counterpart or a decision.

- **guidecfg.py**: embedded requires gfm (671-672, C); front page defaults to `../README.md` and must be `.md` (692-696, C); `embedded_front_page() is not None` is the embedded test, reused in embed.py:122, drift.py:473/630, runs.py:267, ledger.py:44, attrs.py:116, fetch.py:314 (C, needs `is_embedded()`); `pages()` appends the README (1025-1028, C); validate requires the front page (1057-1073, C); `publish` gfm-only (745-746, S or C). N: no internal part and `confidential.local.yaml`, `developer_readme`, `stubs`, `pr_check`, `self` source and `self:`/`local:` inputs.
- **embed.py**: inventory, Markdown helpers, `register_inputs`, developer README (N); README must become the front page in the move plan (580-589, 658-685, C); `apply` writes region markers (749-782, C); stubs link to the front page (832-841, 903-904, C: site URL); `retarget` rewrites Markdown links to host paths (917-962, C); `front-page-status` (968-1009, N for a region); `stage` (1044-1123, S: gfm Makefile only).
- **fetch.py**: `self` snapshot, `where self`, fingerprints, rebaseline (N); `self_cited` parses source blocks in the adapter's comment style, so a Markdown README region in an Antora guide is never read (290, C); front page blob (304-322, N or S).
- **drift.py**: fingerprint mode, linking pages, `--pr` (N); gated on the front page (473, 630, C, small).
- **check.py**: embedded navigation is the README only, replacing `nav.adoc` (408-412, C); absolute blob links (604-643, C: site URLs); ownership comment (646-684, C); stub checks (713-741, C); one source block style per adapter (952, 996, C: per-file style); self-citation and fingerprint warnings (N).
- **Elsewhere**: `sources.py:166` recognizes the front page only for the `html` style (C); `attrs.py:116` rewrites README attribute regions but the Antora Makefile has no regions step (C or S); `publish.py:59-69` relinks Markdown only (C or S); `region.py` markers (N); `guide-pr-check.yml` (N); `scaffold-project.sh:42-46` refuses non-gfm `--embedded` and line 53 installs the gfm pointer page (C); `playbook.py` subdirectory builds (N).
- **Skills and docs**: create sections 3, 4, 5, 5a, 10 fix the format to gfm and treat the README as start page and navigation (C); evolve section 8 hand edits, impact set, retarget (C) and 3a refuses embedded guides (C); `page-task/front-page-contract.md` assumes a Markdown README throughout (C); `EMBEDDED_RULES` in `global-constraints.template.md`, `page-task/SKILL.md`, `page-procedure.md` (C); `guide/docs/embedded.md` (mostly C, the `self` and pull request check parts N).
- **Specs**: `specs/005-embedded-guide` FR-004/005 (gfm only), FR-008/008a (README is front page and navigation), FR-009 (front page prints first), FR-010/010a (links resolve on GitHub), FR-023 (stubs), FR-029 (Antora unchanged); `specs/006-*` FR-006/016 (publish gfm first), FR-015 (exports print the front page).
- **Tests encoding gfm assumptions**: `test_guidecfg.py` (embedded requires gfm, front page location, pages include front page, publish and pages format rules); `test_scaffold_project.py` (pointer page, refuses other formats); `conftest.py:115` `make_embedded_guide` is gfm, so every embedded test in `test_check.py`, `test_drift.py`, `test_fetch.py`, `test_attrs.py`, `test_ledger.py` is gfm-only; `test_embed.py` (stage, author region, stubs and retarget, front-page-status).

## Open Questions

- Which approach (A recommended, see above).
- Page set: does the README region join the Antora page list (then source block style per file in `sources.py`, `check.py`, `fetch.py`), or is it a separate artifact with its own checks?
- Navigation: `index.adoc` and `nav.adoc` stay the navigation; how does `check.py --structure` cover the README region (persona links, ownership marker)?
- Region placement: where the region goes in an existing README (author picks, or after the title and badges), and what happens with a README that has no natural place.
- Site URL source: `pages.url` when Pages is used, a new key otherwise; required before the first page task, since stubs and the region link to it.
- Consolidation: which host documentation is absorbed into `.adoc` pages (converted by page tasks from Markdown, reStructuredText, AsciiDoc inputs) versus kept; stub format for removed non-Markdown docs.
- Existing documentation site in the host (MkDocs, Sphinx, Antora): replace, keep, or refuse.
- GitHub Pages: optional or default; interaction with an existing project site (`/guide:evolve --pages` refuses embedded guides today).
- Exports: does the PDF include the README region (specs/006 FR-015 prints the gfm front page first)?
- Scaffold: an Antora embedded overlay (no `internal` module, no `site-internal.yml`, branding asked).
- Evolve: hand edits of the region, impact set naming the README, retargeting to site URLs.
- Spec work: amend `specs/005-embedded-guide` (FR-004, FR-005, FR-008a, FR-009, FR-010, FR-029) or write a new spec that extends it.
