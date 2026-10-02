# Final review addendum: whole guide

This addendum extends the superpowers `requesting-code-review` dispatch for the final review of a guide run (FR-013). The per-page reviews already checked each page against its sources; this review looks at what no single page review can see. Read `global-constraints.md` and `page-review-guide.md` in this directory first; their rules and severity calibration apply.

## Inputs (paths are in your dispatch)

- The guide spec (`docs/guide/spec.md`) and plan (`docs/guide/plan.md`).
- The review package for the whole run (base of the first task to the current head).
- The progress ledger's deferred minor findings and parked findings (listed in your dispatch).
- The built sites: `build/site` (shareable) and, when the internal part is enabled, `build/site-internal`.

## What to check

1. **Cross-page consistency.** The same thing has the same name, value, and spelling on every page: ports, namespaces, file paths, target names, defaults, version attributes, persona names. Two pages that disagree are Important, even when each matches a source (then one of them cites the wrong location or a different revision).
2. **Persona journeys.** Walk each persona from its entry page (`personas[].start` in `guide.yaml`) to the end of its section, following only the links on the pages:
   - every step the persona needs is reachable in order
   - no page assumes access the persona does not have (for example a user page that needs cluster-admin commands)
   - prerequisites are stated before they are needed
   - each journey ends with a working result and a check
3. **Shareable and internal boundary.** Nothing from the internal part reaches the shareable part: no links into it, no confidential terms or patterns, no content whose only support is a confidential input. Run `uv run tools/guide/leakcheck.py build/site` and read the result. Also check the reverse: the internal part does not duplicate shareable pages in ways that will drift.
4. **Experimental content.** Every experimental label matches a change request in `baseline.yaml` with the right tier and anchor, and nothing in-review is described as if it were released.
5. **Guide-wide prose.** Consistent voice per section, no repeated introductions, no filler. Skip the prose AI-pattern check in this pass (it ends the turn and adds little at this scale).
6. **Deferred minors.** For each deferred minor and parked finding from the ledger, decide: fix now (list it under Important or Minor with the fix), or accept with a reason. Every accepted one needs a one-line ruling the controller records. A deferred finding that ends up with neither a fix nor a ruling blocks the wrap-up; the controller checks this table against the ledger for completeness.
7. **Sampled facts.** Pick at least ten statements across different pages that the per-page reviews did not list in their spot-check tables and verify them against the pinned sources. Count a statement as supported only when a cited source states it; an added unit, an inferred side effect, or general advice counts as unsupported.

## Rules for you

The rules of `page-review-guide.md` apply: read-only, commands from the guide project root with path arguments, never `cd` into `.guide/cache/`, cite `file:line` for every finding, and name the source location for every factual correction.

## Output

Use the output format of `page-review-guide.md`, with these extra sections before "Assessment":

### Persona Journeys
One short paragraph per persona: path taken, gaps found.
### Boundary Check
The leak check result and anything found by reading.
### Deferred Minor Adjudication
| Finding | Decision (fix now / accept) | Reason |
|---|---|---|

The controller applies the fixes in one fix round, re-verifying every factual correction against the pinned source first, then runs `make check`.
