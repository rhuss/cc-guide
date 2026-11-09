# Code Review: Author-owned region on the generated front page

**Spec:** specs/006-author-owned-front-page-region/spec.md
**Date:** 2026-11-09
**Branch:** 006-author-owned-front-page-region
**Reviewer:** Claude (speckit-spex-gates.review-code + spex-deep-review)
**Scope:** `git diff e4fd005..HEAD`, reviewed against the spec only (plan.md and tasks.md deliberately not consulted).

## Compliance Summary

**Overall Score: 100% (16/16 functional requirements, 8/8 edge cases, 5/5 success criteria).**

No `## Constants` section in the spec, so the spec-declared-constants check was skipped.

## Functional Requirements

| FR | Status | Evidence |
|----|--------|----------|
| FR-001 one region per file, markers, outside is author-owned | Compliant | guide/toolkit/region.py: parse/splice; region-duplicate and region-unbalanced errors; tests/toolkit/test_region.py |
| FR-002 no markers on a guide-owned file keeps spec 005 behavior; publish target without markers is an error | Compliant | region.parse returns the whole file as content; publish.py `_target_region` refuses unmarked targets; test_write_without_markers_errors_and_writes_nothing |
| FR-003 every guide command operates on the region only | Compliant | publish.py splice; check.py check_pages narrows page rules with a line offset; fetch.normalized_front_page (hand-edit detection); attrs.regions rewrites the region only. FR-008 link check is the single whole-file exception, as specified |
| FR-004 checks fail, nothing written, on malformed markers | Compliant | check.py reports region-unbalanced/region-duplicate (Violation with file and line); publish.py refuses before any write; tests test_region_validity_errors_for_target, test_write_with_malformed_markers_errors_and_writes_nothing |
| FR-005 markers inside fences are text | Compliant | region.fence_mask (backtick and tilde fences, matching fence char and length to close); test_markers_inside_fenced_code_blocks_are_text, test_tilde_fences_mask_markers_too |
| FR-006 publish block in guide.yaml, gfm only, page inside and target outside the content root | Compliant | guidecfg._load_publish (ConfigError with file and key, format gate, _inside checks); without the block publish.py is a no-op exit 0 and check_publish returns nothing |
| FR-007 writer rebases links, writes only the region, comparison in the standard check flow | Compliant | publish.render uses embed.relink (built on embed.rewrite_links, the same transform as move-plan relocations); Makefile check target runs check-publish; test_write_rebases_links_for_the_target_location, test_check_fails_when_the_region_is_stale_after_a_page_edit |
| FR-008 whole-file link check | Compliant | check.py `_md_link_rules` over the whole marked front page at file line numbers; `_relative_links` over the publish target; test_unresolvable_author_link_in_target_fails |
| FR-009 sources block and front page contract inside the region | Compliant | publish.render copies the page text including the sources block (test_write_keeps_sources_block_and_attr_regions); front-page-contract.md rules 4 to 7 scoped to the region; check rules run on the region |
| FR-010 embedded front page machinery narrows to the region | Compliant | check_pages/check_embedded/check_structure (nav_text), attrs.regions, normalized_front_page; badges and logo become ordinary author text (front-page-contract rule 3); test_marked_front_page_author_text_is_not_checked |
| FR-011 ownership comment inside the region, region wording | Compliant | sources.OWNERSHIP_COMMENT_REGION; check_embedded expects it as the first line of the region; test_marked_front_page_needs_the_region_ownership_comment |
| FR-012 create offers author-region as the default for landing sections | Compliant | guide/skills/create/SKILL.md classification step (author-region default for pitch, context, usage examples); input keeps instructional material |
| FR-013 author text never verified, validated, or rewritten | Compliant | Region narrowing in every consumer; the only failing check over author text is the link check; contract rule: report problems in the run summary, never edit |
| FR-014 reviewer briefs flag contradictions as non-blocking | Compliant | page-review-guide.md check 9; page-procedure.md step 3 addition; front-page-contract.md review additions (same wording) |
| FR-015 exports unchanged | Compliant | embed.stage stages the whole front page (test_stage_keeps_the_whole_front_page); a plain guide's region exists only in the README target, never in docs/ |
| FR-016 gfm adapter only | Compliant | guidecfg._load_publish rejects non-gfm formats; no publish wiring in the antora or mkdocs scaffolds |

## Edge Cases

| Edge case | Status | Evidence |
|----|--------|----------|
| Unbalanced markers | Compliant | RegionError region-unbalanced naming file and marker line; check.py reports it; nothing written |
| More than one pair | Compliant | region-duplicate naming file and counts |
| Markers inside fences | Compliant | fence_mask, both fence styles tested |
| Source page deleted or renamed | Compliant | publish.render names the missing page; guidecfg.validate reports guide.yaml:publish.page not found |
| Markers deleted between runs | Compliant | publish stops with the missing-markers error naming the file; no command inserts markers outside an approved move plan |
| Author link into the guide not resolving | Compliant | whole-file link check fails (test_unresolvable_author_link_in_target_fails) |
| Package registry publishes the README | Compliant | absolute_links rule untouched (guide region only); author relative links produce no form warning, only resolution failures |
| Empty or short region | Compliant | front-page-contract rule 5 (region holds on its own); test_parse_empty_region |

## Success Criteria

| SC | Status | Evidence |
|----|--------|----------|
| SC-001 author edits never fail or revert | Compliant | test_check_passes_when_only_author_text_was_edited; test_author_edit_above_markers_is_invisible |
| SC-002 bytes change only inside the region | Compliant | region.splice byte-preserves prefix and suffix (test_write_splices_only_the_region); apply keeps landing text byte-identical |
| SC-003 published links resolve from the README location | Compliant | relink rebasing plus whole-file link check on the target |
| SC-004 embedded create preserves landing sections verbatim | Compliant | test_apply_keeps_landing_sections_as_author_region, test_apply_author_region_markers_below_last_retained_section |
| SC-005 planted contradiction reported as advisory, gates pass | Compliant | reviewer briefs (FR-014); quickstart scenario 5 recorded in tests/manual/006-author-region-quickstart.md |

## Extra Features (Not in Spec)

None. The publish no-op notice and the guidecfg.validate check for a missing publish page are within FR-006's intent (load must not fail on a page create has not written yet; validate reports it).

## Project-rule checks

- No em dash or en dash in any changed file: PASS (ripgrep scan of all 33 changed files, before and after the fix below).
- guide/toolkit/ imports nothing outside its own directory: PASS (region.py stdlib-only; consumers import region, embed, guidecfg, sources, branding, all local; pyyaml declared in the PEP 723 header).
- No secrets, tokens, or raw inputs in fixtures: PASS (all fixtures are synthetic Markdown trees under tmp_path).
- No script cds into .guide/cache/: PASS (no such change in the diff).

## Deep Review Report

Review chain: spec compliance (above), then the deep review pass over the same diff: correctness, architecture, security, production readiness, and test coverage, plus the CodeRabbit CLI local review (`coderabbit review --agent --type all`).

**Correctness.** Line-number arithmetic verified where regions shift offsets: attrs.regions maps content offsets to file lines via begin_line; check_pages adds the begin-line offset to every region violation and reports whole-file link violations at file lines; check_embedded points at begin_line + 1. embed.apply computes moved-section removals in reverse span order and recomputes retained-section spans on the mutated text, with overlapping sections refused up front (check_plan), so the marker pair lands below the last retained section without eating author text. The region write is behind the dry_run guard like every other apply write. region.fence_mask requires the closing fence to use the same character and at least the opening length, so a tilde fence cannot be closed by backticks.

**Architecture.** One shared parser (region.py, no CLI) consumed by publish, check, embed, attrs, and fetch, matching the generated-region precedent of attrs.py. The publish writer reuses embed.relink (the move-plan relocation transform) rather than a second link rewriter. guidecfg follows the branding/embedded block pattern for the publish block, including the load-must-not-fail-on-missing-page rule with validate reporting it.

**Security.** The publish target is author-declared in guide.yaml and validated outside the content root; the writer refuses unmarked or malformed targets before any write and only ever splices between markers. No network access, no secrets, fixtures synthetic.

**Production.** Exit codes and messages per contracts/publish-cli.md (0 clean/no-op, 1 error or difference, unified diff in check mode, errors on stderr). The gfm Makefile wires publish into the standard flow (check runs check-publish) and adapter.yaml documents the block and markers. One operational gap found and fixed (FINDING-1 below).

**Tests.** 980 passed (baseline 918 plus 62 new across test_region, test_publish, test_guidecfg, test_attrs, test_check, test_embed), covering every FR and edge case above, plus the recorded end-to-end quickstart scenarios (tests/manual/006-author-region-quickstart.md).

### Findings

| # | Source | Severity | Finding | Disposition |
|---|--------|----------|---------|-------------|
| FINDING-1 | CodeRabbit | Minor (fixed) | `make publish` copied the page as-is from docs/, so a stale `guide:attr` value (before `make regions` refreshes it) was published and then failed `check-publish`, forcing a second `make publish` | Fixed: the publish target now depends on regions (guide/adapters/gfm/scaffold/Makefile), so attribute values are current before the page is copied |

No Critical or Important findings. The fix was re-verified: the regions target exists in the scaffold, rewrites the same dirs the site build uses, and the toolkit suite still passes.

## Conclusion

**Verdict: PASS.** 100% spec compliance, no Critical or Important findings, one minor operational finding fixed during review, full suite green. Ready for verification and walkthrough.
