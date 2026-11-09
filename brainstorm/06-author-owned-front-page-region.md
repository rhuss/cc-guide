# Brainstorm: Author-owned region on the generated front page

**Date:** 2026-11-09
**Status:** active

Seed captured from work on the aprofile repository, where the root README is generated from the guide's introduction page. Continued and decided in the same day's session.

## Problem Framing

When a guide owns the repository's root `README.md`, the README becomes the guide's introduction: written for a reader who already decided to use the tool. A stranger who lands on the repository needs something else first: the wider context (which problem space this lives in, what the tool is for, why it exists), the idea in a few sentences, and a handful of short usage examples that show the value. Today the README jumps straight into the guide.

In aprofile this shows up concretely. `docs/guide/scripts/sync-readme.py` (a project-local precursor of the publish mechanism) rewrites the whole `README.md` from `docs/guide/docs/README.md`, and `--check` fails on any difference. Every hand-written line in the README is lost on the next `make -C docs/guide readme`. The project wants a top section on "managing coding agent harnesses" with before/after examples (named wrappers per account, an endpoint profile for a local model, two profiles continuing one conversation) above the guide's own introduction.

Embedded mode (brainstorm #05, spec 005) has the same gap at a larger scale: FR-008 makes the root README the guide's front page, FR-009 treats it as a guide page with a sources block and reviews, and FR-009a makes `evolve` report hand edits and never keep them silently. FR-010a keeps badges and the project logo at the top unverified, already a small author-owned enclave, but a special case. There is no general place on the front page that the author owns.

Success: the root README can carry an author-owned landing section (pitch, context, examples, badges) that the guide never rewrites or verifies line by line, followed by a guide-owned region that `create`, `evolve` and the checks keep current exactly as today. The mechanism is general: any gfm guide publishing a README gets it, not just embedded guides, and aprofile can migrate onto it.

Failure even if it technically works:
- Author text and guide text drift apart silently (the author region contradicts the guide region or the code, and nothing notices).
- The marker scheme leaks into every guide even when no author region is wanted.
- `evolve` or the checks start flagging normal author edits as drift.
- The front page loses the overview guarantees (why card, cold-reader test) because the guide region becomes a fragment.

## Approaches Considered

### A: One unnamed marker region, as a general publishing mechanism (chosen)

A README carries one guide-owned region between HTML comment markers, following the existing `guide:attr` generated-region convention family. Everything outside the markers belongs to the author.

- Any gfm guide can declare a publish target: a designated guide page is rendered with rebased links into the region of a README outside the content root (aprofile's `sync-readme.py` model, moved into the toolkit).
- Embedded mode keeps spec 005's model: the root README *is* the front page, and the page task, sources block, reviews, and structure checks operate on that file, narrowed to the region.
- Shared machinery for both consumers: marker parsing, region-scoped check / drift / hand-edit detection, link rebasing.
- Pros: one file, author edits it freely on GitHub; the guide keeps full control and verification of its part; backwards compatible (no markers means the whole file is guide-owned, as today); FR-010a's badge special case dissolves into ordinary author text; aprofile deletes its script.
- Cons: author text is unverified and can drift (mitigated by advisory contradiction flags only); markers are visible in the raw file; position of the region is fixed by the author.

Sub-decision considered within A: whether embedded mode should move to the publish model too (front page source inside the guide, README a pure output). Rejected: spec 005 was just implemented around README-is-the-page (FR-008a TOC pointer, structure checks, sources block), and the publish model would reintroduce a visible second front page inside the guide subdirectory. The split (embedded in-place, plain guides publish) shares everything that matters.

### B: Author intro file composed into the front page

An author-owned file (for example `guide/front-intro.md`) is prepended by the writer.

- Pros: clean separation, no markers in the README.
- Cons: two files to edit for one page; editing the README on GitHub does the wrong thing; harder to explain.

### C: Put the context into the guide's overview contract

Extend the front page contract so the guide itself writes a "context and examples" section (verified, cited).

- Pros: everything verified.
- Cons: pitch and positioning are an author's voice, not a source fact; `evolve` would rewrite them, which is exactly what this feature exists to prevent.

## Decision

Approach A, as a general mechanism for any gfm guide publishing a README, with these agreed points:

- **One unnamed guide-owned region per file.** Every use case so far needs exactly one (author pitch above, guide content below); named regions would add config and error cases for no concrete second use. The author chooses the region's position by placing the markers.
- **Scope is general, not embedded-only.** Plain gfm guides get the publish model (designated page rendered with rebased links into the region); embedded mode keeps README-is-the-page from spec 005, writing its region in place. One toolkit mechanism, two consumers.
- **Embedded create offers "stays as the author region" as a default move-plan destination** for landing-oriented sections of an existing hand-written README (pitch, context, usage examples), unverified and in the author's voice. Instructional material still goes through verification as guide input.
- **Author region verification is link checks plus advisories, nothing more.** Link checks cover the whole file (author links into the guide must resolve). No claim verification, no code-block validation of author text. When a page task or review touches the front page (or the published region's source page), the brief tells the reviewer to read the author region and flag contradictions as a non-blocking finding in the run summary. Nothing in the author region ever fails a build.
- **Sources block sits inside the region** (it belongs to the guide-owned content).
- **Exports:** in embedded mode the front page prints first in PDF and site exactly as today, whole file including author text. For a plain guide, the author region exists only in the README, so exports never see it.

## Key Requirements

- No markers present: behavior unchanged (whole front page guide-owned).
- Markers present: only the region is generated, checked, reviewed and drift-detected; text outside is never modified by any guide command.
- One unnamed region per file; marker syntax follows the existing `guide:attr` generated-region convention family (exact spelling is a spec decision).
- Any gfm guide can declare a publish target: a designated page, a target README outside the content root, region-scoped write and check. Without the declaration, nothing changes.
- Embedded mode narrows spec 005's front-page machinery to the region: FR-009's page task and checks, FR-009a's hand-edit reporting, FR-013/FR-014 drift. FR-010a's badges become ordinary author-region text.
- Embedded create's move plan (FR-016 through FR-019) gains "stays as the author region" as a default destination for landing-oriented sections.
- The guide region keeps the front page contract (why card, cold-reader test, navigation) on its own, so it reads correctly when the author section is short or missing.
- Link checks still cover the whole file.
- Reviewer briefs for front-page work include reading the author region and flagging contradictions as non-blocking findings.
- aprofile migration path: replace `sync-readme.py` and the `make readme` / `check-readme` targets with the toolkit publish mechanism.

## Open Questions

- Exact marker spelling and the ownership comment: what the guide-owned comment at the top of the file says for plain guides (the FR-009a analog), and whether the region markers themselves carry instructions.
- Config shape of the publish declaration: guide.yaml key, source page, target path, defaults.
- How `--check` and drift report a missing, unbalanced, or duplicated region: error, warning, or silent whole-file fallback.
- Whether the mechanism stays gfm-only for now or the adapter contract gains a general "publish" capability other formats can implement later (proposal: gfm-only in v1, my call).
- Interaction with FR-010a's package-registry inventory: when a registry publishes the README, absolute links in the guide region are the guide's job; do the checks also warn about relative links in the author region, or is that the author's alone?
