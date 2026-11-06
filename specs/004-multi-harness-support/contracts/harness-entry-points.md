# Contract: Harness entry points

Defines the entry point each harness reads and the invariant they share. Modeled on `cc-review/review/.codex-plugin/`, `cc-review/review/opencode/`, and superpowers 7.0.0.

## Claude Code (existing, unchanged)

- `guide/.claude-plugin/plugin.json` and `guide/commands/*.md` (thin wrappers: run `guide:preflight`, then `guide:<name>`).
- Repo-root `.claude-plugin/marketplace.json` lists the plugin.
- Behavior and output MUST match the pre-feature baseline (FR-012).

## Codex (new)

- `guide/.codex-plugin/plugin.json`:
  ```json
  {
    "name": "guide",
    "version": "<same as .claude-plugin>",
    "description": "<same>",
    "author": { "name": "Roland Huss", "email": "rhuss@redhat.com" },
    "license": "MIT",
    "skills": "./skills/"
  }
  ```
- Codex discovers the skills under `guide/skills/`. No command layer is added: the `create`/`evolve`/`preview`/`export`/`validate`/`upstream` skills run `guide:preflight` themselves when its result is not already present.
- Install (documented in README): register the local dir and install through Codex's plugin mechanism, as cc-review documents.

## OpenCode (new)

- `guide/opencode/command/<name>.md` for each of the six commands. Each shim contains only:
  1. Invoke the `guide:preflight` skill with the passed arguments; stop if it stops.
  2. Invoke the `guide:<name>` skill with the same arguments.
  No skill logic is duplicated into the shim (FR-018).
- `guide/opencode/install.sh [--project-dir <path>]`: copies `command/*.md` into `<project-dir>/.opencode/plugins/guide/command/`. Mirrors `cc-review/review/opencode/install.sh` minus the `.core-path` pointer (cc-guide has no `core/`).

## Shared invariant

- All three entry points resolve to the same `guide/skills/`; none changes behavior (FR-003, FR-018).
- The version string in `.codex-plugin/plugin.json` MUST equal the one in `.claude-plugin/plugin.json`.
- Adding a future harness means adding one entry point here and nothing in `skills/` or `toolkit/` (FR-019 allows later additions without precluding them).
