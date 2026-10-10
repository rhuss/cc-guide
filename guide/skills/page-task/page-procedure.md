# Page task procedure

Every page task (create and evolve) follows these steps. Your task brief gives the task-specific inputs: the page path, its outline, its voice, the facts to verify with source hints, and the content rules for the page. Read `global-constraints.md` (in the same directory as this file) before you write anything; its rules bind every page.

Run every command from the guide project root with path arguments. Never `cd` into `.guide/cache/`, and never run git there except as `git -C .guide/cache/<id> ...` from the root (repeated subagent stalls came from changing into the cache). If a `git` command is refused because a shell hook rewrites it (for example to `rtk git`), call `/usr/bin/git` directly.

## Steps

1. **Add the page rules first.** Append the brief's content rules for this page to `guide-rules.yaml` (`require`, `forbid`, `require_order` per glob). Run `make check` and confirm the new rules fail. This keeps the rules honest: a rule that passes before the page exists checks nothing.

2. **Write the skeleton.** Create the page with its title, an empty source block, and the stub marker (`// STUB` in AsciiDoc, `<!-- STUB -->` in Markdown), and add it to the navigation in the order the plan gives. Commit nothing yet.

3. **Verify facts and list sources.** For every fact in the brief's fact list, and every further fact you plan to write:
   - Find it in the pinned sources under `.guide/cache/<source-id>/` (for example `rg -n 'port' .guide/cache/mini/config/` or `sed -n '1,40p' .guide/cache/mini/Makefile`), or at a `url:` source.
   - Add the exact file and line range to the page's source block: `<source-id>:<path>:<first>-<last>`.
   - A fact you cannot confirm does not go into the page. List it under "Unverified" in your report.
   - Write only what a cited source states. Units, defaults, side effects, and operational advice never come from general knowledge: when the source shows `timeout: 30` without a unit, the page gives the value without inventing one, and advice the source does not give (restart this, expose it like that) stays out.
   - Inputs (transcripts, notes, tickets) are hints, never proof. A claim from an input enters the page only after a pinned source confirms it. When a source contradicts an input, the page follows the source, and you list the contradiction under "Findings" in your report (input claim, source location, what the source says).
   - Quotes from a transcript appear only verbatim. Anything you rephrase is a paraphrase without quotation marks.
   - Content whose only support is an input marked `confidential` in `inputs.yaml` may appear only on internal pages, cited there as `input:<id>` in the source block. Never cite `input:` on a shareable page.
   - When a source contradicts itself (for example a README value that differs from the configuration default), the page follows the code or configuration, and you list the location pair under "Upstream candidates" in your report with the exact text at each location.

4. **Draft the page.**
   - Start the body directly after the title and the source block.
   - The start page and the section overview pages follow `overview-contract.md` in this directory: the start page shape, the four tests for every component definition, and the spec's `## Why` card as the content to carry. Define each product from its own pinned source. When the brief's outline asks for repository layout or implementation detail on the start page, move it to the page the contract names and report the deviation.
   - Explanations first, then tasks. A task section opens with a short paragraph on why the reader does it, followed by numbered steps with copy-paste commands.
   - A step with an observable result ends with a check: a `Check:` line saying what the reader should see, the command listing, and an expectation comment (see the snippets below). Write an expectation whenever the result is predictable; `/guide:validate` reports checks without one as not evaluable.
   - Versions, commits, and permalinks come only from the baseline values (snippets below). Never type them.
   - Use only the five admonition types with their fixed meanings: NOTE (helpful background), TIP (a shortcut or better way), IMPORTANT (must not be missed; also experimental labels), WARNING (risk of a failed step or confusing behavior), CAUTION (risk of data loss, security exposure, or an irreversible change).
   - Experimental content (an open or merged-but-unreleased upstream change request from `baseline.yaml` `change_requests`) is labeled only through the adapter's experimental snippet, with its feature name, change request number, and anchor.
   - Diagrams are separate tasks; reference an existing diagram with the adapter's image markup only.
   - Voice: the section's voice from the brief.
     - **When cc-prose is installed** (the brief says `prose: present`): write with the `prose:content-generator` skill and the section's voice profile, then run the prose AI-pattern check on the page (`prose:check`). The check ends your turn; the controller resumes you with "finish", and you continue at step 5. Skip the check on table-heavy reference pages.
     - **When cc-prose is absent** (`prose: absent`): follow `style-rules.md` in this directory for the section's built-in style.
   - Follow the terms in the guide's `styleguide.md`.
   - No em dash or en dash characters anywhere.

5. **Remove the stub marker and run the gates.** Run `make check` (and `make check STRICT=1` when the brief says the rigor is strict). Fix every violation. The build runs at warning level, so a broken cross-reference, include, image, or missing attribute fails it.

6. **Commit** the page, the navigation change, and the rule additions with the message `docs(<area>): write <page>` and the trailer `Assisted-By: 🤖 Claude Code`. Do not push; the controller pushes when the author opted in.

7. **Report** to the controller, starting with the status line `DONE`, `DONE_WITH_CONCERNS`, or `BLOCKED`, then:
   - the commit SHA and the files changed
   - the source block entries you added and which statements each supports
   - Findings (input claims the sources contradict), Upstream candidates (with `path:line` and the quoted text at the pinned commit), Unverified facts left out
   - the `make check` result (last lines)

## Format snippets

The guide's format is in `guide.yaml` (`format`). Use the snippets for that format.

### antora (AsciiDoc)

One sentence per line. Source block directly after the title (and any attribute entries):

```asciidoc
= Install minisvc

// Sources:
// mini:Makefile:3-4
// mini:config/defaults.yaml:2-4,6-7
// url:https://example.com/minisvc
```

A navigation-only page without facts carries `:guide-no-sources:` in its header instead.

Check with expectation:

```asciidoc
Check: the status endpoint answers with ok.

[source,bash]
----
curl -s http://127.0.0.1:9090/status
----
// expect: contains "ok"
```

Matchers: `exit <n>`, `contains "<text>"`, `not-contains "<text>"`, `matches /<regex>/`, `lines >=|<=|== <n>`, combined with `and`.

Admonitions:

```asciidoc
[WARNING]
====
The service binds to 127.0.0.1, so other hosts cannot reach it.
====
```

Baseline values: `{<source-id>-commit}`, `{<source-id>-commit-short}`, `{<source-id>-blob}/<path>`, `{<source-id>-tree}`, `{<source-id>-repo}`, `{<source-id>-<attribute>}`, `{baseline-date}`. A listing that uses them needs `[source,bash,subs="attributes+"]`, and shell variables inside such a listing must be written `$VAR` (or `$\{VAR}`), never `${VAR}`, or the warning-level build fails.

Experimental labels (tier `in-review` or `on-main`, matching the change request in `baseline.yaml`). The section that holds the label carries the change request's `anchor` as its id; the partial sets no id itself (a second element with the same id fails the build):

```asciidoc
[#status-history]
== Status history

:feature-name: Status history
:feature-pr: 4
:feature-anchor: status-history
:feature-repo: {mini-repo}
include::ROOT:partial$experimental-in-review.adoc[]
:feature-name!:
:feature-pr!:
:feature-anchor!:
:feature-repo!:
```

Use `ROOT:partial$experimental-on-main.adoc` for the merged tier. The `ROOT:` prefix makes the same include work on internal pages. The baseline note: `include::ROOT:partial$baseline-note.adoc[]`.

Cross-references: `xref:admin/install.adoc[Install minisvc]`. Shareable pages never reference the `internal` module.

Images: `image::01-architecture.svg["Architecture of minisvc, with the status endpoint",role=expand]`. Always quote the alt text.

### mkdocs (MkDocs Material)

Source block directly after the title (an HTML comment; Markdown pages need not keep one sentence per line):

```markdown
# Install minisvc

<!-- Sources:
mini:Makefile:3-4
mini:config/defaults.yaml:2-4,6-7
url:https://example.com/minisvc
-->
```

A navigation-only page carries `<!-- guide: no-sources -->` instead.

Check with expectation:

````markdown
Check: the status endpoint answers with ok.

```bash
curl -s http://127.0.0.1:9090/status
```
<!-- expect: contains "ok" -->
````

Admonitions (`note`, `tip`, `important`, `warning`, `caution`), body indented four spaces:

```markdown
!!! warning

    The service binds to 127.0.0.1, so other hosts cannot reach it.
```

Baseline values through the macros module, with the guide's own delimiters (Go, Helm, and shell templates in listings stay literal): `{{= attr("mini-commit-short") }}`, also inside listings; the baseline note: `{{= baseline_note() }}`. An unknown attribute fails the build.

Experimental labels; the section heading carries the change request's anchor:

```markdown
## Status history { #status-history }

{{= experimental("in-review", "Status history", 4) }}
```

Use `"on-main"` for the merged tier. Cross-references are relative Markdown links (`[Get started](../user/start.md)`); shareable pages never link into `docs/internal/`. Diagrams: `![Architecture of minisvc](../assets/diagrams/01-architecture.svg)` (the lightbox enlarges them on click).

### gfm (GitHub Markdown)

Source block, no-sources marker, and checks as for mkdocs.

Admonitions are GitHub alerts (`NOTE`, `TIP`, `IMPORTANT`, `WARNING`, `CAUTION`):

```markdown
> [!WARNING]
> The service binds to 127.0.0.1, so other hosts cannot reach it.
```

Baseline values are generated regions that `make site` rewrites from `baseline.yaml`; write the region with any placeholder value and run `make site`:

```markdown
Check out commit <!-- guide:attr mini-commit-short -->0000000<!-- /guide:attr -->.
```

Listings cannot hold baseline values in this format; describe the value in the text before the listing instead.

Experimental labels: an anchor, then an IMPORTANT alert with the fixed first line:

```markdown
<a id="status-history"></a>

> [!IMPORTANT]
> **Experimental: in review.** Status history is not part of the baseline. It is proposed in [change request #4](<repo URL>/pull/4) (status as of <!-- guide:attr baseline-date -->2026-01-06<!-- /guide:attr -->) and may change or be dropped before it merges.
```

The merged tier starts with `> **Experimental: on main.**`. Cross-references are relative `.md` links; shareable pages in `docs/` never link into `internal/`. Diagrams link to the full-size SVG: `[![Architecture of minisvc](assets/diagrams/01-architecture.svg)](assets/diagrams/01-architecture.svg)`.
