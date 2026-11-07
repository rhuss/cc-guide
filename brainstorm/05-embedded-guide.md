# Brainstorm: Embedded guide with the README as front page

**Date:** 2026-11-07
**Status:** active

## Problem Framing

Today a cc-guide guide is its own repository. `create` refuses a non-empty directory and runs `git init` (FR-005b), every source is pinned and cloned into `.guide/cache/`, and the guide project root holds `guide.yaml`, `baseline.yaml`, `tools/guide/`, a `Makefile`, a `package.json`, and `node_modules/`.

The author wants a second mode where the guide lives inside the repository it documents, mostly existing repositories with a hand-written README. The top-level `README.md` becomes the guide's front page: it introduces the project the way the guide's overview would and leads into the persona pages and reference. Developer material (build, test, release, contributing) moves to a secondary developer README. `/guide:evolve` must keep the root README current as the code changes, exactly like any other guide page.

Success: a visitor to the repository on GitHub lands on a source-verified guide front page; the guide stays in step with the code over time, either through occasional `/guide:evolve` runs or through an optional drift check on every pull request.

Failure even if it technically works:
- The guide's machinery spreads over the host repository and collides with its own build files or Markdown.
- Old documentation links from blog posts or issues break without a pointer.
- Existing documentation is moved or deleted without the author seeing and approving the plan.
- Confidential content ends up in a public code repository.

## Approaches Considered

All approaches treat the host repository as a source named `self`, pinned to a commit like any other source. Drift counts only changes to files that pages cite, so commits touching only the guide are not drift.

### A: Guide project in a subdirectory, README mapped in (chosen)
All guide machinery (`guide.yaml`, baseline, `tools/guide/`, its own `Makefile` and `package.json`, persona pages) lives in one directory, for example `guide/`. A setting in `guide.yaml` names `../README.md` as the front page. An optional workflow runs the drift check on pull requests.
- Pros: the host repository's `Makefile`, `package.json`, and `docs/` stay untouched; commands work as for a separate guide, run from `guide/`; removing the guide means deleting one directory and restoring a README.
- Cons: check, link handling, pandoc rendering, and the PDF printer must accept one page outside the guide root; README links point into `guide/...` while links inside the guide are relative to it.

### B: Guide spread over the repository root
Configuration and tools at the root, pages under `docs/`, guide targets merged into the host `Makefile`.
- Pros: the README sits naturally at the root, so the toolkit needs few special cases.
- Cons: the guide's files mix with the project's own; collisions with the host build and `package.json`; `page_glob: "**/*.md"` sweeps every Markdown file, so evolve cannot tell guide pages from project files.

### C: Separate guide repository that publishes into the project
The guide is built as today; a sync step copies the README and pages into the project repository.
- Pros: no toolkit change for verification.
- Cons: two repositories and sync pull requests; developers cannot edit the README in place; CI in the project needs access to the guide repository; misses the goal of the guide being part of the repository.

### Dropped: guide-owned generated region inside the README
The README keeps hand-written parts and the guide owns a `<!-- guide:... -->` region (the gfm attribute-region pattern). Dropped because the author accepts the guide owning the whole README, which keeps evolve simple.

### Dropped: a separate front page next to a README variant
A slightly different README beside the guide's own front page. Dropped (Claude's call): two near-identical introductions drift apart and evolve would have to keep both in sync.

## Decision

Approach A. The embedded mode is designed format-neutral (subdirectory layout, `self` source, consolidation, optional PR drift check), and the first delivery supports gfm only, where GitHub renders the Markdown front page at the root without a build.

Antora and MkDocs embedding is a recorded follow-up. Embedding itself fits both (Antora reads a component from a subdirectory of a code repository; most MkDocs projects keep `mkdocs.yml` and `docs/` beside the code). Their only new piece is the README: GitHub does not render Antora xrefs, attributes, and includes, or MkDocs admonitions, macros, and tabs, so for those formats the README would be a short plain-syntax landing page (what the project is, one install line, a link to the published site) instead of the front page itself.

## Key Requirements

1. **Embedded mode** for gfm guides: the guide project lives in a subdirectory of the documented repository (default `guide/`, Claude's proposal), and the root `README.md` is the guide's front page.
2. **README as front page**: one page, not two (Claude's call, see above). It carries a sources block, gets the same reviews as other pages, and evolve updates it when cited files change. It takes over the navigation role of the gfm table of contents (reading order, links to each persona's entry page); print order for the PDF stays in its own file.
3. **Self-source**: the host repository is a pinned source `self`; verification uses the pinned commit, never an uncommitted working tree. Drift considers only cited files.
4. **Consolidation of existing documentation** (create in an existing repository): inventory the README, `CONTRIBUTING.md`, any `docs/` tree, and loose files such as `INSTALL.md` or `USAGE.md`, then classify each piece:
   - user-facing material becomes input for guide pages; its claims are verified against the code, never copied;
   - developer material moves into a developer README linked from the front page;
   - claims the code contradicts are dropped and listed (candidates for the existing upstream findings flow).
5. **Move plan approval**: create shows the full plan (what moves where, what is removed) and acts only after the author approves (Claude's call, consistent with cc-guide's approval rule for destructive steps). Git history keeps the originals.
6. **Stubs for removed paths**: every removed documentation path keeps a one-line stub saying the content moved, with a link to the new page. The guide checks accept stubs and do not report them as orphans.
7. **LICENSE stays at the root** (GitHub license detection only looks there). `CONTRIBUTING.md` may move to `.github/` or `docs/`, where GitHub still finds it.
8. **Input rule exception**: today create refuses inputs located inside the guide project. In embedded mode the repository's own documentation may be registered as input while it is being consolidated.
9. **No internal part in embedded mode** (Claude's call): an internal part inside a code repository, often public, is a leak risk. Guides that need internal pages stay separate repositories.
10. **Optional CI drift check**: offered during setup, default off. On each pull request it flags changes to cited files that come without a guide update.
11. **Format-neutral design**: nothing in the mode's design assumes gfm beyond the README front-page mapping, so Antora and MkDocs can follow with a landing-page README.

## Out of Scope

- Antora and MkDocs embedding in the first delivery (follow-up, see Decision).
- Internal pages in embedded mode.
- A guide-owned generated region inside a hand-written README.
- Converting an existing separate guide repository into an embedded one.

## Open Questions

- Name of the `guide.yaml` setting for the front page, and the default subdirectory name.
- Whether the `self` source is fetched from the local repository (clone of the local path) or from the remote.
- Stub file format, and whether stubs ever expire.
- Name and location of the developer README (`DEVELOPMENT.md` at the root, or under `.github/`).
- Whether the CI drift check fails the pull request or only comments on it.
- How a pull request that intentionally updates both code and guide moves the baseline (`self` pin) forward.
- How `create` detects that it runs in an existing repository and switches from the empty-directory rule (FR-005b) to embedded mode.
- How the page conventions and link checks handle links from the root README into `guide/` and back.
