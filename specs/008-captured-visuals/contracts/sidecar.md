# Contract: visual sidecar

`visuals/<name>.visual.yaml` (dark variant: `visuals/<name>-dark.visual.yaml`), written by `visuals.py capture`, read by `check.py`, reviewers, and `visuals.py drift`. Keys are written in this order; values are deterministic except `captured_at`.

```yaml
schema: 1
name: mlflow-runs
variant: light                 # light | dark | default (no variants declared) ; cli visuals: default
kind: web
image: content/modules/ROOT/images/visuals/mlflow-runs.png   # relative to the guide root
environment:
  name: mlflow
  image: ghcr.io/mlflow/mlflow:v2.19.0
  digest: sha256:4f3c...       # index (manifest list) digest when available, else the image digest
  platform: linux/arm64
  source: mlflow               # only when the environment names one
  source_commit: 0a1b2c3...    # pinned commit of that source at capture time
fingerprint: 9c1e0b5f2a7d4e11
capture_env: 3fa9c0d1e2b4
captured_at: "2026-11-22T10:15:00Z"
redaction:
  rules: [home-path, user-path, user-at, hostname, ipv4, bearer, api-key, jwt, k8s-api, tenant]
  disabled: []
  replacements: {hostname: 1, ipv4: 0}
masks: 1                       # number of mask replacements
scripts: []                    # visuals/scripts/... files the visual ran
variants: {dark: captured}     # only on the light (or default) sidecar of a visual with variants: captured | skipped
highlights:
  - label: "1"
    selector: "role=columnheader[name=accuracy]"
    text: accuracy
style: null                    # cli only: sha256 (16 hex) over masked text plus style runs
text: |
  - table:
    - rowgroup:
      - row "Run Name accuracy loss":
        - columnheader "Run Name"
        - columnheader "accuracy"
  ...
```

Placeholder visuals (FR-031a) have only `schema`, `name`, `variant`, `kind`, `image`, `fingerprint`, `placeholder: true`, and an empty `text`.

## Rules

- `redaction` is required on every non-placeholder sidecar; its absence is a check error (FR-023).
- `redaction`, `fingerprint`, and every other field never contain the capturing user's name, home path, host name, or a replaced value.
- `text` holds the redacted and masked content: the `aria_snapshot` outline of the captured region for web visuals, the command line (with the displayed prompt) followed by the output lines, right-trimmed, for CLI visuals.
- The drift text comparison uses `text` and `highlights` only.
