## Global Constraints

<!-- Rendered by the create and evolve skills into the guide plan (docs/guide/plan.md)
     and into the plan workspace as global-constraints.md. Fill every {{...}} from
     guide.yaml, baseline.yaml, inputs.yaml, and the preflight result. -->

- Guide: "{{TITLE}}", format `{{FORMAT}}`, rigor `{{RIGOR}}`, cc-prose {{PROSE}} (present: write with the section voice profiles and run the prose check; absent: follow `style-rules.md`).
- Baseline (captured {{CAPTURED}}); every statement is verified at these commits, never at a branch head:
{{BASELINE_TABLE}}
- Baseline values available to pages (never type versions or commits): {{ATTRIBUTES}}.
- Change requests documented as experimental (label only through the adapter snippet):
{{CHANGE_REQUESTS}}
- Personas and their entry pages: {{PERSONAS}}.
- Sections and voices: {{SECTIONS}}.
- Every page starts with a source block after the title; entries are `<source-id>:<path>[:<lines>]`, `url:<url>`, or (internal pages only) `input:<input-id>`. Facts without a pinned source stay out of the page.
- Inputs are hints, never proof. Registered inputs: {{INPUTS}}. Content derived from a confidential input ({{CONFIDENTIAL_INPUTS}}) appears only on internal pages.
- Shareable pages never contain: {{CONFIDENTIAL_TERMS}}, text matching {{CONFIDENTIAL_PATTERNS}}, or links into the internal part ({{INTERNAL_ROOT}}).
- No em dash or en dash characters in any file.
{{FORMAT_RULES}}
- Admonitions: only NOTE, TIP, IMPORTANT, WARNING, CAUTION, with their fixed meanings (see `page-procedure.md`).
- Task pages: a why-paragraph, numbered steps with copy-paste commands, `Check:` lines with expectations.
- The start page and the section overview pages follow `overview-contract.md`: why before how, the spec's `## Why` card as their content, every product defined from its own pinned source, and the cold-reader test as their review gate.
- Diagrams follow the diagrams skill. Every label, arrow, and frame is a claim with a source in the diagram's claims file (`diagrams/<name>.claims.yaml`); where a product runs its parts comes from its own architecture documentation at the pinned version. Palette: platform gray (`#e9ecef`/`#495057`), governance orange (`#ffe8cc`/`#e8590c`), admin red (`#ffe3e3`/`#c92a2a`), user blue (`#d0ebff`/`#1971c2`); text and legends `#495057`.
- Run every command from the guide project root with path arguments; never `cd` into `.guide/cache/`.
- Containers: `podman`, never `docker`. Python packages: `uv`, never pip.
- Commit messages end with the trailer `Assisted-By: 🤖 Claude Code`. Only the controller pushes, and only when the author opted in ({{PUSH}}).
{{EXTRA_RULES}}
