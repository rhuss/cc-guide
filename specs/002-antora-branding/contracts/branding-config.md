# Contract: branding configuration and validation

## `guide.yaml`

```yaml
branding:
  logo_text: Agent Starter Kits        # or: logo: branding/logo.svg (then logo_alt is required)
  logo_alt: Red Hat Agent Starter Kits # optional with logo_text
  footer:                              # rhdp | none | {text, url}; default none
    text: Agent Starter Kits on GitHub
    url: https://github.com/red-hat-data-services/agentic-starter-kits
  favicon: branding/favicon.png        # optional: .ico, .png, .svg
  color: "#3e8635"                     # optional
```

The plugin's `templates/guide.yaml` carries this block commented out, with a note that `logo_text` renders the Red Hat logo and is meant for guides about Red Hat products (FR-030).

## Validation messages

`uv run tools/guide/guidecfg.py validate` and `uv run tools/guide/playbook.py path` report one line per problem in the existing `file:key: message` form and exit 1:

| Condition | Line |
|---|---|
| block in a guide whose adapter lists none of its keys | `guide.yaml:branding.<key>: not supported by the <format> adapter` (one per key; an empty block: `guide.yaml:branding: not supported by the <format> adapter`) |
| both or neither logo key | `guide.yaml:branding: set exactly one of logo_text or logo` |
| `logo_text` empty, multi-line, or too long | `guide.yaml:branding.logo_text: must be one line of 1 to 40 characters (got <n>)` |
| `logo` without `logo_alt` | `guide.yaml:branding.logo_alt: required with branding.logo` |
| path missing | `guide.yaml:branding.<key>: file not found: <path>` |
| path outside the project (absolute, `..`, or a symlink resolving outside) | `guide.yaml:branding.<key>: must be a path inside the guide project (got <path>)` |
| wrong file type | `guide.yaml:branding.logo: must be an .svg file (got <path>)` / `guide.yaml:branding.favicon: must be an .ico, .png, or .svg file (got <path>)` |
| bad footer | `guide.yaml:branding.footer: must be rhdp, none, or a mapping with text and optional url`; `guide.yaml:branding.footer.url: must be an absolute http or https URL` |
| bad color | `guide.yaml:branding.color: must be a #rrggbb color (got <value>)` |
| overlay is not a directory, or a file links outside | `ui/supplemental:<rel path>: <reason>` |
| playbook already sets supplemental files while branding or overlay applies | `site.yml:ui.supplemental_files: already set; move these files into ui/supplemental/` (same for `site-internal.yml`) |

Warnings (exit status unchanged):

| Condition | Line |
|---|---|
| overlay file shadows a generated file | `ui/supplemental/<rel path>: warning: shadows the file generated for branding.<key>` |
| overlay has its own `partials/head-meta.hbs` and `css/extra.css`, and neither `color` nor `favicon` is set | `ui/supplemental/partials/head-meta.hbs: warning: shadows the file generated for ui/supplemental/css/extra.css` (the author's head-meta must link `extra.css` itself) |

`playbook.py path` prints problems and warnings to stderr; on problems it prints no path and exits 1, so the Makefile `BUILD` macro and the preview stop before Antora runs. MkDocs and gfm builds never call `playbook.py`; `mkdocs_macros.define_env` (every `mkdocs build`) and `attrs.py regions` (the first step of the gfm `site` targets) report the same lines and stop the build. `guidecfg.load_guide` does not run these checks, so `guidecfg.py get` keeps working for an invalid block and the Makefile reaches the step that reports it.
