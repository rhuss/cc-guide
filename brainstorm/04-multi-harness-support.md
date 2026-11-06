# Brainstorm: Multi-harness support (Codex, OpenCode)

**Date:** 2026-11-06
**Status:** active

## Problem Framing

cc-guide ships as a Claude Code plugin only (one `guide/.claude-plugin/`
manifest). The goal is to run the full `/guide:*` command set on Codex
(primary) and OpenCode (secondary, less important), the way cc-review already
supports Claude Code, Codex, and OpenCode from one plugin directory.

Why it matters: authors who work in Codex cannot create, evolve, preview,
export, validate, or report upstream on a guide today. cc-review proved the
pattern is cheap when the orchestration layer is harness-neutral.

**Success:** `create`, `evolve`, `preview`, `export`, `validate`, and
`upstream` all run on Codex, installed through Codex's own plugin mechanism,
with behavior equivalent to Claude Code. OpenCode follows with the same
adapter.

**Non-goals / anti-goals:**
- Not reimplementing the orchestration. superpowers is already multi-harness
  (see Findings), so create/evolve reuse it rather than growing a second
  engine.
- Not blocking v1 on the two optional, Claude-bound capabilities (cc-prose
  voice profiles, Excalidraw diagrams). Both already degrade gracefully and are
  ported separately.
- No per-harness behavior fork in the toolkit or skills; one source of truth.

## Findings that shaped the design

- **superpowers is genuinely multi-harness.** Its 7.0.0 package ships
  `.codex-plugin/`, `.opencode/`, an `AGENTS.md`, and
  `skills/using-superpowers/references/<harness>-tools.md` (for example
  `codex-tools.md`, which maps subagent-driven-development onto Codex's
  `spawn_agent`/`wait_agent`/`followup_task`, with `multi_agent = true` in
  `~/.codex/config.toml`). So create/evolve's interview, plan, and per-page
  review loop run on Codex once superpowers is installed there.
- **The cc-guide toolkit is already format-neutral** (PEP 723 Python + Node),
  so preview/export/validate/upstream are close to cc-review's mechanical half.
- **The three superpowers SDD scripts** cc-guide calls (`sdd-workspace`,
  `task-brief`, `review-package`) are plain portable bash doing git/file
  plumbing, with no Claude-specific logic. They can be vendored.
- **The Claude-bound surface is narrow:** (1) only `.claude-plugin/` exists;
  (2) `superpowers-probe.sh` reads `~/.claude/plugins/installed_plugins.json`
  for an install path, and create/evolve call the SDD scripts *inside* that
  path; (3) preflight and diagrams read `.claude/settings*.json` for the
  Excalidraw MCP permission.
- **cc-prose is Claude Code only** (single `.claude-plugin/` manifest, no Codex
  entry). It is optional: cc-guide already threads `prose: present|absent` and
  falls back to `guide/skills/page-task/style-rules.md` when absent. Its Codex
  port is tracked in the cc-prose repo brainstorm `07-multi-harness-support.md`.
- **Excalidraw MCP** works on Codex, but its permission detection is
  Claude-specific; diagrams already have a placeholder fallback when the tools
  are absent.

## Approaches Considered

### A: Thin multi-harness adapter, reuse superpowers, fallbacks for optionals (chosen)

- Add `guide/.codex-plugin/` (+ an OpenCode entry point and a repo-root
  `AGENTS.md`), mirroring cc-review, over cc-guide's existing `skills/`.
- Vendor the three portable SDD scripts into cc-guide's toolkit so create/evolve
  invoke superpowers *skills by name* and never reach into superpowers' install
  path. This removes the one hard Claude-registry coupling.
- Detect dependencies by skill/tool exposure, not by reading `~/.claude/...`:
  superpowers (is its skill available), cc-prose (is `prose:humanizer`
  exposed), Excalidraw (are `mcp__excalidraw__*` tools present). The cc-review
  method.
- On Codex, when cc-prose is absent use the built-in `style-rules.md`; when
  Excalidraw is absent use the existing placeholder-diagram path.
- Make preflight harness-aware: the `.claude/settings*.json` permission wiring
  runs on Claude only.

- Pros: smallest, mostly mechanical change; reuses the proven cc-review and
  superpowers templates; create/evolve/preview/export/validate/upstream all run
  on Codex; no second orchestration engine.
- Cons: diagrams and prose polish are degraded on Codex until their separate
  ports land; vendoring the SDD scripts adds a small sync obligation if
  superpowers changes them.

### B: Full parity in v1

Also wire Excalidraw MCP + Codex permissions and depend on the cc-prose Codex
port landing first.

- Pros: nothing degraded on Codex at launch.
- Cons: larger v1; blocks cc-guide on a separate repo's port and on new Codex
  MCP permission wiring. Rejected: the optionals already degrade gracefully, so
  the cost is not worth delaying the mechanical adapter.

### C: Teach the probe Codex's registry instead of vendoring the scripts

Extend `superpowers-probe.sh` to locate superpowers under Codex's plugin layout
and keep calling the SDD scripts in place.

- Pros: no vendored copy to keep in sync.
- Cons: brittle (every harness's plugin layout must be taught to the probe) and
  still reaches into another plugin's install directory. Vendoring (A) is
  cleaner and harness-agnostic.

## Decision

**Approach A.** Ship a thin multi-harness adapter: per-harness manifests over
the shared `skills/`, vendor the three SDD scripts, detect every dependency by
skill/tool exposure, make preflight harness-aware, and let cc-prose and
Excalidraw fall back to their built-in paths on Codex. Codex first, OpenCode
second. The cc-prose and Excalidraw-on-Codex ports are separate follow-ups.

## Key Requirements

- Add `guide/.codex-plugin/plugin.json` (point `"skills": "./skills/"`), an
  OpenCode entry point, and a repo-root `AGENTS.md`, modeled on cc-review and
  superpowers.
- Vendor `sdd-workspace`, `task-brief`, `review-package` into the cc-guide
  toolkit; change create/evolve to call the vendored scripts and to invoke
  superpowers skills by name only.
- Replace registry-path detection with skill/tool-exposure detection for
  superpowers, cc-prose, and Excalidraw. Keep the superpowers version/contract
  intent (`compat.yaml`) expressed in a way that does not require a Claude
  plugin registry.
- Preflight runs harness-aware; the `.claude/settings*.json` permission wiring
  is Claude-only and skipped elsewhere.
- Preserve current Claude Code behavior exactly (no regression).
- On Codex: cc-prose absent -> `style-rules.md`; Excalidraw absent ->
  placeholder diagrams. Both paths already exist.
- Constraints owned by the user: follow the cc-review / superpowers packaging
  conventions; Codex is the priority harness, OpenCode is secondary.

## Open Questions

- OpenCode command parity: what is the minimal shim (cc-review uses
  `opencode/command/*.md` + an `install.sh`) that keeps the `/guide:*` commands
  working without duplicating skill logic?
- Exact superpowers detection without a registry: by skill availability in the
  session, and how to surface a useful "install superpowers for this harness"
  message per harness.
- Version/contract checks: how much of `compat.yaml`'s known-good / minimum
  logic survives once detection is by skill exposure, and where the probe
  output feeds create/evolve now that `installPath` is gone.
- Codex permission/config model for preflight: what, if anything, replaces the
  `.claude/settings*.json` reads (for example `~/.codex/config.toml`), and
  whether preflight should say anything about Excalidraw permissions on Codex.
- Testing: a per-harness adapter smoke test (the repo already has
  `make test-adapters` for formats; add a harness dimension).
- `AGENTS.md` content for cc-guide, and whether the guide project scaffold's
  `.gitignore` needs Codex/OpenCode workspace entries alongside `.guide/` and
  `.superpowers/`.
- Which harnesses are in v1 scope at what depth: Codex fully, OpenCode to what
  level given it is secondary.

## Related

- cc-prose Codex/OpenCode port: `cc-prose` repo, brainstorm
  `07-multi-harness-support.md` (mimic the superpowers packaging).
- Reference implementations: cc-review (`review/.codex-plugin/`,
  `review/opencode/install.sh`, `AGENTS.md`) and superpowers 7.0.0.
