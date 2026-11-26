# /guide:evolve

Keeps an existing guide current after its sources changed. It compares the pinned source commits in `baseline.yaml` with the sources' current state, updates only the affected pages (with the same per-page reviews as `/guide:create`), and writes the new baseline last, after the checks pass.

## Usage

```text
/guide:evolve [--check] [--adopt] [--pages] [--visuals] [--to ID=REF]... [--input PATH]... [--rigor fast|standard|strict] [--dir PATH]
/guide:evolve --help
```

## Modes

| Call | What it does | Needs superpowers |
|---|---|---|
| `/guide:evolve` | Drift report, change request decisions, plan for the affected pages (shown for approval), page updates with reviews, new baseline | yes |
| `/guide:evolve --check` | Drift report only; changes and commits nothing. Exit 0 no drift, 10 drift found | no |
| `/guide:evolve --adopt` | Brings a guide that cc-guide did not create under cc-guide (toolkit, `guide.yaml`, baseline, source blocks) | yes |
| `/guide:evolve --pages` | Sets up the GitHub Pages workflow for an Antora or MkDocs guide | no |
| `/guide:evolve --visuals` | Sets up captured visuals (`visuals.yaml`, build targets, optional CI workflow) | no |

## Options

| Option | Meaning |
|---|---|
| `--to ID=REF` | Target revision for one source (repeatable). Default: the head of each source's tracked branch |
| `--input PATH_OR_URL` | Register a new input such as notes or a transcript (repeatable) |
| `--rigor fast\|standard\|strict` | Review depth. Default from `guide.yaml` |
| `--dir PATH` | The guide project (the directory holding `guide.yaml`). Default: see "Where to run it" |
| `--help`, `-h` | Show this help. Runs no checks and needs no guide project |

## Guide setups

| Setup | Layout | Notes for evolve |
|---|---|---|
| Separate guide | The guide is its own git repository (Antora, MkDocs, or gfm). Its sources are other repositories, pinned in `baseline.yaml` | All modes. `--pages` only for Antora and MkDocs |
| Embedded guide | A gfm guide in a subdirectory (default `guide/`) of the repository it documents. The repository's `README.md` is the guide's front page and the repository itself is the source `self` | Drift for `self` counts only cited files, so commits that touch only guide files are no drift. Evolve also keeps the README's guide part current and never overwrites hand edits silently. No `--pages` (GitHub renders the README) |
| In-repo guide | An Antora or MkDocs guide in a subdirectory (for example `docs/guide/`) of a project repository, without an `embedded` block. The README stays the author's | Confidential terms and the real locations of confidential inputs stay in the git-ignored `confidential.local.yaml`. The repository is a source only when the guide pins it like any other source. `--pages` publishes from that repository |
| Nested separate guide | A separate guide with its own git repository inside a parent repository (for example a workspace directory that is under git) | Works like a separate guide; run it from the guide's own directory |
| Foreign guide | An existing guide without a cc-guide `guide.yaml` or source blocks | Run `/guide:evolve --adopt` first; regular evolve refuses it until adoption is done |

## Where to run it

Evolve resolves the guide project in this order:

1. `--dir PATH` when given.
2. The current directory, when it holds `guide.yaml`.
3. The one guide project found up to three levels below the current directory, such as `guide/` or `docs/guide/` when you run from the root of the repository it documents. Hidden, `node_modules`, `build`, `dist`, and `target` directories are skipped.

| Setup | Run it from |
|---|---|
| Separate guide | The guide repository's root |
| Embedded guide | The root of the documented repository (the guide in `guide/` is found automatically), or the guide subdirectory |
| In-repo guide | The repository root (found automatically when the guide sits at most three levels deep), or the guide subdirectory, or pass `--dir docs/guide` |
| Nested separate guide | The guide's own directory, or pass `--dir` |
| Foreign guide (`--adopt`) | The guide's directory itself, or pass `--dir`; without a `guide.yaml` there is nothing to find below the current directory |

When several guide projects are equally close below the current directory, evolve stops and lists them; run it again with `--dir`. Without any guide project it stops and suggests `/guide:create`.

On Claude Code, permission entries (for example for the Excalidraw tools) are read from the directory the session was started in, so start the session in the directory you run evolve from, or add the entries there.

## Other harnesses

On Codex there is no command layer: ask for the `guide:evolve` skill with the same arguments. On OpenCode, install the command shims with `bash guide/opencode/install.sh --project-dir <project>` and use `/guide:evolve` there.

## Related

`/guide:create` starts a guide, `/guide:validate` runs its commands against a cluster, `/guide:preview` serves it locally, `/guide:export` writes a PDF, and `/guide:upstream` files reports for problems found in the sources.
