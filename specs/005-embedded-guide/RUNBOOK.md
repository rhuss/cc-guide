---
runbook_version: 1
feature: 005-embedded-guide
status: drafted
mode: light
steps_total: 8
step_results: pending,pending,pending,pending,pending,pending,pending,pending
drafted_at: bedf18d
drafted_fingerprint: cd8bb43a2117839eac575b8eb4456280cfd012cf1745256f841bb599a26267d0
tested_at:
tested_fingerprint:
updated: 2026-11-07
---

# Try it: Embedded guide with the README as front page

<!-- runbook-status -->
> **Status:** drafted · 0 of 8 steps · Mode: light · Drafted at bedf18d · 2026-11-07
<!-- /runbook-status -->

## What you're testing

You turn a small existing repository (the Mini Host fixture: a README with user and developer sections, `CONTRIBUTING.md`, `LICENSE`, `docs/install.md`, its own `Makefile` and `pyproject.toml`) into a repository with an embedded guide. The journey follows the order an author meets the feature:

1. Create the host repository.
2. Scaffold the guide into `guide/` and let the toolkit find it from the host root.
3. Take stock of the existing documentation.
4. Pin the host as the `self` source.
5. Preview and apply a move plan: development sections move to `DEVELOPMENT.md`, `docs/install.md` becomes a stub, nothing else outside `guide/` changes.
6. Run the full embedded smoke test, which adds pages and a front page, builds the site and the PDF, and exercises drift, squash safety, stubs, and the pull request check.

Run every command from the root of the cc-guide plugin checkout (the directory with `guide/` and `tests/`). The scratch host lives in `/tmp/cc-guide-embedded-try` and is removed in the last step.

## Test environment

No fixtures. The journey uses a throwaway git repository in `/tmp/cc-guide-embedded-try` and the tools `make test-adapters` already needs (`uv`, `git`, `node`, `npx`, `pandoc`, Playwright Chromium).

## Steps

### Step 1 of 8: Create the host repository (US1)

**Why this step:** Embedded mode is for existing repositories, so the journey starts with one that has a hand-written README and loose docs.

**Needs:** nothing

**Run:**

```
rm -rf /tmp/cc-guide-embedded-try && mkdir -p /tmp/cc-guide-embedded-try && cp -R tests/fixtures/mini-host /tmp/cc-guide-embedded-try/host && git -C /tmp/cc-guide-embedded-try/host init --quiet -b main && git -C /tmp/cc-guide-embedded-try/host add -A && git -C /tmp/cc-guide-embedded-try/host -c commit.gpgsign=false commit --quiet -m "Initial Mini Host" && git -C /tmp/cc-guide-embedded-try/host ls-files
```

**What you should see:** a list of tracked files including `README.md`, `CONTRIBUTING.md`, `LICENSE`, `Makefile`, `pyproject.toml`, `USAGE.md`, `docs/install.md`, `src/cli.py`, and `config/defaults.yaml`.

**If you see something else:** an error from `cp` means you are not in the plugin checkout root; a git identity error means `user.name`/`user.email` are unset (set them or export `GIT_AUTHOR_NAME` and friends).

**Result:**

### Step 2 of 8: Scaffold the embedded guide (US1)

**Why this step:** The guide machinery must live in one subdirectory, without an internal part, and with a pointer page instead of a second front page (FR-002, FR-006, FR-008a).

**Needs:** Step 1

**Run:**

```
bash guide/scripts/scaffold-project.sh --format gfm --title "Mini Host" --embedded /tmp/cc-guide-embedded-try/host/guide && ls /tmp/cc-guide-embedded-try/host/guide && cat /tmp/cc-guide-embedded-try/host/guide/docs/README.md && grep -n confidential.local.yaml /tmp/cc-guide-embedded-try/host/guide/.gitignore
```

**What you should see:** the scaffold output, then a listing with `Makefile`, `package.json`, `docs`, and `tools` but no `internal`; a one-line pointer page linking `../../README.md`; and a `.gitignore` line for `confidential.local.yaml`.

**If you see something else:** an `internal` directory means the `--embedded` flag was ignored; a refusal mentioning the format means the flag combination was wrong.

**Result:**

### Step 3 of 8: Configure the guide and find it from the host root (US1)

**Why this step:** Every guide command run from the host root must find the embedded guide on its own (FR-031), and the configuration must pass the embedded rules (FR-004).

**Needs:** Step 2

**Run:**

```
printf '%s\n' 'schema: 1' 'title: "Mini Host"' 'format: gfm' 'personas:' '  - id: admin' '    title: Administrator' '    start: admin/install' 'sections:' '  - id: overview' '    title: Overview' '    voice: concepts' '  - id: admin' '    title: Admin guide' '    voice: technical' 'rigor: standard' 'internal:' '  enabled: false' '  confidential_terms: []' '  confidential_patterns: []' 'embedded:' '  front_page: ../README.md' '  stubs: []' '  pr_check: off' > /tmp/cc-guide-embedded-try/host/guide/guide.yaml && printf 'rules: []\n' > /tmp/cc-guide-embedded-try/host/guide/guide-rules.yaml && uv run --quiet guide/toolkit/guidecfg.py discover --dir /tmp/cc-guide-embedded-try/host
```

**What you should see:** one line, the absolute path of `/tmp/cc-guide-embedded-try/host/guide` (on macOS it may start with `/private/tmp`).

**If you see something else:** exit 4 with "no guide" means `guide.yaml` has no `embedded` block; a configuration error names the failing key.

**Result:**

### Step 4 of 8: Take stock of the existing documentation (US1)

**Why this step:** Consolidation starts with an inventory of what the repository already documents, and flags manifests that publish the README to a package registry (FR-016, FR-010a).

**Needs:** Step 3

**Run:**

```
cd /tmp/cc-guide-embedded-try/host/guide && uv run --quiet tools/guide/embed.py inventory; cd - >/dev/null
```

**What you should see:** YAML listing `README.md` (kind `readme`, with its headings such as `Install`, `Usage`, `Building from source`, `Running tests`), `CONTRIBUTING.md` (`community`), `LICENSE` (`license`), `USAGE.md` and `docs/install.md` (`doc-file`), the `docs` directory, and `pyproject.toml` flagged as publishing the README. Nothing under `guide/` appears.

**If you see something else:** files from `guide/` in the list would mean the inventory sweeps the guide's own files (a bug).

**Result:**

### Step 5 of 8: Pin the host as the self source (US2)

**Why this step:** The host repository is verified like any other source, pinned to a commit, read from the local repository and never cloned into itself (FR-011).

**Needs:** Step 3

**Run:**

```
cd /tmp/cc-guide-embedded-try/host/guide && XDG_CACHE_HOME=/tmp/cc-guide-embedded-try/xdg uv run --quiet tools/guide/fetch.py pin --source self=.. && cat baseline.yaml && ls .guide/cache 2>/dev/null; git -C .. status --porcelain -- . ':(exclude)guide'; cd - >/dev/null
```

**What you should see:** a `baseline.yaml` with a `self` source (`repo: ..`, `ref: main`, a 40-character `commit`, and a `fingerprints` entry, empty because no page cites anything yet); no `self` directory under `.guide/cache`; and an empty `git status` outside `guide/`.

**If you see something else:** a `.guide/cache/self` directory would mean the host was cloned into itself; any path listed by `git status` means something outside `guide/` changed before the move plan.

**Result:**

### Step 6 of 8: Preview the move plan (US1, US3)

**Why this step:** Nothing outside `guide/` may change before the author approves; the dry run shows exactly what would happen (FR-018).

**Needs:** Step 5

**Run:**

```
cd /tmp/cc-guide-embedded-try/host/guide && mkdir -p .guide/runs/try && printf '%s\n' "self_revision: $(git -C .. rev-parse HEAD)" 'developer_readme: ../DEVELOPMENT.md' 'developer_readme_exists: false' 'entries:' '  - {path: ../README.md, section: null, destination: input}' '  - {path: ../README.md, section: Building from source, destination: developer}' '  - {path: ../README.md, section: Running tests, destination: developer}' '  - {path: ../CONTRIBUTING.md, destination: keep}' '  - {path: ../LICENSE, destination: keep}' '  - {path: ../docs/install.md, destination: input, stub: true}' 'manifests:' '  - {path: ../pyproject.toml, publishes_readme: true}' 'absolute_links: false' > .guide/runs/try/move-plan.yaml && uv run --quiet tools/guide/embed.py apply --plan .guide/runs/try/move-plan.yaml --dry-run; git -C .. status --porcelain -- . ':(exclude)guide'; cd - >/dev/null
```

**What you should see:** a list of planned operations (move two README sections to `DEVELOPMENT.md`, register inputs, write a stub at `docs/install.md`) ending with `(dry run, nothing changed)`, followed by an empty `git status` outside `guide/`.

**If you see something else:** exit 2 with a refusal names the plan entry it rejects; any `git status` output means the dry run changed files (a bug).

**Result:**

### Step 7 of 8: Apply the move plan and inspect the result (US1, US3)

**Why this step:** Development material moves with its text unchanged (links rewritten), the removed doc path keeps a stub, and `LICENSE` stays at the root (FR-021, FR-022, FR-023).

**Needs:** Step 6

**Run:**

```
cd /tmp/cc-guide-embedded-try/host/guide && uv run --quiet tools/guide/embed.py apply --plan .guide/runs/try/move-plan.yaml && cat ../DEVELOPMENT.md && cat ../docs/install.md && grep -A3 '^embedded:' guide.yaml && git -C .. status --porcelain -- . ':(exclude)guide'; cd - >/dev/null
```

**What you should see:** `apply: N operation(s)`; `DEVELOPMENT.md` with `## Building from source` and `## Running tests` and working relative links; `docs/install.md` reduced to the `<!-- guide: moved -->` marker, one heading, and one link to the front page; `guide.yaml` now listing `developer_readme` and the stub; `git status` outside `guide/` showing only `DEVELOPMENT.md`, `README.md`, and `docs/install.md`.

**If you see something else:** `LICENSE` or `CONTRIBUTING.md` in the status output would violate the keep entries; a refusal about a dirty tree means files outside `guide/` were modified by hand.

**Result:**

### Step 8 of 8: Build, print, and exercise drift and the pull request check (US1, US2, US3, US4)

**Why this step:** The smoke test completes the journey with real pages and a front page: the site and PDF start with the README, guide-only commits are not drift, cited changes are, a squash merge causes no false drift, stubs keep resolving, and the pull request check fails and skips as specified.

**Needs:** nothing (it builds its own host); run from the plugin checkout root

**Run:**

```
rm -rf /tmp/cc-guide-embedded-try && bash tests/adapters/test_gfm_embedded.sh
```

**What you should see:** only `PASS gfm-embedded: ...` lines (about 26), including "the PDF starts with the front page", "outside guide/ only README.md, DEVELOPMENT.md, and the stub changed", the drift checks, and the pull request checks; exit status 0.

**If you see something else:** any `FAIL gfm-embedded:` line names the broken behavior; rerun with `KEEP=1` to keep the temporary host for inspection. A missing tool (pandoc, Chromium) fails the build steps.

**Result:**

## Not covered here

- The interactive `/guide:create --embedded` run (intake, classification of README sections, the move plan table, page writing by subagents, and the final review) needs a live Claude Code session with superpowers installed. Its procedure is in `tests/manual/embedded-quickstart.md`, marked "not yet run".
- `/guide:evolve` hand-edit reporting through the skill (the toolkit side, `embed.py front-page-status`, is covered by `make test`).
- The GitHub workflows running on GitHub itself; the smoke test runs the same `drift.py --pr` command locally.

## Coverage

- US1 (front page in an existing repository): steps 1 to 4, 6, 7, and 8.
- US2 (evolve keeps the README current): steps 5 and 8 (drift and squash safety); the evolve skill itself is not covered (see above).
- US3 (old links keep working): steps 6 to 8.
- US4 (pull request check): step 8, locally.
- US5 (separate guides unchanged): not covered by this journey; `make test` and `make test-adapters` cover it.

## Results
