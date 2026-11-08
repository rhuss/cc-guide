# Quickstart: validating the embedded guide

Prerequisites: the plugin checkout, `uv`, `node` 20+, `npx`, `pandoc` 3+, Playwright Chromium (as for `make test-adapters`).

## 1. Automated checks

```bash
make test             # toolkit unit tests, including the new embedded tests
make test-adapters    # adds tests/adapters/test_gfm_embedded.sh
make validate
```

Expected: all pass; the existing gfm, mkdocs, and antora smoke tests are unchanged (SC-008).

## 2. Embedded smoke test (what `test_gfm_embedded.sh` asserts)

1. Build a host repository from `tests/fixtures/mini-host/` (README with user and developer sections, `CONTRIBUTING.md`, `LICENSE`, `docs/install.md`, a `Makefile`, a `pyproject.toml` with `readme = "README.md"`).
2. `scaffold-project.sh --embedded --format gfm --title Mini host/guide`; pin `self=..`; write an approved move plan fixture; `embed.py apply --plan`.
3. Install fixture pages and a fixture front page (with a sources block citing `self`), then `make -C host/guide check dist print-pdf`.

Expected:
- `check` passes; `build/site/README.html` (or `index.html`) contains the front page title; the PDF's first content page is the front page.
- `cmp` shows the host `Makefile` and `pyproject.toml` unchanged; `LICENSE` is still at the root.
- `docs/install.md` is a stub with a resolving link; `DEVELOPMENT.md` holds the developer sections with working relative links.
- A page citing `self:guide/docs/x.md` makes `check` fail.
- Committing a change to a guide page only: `drift.py --check` exits 0. Changing a cited file: exits 10 and lists `../README.md` among affected pages.
- Squash simulation: rewrite history so the pinned commit is unreachable (reuse `_rewrite_history` from `tests/toolkit/test_drift.py`); `drift.py --check` reports no `pin-missing` and no false drift.
- PR mode: `drift.py --pr --base <base>` exits 10 when a cited file changed without a baseline update, 0 with `GUIDE_SKIP=1`, 0 after a rebaseline whose fingerprints match.

## 3. Manual run with Claude Code

In a scratch copy of a real repository with a README and some docs:

```bash
git clone <repo> /tmp/embedded-try && cd /tmp/embedded-try
claude   # then: /guide:create --embedded
```

Check by hand:
- The move plan is shown before anything outside `guide/` changes; declining leaves `git status` clean outside `guide/`.
- After approval and the run: GitHub-style rendering of `README.md` (for example `make -C guide preview`) shows the front page with working persona links and the developer README link.
- `/guide:evolve --check` from the repository root finds the guide without `--dir`.
- Edit `README.md` by hand, run `/guide:evolve`: the hand edit is reported before any update.

Record the run in `tests/manual/` like the earlier quickstart runs.
