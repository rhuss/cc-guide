# Brainstorm: create sets up an Antora or MkDocs guide inside an existing repository

**Date:** 2026-11-23
**Status:** active
**Source:** conversation, option A set aside in #10 and then chosen as the near-term step

## Intent

`/guide:create` offers only the gfm embedded mode at a repository root and stops in a subdirectory of a repository, so an Antora or MkDocs guide can live in a code repository only by creating it elsewhere and moving it in. Since #08 such a guide builds there and publishes with `/guide:evolve --pages`. Create should set it up directly, in a subdirectory such as `docs/guide/`, with the README untouched. The guide's sources are pinned like in a separate guide; the host repository can be one of them.

## Non-goals

The `self` source with fingerprint drift, the pull request check, README changes, and consolidating existing docs. Those belong to #10.

## Approaches

- **A: an in-repo guide in create (chosen).** One more target case in create section 3, the embedded preconditions reused, the separate-guide intake with a few changes, and a small toolkit change for confidential data.
- **B: document the manual move.** Dropped: the author asked for create to do it.
- **C: wait for #10.** Dropped: #10 is a large project; this is the near-term step it builds on.

## Design

1. **Target (create section 3)**: at a repository root, ask whether to embed a gfm guide (the README becomes the front page) or add an Antora or MkDocs guide in a subdirectory (README untouched; default `docs/guide`). `--format antora|mkdocs` at a repository root selects the in-repo guide instead of being refused. In a subdirectory of a repository that is empty or does not exist yet, offer the in-repo guide there instead of stopping.
2. **Preconditions**: the embedded ones (clean tree; a working branch offered on the default branch).
3. **Intake**: the separate-guide intake without the remote question (the repository's `origin` is used) and without an internal part (code repositories are often public); format antora or mkdocs; drift check and Pages offered.
4. **Setup**: no `git init`; `scaffold-project.sh --in-repo` skips `internal/` and git-ignores `confidential.local.yaml`; confidential terms, patterns, and the real locations of confidential inputs (`local:<id>`) go to that file, never into committed files.
5. **Toolkit**: `guidecfg.py` reads `confidential.local.yaml` and accepts `local:` inputs for a guide inside a git repository but not at its top level (an in-repo guide), as it does for embedded guides. It does not require them there, so guides already moved into a repository keep validating.
6. **Workflows**: the drift and Pages workflows go to the repository root's `.github/workflows/`, with `{{GUIDE_DIR}}` set to the guide's path and `{{BRANCH}}` to the default branch; Pages first runs the read-only checks of `/guide:evolve --pages` (GitHub `origin`, existing Pages site, visibility and branch).
7. **Tests**: local file and `local:` inputs for in-repo guides (and still ignored for a guide at its own repository root), the scaffold flag, the create skill text.
