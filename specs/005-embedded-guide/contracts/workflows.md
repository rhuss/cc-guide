# Contract: GitHub workflows for embedded guides

Both workflows are installed only on opt-in, into the host's `.github/workflows/`. create stops before overwriting an existing file of the same name and asks for another name.

## Scheduled drift check (`guide-drift.yml`, existing template, extended)

- New placeholder `{{GUIDE_DIR}}`, used as `defaults.run.working-directory`. Separate guides render it as `.`, which keeps the rendered file equivalent to today's.
- Behavior otherwise unchanged: weekly cron, `workflow_dispatch`, `contents: read`, `issues: write`, one `guide-drift` issue.
- In embedded mode the report never names `local:` input locations.

## Pull request check (`guide-pr-check.yml`, new template)

```yaml
name: guide pr check
on:
  pull_request:
    types: [opened, synchronize, reopened, labeled, unlabeled]
permissions:
  contents: read
defaults:
  run:
    working-directory: {{GUIDE_DIR}}
concurrency:
  group: guide-pr-check-${{ github.event.pull_request.number }}
  cancel-in-progress: true
jobs:
  guide:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
          fetch-depth: 0
          persist-credentials: false
      - uses: astral-sh/setup-uv@v6
      - name: Check the guide against this pull request
        env:
          GUIDE_SKIP: ${{ contains(github.event.pull_request.labels.*.name, 'guide-skip') && '1' || '' }}
        run: |
          set -o pipefail
          uv run tools/guide/drift.py --pr --base "${{ github.event.pull_request.base.sha }}" --head "${{ github.event.pull_request.head.sha }}" | tee -a "$GITHUB_STEP_SUMMARY"
```

- The source of truth is `guide/templates/guide-pr-check.yml`; the block above omits its comments.
- Checks out the pull request's head commit (not the merge commit) with the full history, so the base revision and its `baseline.yaml` are available. `set -o pipefail` keeps the check's exit status through `tee`. A newer push cancels a running check of the same pull request, and the job stops after 10 minutes.
- Reads only the host repository; no tokens, no other sources, no write permission.
- The job result is the report: pass or fail with the changed cited files, the affected pages, and whether the baseline was re-verified. Whether it blocks merging is decided by the repository's branch protection.
- The `guide-skip` label is the maintainers' opt-out (FR-027).
