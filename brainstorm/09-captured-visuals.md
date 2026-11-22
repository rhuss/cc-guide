# Brainstorm: Captured visuals (screenshots and rendered CLI output)

**Date:** 2026-11-22
**Status:** active

## Problem Framing

Guides about tools with a UI should show that UI. The main targets are web UIs that normally run on a cluster (the MLflow UI, for example) and CLI tools whose output is colored or uses Unicode bars and symbols. Today a guide can only carry Excalidraw diagrams; screenshots would have to be made by hand, and hand-made images go stale silently when the tool changes, which contradicts the guide's source-pinned, drift-checked model.

Success means:

- Visuals are produced unattended by one command, the same way on a laptop and in a CI pipeline, with no personal cluster, no credentials, and no hand-made images.
- Every visual is reproducible from a recipe committed in the guide project and records the source version it was captured from.
- Visuals are checked like any other claim, and every check works with text-only models (for example GLM through a non-multimodal harness). A multimodal model may look at the image as an extra, never as a requirement.
- When the tool changes, the pipeline notices (visual drift) and `evolve` recaptures.

Anti-goals (a failure even if it technically works):

- A screenshot that leaks a hostname, user name, local path, token, or cluster ID (the example CLI capture from the brainstorm session showed an OpenShift API hostname and `/Users/...` paths in the prompt and output).
- Visuals that only a multimodal model can verify, or drift that only a model's eye can detect.
- A capture that depends on the author's shell setup (prompt, theme, emoji) or on an existing personal environment.

## Approaches Considered

All approaches share: a podman capture container (browser, terminal renderer, CLI tools pinned to the guide's source pins), a throwaway tool environment, committed fictional seed data, text sidecars, and computed drift.

### A: Declarative recipes (chosen)

One `visuals.yaml` in the guide project declares the environment (plain podman container or kind cluster in podman), the seed step, and each visual as a list of steps (`goto`, `click`, `fill`, `highlight <selector> "<label>"`, `crop <selector>`, `run <command>` for CLI renders). A toolkit runner replays them inside the capture container.

- Pros: the model writes data, not code; a schema gate catches mistakes before a run; text-only reviewers can read every recipe; `evolve` diffs it like any other file.
- Cons: a small step language to build and maintain; unusual cases need a `script:` escape hatch.

### B: Playwright scripts per visual

Each visual is a small Playwright test using toolkit helpers (highlight, crop, sidecar, redact); Playwright's screenshot comparison gives drift.

- Pros: full flexibility, known ecosystem.
- Cons: generated code per visual is harder to gate and review; selectors in code break easily; CLI captures do not fit the test model and need a second mechanism.

### C: Agent drives the browser live (dropped as standalone)

The model explores the UI through a browser tool and shoots what it sees.

- Pros: no recipes to write.
- Cons: cannot run in CI without a model, needs a multimodal model, not reproducible. Conflicts with both core requirements.
- Kept as a helper inside A: the model may explore a live UI while authoring a recipe, but the committed output is always a replayable recipe.

## Decision

Approach A: declarative capture recipes in `visuals.yaml`, replayed by a toolkit runner inside a podman capture container, with a self-contained tool environment and committed seed data. Chosen because it keeps every visual reproducible, reviewable as text, and checkable by a script, and runs unattended in CI.

## Key Requirements

Scope agreed with the author:

- **v1 visual kinds:** web UI screenshots with annotations (highlight and numbered callouts placed by element selector, not pixel coordinates), panel crops by selector, and rendered CLI output.
- **Later, not v1:** animations (step filmstrips, terminal playback).
- **Bonus, not mandatory:** light and dark variants that follow the guide theme where the tool supports both.
- **Self-contained:** a capture run stands up its own environment and runs unattended in CI. The author's own clusters are not used.
- **Standalone tools only:** a screenshot may show the standalone tool (for example an `mlflow server` container) instead of its platform-embedded look. Platform-only UIs (for example the OpenShift AI dashboard) are skipped in v1.
- **Text-model compatible checks:** every capture writes a text sidecar (visible text and element structure of the captured region for web UIs, plain output for CLI renders); caption and page-text review run against the sidecar.
- **Visual drift:** computed by a script, combining a perceptual image difference with a diff of the text sidecar; findings go into the drift report and trigger recapture in `evolve`.

Proposed by Claude during the session (not stated by the author):

- CLI output is captured as text with its ANSI codes and rendered to SVG or HTML instead of a pixel screenshot, so it stays sharp, searchable, and diffable, and redaction is a text substitution. A neutral prompt (`$ command`) replaces the author's shell prompt.
- One command (for example `make visuals`) runs the whole capture: start the capture container, bring up the tool (podman container or kind cluster), seed demo data, replay recipes, redact, write visuals and sidecars, tear down.
- No network access during capture beyond pulling images, so runs are deterministic.
- Seed data is fictional and committed with the guide; redaction runs anyway as a safety net before anything is written.
- Each visual records the source version it was captured from.
- A visual counts as a claim: its caption must match the sidecar, and the reviewer checks it like a diagram's claims file.
- create: the plan proposes visuals per page, page tasks write recipes and seed data, one capture run produces all visuals, gates check existence, pinning, sidecar against caption, and that redaction ran.
- evolve: recapture after source drift; a way to add visuals to an existing guide, similar to `evolve --pages`.
- CI: the same capture command runs in a scheduled or PR job and can propose a pull request when visuals drift.
- PDF export uses the static images; nothing in v1 depends on interactive content.

## Parked Ideas

- **Pluggable capture providers.** A project could ship its own capture recipe (for example in the source repository the guide is written for) that reaches platform-only screens. This is the path to OpenShift AI and similar UIs that do not run in kind.
- **Animations.** Step filmstrips for UI flows and terminal playback with a static fallback frame for PDF.

## Open Questions

- Which renderer turns ANSI output into SVG or HTML, and how are Unicode block characters, emoji, and underlined links rendered faithfully?
- How does the recipe declare the tool environment: an image reference plus ports, a compose-like file, or a kind cluster with the guide's own install steps?
- How do the three adapters (Antora, MkDocs, gfm) embed SVG or HTML CLI renders, and what does the PDF export do with them?
- Thresholds for visual drift: which perceptual difference and which sidecar change count as a finding, and how are timestamps and other volatile values masked?
- Where do the capture container image definition and its version pins live, and is the image built per guide or shared by the plugin?
- How does a CI job without podman-in-podman (for example GitHub Actions runners) run the capture container and kind?
- How do redaction rules get configured per guide, and what is the default pattern set (hostnames, paths, tokens, user names)?
- What does the review of an annotated screenshot check: that the highlighted selector exists in the sidecar and that the callout label matches the page text?
