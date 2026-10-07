# Data Model: Antora branding for guides

## Branding block (`guide.yaml` `branding`)

Optional mapping. Owned by the guide project; the single source of truth for branding (FR-001).

| Key | Type | Required | Rule |
|---|---|---|---|
| `logo_text` | string | exactly one of `logo_text`, `logo` | one line, 1 to 40 characters after trimming (FR-002, FR-003) |
| `logo` | path | exactly one of `logo_text`, `logo` | `.svg` file inside the guide project (FR-002, FR-008) |
| `logo_alt` | string | required with `logo`, optional with `logo_text` | one line, non-empty; default with `logo_text`: `Red Hat <logo_text>` (FR-004) |
| `footer` | `rhdp` \| `none` \| mapping | no (default `none`) | mapping keys: `text` (required, one line, non-empty), `url` (optional, absolute `http`/`https`) (FR-005) |
| `favicon` | path | no | `.ico`, `.png`, or `.svg` file inside the guide project (FR-006, FR-008) |
| `color` | string | no | `#rrggbb` (FR-007) |

Unknown keys are errors (like every other `guide.yaml` mapping). Keys the guide's adapter does not list are errors naming the key and the format (FR-009).

**Resolved branding** (computed, never stored): `logo_text` or `logo`, `alt` (with the default applied), `footer` (one of `rhdp`, `none`, or `{text, url}`), `favicon` (absolute path or none), `color` and its hover shade (each RGB channel times 0.75, rounded half up: `int(c * 0.75 + 0.5)`, so `#0066cc` gives the stock `#004d99`).

**Where it is checked**: `guidecfg.load_guide` accepts the block and stores it raw (`Guide.branding`, None when it is not a mapping, so `guidecfg.py get` keeps working and every build reaches `playbook.py`, which reports it; checkpoint 2 review); the full checks run in `branding.check_guide`, called by `guidecfg.validate`, `playbook.py path`, `mkdocs_macros.define_env`, and `attrs.py regions`.

## Overlay directory (`ui/supplemental/`)

Optional directory in the guide project. Every regular file in it is added to the UI at the same relative path (FR-019). Rules:

- Must be a directory if it exists.
- Files must be regular files; a symbolic link that resolves outside the guide project is an error.
- A file whose relative path equals a generated path (see below) shadows the generated file and produces a warning naming the branding key (FR-020).
- `css/extra.css`, when present, is linked on every page after `css/site.css` and `css/branding.css`.

## Adapter branding capability (`adapter.yaml` `branding`)

List of the branding keys an adapter supports. Antora: `[logo_text, logo, logo_alt, footer, favicon, color]`. MkDocs and gfm: `[]`. Missing list means `[]` (older vendored descriptors). Read into the `Adapter` dataclass as `branding: list[str]`.

## Branding overlay (build output, never committed)

Directory `build/branding/<view>/` where `<view>` is `shareable` or `internal`:

```text
build/branding/<view>/
├── ui/                          # ui.supplemental_files of the generated playbook
│   ├── img/logo-guide.svg       # rendered from logo_text, or a copy of logo
│   ├── img/favicon-guide.<ext>  # only with favicon
│   ├── helpers/navbar-logo-alt.js
│   ├── partials/footer-content.hbs   # only when footer is not rhdp
│   ├── partials/head-meta.hbs        # when color, favicon, or css/extra.css applies
│   ├── partials/head-icons.hbs       # only with favicon
│   ├── css/branding.css              # only with color
│   └── <every file of ui/supplemental/, copied last>
└── branding.json                # {"logo": "<abs path of ui/img/logo-guide.svg>", "alt": "...", "footer": "...", "generated": [...], "shadowed": [...]}
```

Without a branding block but with an overlay directory, `ui/` holds only the overlay files (plus `head-meta.hbs` when `css/extra.css` exists), `site.keys.navbar_logo` is not set, and `branding.json` is not written.

**Lifecycle**: rendered on every call of `playbook.py path` for a branded or overlaid guide; written to `build/branding/<view>.tmp-<pid>/`, then swapped in (the previous directory is renamed to `<view>.old-<pid>`, the new one renamed into place, the old one deleted; POSIX `rename` cannot replace a non-empty directory); removed by `make clean` with the rest of `build/`.

## Generated playbook

`build/playbook.yml` (shareable) or `build/playbook-internal.yml` (internal): a copy of `site.yml` / `site-internal.yml` with:

- absolute paths: Antora resolves `.` and `./` paths against the playbook's own directory, which is now `build/`. In a main checkout every `url: .` content source becomes the absolute guide root (branches unchanged); in a linked worktree the existing rewrite points it at the main repository with `branches` and `worktrees`. In both cases `output.dir`, a relative bundle URL, and relative extensions become absolute.
- `ui.supplemental_files`: absolute path of `build/branding/<view>/ui`
- `site.keys.navbar_logo: guide` (other `site.keys` entries kept) when a branding block exists. Antora lowercases playbook keys and camelCases them on `_` and `-`, so the UI templates see `site.keys.navbarLogo`; a literal `navbarLogo` key would arrive as `navbarlogo` and be ignored (found in the T016 smoke test)

Generated when the guide has a branding block, an overlay directory, or is a linked worktree. Otherwise `playbook.py path` prints the committed playbook path unchanged.

## Bundle contract (`contract.yaml`)

Shipped in `guide/adapters/antora/branding/contract.yaml`, vendored to `tools/guide/branding/contract.yaml`. A list of rules, each with an `id` (the name reported when it fails), a bundle-relative `file`, and one check:

| Check | Meaning |
|---|---|
| `exists: true` | the file exists |
| `contains: [str, ...]` | every string occurs in the file |
| `matches: [regex, ...]` | every regular expression matches |
| `equals: str` | the file content equals the string after stripping leading and trailing whitespace from both (for partials the overlay replaces wholesale; the stock `head-icons.hbs` is indented by four spaces) |

The accent selectors for `color` are listed once in the contract (`accent_selectors`, `accent_hover_selectors`) and used both by the checker and by the `branding.css` renderer, so the CSS and the contract cannot disagree.
