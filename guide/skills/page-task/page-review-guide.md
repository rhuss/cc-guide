# Page task review guide

You review one page task of a source-verified guide. The guide project is the repository in your dispatch. This is a task-scoped gate: the page must be trustworthy before the next page starts. A whole-guide review happens at the end of the run.

## Inputs (paths are in your dispatch)

- The task brief: page, outline, voice, facts to verify with source hints, content rules.
- `page-procedure.md` and `global-constraints.md` in this directory (binding rules).
- The implementer's report and the review package (commit list, stat, full diff).
- The guide's `styleguide.md`, `baseline.yaml`, and `inputs.yaml`.

## What to check

1. **Factual accuracy (most important, FR-011).** For every factual statement in the changed pages, find its support in the page's source block: open each cited file at the cited lines in `.guide/cache/<source-id>/` (the source at the pinned commit), or the `url:` page.
   - Check at least twelve statements, or every factual statement when the page has fewer. Prioritize numbers, names, ports, paths, commands, flags, defaults, version claims, and behavior claims.
   - A statement that no listed source supports, or that a source contradicts, is **Important**.
   - A command that would not work as written (wrong target, wrong flag, missing required variable, wrong order of steps) is **Important**.
   - A citation that points at the wrong file or lines is **Important**, even when the statement is true.
   - A unit, default, side effect, or capability the cited source does not state is an unsupported statement and **Important**, even when it is plausible. When the source shows `timeout: 30` and nothing names a unit, "30 seconds" is unsupported.
   - Operational advice no source gives (restart hints, tuning guidance, instructions for exposing a service) is **Important**: it gets a source or leaves the page.
   - A statement on a shareable page whose only support is an input marked `confidential` in `inputs.yaml`, or any `input:` reference on a shareable page, is **Important** (it must move to the internal part).
   - A quotation from a transcript that is not verbatim is **Important** (paraphrase without quotation marks instead).
   - Under strict rigor, every verifiable statement must also carry a claim identifier in the claim ledger; a missing one is **Important**.
2. **Spec compliance.** Every outline item from the brief is present; the brief's content rules were added to `guide-rules.yaml` exactly; required cross-references, images, experimental labels (correct number, tier, and anchor, parameters unset afterwards), and checks are there. Nothing extra that the brief did not ask for.
3. **Global constraints.** One sentence per line in AsciiDoc; no em dash or en dash characters; no typed versions or commits (baseline values only); listings that use baseline values enable attribute substitution and contain no `${VAR}`; only the five admonition types with their meanings; experimental labels only through the adapter snippet; shareable pages carry no confidential terms or patterns and no links into the internal part; voice matches the brief.
4. **Checks and expectations.** Task steps with an observable result end with a `Check:` line, a listing, and an expectation whose matcher fits the documented output.
5. **Prose quality.** Clear structure, no filler, no inflated significance, no rule-of-three padding, terms defined at first use, the why-paragraph before the steps.
   - When cc-prose is installed, read the implementer's `prose:check` result and treat unaddressed AI-pattern findings as Minor (Important when they distort a fact).
   - When it is absent, apply `style-rules.md` in this directory.
6. **Build.** Valid markup; the implementer's report shows `make check` passing.
7. **Why (start page and section overview pages only).** Apply the cold-reader test from `overview-contract.md` in this directory and add its five answers to your output. Every unanswered question, every answer that only repeats a name, path, or container, and every component definition that fails one of the contract's four tests is **Important**. A page that matches its outline but fails the test still needs fixes: report the outline gap as well, so the controller corrects the spec's why card.

## Rules for you

- Run commands from the guide project root with path arguments, for example `sed -n '40,60p' .guide/cache/mini/Makefile` or `rg -n port .guide/cache/mini/config/`. Never `cd` into `.guide/cache/` and never run git there except `git -C .guide/cache/<id> ...` from the root. If a `git` command is refused because a shell hook rewrites it, call `/usr/bin/git` directly.
- Read-only: do not modify files or git state, do not run make targets, do not spawn subagents.
- Do not trust the report; verify against the diff and the sources.
- A finding that changes a fact must name the source location that supports your correction. The controller re-checks it against the pinned source before applying it (FR-012); a finding the source contradicts is rejected and recorded.

## Calibration and output

Plausible is not supported: when you would have to run the system, or fall back on general knowledge, to confirm a statement, count it as unsupported. Critical or Important means the page cannot be trusted until fixed: a wrong or unsupported fact, a broken command, a missing required section or rule, a constraint violation, or confidential content on a shareable page. Polish is Minor. Acknowledge what was done well. Cite `file:line` for every finding.

Begin directly with the first heading:

### Spec Compliance
- ✅ Spec compliant | ❌ Issues found: [...]
- ⚠️ Cannot verify: [...]
### Factual Spot-Checks
| # | Statement (page:line) | Source read | Verdict |
|---|---|---|---|
### Cold-Reader Test
(start page and section overview pages only; otherwise write "not an overview page")
| Question | Answer in one sentence | Page lines |
|---|---|---|
### Strengths
### Issues
#### Critical (Must Fix)
#### Important (Should Fix)
#### Minor (Nice to Have)
### Assessment
**Task quality:** [Approved | Needs fixes]
**Reasoning:** [1-2 sentences]
