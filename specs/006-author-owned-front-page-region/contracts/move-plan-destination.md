# Contract: move-plan destination `author-region`

Extends the embedded-create move plan of spec 005 (`.guide/runs/<run-id>/move-plan.yaml`) with one destination value.

## New destination

`author-region`: the entry's section of the root Markdown README stays in place as author-owned text above the guide region. Valid only for:

- `path` = the root Markdown README (the file the front page replaces)
- `section` = a non-null heading title
- `stub` not set (cannot combine with a stub)

## Semantics

- Classification default (FR-012): landing-oriented sections (pitch, context, usage examples) default to `author-region`; instructional material keeps its defaults (`input`, verified as guide input; `developer`, moved). The author can change any destination before approval, as today.
- On `apply`: the retained sections' text stays byte-identical; the plan writes `<!-- guide:region -->` and `<!-- /guide:region -->` immediately below the last retained section. The front page task then writes the guide region between the markers.
- Nothing from an `author-region` section is registered as guide input, verified, rewritten, or dropped (FR-013): the run summary never lists claims from it.
- The existing root-README constraint (its only destinations are `input`, `developer`, and now `author-region`) still holds; a non-Markdown root README keeps today's rules (input plus remove/relocate, no author region).

## Plan file shape

```yaml
entries:
  - path: README.md
    section: "Why this exists"
    destination: author-region
  - path: README.md
    section: "Installation"
    destination: input
```

Validation errors use the existing move-plan validator's message style (path, section, problem).
