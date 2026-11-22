# Data model: Captured visuals

Formats are defined in `contracts/visuals-yaml.md` (recipe) and `contracts/sidecar.md` (sidecar). This file lists the entities, their identity, validation rules, and state.

## Recipe (`visuals.yaml`, guide root)

| Field | Type | Rules |
|---|---|---|
| `schema` | int | `1` |
| `defaults` | map | optional: `width` (int, default 100), `prompt` (str, default `"$ "`), `viewport` (`{width, height}`, default 1280x800), `timeout` (seconds per web step, default 15), `tolerance` (0 to 255, default 16), `threshold` (percent, default 0.5) |
| `redaction` | map | optional: `rules` (list of `{id, pattern, replacement}`), recipe rule ids must not collide with default rule ids |
| `environments` | map name to Environment | names: `^[a-z][a-z0-9-]{0,30}$` (host name safe, FR-002) |
| `visuals` | map name to Visual | names: `^[a-z][a-z0-9-]{0,62}$`; no name `<x>-dark` when visual `<x>` declares `dark` |

## Environment

| Field | Kind | Rules |
|---|---|---|
| `kind` | all | `web`, `cli`; `kind-cluster` is rejected with "not supported yet" |
| `image` | all | must contain `:<tag>` or `@sha256:` (FR-003); `:latest` is rejected too |
| `source` | all | optional baseline source id; must exist in `baseline.yaml`; not `self` |
| `port` | web | required int |
| `ready` | web | path starting with `/`, default `/` |
| `ready_timeout` | web | seconds, default 120 |
| `env` | all | map of string to string |
| `command` | all | optional list of strings (container command); for `cli` the default keeps the container alive (`sleep infinity`) |
| `seed` | all | list of SeedStep |

Identity: the environment name; the container gets the name as network alias (DNS) and host name; URL variable `GUIDE_ENV_<NAME>_URL` with `NAME = name.upper().replace("-", "_")`, value `http://<name>:<port>` (web only).

## SeedStep

| Field | Rules |
|---|---|
| `run` | shell command string |
| `in` | `tool` (default) or `capture` |
| `files` | list of paths relative to `visuals/` (for example `seed/runs.py`); each must exist; contents feed the fingerprint |

The guide's `visuals/` directory is mounted read-only at `/visuals` in every container of the run.

## Visual

| Field | Kind | Rules |
|---|---|---|
| `kind` | all | `web` or `cli` |
| `env` | all | an environment name; a `cli` visual accepts `cli` and `web` environments, a `web` visual only `web` |
| `steps` | web | non-empty list of Step; at most one `crop`; `highlight` labels unique within the visual |
| `viewport` | web | optional override |
| `variants` | web | optional subset of `[light, dark]`, default none (one image in the tool's default scheme) |
| `command` | cli | shell command string |
| `exit` | cli | expected exit status, default 0 |
| `width` | cli | columns, 20 to 300 |
| `prompt` | cli | displayed prompt |
| `env_vars` | cli | map of extra environment variables |
| `masks` | all | list of `{pattern, replacement}` (regex, fixed replacement) |
| `disable_redaction` | all | list of default rule ids |
| `threshold` | web | percent override |

Placeholder state lives only in the sidecar (`placeholder: true`, FR-031a); the recipe is never rewritten by a tool, so its comments and fingerprint stay intact.

## Step (web)

One-key maps: `goto: <path>`, `click: <sel>`, `fill: {selector, text}`, `press: <key>`, `wait: <sel>`, `highlight: {selector, label}`, `crop: <sel>`, `hide: <sel>`, `script: <path under visuals/scripts/>`. Selector forms: CSS, `text=<text>`, `role=<role>[name=<name>]`.

## Sidecar (`visuals/<name>[-dark].visual.yaml`)

Fields in `contracts/sidecar.md`. Identity: visual name plus variant. Holds provenance, fingerprint, redaction record, scripts, variants, highlights, style fingerprint (CLI), text content, and `placeholder` for placeholder visuals.

## Run (scratch, `.guide/visuals/<run-id>/`, mounted read-write at `/work` in the capture container)

| Item | Purpose |
|---|---|
| `job.json` | resolved job for the runner (host values for redaction live only here) |
| `out/` | images and runner results of this run |
| `raw/` | raw CLI bytes, deleted at the end of the run |
| `debug/` | debug screenshots of failed web steps (FR-013) |
| `report.md`, `report.json` | capture summary or drift report |

## Visual state

```text
declared (recipe entry, no sidecar)
  -> placeholder (sidecar with placeholder: true, no image)   [create without podman]
  -> captured (image + sidecar, fingerprint current)
  -> stale (fingerprint differs from recipe)                  [check warning]
  -> behind-baseline (sidecar source commit != baseline pin)  [check warning]
captured -> drifted | recapture-failed                         [visual drift report]
```

## Drift result per visual

`{name, variant, status: unchanged|drifted|recapture-failed|environment-failed, image_diff: float|null, platform_mismatch: bool, text_diff: [lines], style_changed: bool, pages: [paths], image_before, image_after, step, selector}`
