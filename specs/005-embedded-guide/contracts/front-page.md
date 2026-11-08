# Contract: front page and consolidation in the skills

## Front page contract (`guide/skills/page-task/front-page-contract.md`, new)

Applies to the page task that writes the front page and to its review. It extends `overview-contract.md`; both apply.

1. The first line is the ownership comment (data-model.md). Nothing above it.
2. A Markdown `#` title follows; raw HTML titles are not allowed.
3. Badges and a logo from the old README come right after the title, unchanged and unverified. They are the only unverified content.
4. The sources block follows, citing `self` files and other sources like any page. Never files inside the guide subdirectory, the developer README, or stubs.
5. The why card and the overview body follow the overview contract (cold-reader test applies).
6. Persona navigation: one link per persona entry page, in section order, plus the reference section.
7. A short closing section links to the developer README (when it exists), `LICENSE`, and `CONTRIBUTING` (wherever it lives).
8. Link form: host-relative (`guide/docs/...`) by default; absolute URLs (the `self` `web` URL at the tracked branch) when the move plan set `absolute_links: true`.
9. No internal content and no `input:` references.

## create skill: embedded branch

Inserted points (existing section numbers):
- **§3 Target directory**: run `guidecfg.py discover`. One embedded guide found: resume it. None found and the target is the root of a git repository: offer embedded mode (and accept `--embedded`). Non-git non-empty directory: refuse as today. A subdirectory of a repository: refuse with the monorepo note.
- **Preconditions** (before intake): host working tree clean; when on the default branch, ask before committing there and offer a working branch.
- **§4 Intake** (embedded): guide subdirectory name (default `guide`), developer README path (default `DEVELOPMENT.md`), PR check offer (default no), scheduled drift offer as today. Format fixed to gfm (explain when Antora or MkDocs is requested). No internal part (explain). No remote offer. Confidential terms go to `confidential.local.yaml`.
- **§5 Setup** (embedded): no `git init`; `scaffold-project.sh --embedded`; pin `self` and the other sources; write `confidential.local.yaml` when needed; add host-root session files to `.git/info/exclude`.
- **§5a Consolidation** (new): `embed.py inventory`; classify sections; write the move plan; show it as a table (path, section, destination, stub, relocation) plus the list of removals and flagged manifests; let the author change destinations; on approval run `embed.py apply`; on decline stop (offer to remove the uncommitted guide subdirectory).
- **§6 Guide spec and plan**: the front page is the start page; the page plan maps every stubbed path to its covering page.
- **§7 Execution**: the front page task uses the front page contract; after the last page task run `embed.py retarget` with the plan's map.
- **§8 Final review**: `check.py --structure` covers front page, stubs, developer README.
- **§9 Run summary**: list dropped (contradicted) claims with source locations; offer upstream candidates only for material kept in place.
- **Workflows**: render `{{GUIDE_DIR}}` and install the opted-in workflows into the host's `.github/workflows/`.

## evolve skill: embedded additions

- Resolve the guide with `discover`.
- Before planning updates: run `embed.py front-page-status`; when the front page differs from the blob recorded in the baseline, show the diff as hand edits and ask before overwriting them.
- The impact set includes the front page and stubs whose targets are renamed or removed (`embed.py retarget`).
- Never move, create, or remove files outside the guide subdirectory.
- Rebaseline recomputes `self` fingerprints.

## preflight, preview, export

- preflight resolves `GUIDE` with `discover` and adds `embedded=yes|no` to its result line.
- preview opens `README.md` on the host-root server in embedded mode.
- export needs no change beyond the Makefile staging.
