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
