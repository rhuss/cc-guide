# Embedded guides

An embedded guide lives inside the repository it documents. Its machinery sits in one subdirectory (default `guide/`), and the repository's root `README.md` becomes the guide's front page: a visitor on GitHub lands on a source-verified introduction with links to each persona's pages. `/guide:evolve` keeps the README current as the code changes.

## When to choose it

| Choose | When |
|---|---|
| Embedded (`/guide:create --embedded`, or create from the root of an existing repository) | The guide documents one code repository, its readers arrive through that repository, and GitHub Markdown is enough |
| A separate guide repository | The guide spans several repositories, needs internal pages, or uses Antora or MkDocs |

Embedded mode is offered when create runs at the root of an existing git repository that is not a guide project. An empty directory always gets a separate guide.

## Limits in this release

- GitHub Markdown (`gfm`) only. Antora and MkDocs guides live in their own repository.
- No internal part. Everything in the repository is visible to its readers.
- The repository root only; a subdirectory of a monorepo is not a valid target.
- The workflows (scheduled drift check, pull request check) require a GitHub-hosted repository.

## Layout

```text
<repository>/
├── README.md              # the front page (owned by the guide)
├── DEVELOPMENT.md         # the developer README (moved development material)
├── LICENSE                # stays where it is
├── docs/install.md        # a stub when its content moved into the guide
├── .github/workflows/     # guide-drift.yml and guide-pr-check.yml, when opted in
└── guide/                 # everything else: guide.yaml, baseline.yaml, inputs.yaml,
    ├── docs/              #   toolkit, Makefile, pages, diagrams, caches, run data
    │   └── README.md      # one-line pointer to the front page
    └── tools/guide/
```

Outside the guide subdirectory, create changes only the front page, the developer README, stubs, files the approved move plan names, and the workflows you opted into. The host's own build files, package files, ignore rules, and documentation directories stay as they are.

## Consolidation and the move plan

Before it writes anything outside the guide subdirectory, create takes stock of the existing documentation (`tools/guide/embed.py inventory`): the README in any format, a `.github/README*` (GitHub shows it instead of the root README), `CONTRIBUTING`, `INSTALL`, `USAGE`, `CHANGELOG`, community health files, `docs/`, `doc/`, `documentation/`, and documentation sites. It proposes a destination for every file, or for every section of a file that mixes audiences:

| Destination | What happens |
|---|---|
| `input` | User-facing material becomes guide input. Its claims are verified against the pinned sources; only verified facts reach the guide, and text is never copied. Claims the code contradicts are dropped and listed in the run summary. |
| `developer` | Development material moves to the developer README, text unchanged except heading levels and relative links. |
| `keep` | `LICENSE`, community health files where GitHub finds them, the changelog, and by default an existing documentation site (the site stays in place; its pages are also read as input). |
| `remove` (with `stub`) | The file is absorbed into the guide and replaced by a stub. |
| `relocate` | The file moves, for example a `.github/README.md` that would hide the front page. |

You see the whole plan, change any destination, and approve it. Nothing outside the guide subdirectory changes before that, and declining leaves the repository as it was.

## The front page

The root README is a guide page: it has a source block, goes through the same page task and review as any other page, and the checks validate it. Its first line says that the guide owns it:

```markdown
<!-- guide: front page. This file is generated and maintained by cc-guide; change it with /guide:evolve. -->
```

Badges and a logo from the old README stay at the top, unverified. Then come the source block, the why card (what the project is for and why a reader wants it), one link per persona entry page, and links to the developer README, `LICENSE`, and `CONTRIBUTING`. When a package manifest publishes the README to a registry (for example `readme = "README.md"` in `pyproject.toml`), the move plan offers absolute links so the page renders outside GitHub.

Edit the front page with `/guide:evolve`. When someone edits it by hand, evolve shows the diff against the version it recorded and asks before it overwrites anything.

## Stubs

Every removed documentation path keeps a stub, so links from blog posts, issues, and other repositories still work:

```markdown
<!-- guide: moved -->
# Installation

This page moved to [Installation](../guide/docs/admin/install.md).
```

Stubs are listed in `guide.yaml` (`embedded.stubs`). The checks verify their links and skip the page rules. Evolve updates their links when a page is renamed or removed. They stay until you delete them.

## The developer README

`DEVELOPMENT.md` (or the path you chose) receives the development sections of the old README. The project's developers maintain it, so the guide moves its text without rewriting it, and the checks verify only that its relative links resolve. When the file already exists, the moved sections are appended under `## Moved from the README`.

## The `self` source and fingerprints

The host repository is a pinned source with the reserved id `self` (`repo: ..`). It is read straight from the local repository, so private repositories need no extra credentials, and only committed content counts. The subagents that write and review pages read a snapshot of every tracked file at the pinned commit, exported outside the repository (`uv run tools/guide/fetch.py where self` prints it); the host code is never copied into the host repository.

Pages may not cite guide material (`self:guide/...`, the front page, the developer README, or a stub): the guide must not verify itself against its own text.

The baseline records a fingerprint (the git blob id) for every host file the pages cite. Drift for `self` compares those fingerprints with the cited files at the checked-out commit (the default branch in the scheduled workflow), so:

- commits that change only guide files are never drift,
- squash and rebase merges do not break the check, even when the pinned commit is gone.

## Pull request check

Create offers an optional workflow (`.github/workflows/guide-pr-check.yml`) that runs on every pull request. It looks only at the `self` source. Pull requests that touch no cited file pass. A pull request that changes files guide pages cite fails unless it also re-verified the guide: the `self` entry of `baseline.yaml` changed, and its fingerprints match the cited files at the pull request's head (running `/guide:evolve` on the branch does both). It needs no AI session, no tokens, and only read permission.

Maintainers add the label `guide-skip` to a pull request that does not change documented behavior; the check then passes and says the update was skipped by request. Whether the check blocks merging is up to your branch protection.

The scheduled drift check (`guide-drift.yml`) remains a separate offer; in embedded mode both workflows run with the guide subdirectory as their working directory.

## Confidential terms

An embedded guide's `guide.yaml` is public with the repository, so confidential terms, patterns, and the real locations of confidential inputs live in `guide/confidential.local.yaml`, which git ignores. The checks and the leak check still read it. Confidential inputs are registered as `local:<id>`, and run summaries, findings, and drift reports name them by id only.

```yaml
confidential_terms: [ACME Corp]
confidential_patterns: ['\b[A-Z]{2,}-\d+\b']
inputs:
  call-2026-10: ~/transcripts/acme-call.txt
```

## Commands

All guide commands work from the repository root: they find the embedded guide in its subdirectory. Inside the guide subdirectory they work as in a separate guide. `make -C guide preview` serves the repository and opens the front page as GitHub would show it; `make -C guide pdf` prints the front page first.

## Reference: the move plan file

Create writes the plan to `guide/.guide/runs/<run-id>/move-plan.yaml` (local, never committed), shows it, and runs `tools/guide/embed.py apply` on it after your approval. Paths are relative to the guide subdirectory.

```yaml
self_revision: 0123...              # the host commit the inventory ran at (full SHA)
developer_readme: ../DEVELOPMENT.md
developer_readme_exists: false
entries:
  - path: ../README.md               # the whole file: read as input, replaced by the front page
    section: null
    destination: input
  - path: ../README.md               # one section, by its heading text
    section: Building from source
    destination: developer
  - path: ../docs/install.md         # read as input, then replaced by a stub
    destination: input
    stub: true
  - path: ../.github/README.md
    destination: relocate
    to: ../.github/README.old.md
manifests:
  - path: ../pyproject.toml
    publishes_readme: true
absolute_links: true                 # front page links as <web>/blob/<ref>/... URLs
```

`apply` refuses the plan and changes nothing when:

- the host has uncommitted changes outside the guide subdirectory,
- a path does not exist at `self_revision`, or a section is not found,
- a license or community health file would be removed or moved where GitHub no longer finds it,
- a file that is not documentation would be removed, or a documentation file would be removed without a stub,
- a stub would sit on a root or `.github` README,
- a directory is named for removal (name its files). A Markdown root README takes only `input` and `developer` sections; a non-Markdown one is `input` plus `remove` or `relocate`, so there is never a second root README.
