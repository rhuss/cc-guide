# Brainstorm: Antora branding for guides

**Date:** 2026-10-07
**Status:** active

## Problem Framing

Every Antora guide that cc-guide scaffolds looks like a Red Hat Demo Platform lab. Both playbooks (`site.yml`, `site-internal.yml`) hardcode the RHDP showroom UI bundle v2.0.3, and nothing in `guide.yaml` changes its look:

- The header logo is `img/logo-<site.keys.navbarLogo>.svg`, defaulting to `demo-platform` (the bundle also ships `summit`). Each logo is the Red Hat hat, a vertical divider, and a plain SVG `<text>` element.
- The `navbar-logo-alt` helper maps only `demo-platform` and `summit` and falls back to "Red Hat Demo Platform".
- The footer reads "Powered by Red Hat Demo Platform" and links to demo.redhat.com.

The first guide that needs its own look is the agentic-starter-kits guide (OpenClaw recipe first), which should read "Red Hat | Agent Starter Kits": same hat and divider, different text, and no RHDP footer. Its `/guide:create` run is paused until this lands, so the guide is scaffolded with branding from the start and serves as the first real user.

The PDF export does not inherit the site header: `make pdf` prints the `@antora/html-single-extension` output, which uses the built-in Asciidoctor.js converter and not the UI bundle. The PDF title page shows only the guide title, baseline date, and sources.

Antora's `ui.supplemental_files` overlays files onto a UI bundle without forking it, and `tools/guide/playbook.py` already rewrites that key to an absolute path for linked worktrees.

## Approaches Considered

### A: Overlay rendered at build time

`guide.yaml` `branding` is the single source. On each build, a toolkit script renders the logo SVG, the alt-text helper, the footer partial, the favicon, and the accent CSS into `build/`, merged with the author's `ui/supplemental/`. `playbook.py` injects `ui.supplemental_files` and `site.keys.navbarLogo` into the playbook it builds from. The PDF title page uses the same rendered logo.

- Pros: no generated files in git; one source of truth; existing guides adopt branding through the evolve toolkit refresh plus a `guide.yaml` block, without hand-editing `site.yml`; the bundle stays pinned and unforked.
- Cons: depends on bundle internals (partial names, the helper, the `navbarLogo` key), so a bundle upgrade can break the overlay silently unless a test guards it; branded guides build from a generated playbook instead of `site.yml` as is.

### B: Rendered once and committed

A `make branding` step writes the overlay files into `ui/supplemental/` and edits `site.yml`.

- Pros: what is in git is exactly what builds; `site.yml` stays authoritative.
- Cons: two sources of truth (`guide.yaml` and the generated files) can drift; every change needs a regeneration step; existing guides need `site.yml` edits.

### C: Own cc-guide UI bundle

Fork the RHDP showroom theme, make header and footer configurable through `site.keys`, and publish the bundle.

- Pros: clean configuration without overlaying internals; full control over the UI.
- Cons: a fork and a release pipeline to maintain; RHDP fixes must be followed by hand; heavy for a logo and a footer.

## Decision

Approach A, build-time overlay. Branding is configured per guide in `guide.yaml` (no shared presets), applies to the Antora site (both views) and the PDF title page, and leaves guides without a `branding` block exactly as they are today.

## Key Requirements

- An optional `branding` block in `guide.yaml`. Without it, the built site and PDF are unchanged from today (stock RHDP look).
- Logo: either `logo_text` (renders the Red Hat hat, the divider, and the text, like the bundle's own logos) or `logo` (a path to the author's SVG, for guides that are not Red Hat branded). The two are mutually exclusive.
- `logo_alt`: alt text for the header logo; replaces the "Red Hat Demo Platform" fallback.
- `footer`: `rhdp` (stock footer), `none` (no footer content), or `{text, url}` (for example "Agent Starter Kits on GitHub").
- `favicon`: a path to an icon that replaces the bundle's browser-tab icon.
- `color`: one accent color that overrides the header and link accent through a small CSS overlay.
- A free overlay directory `ui/supplemental/` in the guide project: any file there overlays the bundle (escape hatch for CSS or partials the block does not cover).
- Both Antora views (shareable and internal) carry the same branding.
- The PDF title page shows the branded logo.
- Rendering happens at build time from `guide.yaml`; no generated branding file is committed. Only branded guides build from a generated playbook.
- `adapter.yaml` declares which branding keys an adapter supports; `guidecfg.py validate` rejects keys the guide's adapter does not support (mkdocs and gfm support none in this iteration).
- The `/guide:create` intake asks for branding when the format is antora.
- Existing guides adopt branding through the evolve toolkit refresh plus the `guide.yaml` block.
- A contract smoke test fails when the pinned UI bundle no longer has the files, helper, or `site.keys.navbarLogo` lookup the overlay relies on.
- Paths in the block are relative to the guide project root and must stay inside it.

### Out of scope

- Branding for the MkDocs Material and gfm sites.
- Named or shared branding presets across guides.
- Forking or upgrading the RHDP UI bundle.
- Theming beyond one accent color.

## Open Questions

- Precedence between author files in `ui/supplemental/` and the generated branding files when both provide the same path (author wins as the escape hatch, or generated wins to keep the block authoritative).
- Footer default when a `branding` block exists but sets no `footer` (`none` avoids the misleading RHDP link; `rhdp` keeps today's output).
- Sizing the `logo_text` SVG (viewBox width) for long text without font metrics, so the header neither clips nor leaves a gap.
- Default `logo_alt` when omitted (for example "Red Hat <logo_text>" for the template, required for an own SVG).
- How the guide and docs state that the `logo_text` template renders the Red Hat logo and is meant for Red Hat-owned guides.
- Which CSS custom properties of the bundle the accent `color` overrides, and whether the same color reaches the PDF title page.
