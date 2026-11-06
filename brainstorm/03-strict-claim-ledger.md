# Brainstorm: Strict rigor without a claim ledger

**Date:** 2026-10-15
**Status:** parked

## Problem Framing

A `/guide:create` run with `--rigor strict` reported:

> Strict mode needs a claim ledger page, internal/modules/internal/pages/claim-ledger.adoc, which the plan never created.

The controller blamed its own plan, but the cause is in the plugin:

- `make check STRICT=1` runs `tools/guide/ledger.py`, which requires the ledger at `<internal_root>/modules/internal/pages/claim-ledger.adoc` (Antora) or `<internal_root>/claim-ledger.md` (MkDocs, gfm). A missing file fails with `ledger not found: <path>` (`guide/toolkit/ledger.py:138`).
- Nothing creates that file: not the adapter scaffold, not create's project setup (section 5), not the plan instructions (6d), not the `guide:page-task` setup. Only `tests/toolkit/test_ledger.py` writes one.
- Nothing tells anyone to fill it. `page-procedure.md` only says to run `make check STRICT=1` under strict rigor, while `page-review-guide.md:23` rates a verifiable statement without a ledger row as **Important**. So even with an empty file in place, every strict page review fails.

Strict rigor is therefore half built: the checker and the reviewer expectation exist, the producer does not.

## Workaround for a running guide

Create the empty ledger by hand; an empty table passes `ledger.py`:

```asciidoc
= Claim ledger

[cols="1,4,2,3,1",options="header"]
|===
|ID
|Claim
|Page
|Source
|Status

|===
```

Page tasks then add rows: `C-<AREA>-<nn>`, the claim, the page path without extension (or `-`), source references separated by `;`, and `CONFIRMED`, `CONTRADICTED`, or `OPEN`.

## Approaches Considered

### A: `ledger.py init` plus a page-procedure step (proposed)

1. `ledger.py init` writes the empty ledger in the adapter's format and refuses to overwrite an existing one. The `ledger not found` error gains the hint `run uv run tools/guide/ledger.py init`.
2. Create (section 5) and evolve run `ledger.py init` when the rigor is `strict`, including a `--rigor strict` override; the file is committed with the scaffold.
3. `page-procedure.md`, strict only: before the gates, add one ledger row per verifiable statement, IDs `C-<SECTION>-<nn>` continuing the existing numbering.
4. Tests: `init` for both table formats, overwrite refusal, an empty ledger passing `check`.

- Pros: small, fits the existing toolkit; the error message points at the fix.
- Cons: the ledger is one shared file every page task edits; fine while SDD runs tasks sequentially, a merge point if tasks ever run in parallel.

### B: Scaffold always ships the ledger

Every adapter scaffold contains an empty ledger, whatever the rigor.

- Pros: no rigor-dependent setup step.
- Cons: an unused internal page in every non-strict guide; still needs the page-procedure step.

### C: Ledger optional under strict

`ledger.py` treats a missing ledger as empty and only checks source blocks.

- Pros: smallest change.
- Cons: hides the gap instead of closing it; the reviewer rule still fails pages.

## Decision

Not decided. Approach A was proposed on 2026-10-15; implement on its own branch (`fix/strict-claim-ledger`), separate from spec 003.

## Open Questions

- Should the ledger page appear in the internal navigation (`internal/modules/internal/nav.adoc`), or stay an unlisted page?
- What does a guide without an internal part do with a ledger that lives in the internal root? Is the internal module built at all then?
- What is `<AREA>` in `C-<AREA>-<nn>`: the section, the page, or a free code chosen by the plan?
- Should pages reference claim IDs inline (for example in the `// Sources:` block), so `ledger.py` can check that every claim on a page has a row?
