# {{TITLE}} style guide

Project terms and rules that every page follows, on top of the built-in style rules (or the cc-prose voice profiles when cc-prose is installed). Page implementers and reviewers read this file. Keep one rule per bullet.

## Terms

- "{{TERM}}" means {{MEANING}}. It is a domain term; prose-check hits for this sense are false positives.
- Product names are spelled exactly: {{PRODUCT_NAMES}}.
- Persona names: "{{ADMIN_PERSONA}}" and "{{USER_PERSONA}}".
- Capitalize Kubernetes kinds: Pod, ConfigMap, Secret, Service, Namespace, Deployment.

## Rules

- No em dash or en dash characters.
- AsciiDoc pages: one sentence per line.
- Versions and commits come from the baseline attributes, never typed.
- Task pages: a short paragraph on why, then numbered steps, then a `Check:` line with the expected result.
