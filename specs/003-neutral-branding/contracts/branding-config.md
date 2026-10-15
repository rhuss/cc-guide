# Contract: branding configuration (delta to spec 002)

Interface: the `branding` block of `guide.yaml`, read by `tools/guide/branding.py` (validation, rendering) and written by `/guide:create`. Spec 002's contract (`specs/002-antora-branding/contracts/branding-config.md`) stays in force except where this file changes it.

## Keys

```yaml
branding:
  wordmark: OpenClaw on OpenShift   # NEW; exactly one of logo_text, wordmark, logo
  theme: neutral                    # NEW; neutral | stock; missing means stock
  footer: none
```

- `wordmark` and `theme` are listed in `KEYS` and in the Antora `adapter.yaml` `branding:` list; MkDocs and gfm keep `branding: []`.
- Unknown values of `theme` are errors, never ignored.
- The logo keys are mutually exclusive: zero or two or three of them fail with `guide.yaml:branding: set exactly one of logo_text, wordmark, or logo`.

## Defaults

| Situation | Alt text | Logo |
|---|---|---|
| `logo_text`, `stock` | `Red Hat <logo_text>` | spec 002 template, `<text>` (byte-identical) |
| `logo_text`, `neutral` | `Red Hat <logo_text>` | spec 002 template, text outlined at weight 700 |
| `wordmark` (either theme) | `<wordmark>` | outlined wordmark at weight 500 |
| `logo` | `logo_alt` (required) | the file, copied |

## What create writes

```yaml
# about a Red Hat product
branding:
  logo_text: OpenShift AI
  theme: neutral
  footer: none

# about anything else
branding:
  wordmark: OpenClaw on OpenShift
  theme: neutral
  footer: none
```

Follow-up answers replace the logo key with `logo` plus `logo_alt`, replace `footer` with `{text, url}`, or add `favicon`. Create never writes `footer: rhdp` and never omits the block for an Antora guide.

## Compatibility

- A guide without a block: unchanged (spec 002 FR-002, SC-004 here).
- A block without `theme`: `stock`, unchanged output.
- A guide on toolkit 0.3.x and earlier that sets `wordmark` or `theme` fails validation with `unknown key` until the toolkit is refreshed (as spec 002 documented for the block itself).
