# Contract: Page Conventions

Conventions every guide page follows, independent of the output format. Adapters only change the comment syntax. Checks (FR-019), evolve impact analysis (FR-025), and validate (FR-038) parse these structures, so they are a stable contract.

## 1. Source reference block (FR-010)

Called "source block" for short in the plan and tasks.

Placed directly after the page title. One reference per line.

| Adapter | Syntax |
|---|---|
| antora | Line comments: `// Sources:` then one `// <ref>` per line |
| mkdocs, gfm | One HTML comment: `<!-- Sources:` then one `<ref>` per line, then `-->` |

Reference grammar:

```text
ref        = source-ref | url-ref | input-ref
source-ref = source-id ":" path [ ":" lines ]
lines      = range *( "," range )
range      = number [ "-" number ]
url-ref    = "url:" absolute-url
input-ref  = "input:" input-id
```

Rules:
- `source-id` must exist in `baseline.yaml`; `path` must exist at the pinned commit; line ranges must lie inside the file.
- `input-id` must exist in `inputs.yaml`. An `input:` reference is allowed only on internal pages: content whose only support is an input (above all a confidential one) never reaches the shareable part.
- A page without a block fails the content check. An empty block is allowed only for pages marked `:guide-no-sources:` (antora attribute) or `<!-- guide: no-sources -->` (Markdown), for example a pure navigation page.
- The block is parsed only at the top of the page, never inside listings (fixes the saw-guide checker defect that matched `// Sources:` anywhere).

## 2. Task steps and checks

Task steps follow a short "why" paragraph and are numbered. A step that has an observable result ends with a check:

```text
Check: <what the reader should see, one sentence>
<listing with one or more commands>
<optional expectation>
```

Expectation syntax:

| Adapter | Syntax |
|---|---|
| antora | Line comment directly after the listing: `// expect: <matcher>` |
| mkdocs, gfm | HTML comment directly after the fenced block: `<!-- expect: <matcher> -->` |

Matcher grammar (applied to the combined stdout of the listing's last command):

```text
matcher = "exit" number
        | "contains" quoted
        | "not-contains" quoted
        | "matches" "/" regex "/"
        | "lines" op number          ; op = ">=" | "<=" | "=="
        | matcher "and" matcher
```

A check without an expectation is reported as `not-evaluable` (edge case in spec).

## 3. Read-only classification for validate (FR-038)

A command is a **query** only if every pipeline segment matches the plugin's allowlist; everything else is **mutating**. The allowlist ships with the plugin (`guide/validate/readonly.yaml`) and can be extended per guide through `validate.extra_queries` in `guide.yaml`, only with additional query patterns, never by removing the default-deny rule or reclassifying a command on the explicit mutating list below.

Default allowlist (initial content):

| Tool | Query forms |
|---|---|
| `oc`, `kubectl` | `get`, `describe`, `logs`, `explain`, `api-resources`, `api-versions`, `version`, `whoami`, `auth can-i`, `adm top`, `config view --minify`, `config current-context` |
| `curl` | Only without `-X`/`--request` other than `GET`/`HEAD`, and without `-d`, `--data*`, `-F`, `--form`, `-T`, `--upload-file` |
| `openshell` | `status`, `version`, `whoami`, and `list`/`get` subcommands |
| filters | `grep`, `rg`, `jq`, `yq`, `head`, `tail`, `wc`, `sort`, `uniq`, `cut`, `awk` without `system(` |

Explicitly mutating even though they look harmless: `oc debug` (creates a Pod), `oc exec`, `oc rsh`, `oc port-forward`, any `make` target, any shell redirection to a file (`>`, `>>`, `tee`).

## 4. Experimental labels (FR-015)

Experimental content is labeled only through the adapter's experimental partial or snippet, with three parameters: feature name, change request number, anchor. Two tiers:

| Tier | Admonition | Meaning |
|---|---|---|
| `on-main` | IMPORTANT | Merged on the default branch, not in the pinned release |
| `in-review` | IMPORTANT | Open change request; described at its recorded head |

## 5. Admonition semantics

Exactly five admonition types with fixed meanings, mapped by each adapter:

| Type | Meaning |
|---|---|
| NOTE | Background that helps but is not required |
| TIP | A shortcut or better way |
| IMPORTANT | Must not be missed; also used for experimental labels |
| WARNING | Risk of a failed step or confusing behavior |
| CAUTION | Risk of data loss, security exposure, or irreversible change |

## 6. Typography and links

- No em dash or en dash characters anywhere in pages.
- AsciiDoc only: one sentence per line (semantic line breaks).
- Versions and commits appear only through baseline attributes or placeholders, never typed.
- Shareable pages contain no links into the internal part and none of the confidential terms or patterns from `guide.yaml`.
