# Brainstorm Overview

Last updated: 2026-11-06

## Sessions

| # | Date | Topic | Status | Spec | Issue |
|---|------|-------|--------|------|-------|
| 01 | 2026-10-01 | cc-guide-plugin | active | - | - |
| 02 | 2026-10-07 | antora-branding | active | - | - |
| 03 | 2026-10-15 | strict-claim-ledger | parked | - | - |
| 04 | 2026-11-06 | multi-harness-support | active | - | - |

## Open Threads
- How does cc-guide detect superpowers version drift (renamed skills or scripts), and what is the fallback? (from #01)
- How are the three adapters' admonition and experimental-label partials expressed in Markdown without Antora's attribute and partial features? (from #01)
- Where does the guide repository's `.superpowers` workspace live, and what survives after a run? (from #01)
- How does `validate` map a `Check:` command to an expected result, and how are cluster credentials passed safely to subagents? (from #01)
- Should `upstream` support GitLab and Jira targets in v1, or GitHub only? (from #01)
- How are effort and model recommendations applied: documented only, or checked at command start? (from #01)
- What does the eval suite for the plugin look like? (from #01)
- Precedence between author files in `ui/supplemental/` and generated branding files (from #02)
- Footer default when a `branding` block sets no `footer` (from #02)
- Sizing the `logo_text` SVG for long text without font metrics (from #02)
- Default `logo_alt` when omitted (from #02)
- How docs state that the `logo_text` template is meant for Red Hat-owned guides (from #02)
- Which bundle CSS properties the accent `color` overrides, and whether it reaches the PDF title page (from #02)

- Who creates and fills the claim ledger under strict rigor (from #03)
- OpenCode command parity: minimal shim to keep `/guide:*` working without duplicating skill logic (from #04)
- superpowers detection without a Claude plugin registry, and the per-harness "install superpowers" message (from #04)
- How much of `compat.yaml` version/contract logic survives detection-by-skill-exposure, and what feeds create/evolve once `installPath` is gone (from #04)
- Codex permission/config model for preflight (for example `~/.codex/config.toml`) in place of `.claude/settings*.json` reads (from #04)
- Per-harness adapter smoke test dimension alongside `make test-adapters` (from #04)
- `AGENTS.md` content for cc-guide and whether the scaffold `.gitignore` needs Codex/OpenCode workspace entries (from #04)
- OpenCode depth in v1, given it is the secondary harness (from #04)

## Parked Ideas
