# Idea Inbox

Ideas captured from code reviews for future brainstorming.

### drift-check-flag-only-mode

- **Source**: deep-review
- **Date**: 2026-10-01
- **Reference**: 001-cc-guide-plugin
- **Summary**: `drift.py --check` accepts a flag that selects its only mode.

> The contract and the scheduled workflow call `drift.py --check`; decide whether drift gets other modes (for example a JSON-only machine mode) or the flag becomes implicit.

### offline-pdf-printing

- **Source**: deep-review
- **Date**: 2026-10-01
- **Reference**: 001-cc-guide-plugin
- **Summary**: The PDF printer blocks remote fonts, scripts, and styles but still loads remote images.

> Fully offline printing would make PDFs reproducible and avoid outbound requests during export, but guides with remote images would then fail; an opt-in offline mode or a rule that guide images are local could settle it.

### node-script-unit-tests

- **Source**: deep-review
- **Date**: 2026-10-01
- **Reference**: 001-cc-guide-plugin
- **Summary**: print-pdf.mjs, preview-watch.mjs, and shoot.mjs are covered only by shell smoke tests.

> Unit tests for title page content, TOC grouping, landscape pages, link rewriting, and the watcher's queue would catch regressions the happy-path smoke tests miss.

### shared-link-regex-looseness

- **Source**: deep-review
- **Date**: 2026-10-01
- **Reference**: 001-cc-guide-plugin
- **Summary**: The shared Markdown link regex matches any `](path)`, slightly looser than the old check.py pattern.

> Unifying the link syntax for check and drift removed a divergence; if stray `](...)` text produces false broken-link reports, add a stricter variant for the broken-link check.

### guidecfg-branding-coupling

- **Source**: deep-review
- **Date**: 2026-10-07
- **Reference**: 002-antora-branding
- **Summary**: guidecfg imports the branding module at load time, and branding.py keeps its own guide.yaml and adapter.yaml readers.

> The core loader now depends on a feature module while loader logic is duplicated with slightly different defaults; a lazy import in validate() and one shared reader would keep the dependency direction clean.

### branding-facts-shared-with-node

- **Source**: deep-review
- **Date**: 2026-10-07
- **Reference**: 002-antora-branding
- **Summary**: print-pdf.mjs and preview-watch.mjs hard-code the branding output layout, the band color, and the path-valued keys that branding.py owns.

> Publishing these facts from branding.py (for example a band color and an input list in branding.json, or a `branding.py paths` subcommand) would leave one source of truth when keys or layouts change.

### one-build-guard-per-format

- **Source**: deep-review
- **Date**: 2026-10-07
- **Reference**: 002-antora-branding
- **Summary**: The FR-010 "validate before the generator runs" guard lives in three unrelated modules (playbook.py, mkdocs_macros.py, attrs.py regions).

> Unchanged Makefiles force the design; a single `branding.guard(root)` helper and a table of hook points in docs/adapters.md would make a fourth adapter or entry point harder to forget.

### reference-table-generation

- **Source**: adoption
- **Date**: 2026-10-13
- **Reference**: saw-guide-adoption
- **Summary**: The SAW guide's retired gen-reference.sh auto-generated per-chart reference tables (key, default, meaning) from each chart's values.yaml at the baseline; cc-guide has no equivalent.

> The generator paired a hand-maintained meanings file (one reference-voice sentence per value, derived from the values.yaml comment) with the chart defaults to emit include-able reference partials, keeping a large "chart values" reference page in sync with the pinned sources. After adoption those partials become hand-maintained and drift from the baseline silently. A toolkit feature (for example `tools/guide/reference.py` rendering `reference-meanings.yaml` + source values into partials, checked by `make check`) would restore single-source reference tables for config-heavy guides.

### citation-repointing-on-bump

- **Source**: adoption
- **Date**: 2026-10-13
- **Reference**: saw-guide-adoption
- **Summary**: The SAW guide's retired repoint_sources.py mechanically shifted cited source line ranges after a baseline bump and flagged only citations whose lines genuinely changed or whose files moved for human re-verification; evolve re-verifies every impacted page via subagents but does no mechanical line-shift.

> On a bump where most cited files only shifted by a few lines, a mechanical re-pointer (diff old->new commit, shift unchanged hunks, mark REVIEW for changed/deleted) sharply narrows what a human or subagent must re-check, and keeps `// Sources:` line ranges accurate without a full re-read. A `tools/guide/repoint.py` run before the evolve page tasks would cut evolve cost on large, slow-moving guides.

### reader-facing-prose-no-process-narration

- **Source**: author-review
- **Date**: 2026-10-27
- **Reference**: cc-rosa-guide
- **Summary**: Generated pages narrated the guide's own creation in rendered prose: claim-ledger references ("every claim traces to a source recorded in the claim ledger"), pinned commit hashes ("the plugin is described at commit X"), and an "internal knowledge" marking convention repeated on dozens of facts.

> The strict-rigor machinery (claim ledger, pinned sources, registered inputs) is maintainer-facing and already lives in non-rendering `//` source comments and the ledger page, but nothing stops it from leaking into reader-facing prose. A reader cares what the guide states and how much to trust it, not how the guide was verified. Worth adding to the toolkit: page-task brief guidance that provenance belongs in `//` comments only, plus a check (guide-rules forbid patterns such as "claim ledger", "internal knowledge", or commit-short attributes outside the Baseline note) so the leak fails `make check`. Uncertainty should surface as a reader-relevant hedge ("unconfirmed", "reported by the team") rather than a provenance label. The Baseline note stays as the single standardized statement of covered versions. Fixed by hand in the cc-rosa guide (16 files); the idea is to make the toolkit prevent it.
