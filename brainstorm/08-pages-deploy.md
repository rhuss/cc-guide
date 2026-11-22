# Brainstorm: Publish a guide with GitHub Pages from its own repository

**Date:** 2026-11-21
**Status:** active
**Source:** conversation (no issue yet)

## Intent

A guide built with Antora or MkDocs today has no hosted home. Readers either build it themselves or get a PDF from `/guide:export`. The author wants `/guide:create` to offer a GitHub Pages deployment from the guide's own repository, so the shareable view is reachable at `https://<owner>.github.io/<repo>/` without a separate pages repository and without a `gh-pages` branch. The audience is anyone on the web; GitHub Pages is the chosen host.

Success: after a create run that opted in, a push to `main` builds the shareable view in CI, leak-checks it, and publishes it, and the run summary names the URL.

## Goals

- One optional intake question in `/guide:create` for separate Antora and MkDocs guides.
- A workflow template `guide/templates/guide-pages.yml`, rendered like the drift and pull request check templates (section 11 of the create skill).
- Deployment through GitHub Actions (`actions/upload-pages-artifact`, `actions/deploy-pages`); no branch, no second repository, nothing committed back.

## Non-goals

- Adding Pages to existing guides (`/guide:evolve`, a `make pages-setup` target). Possible follow-up.
- GitLab Pages, custom domains, access-controlled hosting.
- gfm guides (they render on GitHub already) and embedded guides (always gfm, and the host repository may already use its one Pages site).

## Anti-goals (failure even if it works)

- The internal view, or anything that fails the leak check, reaches the public site.
- A half-written guide goes live while page tasks push during the create run.
- The author believes a private repository keeps the guide private.

## Approaches

- **A: workflow template installed at wrap-up (chosen).** Smallest change; follows the existing drift and pull request check pattern; installing the workflow only at the end keeps intermediate pushes from deploying.
- **B: A plus a toolkit script for existing guides.** Covers more but roughly doubles the work and touches `/guide:evolve`, which was not asked for.
- **C: local deploy (`mkdocs gh-deploy`, push to `gh-pages`).** Dropped: brings back the branch the author wants to avoid and skips the CI leak check.

## Design

### Intake (section 4)

New question after the remote repository question, asked only for a separate guide with format `antora` or `mkdocs`: "Publish the shareable view on GitHub Pages? (default no)". When the remote is (or will be) private, say before the answer: the published site is public on the web regardless of repository visibility, and serving Pages from a private repository needs a paid GitHub plan. The internal view is never published.

### Workflow template

`guide/templates/guide-pages.yml`, same header comment style as `guide-drift.yml`:

- Triggers: `push` to `main`, `workflow_dispatch`.
- Permissions: `contents: read`, `pages: write`, `id-token: write`; concurrency group `pages` without cancelling a running deployment.
- Build job: checkout (`persist-credentials: false`; full history, since the Antora playbook reads content from the local git repository at `HEAD`), set up Node and uv, `npm ci`, `make site`, then `uv run tools/guide/leakcheck.py build/site`, then upload `build/site`.
- Deploy job: `environment: github-pages`, `actions/deploy-pages`.
- No source fetch and no secrets: `make site` builds from committed pages and `baseline.yaml` attributes, so private sources need no token.
- Placeholders as in the other templates (`{{GUIDE_DIR}}` is always `.` here).

### Create flow (wrap-up, section 9)

When opted in, after the final review:

1. Check that `.github/workflows/guide-pages.yml` does not exist (never overwrite a workflow), then render the template.
2. Set the site URL when owner and repository are known: `site.url` in `site.yml` only (Antora; `playbook.py` copies it into generated playbooks; the internal view is never published, so `site-internal.yml` keeps no public URL) or `site_url` in `mkdocs.yml`. Links stay relative, so the site works under `/<repo>/` either way.
3. Record `pages.enabled: true` and `pages.url` in `guide.yaml`; `guidecfg.py validate` accepts the new block.
4. Commit `ci: publish the guide with GitHub Pages`.
5. When a GitHub remote exists, show `gh api -X POST repos/<owner>/<repo>/pages -f build_type=workflow` and run it only after explicit approval. Without a remote, put the command in the run summary for later.
6. Push only when the author opted into pushes. The run summary names the URL and repeats the visibility note for private repositories.

### Tests

- `tests/toolkit/test_workflows.py`: the rendered template parses; triggers, permissions, leak check before upload, `build/site` as the artifact path, no secrets referenced.
- `tests/toolkit/test_guidecfg.py`: the `pages` block validates and rejects bad values.

## Calls left to the builder (marked as my proposals)

- Exact shape of the `guide.yaml` block (`pages.enabled` plus `pages.url` proposed).
- Whether `site.url` lives in the committed playbooks or is injected only by `playbook.py`.
- Action versions, pinned to current majors like the existing templates.
- What a run reports when the author declines enabling Pages: the deploy job fails until Pages is switched on; the run summary must say so.

## Follow-up (2026-11-22): `/guide:evolve --pages` for existing guides

### Intent

Guides created before the Pages option should get the same setup without waiting for drift. Some existing Antora and MkDocs guides live in a subdirectory of a code repository (for example `docs/guide/`, found by nested discovery); they publish from that same repository, never from a new remote.

### Finding

An Antora guide in a subdirectory does not build today, locally or in CI: Antora requires a local content source (`url: .`) to be the root of a git repository and fails with "Local content source must be a git repository". A playbook whose source points at the git root with `start_path: docs/guide/content` builds (verified on a scratch host repository, 5 pages). MkDocs does not read git and is unaffected.

### Approaches

- **A: a separate mode `/guide:evolve --pages` (chosen).** Like `--check` and `--adopt`: no drift run, no superpowers, no subagents. Pages setup is unrelated to drift, so it must not wait for a source change.
- **B: an offer inside a regular evolve run.** Dropped: only reachable when sources drifted.
- **C: a new `/guide:pages` command.** Dropped: more surface (command, skill, preflight wiring) for the same steps.

### Design

- **Toolkit (`playbook.py`)**: when the guide root is not the top level of its git working tree, generate the playbook and point every `url: .` content source at the working tree's top level (the main repository for a linked worktree, as today) with `start_path` prefixed by the guide's path inside the repository (`git rev-parse --show-prefix`). This also fixes local builds, preview, and PDF for such guides.
- **Toolkit version** 0.5.0; evolve's toolkit note names the `pages` block and `--pages`. Plugin manifest versions stay unchanged.
- **Workflow template**: the upload `path` becomes `{{GUIDE_DIR}}/build/site` (the working-directory default applies to `run` steps only). Create keeps rendering `{{GUIDE_DIR}}` as `.`.
- **Evolve `--pages` mode**: refuses gfm and embedded guides; offers the toolkit refresh first when `tools/guide/VERSION` is below 0.5.0; finds the git root (`git rev-parse --show-toplevel`) and the guide's path in it; refuses when `<git root>/.github/workflows/guide-pages.yml` exists; reads owner and repository from `origin` (an existing GitHub remote is required); stops when `gh api repos/<owner>/<repo>/pages` shows an existing Pages site (one site per repository); warns for a private repository (`gh repo view --json visibility`); then follows create section 9 step 2 with the workflow at the git root and `{{GUIDE_DIR}}` set to the guide path. `gh api` and push only after approval. Commits stay local otherwise.
- **Preflight and the command wrapper**: `--pages` needs neither superpowers nor parallel subagents.
- **Tests**: `playbook.py` for a guide in a subdirectory (main checkout and linked worktree), the workflow upload path for `.` and a subdirectory, the evolve, preflight, and command texts, and the toolkit version.
