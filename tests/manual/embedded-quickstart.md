# Manual run: embedded guide (specs/005-embedded-guide, quickstart section 3)

**Status: not yet run.** The implementation session that added embedded mode could not drive an interactive `/guide:create` run (it needs a live Claude Code session with the author answering the intake and approving the move plan). The automated parts of the quickstart ran instead: `make test` and `tests/adapters/test_gfm_embedded.sh`, which builds a host repository, scaffolds, pins, applies a move plan with a stub, checks, prints, and exercises drift and the pull request mode. Record the manual run here when it happens, as in the earlier records in this directory.

## Procedure

In a scratch copy of a real repository with a README and some documentation:

```bash
git clone <repo> /tmp/embedded-try && cd /tmp/embedded-try
claude   # then: /guide:create --embedded
```

1. Create offers embedded mode at the repository root (or `--embedded` skips the question). On the default branch it offers a working branch first.
2. The intake asks for the guide subdirectory (default `guide`), the developer README (default `DEVELOPMENT.md`), and the optional pull request check; it does not ask for the format, an internal part, or a remote.
3. The move plan is shown before anything outside `guide/` changes. Decline once: `git status --porcelain -- . ':(exclude)guide'` must be empty, and create offers to remove the uncommitted `guide/`.
4. Run again and approve the plan. After the run:
   - `README.md` starts with the ownership comment, keeps the badges, has a source block, persona links, and a link to `DEVELOPMENT.md`.
   - `make -C guide preview` shows the front page as GitHub would, with working persona links and the developer README link.
   - Removed documentation paths are stubs that link to the guide pages.
5. From the repository root, `/guide:evolve --check` finds the guide without `--dir`.
6. Edit `README.md` by hand and run `/guide:evolve`: the hand edit is reported with a diff before any update.

## Observations

Not yet run.

## Deviations

Not yet run.
