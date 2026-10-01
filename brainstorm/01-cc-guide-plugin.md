# Brainstorm: cc-guide plugin for source-verified guides

**Date:** 2026-10-01
**Status:** active

## Problem Framing

The SAW guide in this repository was built from walkthrough transcripts, chat context, a Jira board, and two source repositories (SAW and OpenShell). The process worked: every page was verified against pinned sources, per-task reviews caught a factual error in nearly every page, a baseline file made later updates possible, and the run surfaced real upstream problems (filed as validatedpatterns-sandbox/secure-agent-workspace#58 and #59). But the process lived in one session: rulings, review guides, check scripts, and diagram rules were improvised and are not reusable.

The goal is a Claude Code plugin, `cc-guide`, that turns this into a repeatable method: create a comprehensive, persona-split guide from heterogeneous inputs with systematic source verification, and evolve it over time against a recorded baseline. It should follow the structure of the other `cc-` plugins (for example `rhuss/cc-prose`) and the usual Claude Code plugin conventions.

## Approaches Considered

### A: Orchestrate superpowers (chosen)
cc-guide drives the superpowers flow (brainstorming, writing-plans, subagent-driven-development, final code review) and contributes everything guide-specific: intake, templates, adapters, checks, diagram rules, preview, live validation, and upstream findings.
- Pros: reuses the flow that produced the SAW guide; small plugin surface; per-task reviews come for free.
- Cons: coupled to superpowers internals (skill names, `task-brief` and `review-package` scripts); needs a version check and fallbacks.

### B: Self-contained pipeline
cc-guide implements its own phases and uses superpowers only for discipline skills.
- Pros: full control, stable across superpowers releases.
- Cons: duplicates subagent-driven development; more to maintain; does not treat superpowers as the real dependency.

### C: spec-kit/spex based
Each guide is a spex project (specify, plan, tasks, implement, gates).
- Pros: the user's own ecosystem.
- Cons: spec-kit is software-oriented; per-page tasks with factual source checks fit awkwardly; heavier per run.

## Decision

Approach A. The repository `rhuss/cc-guide` contains the plugin `guide`, structured like `cc-prose` (marketplace manifest at the root, plugin directory with `commands/`, `skills/`, `scripts/`, `docs/`, a Makefile, and an eval suite). Superpowers and the Excalidraw MCP server are runtime dependencies, detected at command start with install hints, since plugin manifests have no dependency field.

## Key Requirements

### Commands
- **create**: intake (transcripts, source repos, Jira, URLs, chat notes), personas and voice layers, then spec and plan through superpowers brainstorming and writing-plans, then subagent-driven execution with per-task reviews and a final whole-guide review.
- **evolve**: baseline diff of every pinned source, impact analysis through each page's `// Sources:` block, intake of new inputs (for example new transcripts), targeted page tasks with reviews, then a new baseline. Re-baselining never happens mid-run.
- **preview**: build with the active adapter and serve locally with live reload, also usable mid-run on finished pages.
- **validate**: opt-in live-cluster validation in two tiers. The read-only tier runs every `Check:` command against a named kubeconfig. The full tier executes install and onboarding recipes end to end, only on a cluster marked disposable, with each mutating command confirmed. Results come back as review findings.
- **upstream**: findings about the source repos (doc drift, bugs, confusing naming or UX) are drafted, re-verified against the current default branch, shown in full for approval, then filed as issues. Small mechanical fixes (doc drift, typos, stale versions) may also become a PR from a fork; naming and UX changes stay issues with a proposal. Public issues never contain Jira keys, customer names, internal links, or links to private repos.

### Renderer adapters
- One adapter contract: scaffold, attribute or variable injection from `baseline.yaml`, admonitions (including the experimental labels), optional shareable/internal split with a leak check, build, content checks, preview, and `dist` tarballs.
- v1 ships three adapters: Antora (AsciiDoc), MkDocs Material (Markdown), and plain GitHub Markdown. Hugo is out of scope for v1.

### Rigor profiles
- `--rigor fast|standard|strict`, default `standard`.
- standard: per-page `// Sources:` blocks, per-task review with factual spot-checks against the pinned sources, screenshot review for diagrams only, final whole-guide review.
- strict: adds the claim ledger with claim IDs and verification items.
- fast: final review only.

### Verification and process assets
- `baseline.yaml` pins every source by commit SHA (and records open PRs with head SHAs); `make baseline-diff` drives `evolve`.
- Templates for the page procedure, the page review guide, and global constraints; rulings are recorded in a ledger with cost-if-wrong and reported at the end.
- In-flight upstream PRs can be documented as experimental, in two tiers (merged on main, in review), through admonition partials.

### Excalidraw diagrams
- Prefer curved arrows; keep arrows clear of notes and labels.
- Fixed semantic palette (no default `#1e1e1e` legend text outside it); one text element per container (remove duplicate bound texts before export).
- Screenshot self-review of every diagram (Playwright or the MCP screenshot), export to SVG and PNG, keep `.excalidraw` sources.
- Back up the user's canvas before drawing and restore it afterwards; pre-authorize the Excalidraw MCP tools so permission prompts do not stall a subagent.

### Learnings and recommended settings (`docs/learnings.md`)
- Per-task reviews are the most valuable gate: they caught swapped Route purposes, a pseudo-config value, collapsed RBAC tiers, wrong citations, and more.
- Reviewers can be wrong too: the controller re-verifies a disputed finding against the source before applying it (the final review proposed `openshift-gitops`; SAW's own scripts use `vp-gitops`).
- Re-verify upstream findings on the current default branch before filing, and test behavior claims empirically: two of four issue candidates were wrong (an intentional version cap; GNU make exports command-line variables).
- Run every command against pinned sources from the repo root with path arguments; never `cd` into or run git against partial-clone caches (a repeatable subagent stall). Read PR heads through `gh api .../compare`.
- A `prose:check` invocation ends a subagent's turn: resume with a standard finish message, and skip it for table-heavy reference pages and the final pass.
- The per-claim ledger was overkill for most runs; per-page `// Sources:` blocks keep most of the value.
- Attribute injection instead of hard-coded versions; listings that use attributes need `subs="attributes+"`, and `${VAR}` in a listing breaks a warn-level build.
- Content gates as scripts: one sentence per line (AsciiDoc), no em or en dashes, no internal xrefs or Jira on shareable pages, leak check on the built site.
- Transcript quotes must be verbatim, or paraphrased without quotation marks.
- Small, source-verified fixes can be applied by the controller directly instead of a fix dispatch plus re-review.
- Pushes fail while the 1Password SSH agent is locked; check before a push.
- Recommended settings: the most capable model for the controller session (this run: Opus 5.5), subagents inherit it (no `model` parameter); effort `high` for create and evolve, `xhigh` for strict rigor; an allowlist for `gh`, `make`, `node`, and the Excalidraw MCP tools rather than bypassing all permissions.

## Out of Scope (v1)

- Hugo adapter.
- Hosting or publishing the site.
- Google Docs export.
- Screenshot review of text pages.

## Open Questions

- How does cc-guide detect superpowers version drift (renamed skills or scripts), and what is the fallback?
- How are the three adapters' admonition and experimental-label partials expressed in Markdown without Antora's attribute and partial features?
- Where does the guide repository's `.superpowers` workspace live, and what survives after a run (ledger and reviews are useful for the next `evolve`)?
- How does `validate` map a `Check:` command to an expected result, and how are cluster credentials passed safely to subagents?
- Should `upstream` support GitLab and Jira targets in v1, or GitHub only?
- How are effort and model recommendations applied: documented only, or checked at command start with a warning?
- What does the eval suite for the plugin look like (fixture repos with known drift, expected findings)?
