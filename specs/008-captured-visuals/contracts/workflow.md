# Contract: CI workflow template and skill changes

## `guide/templates/guide-visuals.yml`

Installed as `.github/workflows/guide-visuals.yml` by `/guide:evolve --visuals` (and `/guide:create` when the guide has visuals) when the author agrees. `{{GUIDE_DIR}}` as in `guide-drift.yml`.

```yaml
name: guide visual drift
on:
  schedule:
    - cron: "41 6 * * 1"
  workflow_dispatch: {}
permissions:
  contents: read
defaults:
  run:
    working-directory: {{GUIDE_DIR}}
jobs:
  visuals:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: {persist-credentials: false}
      - uses: astral-sh/setup-uv@v6
      - name: Visual drift
        run: |
          set +e
          uv run tools/guide/visuals.py drift --format markdown > visual-drift.md
          status=$?
          cat visual-drift.md >> "$GITHUB_STEP_SUMMARY"
          exit $status
```

No secrets, read-only contents permission, podman from the runner image (FR-036).

## Skill changes

- `guide:preflight` and `scripts/deps.sh`: report `podman=available|missing` (FR-031a).
- `guide:create`: plan instructions add proposed visuals per page (name, kind, what it shows, why) next to diagrams; visual tasks come before the pages that embed them; platform-only UIs are omitted with a note (FR-031, FR-032); without podman, placeholders only with the author's agreement and a recorded ruling (FR-031a); the controller runs `make visuals` once after the visual tasks and checks the summary.
- `guide:page-task`: the page procedure cites `visual:<name>` for each embedded visual and reads the sidecar as the source of what the visual shows; the page review guide adds the FR-025 rule (review against the sidecar text; viewing the image is optional).
- `guide:evolve`: with a recipe and podman, run `visuals.py drift` with the source drift, merge visual findings into the drift report, recapture with `visuals.py capture` for drifted visuals, and route affected pages (from `visual:` citations) into page tasks (FR-033); without podman, say "visual drift not checked (podman missing)". New `--visuals` mode (FR-034).
- `guide/commands/evolve.md`: argument hint gains `--visuals`.
