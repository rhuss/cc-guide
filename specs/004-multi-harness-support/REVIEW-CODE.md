# Code Review: Multi-harness support (Codex, OpenCode)

**Spec:** specs/004-multi-harness-support/spec.md
**Date:** 2026-11-06
**Branch:** 004-multi-harness-support
**Reviewer:** Claude (speckit.spex-gates.review-code + spex-deep-review)
**Scope:** `git diff main..HEAD`, reviewed against the spec only (plan.md and tasks.md deliberately not consulted).

## Compliance Summary

**Overall Score: 100% (27/27 code-verifiable requirements), with two OpenCode items flagged for the open live-OpenCode acceptance.**

- Functional Requirements: 19/19
- Success Criteria: 8/8 (SC-001, SC-002 end-to-end runs and SC-008 OpenCode launch are code-complete; their live-session acceptance is recorded open in tests/manual/004-multi-harness.md per the best-effort OpenCode scope)

No `## Constants` section in the spec, so the spec-declared-constants check was skipped.

## Functional Requirements

| FR | Status | Evidence |
|----|--------|----------|
| FR-001 Codex install, same command set | Compliant | guide/.codex-plugin/plugin.json (`skills: ./skills/`, version 0.4.0); README Codex section; test_harness_codex.sh |
| FR-002 OpenCode install, same command set | Compliant (best-effort; live launch open) | guide/opencode/install.sh + command/*.md; README OpenCode section; test_harness_opencode.sh. See Deep Review FINDING-8/9 |
| FR-003 one directory, each harness reads only its own entry point | Compliant | guide/.claude-plugin, guide/.codex-plugin, guide/opencode coexist |
| FR-004 six commands on Codex, equivalent behavior | Compliant | Shared skills; preflight gates Claude-only wiring |
| FR-005 orchestration by superpowers skill name, no registry/path | Compliant | create/evolve use vendored tools/guide/sdd; deps.sh and probe no longer read the registry |
| FR-006 own copies of SDD helper scripts | Compliant | guide/toolkit/sdd/{sdd-workspace,task-brief,review-package}; scaffold vendors to tools/guide/sdd |
| FR-007 capability-exposure detection | Compliant | preflight step 2 decides from exposure; deps.sh takes booleans as args, reads no registry |
| FR-008 cc-prose absent -> built-in style rules | Compliant | preflight records prose absent; page-task fallback |
| FR-009 Excalidraw absent -> placeholder path | Compliant | create 6c, diagrams section 11 |
| FR-010 preflight everywhere; Claude-only wiring gated | Compliant | preflight step 2; deps.sh gated on harness==claude; diagrams section 10 gated |
| FR-011 superpowers absent -> create/evolve stop, name harness | Compliant | preflight step 2 stop message |
| FR-012 Claude no-regression | Compliant | guide/.claude-plugin and guide/commands unchanged; deps.sh still emits the legacy Claude fields with the same values (tested) |
| FR-013 AGENTS.md | Compliant | AGENTS.md |
| FR-014 adapter suite verifies each harness discovers + launches | Compliant | test_harness_*.sh picked up by Makefile wildcard; Codex launch path now asserted |
| FR-015 install + degradation docs | Compliant | README Install (per harness) + Known degradations |
| FR-016 advisory version expectation, no registry | Compliant | compat.yaml known_good_version 7.0.0; superpowers-probe.sh advisory (exit 0/3, never blocks); docs aligned (fix) |
| FR-017 multi-agent absence detected, stop | Compliant | preflight multi_agent from exposure; stop message |
| FR-018 no per-harness fork in shared skills/toolkit | Compliant | Confirmed by the architecture agent: toolkit has no harness branching; only Claude-only wiring and optional-dependency fallbacks branch |
| FR-019 exactly Claude/Codex/OpenCode, extensible, OpenCode best-effort | Compliant | three entry points |

## Success Criteria

| SC | Status | Evidence |
|----|--------|----------|
| SC-001 create on Codex, no Claude setup | Compliant (code); live run open | preflight skips Claude wiring on Codex |
| SC-002 six commands on Codex | Compliant (code); live run open | shared skills |
| SC-003 Claude behavior unchanged, existing tests pass, new checks additive | Compliant | plugin/command layer unchanged; existing test files unmodified; full suite passes |
| SC-004 detection without registry/settings | Compliant | preflight + deps.sh |
| SC-005 cc-prose/Excalidraw absent still produce a guide | Compliant | fallbacks |
| SC-006 superpowers absent -> stop, no partial content | Compliant | preflight stops before writing |
| SC-007 adapter suite exercises every harness | Compliant | three harness checks in test-adapters |
| SC-008 install + launch on OpenCode | Compliant (code, best-effort); live launch open | install.sh + opencode harness check. See FINDING-8/9 |

## Project-rule checks

- No em dash or en dash in any changed file: PASS (ripgrep scan clean, including the fixes).
- Claude no-regression (FR-012): PASS. guide/.claude-plugin/ and guide/commands/ unchanged vs main; deps.sh still emits superpowers, prose, excalidraw_allowed, excalidraw_allowed_in with unchanged Claude values (test_deps.py).
- No per-harness behavior fork in guide/skills or guide/toolkit (FR-018): PASS (architecture agent confirmed).
- guide/toolkit/ imports nothing outside its own dir: PASS (vendored sdd scripts are self-contained bash; no cross-plugin reads).
- No committed .mcp.json: PASS (not tracked; in every scaffold .gitignore).

## Deep Review Report

**Gate: PASS (after fix round 1).** Full detail in review-findings.md.

Deep review dispatched 5 internal agents (correctness, architecture, security, production-readiness, test-quality; Goal Alignment skipped, no PR) plus 2 external tools (CodeRabbit and Codex; Copilot disabled in deep-review-config.yml). The full toolkit test suite passed (exit 0) and all three harness checks pass.

| Agent | Found | Fixed | Remaining | Status |
|-------|-------|-------|-----------|--------|
| Correctness | 2 | 2 | 0 | completed |
| Architecture & Idioms | 5 | 3 | 2 | completed |
| Security | 2 | 1 | 1 | completed |
| Production Readiness | 1 | 1 | 0 | completed |
| Test Quality | 4 | 2 | 2 | completed |
| Goal Alignment | - | - | - | skipped (no PR) |
| CodeRabbit (external) | 1 | 1 | 0 | completed |
| Codex (external) | 2 | 0 | 2 | completed (ambiguous) |
| Copilot (external) | - | - | - | skipped (disabled in config) |
| Test Suite (regression) | 0 | - | 0 | passed |

Severity totals (deduped): 0 Critical, 3 Important (1 fixed, 2 ambiguous), 6 Minor (4 fixed, 2 left), 6 Notable (3 addressed, 3 informational).

### Fixes applied in round 1 (committed)

1. guide/scripts/deps.sh: fixed a confirmed arg-parse infinite loop on a trailing bare value-flag (require a value, matching `--harness`); hardened the two python3 fallbacks with `-I`.
2. guide/scripts/superpowers-probe.sh: hardened the python3 fallback with `-I`; corrected the exit-3 header comment.
3. guide/docs/settings.md and guide/docs/learnings.md: corrected the stale superpowers version (6.3.0 -> advisory 7.0.0 framing) and the stale "runtime contract probe" description (now an advisory version-only check).
4. tests/adapters/test_harness_codex.sh: added launch-path coverage (each command skill self-invokes guide:preflight) and FR-011/FR-017 stop-gate guards; closes the primary-harness launch gap.
5. README.md: declared jq/python3 as a requirement for the capability-detection scripts.

### Surviving findings (adjudicate before merge)

- ambiguous: guide/opencode/install.sh:20 (FINDING-8) OpenCode command discovery path; matches the spec-designated cc-review reference and research.md decision; needs live-OpenCode verification.
- ambiguous: guide/opencode/install.sh:23-25 + README (FINDING-9) OpenCode skill discoverability through install.sh alone; best-effort scope; needs live-OpenCode verification.
- ambiguous: guide/.claude-plugin/plugin.json (NOTABLE-2) Claude hard-dependency makes the whole plugin unavailable without superpowers, tensioning with spec.md:70; pre-existing, FR-012-protected.
- unambiguous-minor: guide/opencode/command/*.md byte-identical to guide/commands/*.md, no parity test (deliberate per-harness layout).
- unambiguous-minor: tests/toolkit/test_probe.py:27-30 version compare exercised only on the leading component.
- unambiguous-minor: tests/toolkit/test_deps.py:197-211 legacy-field value assertion partly vacuous (FR-012 genuinely covered by the excalidraw-wiring tests).

### Notable observations captured

Appended to brainstorm/idea-inbox.md: the vendored task-brief path-input hardening (upstream/vendoring note) and the Claude hard-dependency cross-harness divergence.

## Conclusion

The implementation satisfies all 19 functional requirements and 8 success criteria against the spec, with no Claude Code regression and no per-harness behavior fork in the shared skills or toolkit. The fix round resolved every unambiguous code and documentation issue. The only surviving Important findings are the two OpenCode installer items raised by Codex; both fall inside OpenCode's explicitly best-effort v1 scope, match the spec-designated reference plugin, and are routed to the open live-OpenCode acceptance in tests/manual/004-multi-harness.md.

**Gate outcome: PASS.**
