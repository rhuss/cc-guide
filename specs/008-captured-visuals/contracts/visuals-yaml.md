# Contract: `visuals.yaml`

The capture recipe at the guide root. `uv run tools/guide/visuals.py validate` checks it (FR-007) without starting anything.

```yaml
schema: 1

defaults:
  width: 100            # CLI columns
  prompt: "$ "
  viewport: {width: 1280, height: 800}
  timeout: 15           # seconds per web step
  tolerance: 16         # per-channel pixel tolerance for drift
  threshold: 0.5        # percent of differing pixels that counts as drift

redaction:
  rules:
    - id: tenant
      pattern: "acme-[0-9]+"
      replacement: "example-tenant"

environments:
  mlflow:
    kind: web
    image: ghcr.io/mlflow/mlflow:v2.19.0
    source: mlflow                 # optional baseline source id (FR-030a)
    port: 5000
    command: ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000"]
    ready: /health
    ready_timeout: 120
    seed:
      - run: python /visuals/seed/runs.py
        files: [seed/runs.py]
  tools:
    kind: cli
    image: ghcr.io/mlflow/mlflow:v2.19.0   # an image that already contains the CLI

visuals:
  mlflow-runs:
    kind: web
    env: mlflow
    variants: [light, dark]
    steps:
      - goto: /#/experiments/1
      - wait: "role=table"
      - highlight: {selector: "role=columnheader[name=accuracy]", label: "1"}
      - crop: "role=table"
    masks:
      - pattern: "\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}"
        replacement: "2026-01-01 12:00:00"

  mlflow-cli-runs:
    kind: cli
    env: tools
    command: mlflow runs list --experiment-id 1
    env_vars: {MLFLOW_TRACKING_URI: "${GUIDE_ENV_MLFLOW_URL}"}
    width: 100
```

## Rules

- Unknown keys anywhere are errors (typos must not pass silently).
- Every problem is reported as `visuals.yaml: <path>: <message>`, where `<path>` is for example `visuals.mlflow-runs.step 3`. Steps and seed steps are numbered from 1, like the run's failure messages ("step 3", "seed step 1"); other lists use zero-based indexes (`visuals.mlflow-runs.masks[0]`).
- Image references without a tag or digest, or with `:latest`, are errors (FR-003).
- `source` must name a source in `baseline.yaml`; `self` and `visual` are rejected.
- A `cli` visual may use a `web` environment (the command runs in the tool container). A `web` visual needs a `web` environment.
- `env_vars` values may reference `${GUIDE_ENV_<NAME>_URL}`; nothing else is expanded.
- `seed[].files` and `script` steps must point at existing files under `visuals/`.
- `kind: kind-cluster` gives "kind-cluster environments are not supported yet".
- No file named `visuals.yaml`: `validate`, `capture`, and `drift` print `no visuals declared` and exit 0.
