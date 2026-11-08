# Contract: toolkit command line additions

All scripts run with `uv run tools/guide/<script>` from the guide root or with `--root DIR`. They import nothing from outside `tools/guide/`. Exit codes keep each script's existing meaning (drift and check: 0 success, 10 drift or failure, 2 configuration error; fetch: 0 success, 1 fetch error as today, 2 configuration error or unknown id). New subcommands use 0 success, 10 for a reported difference, 2 for configuration or usage errors.

## guidecfg.py

| Command | Behavior |
|---|---|
| `discover [--dir DIR]` | Print the guide root. `DIR` (default `.`) when it holds `guide.yaml`; otherwise the single immediate subdirectory whose `guide.yaml` has an `embedded` block. Exit 3 and list candidates when several match; exit 4 when none matches. |
| `validate [--allow-missing-front-page]` | As today, plus the `embedded` rules (data-model.md). The flag lets create validate before the front page is written. |
| `get embedded.front_page` (and other `embedded.*` keys) | Print the value, empty when not embedded. |

## fetch.py

| Command | Behavior |
|---|---|
| `pin --source self=..[@<ref>]` | Resolve the host toplevel, pin the committed HEAD of the current branch (or `<ref>` when given), record `ref` as the host's default branch (`origin/HEAD`, else `main`, else `master`), write the `self` entry with `commit`, `ref`, `web` (from `origin` when it is a GitHub URL), and `fingerprints` for all paths that pages cite from `self`. |
| `fetch` | For `self`, export a snapshot of `commit` into `${XDG_CACHE_HOME:-~/.cache}/cc-guide/self/<hash>/<commit>/` when missing: `git read-tree` into a temporary index, then `git checkout-index --all --prefix` (every tracked file as committed, `export-ignore` attributes do not drop any, symlinks stay symlinks; the host's own index and working tree are never touched). Never clone `self` into `.guide/cache/`. Other sources unchanged. |
| `fetch` (missing `self` commit) | When `commit` is not in the host repository, export the snapshot from the tracked head if every fingerprint matches it; otherwise print "pin unavailable, run /guide:evolve" and exit 0 with `self` reported as drifted (never a hard failure). The tracked head is the head of the `ref` branch (the local branch, else `origin/<ref>`, else `HEAD`), not necessarily the checked-out HEAD that drift compares with; the fallback snapshot directory is named after that head commit, never after the missing pinned commit. |
| `where <id> [--commit <sha>]` | Print the readable snapshot path of a source (the cache worktree for ordinary sources, the export directory for `self`; with a missing pin, the directory of the tracked head the fallback exported). For `self`, `--commit` exports and prints a snapshot of another commit (evolve's target revision). Unknown id: exit 2. |
| `rebaseline ...` | As today; for `self` also recompute `fingerprints` and write `front_page_blob` (the normalized front page, stored in the host object database). |

## drift.py

| Command | Behavior |
|---|---|
| `--check` | As today. `self` uses fingerprint mode (research R5): the fingerprints are compared with the checked-out HEAD (not the tracked branch head the snapshot fallback uses), no `pin-missing` because the pin is unreachable; inputs `self:` report `recorded`; `local:` inputs show only their id. |
| `--check --source self` | Limit the report to `self` (used by the scheduled workflow only when the author asks; default stays all sources). |
| `--pr --base <sha> [--head <sha>]` | Pull request mode (research R7). Head defaults to `HEAD`. Reads `GUIDE_SKIP=1` from the environment. Prints the report (markdown, or JSON with `--format json`) and exits 0 on pass, 10 on fail. Needs no network and no other source. |

## check.py

Additions, active only when `embedded` is set:
- The front page is checked as a page (sources block, links, dash rule, confidential terms, guide rules whose glob matches it). Absolute links into the host repository (`<web>/blob/<ref>/<host path>` or `<web>/tree/<ref>/<host path>`, with `web` and `ref` from the `self` baseline entry, as written when the move plan set `absolute_links: true`) are mapped to the host path and checked like relative links: the target must exist, and a target inside the guide subdirectory must be a guide page. Links to other repositories, hosts, or refs are not checked.
- `--structure` reads the front page in place of `docs/README.md`.
- Every `embedded.stubs` file: exactly one `<!-- guide: moved -->` marker and a resolving link; no page rules.
- `embedded.developer_readme`: every relative link resolves; no page rules.
- Any source block entry `self:<path>` whose path lies inside the guide subdirectory, or equals the front page, the developer README, or a stub, is an error (FR-012).
- A `self` citation whose path has no fingerprint in the baseline is reported with the hint to rebaseline.
- `self` citations are resolved (path exists, line ranges valid) whenever `self` is in the baseline, independent of `.guide/cache/`.
- The front page's first line must be the ownership comment; `--structure` reads section titles from the front page only.

## embed.py (new)

| Command | Behavior |
|---|---|
| `inventory [--format yaml\|json]` | List documentation candidates in the host by the FR-016 rules, with kind (`readme`, `github-readme`, `docs-readme`, `community`, `license`, `changelog`, `doc-file`, `doc-dir`, `doc-site`) and Markdown headings for README-like files; list package manifests that publish the README. Read-only. |
| `apply --plan FILE [--dry-run]` | Execute an approved move plan (data-model.md). Refuses a dirty host working tree, plan entries that do not exist at `self_revision`, and removals of license or non-inventoried files. The dirty check covers only paths outside the guide subdirectory. Writes the developer README (append under `## Moved from the README` when it exists), registers `self:` inputs, writes stubs pointing to the front page, relocates and removes files, and updates `embedded.stubs` and `embedded.developer_readme`. `--dry-run` prints the file operations only. |
| `retarget OLD=NEW ...` | Host-relative paths; `NEW` must exist. When `OLD` is a stub listed in `embedded.stubs`, its link is set to `NEW`. Every stub and front page link that resolves to `OLD` (a renamed or removed page) is rewritten to `NEW`. Links are written relative to the file that holds them. The move plan is not read. Exit 2, with nothing written, when a mapping matches nothing. |
| `front-page-status [--record]` | `--record` stores the normalized front page blob as `front_page_blob` (`fetch.py rebaseline` writes it too); without it, compare `git hash-object` of the front page with `front_page_blob` in the baseline (the diff uses the front page from the commit that last changed `baseline.yaml` when its normalized blob matches, else the loose object `--record` wrote); print `unchanged` (exit 0) or `edited` with a unified diff against the blob (exit 10). |
| `stage --out DIR` | Write `DIR/docs/`: a copy of `docs/` with `README.md` replaced by the front page, links rewritten (research R3). Exit 2 when not embedded. |

## scaffold-project.sh

`--embedded` (gfm only): skip `internal/`, install the pointer `docs/README.md` from `adapters/gfm/embedded/`, add `confidential.local.yaml` to `.gitignore`. Combined with `--toolkit-only` it behaves as today.

## gfm Makefile

When `guidecfg.py get embedded.front_page` is non-empty:
- `site`, `print-pdf`, and `check` stage first (`embed.py stage --out build/stage`) and render from `build/stage/docs`.
- `regions` includes the front page.
- `preview` serves the host toplevel and opens `README.md`.
Otherwise every target behaves exactly as today.
