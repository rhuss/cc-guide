# Data Model: Neutral Red Hat inspired branding for new guides

Spec 002's model (`specs/002-antora-branding/data-model.md`) stays valid; this file lists only what changes.

## Branding block (`guide.yaml` `branding`)

| Field | Type | Default | Rules | Change |
|---|---|---|---|---|
| `logo_text` | string | none | one line, 1 to 40 characters after trimming | exactly one of `logo_text`, `wordmark`, `logo` (was: one of two) |
| `wordmark` | string | none | one line, 1 to 40 characters after trimming; every character in the Display coverage of the font manifest | NEW |
| `logo` | path | none | as spec 002 | exclusivity rule extended |
| `logo_alt` | string | `Red Hat <logo_text>`; `<wordmark>`; required with `logo` | one non-empty line | new default for `wordmark` |
| `theme` | `neutral` or `stock` | `stock` | exact value | NEW |
| `footer`, `favicon`, `color` | as spec 002 | as spec 002 | as spec 002 | unchanged |

Under `theme: neutral`, every character of `logo_text` must also be in the Display coverage (it is outlined, FR-007, FR-011).

Validation messages (new or changed):

```text
guide.yaml:branding: set exactly one of logo_text, wordmark, or logo
guide.yaml:branding.wordmark: must be one line of 1 to 40 characters (got 41)
guide.yaml:branding.wordmark: no glyph for "漢" (U+6F22) in Red Hat Display
guide.yaml:branding.logo_text: no glyph for "漢" (U+6F22) in Red Hat Display
guide.yaml:branding.theme: must be neutral or stock (got dark)
tools/guide/branding/fonts/RedHatText-VF.woff2: missing; refresh the toolkit (scaffold-project.sh --toolkit-only)
tools/guide/branding/fonts/RedHatText-VF.woff2: checksum mismatch; refresh the toolkit (scaffold-project.sh --toolkit-only)
guide.yaml:branding.wordmark: not supported by the mkdocs adapter
```

The font file lines appear only when `theme: neutral`, `wordmark`, or both are set (the wordmark is outlined whatever the theme). In the plugin source tree the location reads `guide/adapters/antora/branding/fonts/<file>`.

## Resolved branding (`branding.Resolved`)

Adds two fields:

| Field | Type | Value |
|---|---|---|
| `wordmark` | `str \| None` | trimmed `wordmark` |
| `theme` | `str` | `neutral` or `stock` |

`alt` defaults to the wordmark when `wordmark` is set.

## Font manifest (`branding/fonts/fonts.yaml`)

```yaml
release: 5.0.0
commit: 6bb1048a6402b0076ea04f42951ec66263cd1437   # the tag's commit; downloads come from it
repository: https://github.com/RedHatOfficial/RedHatFont
license: OFL-1.1
ofl_sha256: 4f1417e2...   # OFL.txt, compared on a re-run of the same release
files:
  - file: RedHatDisplay-VF.woff2
    upstream: fonts/Proportional/RedHatDisplay/webfonts/RedHatDisplay-VF.woff2
    sha256: 69dca56d...
    family: Red Hat Display
    style: normal
    weight: [300, 900]
  # one entry per vendored font (six)
display_coverage:            # code point ranges of RedHatDisplay-VF.woff2, inclusive
  - [0x0020, 0x007E]
  # ...
```

Written once by a maintainer script (`guide/adapters/antora/branding/fonts/update-fonts.py`, not vendored into guides) that downloads a release, computes checksums, axis ranges, and coverage, and rewrites the manifest. Read by `branding.py` for validation, `@font-face` generation, and the checksum check.

## Rendered overlay (`build/branding/<view>/ui/`)

Added for `theme: neutral`:

| Path | Content |
|---|---|
| `font/<six>.woff2` | copied from `tools/guide/branding/fonts/` |
| `font/OFL.txt` | copied |
| `css/theme-neutral.css` | `@font-face` rules (one per file, `src: url("../font/<file>") format("woff2")`, `font-weight` from the manifest range, `font-style`, `font-display: swap`) and the navbar rule |
| `partials/head-meta.hbs` | stock favicon link (or the branded one), then `branding.css`, `theme-neutral.css`, `extra.css` links as present |
| `partials/head-styles.hbs` | the stock partial without its three Google Fonts links: only the `css/site.css` link (research R11) |

`img/logo-guide.svg` changes for `wordmark` (always outlined) and for `logo_text` with `theme: neutral` (outlined). `generated_files()` maps each new path to `branding.theme` for shadow warnings.

## `branding.json`

Adds:

| Key | Value |
|---|---|
| `theme` | `neutral` or `stock` |
| `fonts` | absolute path of `build/branding/<view>/ui/font/` for `neutral`, else `null` |
| `font_faces` | for `neutral`, one `{"family", "file", "weight": [min, max], "style"}` per manifest entry in manifest order, else `[]`; the PDF printer reads the faces from here, never from `fonts.yaml` |

## State transitions

None. The theme is a pure function of `guide.yaml` and the vendored assets at build time; removing `theme` returns the guide to the spec 002 output on the next build.
