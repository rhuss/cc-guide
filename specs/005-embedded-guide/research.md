# Research: Embedded guide with the README as front page

All decisions below come from reading the current toolkit, adapter, and skills (references are to files in this repository). Each records the decision, the rationale, and the alternatives considered.

## R1. Where embedded settings live

- **Decision**: A new top-level `embedded` block in `guide.yaml` with `front_page` (default `../README.md`), `developer_readme` (default `../DEVELOPMENT.md`), `stubs` (list of host paths), and `pr_check` (`off` or `on`). All paths are relative to the guide root, like every other path in `guide.yaml`. `guidecfg.GUIDE_KEYS` (guidecfg.py:315) gains `embedded`; FR-004 checks run just before `raise_if_any` (guidecfg.py:417).
- **Rationale**: One file already carries every guide setting, and unknown keys are errors, so the block is self-validating. Listing stubs in the configuration lets the checks find them without scanning the host repository (no repository sweep).
- **Alternatives**: a separate `embedded.yaml` (one more file for no gain); detecting stubs only by a marker comment (requires walking the whole host repository on every check).

## R2. Front page as a page

- **Decision**: `guidecfg.pages()` (guidecfg.py:567) appends the front page in embedded mode, so check, drift, sources, ledger, and attrs see it through the single page enumerator. `drift._rel` (drift.py:221) gets the same outside-root fallback `check._rel` already has. `attrs.py` region rewriting and the dash check include the front page explicitly.
- **Rationale**: Every consumer already goes through `pages()`; adding the page there is the smallest change that reaches all of them. The `_rel` crash is the one place that would fail on a path outside the root.
- **Alternatives**: copying the front page into `docs/` on every build and treating the copy as the page (two sources of truth, and evolve would edit the copy).

## R3. Building the site and the PDF with a page outside the guide root

- **Decision**: A staging step (`embed.py stage`) writes `build/stage/docs/`: a copy of `docs/` in which `README.md` (the pointer) is replaced by the front page, with the front page's links rewritten (`guide/docs/x.md` to `x.md`, images likewise, host files such as `DEVELOPMENT.md` or `LICENSE` to absolute repository URLs when the `self` web URL is known). `render.sh` and `print.sh` take the docs directory as a parameter (default `docs`), and the gfm Makefile passes the staged directory when the guide is embedded. The leak check then sees the front page in `build/site`.
- **Links back to the front page**: staged guide pages that link to the front page (for example `../../README.md`, and the pointer page) are rewritten to the staged `README.md`.
- **Rationale**: The renderer, the PDF printer, and the leak check all assume one docs tree (render.sh:13-43, print.sh:14-31, print.lua:28-68). Staging keeps them unchanged apart from a directory parameter and avoids the `README` key collision, the silent `..` drop in `print.lua`, and a host-root image base. The standalone layout stays byte-identical because the default parameter is `docs`.
- **Alternatives**: teaching `links.lua`, `print.lua`, and `print-pdf.mjs` about a page outside the root (three places with path logic, each with a known silent failure mode); rendering the whole host repository (sweeps unrelated files).

## R4. Reading the `self` source

- **Decision**: `self` is a baseline source with `repo: ..` (the host repository, resolved with `git -C <guide root> rev-parse --show-toplevel`). It is never cloned into `.guide/cache/`. `fetch.py` reads it straight from the host repository's git directory (`git -C <toplevel> ...`), and the snapshot that page writers and reviewers read is exported (`git read-tree <commit>` into a temporary index, then `git checkout-index --all --prefix`) into a directory outside the host repository: `${XDG_CACHE_HOME:-~/.cache}/cc-guide/self/<hash of the toplevel path>/<commit>/`. A new `fetch.py where <id>` prints the readable snapshot path for any source, and the skills use it instead of hard-coding `.guide/cache/<id>/`.
- **Rationale**: A clone or worktree under `guide/.guide/cache/self/` would put a second copy of the host code inside the host repository, where its test runners and linters may pick it up (research report on fetch.py:151-192). Reading the local repository needs no credentials for private hosts and only sees committed content (FR-011).
- **Export method**: read-tree plus checkout-index writes every tracked file straight to disk as committed. `git archive` was the first choice and was replaced: it drops paths with the `export-ignore` attribute, and extracting its tar with the data filter aborts on a symlink that points outside the tree.
- **Alternatives**: a blobless clone like other sources (duplicate code inside the repository); a `git worktree` of the host (worktree metadata in the host `.git`, and the checkout must still live somewhere outside); reading the working tree (violates FR-011).

## R5. Squash-safe drift for `self`

- **Decision**: The baseline `self` entry gains `fingerprints`: a map from each cited path to its git blob id at the pinned commit (`git rev-parse <commit>:<path>`). `fetch.py pin` and `rebaseline` compute it from the citations of all pages. Drift for `self` compares each fingerprint with the blob id at the checked-out head (spec FR-014; the scheduled workflow checks out the default branch, and on a working branch the guide is compared with the code beside it): equal means unchanged, different means modified, missing means deleted. It never calls `_pin_reachable` for `self` and never reports `pin-missing` because the pin is unreachable. When the pin is still reachable, it adds the commit log and rename detection as extra information.
- **Rationale**: Blob ids depend only on content, so they survive squash and rebase merges and need only the head checkout, which also works in shallow CI checkouts.
- **Tracked ref**: `ref` is the host's default branch, not the working branch the pin was taken on, so the comparison and the links survive branch deletion.
- **Missing pinned commit** (fresh clone after a squash merge): `self` falls back on content. Citations resolve from the fingerprint blob ids (`git cat-file blob <id>`, present whenever the content still exists in reachable history). When every fingerprint matches the tracked branch head, the reading snapshot is exported from that head. When some do not, the source is reported as drifted with "pin unavailable" and evolve is the remedy; check resolves those citations against the head and warns instead of failing on the missing commit. Alternatives rejected: pushing a keep-alive ref on every rebaseline (an outward action each time), and accepting `pin-missing` until a re-pin (breaks `make check` after every squash merge).
- **Evolve target**: for `self` the target revision is the committed HEAD of the current branch, exported with `fetch.py where self --commit <sha>`; there is no bare repository and no `-next` worktree for `self`.
- **Alternatives**: content sha256 (same effect, but needs reading files instead of a cheap `rev-parse`); following the squash commit through the pull request API (needs the network and GitHub-specific logic).

## R6. Source links for `self`

- **Decision**: `self-blob` and `self-tree` attributes point at the tracked branch (for example `blob/main/<path>`), using a `web` URL recorded on the `self` entry (derived from the host's `origin` remote at pin time when it is a GitHub URL; omitted otherwise, in which case the attributes are not generated).
- **Rationale**: The pinned commit of a pull request branch disappears after a squash merge, so commit links would break. The embedded guide lives in the same branch as the code it describes, so branch links show the version a reader sees next to the guide.
- **Alternatives**: commit links (break after squash); no links (a regression compared with separate guides).

## R7. The pull request check

- **Decision**: `drift.py --pr --base <sha>` examines only `self`. It computes the cited files from the pages at the head, finds those whose blob id differs between base and head, and passes when there are none. Otherwise it passes only when the `self` entry in `baseline.yaml` differs between base and head and every cited file at head matches the fingerprint in the head baseline. `GUIDE_SKIP=1` (set by the workflow when the pull request carries the `guide-skip` label) makes it pass with a "skipped by request" note. Exit codes follow drift: 0 pass, 10 fail, 2 configuration error. A new template `guide-pr-check.yml` runs it with `actions/checkout` at `fetch-depth: 0` (base blobs are needed), `defaults.run.working-directory: <guide dir>`, `contents: read` permissions, and no other sources.
- **Rationale**: Fingerprints make "the guide was re-verified against exactly this code" checkable without an AI session (FR-028), and later pushes to cited files invalidate the match (spec clarification for FR-026).
- **Alternatives**: comparing page edits (does not prove verification); posting PR comments (needs write permissions, FR-028 forbids more than reporting).

## R8. Scheduled drift workflow in embedded mode

- **Decision**: `guide-drift.yml` gains a `{{GUIDE_DIR}}` placeholder used for `defaults.run.working-directory`; create renders it to `.` for separate guides (identical output to today) and to the subdirectory name for embedded guides, and installs it in the host's `.github/workflows/`.
- **Rationale**: GitHub only reads workflows from the repository root.

## R9. Confidential data in embedded mode

- **Decision**: Embedded `guide.yaml` must keep `internal.enabled: false` and empty `confidential_terms` and `confidential_patterns`. The terms, patterns, and the real locations of confidential inputs live in `confidential.local.yaml` in the guide root, which the scaffold adds to the guide's `.gitignore`. `guidecfg.load_guide` merges it into `Guide.confidential_terms/patterns` (the only place check, leakcheck, and upstream read them, guidecfg.py:110-111). Confidential inputs are registered with `location: local:<id>`; `load_inputs` resolves the real location from the local file. `drift.to_markdown` prints only the id for `local:` inputs, so the drift issue never shows them.
- **Rationale**: The host repository may be public; committed configuration and drift issues must not carry customer names or transcript paths (FR-006).
- **Alternatives**: environment variables (lost between sessions, invisible to the leak check in CI); encrypting the terms (key handling for no real benefit).

## R10. Inputs from the host's own documentation

- **Decision**: Inputs read from host files that consolidation rewrites or removes are registered as `location: self:<path>` with `revision: <commit>`; their checksum is the blob id at that revision, and drift reports them as `recorded` (never changed or unreadable). Inputs kept in place use ordinary paths (`../docs/x.md`) and are tracked by sha256 as today.
- **Rationale**: FR-020 as amended by the spec review. `Input.path()` returns None for `self:` locations so the "inside the guide project" refusal never applies to them.

## R11. Stubs

- **Decision**: A stub is a Markdown file that starts with the marker `<!-- guide: moved -->`, has one heading (the old title), and one sentence with a relative link to the new page. The marker is distinct from the existing `STUB` marker for unfinished pages (check.py:67-68), which strict checks reject. `embedded.stubs` lists them. check verifies every stub link and skips page rules for them; evolve rewrites stub link targets when a page is renamed or removed (`embed.py retarget`).
- **Rationale**: Reusing `STUB` would fail strict checks and confuse the ledger.

## R12. Consolidation mechanics

- **Decision**: Three deterministic `embed.py` subcommands around the AI classification in the create skill:
  - `inventory` lists documentation candidates by the FR-016 rules (root README in any format, `.github/README*`, `docs/README*`, named top-level files, community health files, `docs/`, `doc/`, `documentation/`, directories with a generator configuration) and flags package manifests that publish the README (`pyproject.toml` `readme`, `package.json` `files`/default, `Cargo.toml` `readme`). Output is YAML or JSON.
  - `apply --plan <move-plan.yaml>` executes an approved plan: moves development sections (by heading) to the developer README with heading levels and relative links rewritten, appending under a heading when the file exists; records inputs at the current `self` revision; writes stubs that point to the front page until retargeted; removes files and relocates `.github/README*`. It refuses to run on a dirty working tree.
  - `retarget --map <old=new>...` updates stub links after pages exist (create) or are renamed (evolve).
  The classification (which section is user-facing, which is development) stays with the create skill, because it needs judgment; the plan file is what the author approves.
- **Rationale**: Deterministic moves are testable and repeatable; the plan file is the single artifact the author approves (FR-018).

## R13. Guide discovery

- **Decision**: `guidecfg.py discover [--dir DIR]` prints the guide root: `DIR` itself when it holds `guide.yaml`; otherwise the single immediate subdirectory whose `guide.yaml` has an `embedded` block; exit 3 with a list when there are several; exit 4 when there are none. Preflight uses it to resolve `GUIDE`.
- **Rationale**: FR-031 needs one rule shared by every command.

## R14. Scaffold

- **Decision**: `scaffold-project.sh --embedded` skips `internal/`, writes the pointer `docs/README.md` (from a new `adapters/gfm/embedded/` overlay), appends `confidential.local.yaml` to the guide's `.gitignore`, and refuses formats other than gfm. Host-root session files (for example `.claude/settings.local.json`) are excluded through the host's `.git/info/exclude`, which is untracked.
- **Rationale**: FR-002, FR-003, FR-006; the existing never-overwrite copy (scaffold-project.sh:37-48) stays.

## R15. Remaining touch points

- **Preview**: in embedded mode the gfm `preview` target serves the host root with markserv and opens `README.md` (local only, read-only).
- **Upstream**: `upstream._own_remotes` (upstream.py:300-306) uses the git toplevel of the guide root instead of requiring the guide root to be the toplevel, so embedded guides keep the own-repository protections.
- **Claim ledger**: embedded guides have no internal part; under strict rigor the ledger lives at `ledger/claims.md` in the guide root (not rendered).
- **Front page title**: the front page contract requires a Markdown `#` title (badges and logo after it); raw HTML titles are not recognized by the PDF printer.
- **Known pre-existing behavior**: create writes `docs/guide/spec.md` and `plan.md` inside the gfm content root. In embedded mode they stay there (visible under `guide/docs/guide/`); changing that is outside this feature.
