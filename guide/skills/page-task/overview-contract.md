# Overview contract: the why

The start page and the overview pages answer why before how. A reader who knows none of the products must finish the start page able to say what they get, what each named product is, and why the combination is worth running. This contract fixes the shape of that answer for the guide spec, the plan, the implementers, and the reviewers (FR-043).

## The why card

The guide spec has a `## Why` section with these six slots, in this order. Every slot is one to three plain sentences, and every factual sentence names its source. The author approves the card at the plan approval gate, before any page is written.

| Slot | Answers | Source |
|---|---|---|
| Problem | What the reader cannot do today, or what goes wrong without this setup | The integrating source (the recipe, kit, or product docs that the guide covers) |
| Outcome | What the reader has at the end, as something they can see or use | The integrating source |
| Components | For every product or project the start page names: one sentence on what it is and what it does for the reader | That product's own pinned source (its README or docs), never only the integrating source |
| Fit | How the components work together: who calls whom, who contains whom | Manifests, configuration, or architecture docs |
| Why this combination | The benefit of running them together on this platform, compared with the obvious alternative | The integrating source or the products' own docs |
| Status and limits | Support status, maturity, and the one or two limits that change the decision | The integrating source |

When a slot has no source, the spec says so in that slot and lists it under open questions. The author decides at the approval gate whether the guide states it, drops it, or waits for a source. A slot is never filled from general knowledge.

## A definition that works

A component definition in the card and on the pages passes all four tests:

1. **Function.** It says what the thing does for the reader, not where it lives. "An open-source message relay that buffers events between services" passes. "The relay component of the kit" fails.
2. **No self-reference.** It does not explain a name with the same name or with the artifact that contains it. "Runs the relay in a relay sandbox" and "the kit ships a recipe for running the relay" explain nothing.
3. **Known words only.** Every term it uses is either common knowledge for the guide's audience or defined earlier on the same page. "Gateway", "sandbox", and "control plane" need their own definition the first time.
4. **Own source.** It cites the product's own pinned source. When the integrating source describes the product differently, the page follows the product's own description, states it plainly (no "the recipe describes it as"), and the implementer lists the pair under Upstream candidates.

Add the product's own repository or documentation URL as a pinned source when the intake did not include it. A product without its own source gets a definition from the integrating source plus an open question in the spec.

## Start page shape

The start page follows this order. Sections may merge, but the order holds.

1. **Outcome first.** One short paragraph: what the reader gets and the problem it solves (slots Problem and Outcome).
2. **What the parts are.** One definition per component (slot Components), each passing the four tests.
3. **How they fit and why together.** Slots Fit and Why this combination, with the guide's big-picture diagram when the spec plans one.
4. **Ways to run it.** One or two sentences per path with a link to the page that compares them. File layouts, manifest lists, image pins, replica counts, and directory names belong on the architecture, comparison, or reference pages, never on the start page.
5. **Status and limits.** Support status and the limits from the card.
6. **Where to go next.** One entry per persona, then the baseline note.

The overview page of each persona section opens with one paragraph in the same spirit: what this reader achieves in the section and why it matters to them, before the list of pages.

## The cold-reader test

Reviewers apply this test to the start page and to every section overview page. Read only that page, as a reader who has never heard of any named product, and write one sentence per question, citing the page lines that answer it:

1. What do I get when I follow this guide?
2. What problem does it solve for me?
3. What is each named product, in words I already know?
4. How do the parts work together?
5. Why would I choose this setup over the obvious alternative?

A question the page does not answer, or an answer that only repeats a product name, a repository path, or a container (a recipe, a kit, a directory), is an **Important** finding. Name the question, quote the line that fails, and point to the source that would answer it.

## Common failures

| What the page says | Why it fails | What works |
|---|---|---|
| "The kit ships a recipe for running Relay on the platform." | Defines Relay by its container; the reader still does not know what Relay is | Relay's own one-sentence purpose, then what the kit adds |
| "The recipe describes Relay as a logging tool." | Hedged second-hand definition, possibly wrong | Relay's README states its purpose; cite it and state it plainly |
| "The third way runs Relay in a Corral sandbox." | Names a second product without defining it | One sentence on what Corral is and why a sandbox matters here |
| The second paragraph lists directories, replicas, and image digests | Implementation detail before the reader knows why to care | Move it to the architecture or reference page |
| The only reason given is a support warning | The reader learns the risk before the value | Value first, status and limits after |
