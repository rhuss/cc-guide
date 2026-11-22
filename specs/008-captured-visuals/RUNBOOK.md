---
runbook_version: 1
feature: 008-captured-visuals
status: passed
mode: light
steps_total: 12
step_results: passed,passed,passed,passed,passed,passed,passed,passed,passed,passed,passed,passed
drafted_at: 1e03d3c
drafted_fingerprint: 7f27f8971da9d67f4b677ffd6eaa8389cb302f3fb4d8a42be613e33a0e15988a
tested_at: 4ca32c3
tested_fingerprint: df61dc13123c25367575dfb8e6c9c866adec8ca24e3cc52c7c995a24c07040a1
updated: 2026-11-22
---

# Try it: Captured visuals (web UI screenshots and rendered CLI output)

<!-- runbook-status -->
> **Status:** passed · 12 of 12 steps (12 passed) · Mode: light · Tested at 4ca32c3 · 2026-11-22
<!-- /runbook-status -->













## What you're testing

A guide project declares visuals in `visuals.yaml`, and one command captures them unattended in throwaway podman containers: a colored CLI output rendered to a self-contained SVG, and an annotated, cropped screenshot of a small web page served by nginx with seeded data. Each visual gets a text sidecar that checks, reviews, and drift read instead of the image.

The journey: check podman, scaffold a scratch gfm guide, add the fixture recipe (with this machine's real home path, user name, and host name planted in the demo output), validate the recipe, capture, look at the images, confirm that no host value leaked, read a sidecar, embed the visuals and run `make check`, run visual drift on an unchanged recipe, change the seed and see drift reported, confirm that no container or network is left behind, and clean up.

## Test environment

No fixtures beyond podman itself: every container and network is created and removed by the capture command. The first capture builds the capture image (`localhost/cc-guide-capture:<version>`), which takes several minutes once and is reused afterwards. All files live under `${TMPDIR:-/tmp}/ccg-walk/`.

## Steps

### Step 1 of 12: Check that podman can run containers (US2)

**Why this step:** Captures run only with podman; without it the capture command stops with exit 2.

**Run:**

```
podman info --format '{{.Host.Arch}} {{.Version.Version}}'
```

**What you should see:** One line with the architecture and version, for example `arm64 6.2.0`.

**If you see something else:** An error about the connection means the podman machine is stopped; run `podman machine start`.

**Result:** Passed (agent). Output `arm64 6.0.0` (podman machine server 6.0.0, client 6.2.0).

### Step 2 of 12: Scaffold a scratch gfm guide (US5)

**Why this step:** Visuals live in a guide project; this creates one with the current toolkit (0.6.0, with `visuals.py` and `capture/`).

**Run:**

```
rm -rf "${TMPDIR:-/tmp}/ccg-walk" && CC_GUIDE_SKIP_NPM=1 bash tests/adapters/scaffold.sh gfm "${TMPDIR:-/tmp}/ccg-walk/guide" && ls "${TMPDIR:-/tmp}/ccg-walk/guide/tools/guide/capture" && cat "${TMPDIR:-/tmp}/ccg-walk/guide/tools/guide/VERSION"
```

**What you should see:** The capture build context files (`Containerfile`, `runner.py`, `web.py`, `render_cli.py`, `redact.py`, `licenses`) and the version `0.6.0`.

**If you see something else:** "target is not empty" means an earlier walkthrough left files; the `rm -rf` at the start should prevent it.

**Result:** Passed (agent). `capture/` lists Containerfile, licenses, redact.py, render_cli.py, runner.py, web.py; VERSION `0.6.0`.

### Step 3 of 12: Add the fixture recipe with real host values planted (US1)

**Why this step:** The demo CLI output and the seeded web page print this machine's home path, user name, and host name, so the next steps prove that redaction removes them.

**Run:**

```
G="${TMPDIR:-/tmp}/ccg-walk/guide"; cp tests/adapters/fixtures/visuals/visuals.yaml "$G/" && mkdir -p "$G/visuals" && cp -R tests/adapters/fixtures/visuals/visuals/. "$G/visuals/" && for f in "$G/visuals/demo/colors.sh" "$G/visuals/seed/index.html"; do sed -i.bak -e "s|@@HOME@@|$HOME|g" -e "s|@@USER@@|$(id -un)|g" -e "s|@@HOST@@|$(hostname)|g" "$f" && rm -f "$f.bak"; done; grep -c "$(id -un)" "$G/visuals/demo/colors.sh"
```

**What you should see:** A number of 1 or more: the scratch copy of the demo script now contains your user name.

**If you see something else:** 0 means the placeholders were not replaced; check that the fixture still contains `@@USER@@`.

**Result:** Passed (agent). The user name occurs 4 times in the scratch demo script.

### Step 4 of 12: Validate the recipe without starting anything (US1)

**Why this step:** The schema check catches recipe mistakes before any container starts (FR-007).

**Run:**

```
cd "${TMPDIR:-/tmp}/ccg-walk/guide" && uv run --quiet tools/guide/visuals.py validate; echo "exit=$?"
```

**What you should see:** No problem lines and `exit=0`.

**If you see something else:** Lines of the form `visuals.yaml: <path>: <message>` point at the recipe entry to fix.

**Result:** Passed (agent). `visuals.yaml: 2 visuals, 2 environments, no problems`, `exit=0`.

### Step 5 of 12: Capture both visuals (US1, US2)

**Why this step:** This is the unattended run: build or reuse the capture image, start the alpine and nginx containers on a private network, seed the page, capture, redact, write images and sidecars, and tear everything down.

**Run:**

```
make -C "${TMPDIR:-/tmp}/ccg-walk/guide" visuals; echo "exit=$?"
```

**What you should see:** A summary with `captured  colors` and `captured  table`, then `exit=0`. The first run also shows the capture image build.

**If you see something else:** `failed  table` with a step number and selector means the page or selector did not match; `capture already running` means another capture holds the lock.

**Result:** Passed (agent). `captured  colors  docs/assets/visuals/colors.svg`, `captured  table  docs/assets/visuals/table.png`, `exit=0` (capture image cached).

### Step 6 of 12: Look at the two images (US1, US2)

**Why this step:** Only a person can judge whether the rendering looks right.

**Do:**

1. Run `open "${TMPDIR:-/tmp}/ccg-walk/guide/docs/assets/visuals/table.png"`.
2. Run `open -a Safari "${TMPDIR:-/tmp}/ccg-walk/guide/docs/assets/visuals/colors.svg"` (any browser works).

**What you should see:** The PNG shows the table with its caption (the caption's path and host name replaced by `/home/user` and `example-host`), the `accuracy` header outlined, a red callout `1` outside the outline that covers no text, and the rest dimmed. The SVG shows a `$ sh /visuals/demo/colors.sh` prompt line, a bold green `PASS`, an orange truecolor word, a block progress bar, neutral replacement values where your home path, user name, and host name were printed, redacted `Bearer` and key values, and three emoji lines (rocket, the woman-technologist ZWJ sequence as one emoji, and a colored warning sign).

**If you see something else:** Missing colors in the SVG point at the pseudo-terminal capture; a full page instead of a table points at the crop step.

**Result:** Passed (user, by eye). Crop with redacted caption, outline on `accuracy`, callout `1` outside the outline covering no text, dimming; SVG colors, redaction, and three emoji as expected.

### Step 7 of 12: Confirm that no host value leaked (US1, US2)

**Why this step:** SC-004: images and sidecars must not contain the capturing user's name, home path, or host name.

**Run:**

```
G="${TMPDIR:-/tmp}/ccg-walk/guide"; grep -rl -e "$HOME" -e "/$(id -un)" -e "$(hostname)" "$G/docs/assets/visuals" "$G/visuals"/*.visual.yaml; echo "matches_exit=$?"
```

**What you should see:** No file names and `matches_exit=1` (grep found nothing).

**If you see something else:** Any listed file holds a host value that redaction missed.

**Result:** Passed (agent). No file listed, `matches_exit=1`.

### Step 8 of 12: Read the sidecar a text-only reviewer would use (US3)

**Why this step:** Reviews and drift work on the sidecar text, not the pixels (FR-017, FR-025).

**Run:**

```
cat "${TMPDIR:-/tmp}/ccg-walk/guide/visuals/table.visual.yaml"
```

**What you should see:** Provenance (`environment.image` with `digest` and `platform`), `fingerprint`, a `redaction` block with rule ids and counts but no host values, a `highlights` entry with label `"1"` and text `accuracy`, and a `text` outline with the caption (redacted), `columnheader "accuracy"`, and `columnheader "loss"`.

**If you see something else:** Host values in the `redaction` block or an empty `text` would be a bug.

**Result:** Passed (agent). Sidecar with digest and `linux/arm64`, fingerprint, rule ids and counts only (home-path 1, user-path 1, hostname 1, api-key 2), highlight `1` with text `accuracy`, outline with the redacted caption and `columnheader "accuracy"`, `columnheader "loss"`.

### Step 9 of 12: Embed the visuals and run the guide checks (US3)

**Why this step:** A page that embeds a visual must cite `visual:<name>`; `make check` verifies recipes, images, sidecars, and citations without podman.

**Run:**

```
python3 tests/adapters/add_visuals.py gfm "${TMPDIR:-/tmp}/ccg-walk/guide" --embed-only && make -C "${TMPDIR:-/tmp}/ccg-walk/guide" check >/dev/null 2>&1; echo "check_exit=$?"; mv "${TMPDIR:-/tmp}/ccg-walk/guide/docs/assets/visuals/table.png" "${TMPDIR:-/tmp}/ccg-walk/table.png" && make -C "${TMPDIR:-/tmp}/ccg-walk/guide" check 2>&1 | grep '\[visuals\]'; mv "${TMPDIR:-/tmp}/ccg-walk/table.png" "${TMPDIR:-/tmp}/ccg-walk/guide/docs/assets/visuals/table.png"
```

**What you should see:** `check_exit=0`, then at least one `[visuals]` error line naming the missing `table.png` (the image is restored afterwards).

**If you see something else:** A non-zero first exit means the embedded page or a sidecar fails a rule; read the full `make check` output.

**Result:** Passed (agent). `check_exit=0`; with the image moved away: `docs/user/start.md:42: [visuals] visual 'table' has no image docs/assets/visuals/table.png (run make visuals)`; image restored.

### Step 10 of 12: Run visual drift on the unchanged recipe (US4)

**Why this step:** Repeated captures of an unchanged tool must not report drift (SC-002).

**Run:**

```
cd "${TMPDIR:-/tmp}/ccg-walk/guide" && uv run --quiet tools/guide/visuals.py drift; echo "exit=$?"
```

**What you should see:** A report with no drifted visuals and `exit=0`.

**If you see something else:** `exit=10` on an unchanged recipe means a volatile value is not masked or rendering is not deterministic.

**Result:** Passed (agent). `No visual drift.`, unchanged `colors`, `table`, `exit=0`.

### Step 11 of 12: Change the seed and see drift reported (US4)

**Why this step:** A changed UI label must show up as text drift that names the change (SC-003), while committed files stay untouched (FR-030).

**Run:**

```
cd "${TMPDIR:-/tmp}/ccg-walk/guide" && sed -i.bak 's|<th scope="col">loss</th>|<th scope="col">val-loss</th>|' visuals/seed/index.html && rm -f visuals/seed/index.html.bak && shasum docs/assets/visuals/table.png && uv run --quiet tools/guide/visuals.py drift; echo "exit=$?"; shasum docs/assets/visuals/table.png
```

**What you should see:** A report section for `table` with status `drifted` and a `+` line containing `columnheader "val-loss"`, `exit=10`, and the same `table.png` checksum before and after.

**If you see something else:** `recapture failed` would mean the changed page broke a selector; a different checksum would mean drift wrote into the guide.

**Result:** Passed (agent). `table`: `Status: **drifted**`, `+      - columnheader "val-loss"`, pages `docs/user/start.md`, `exit=10`; `table.png` checksum identical before and after. Image difference reported as 100% because the wider header changed the image size.

### Step 12 of 12: Confirm cleanup and remove the scratch guide (US2)

**Why this step:** No container or network of a run may remain (SC-006).

**Run:**

```
podman ps -a --filter label=io.cc-guide.capture=1 -q | wc -l; podman network ls --filter label=io.cc-guide.capture=1 -q | wc -l; rm -rf "${TMPDIR:-/tmp}/ccg-walk"
```

**What you should see:** `0` and `0`.

**If you see something else:** Any count above 0 means a run left resources; the next capture's sweep removes those of dead runs.

**Result:** Passed (agent). `0` containers and `0` networks with the capture label; scratch removed.

## Not covered here

- `/guide:create` planning visuals and `/guide:evolve --visuals` (US5) are skill flows that need an interactive AI session with a real guide; the toolkit side (`visuals.py init` and `placeholder`) is covered by the unit tests.
- The CI workflow (US6) runs on GitHub Actions; trying it needs a pushed repository, which this walkthrough does not do.
- Light and dark variants need a tool with a dark theme; the nginx fixture page has none.

## Coverage

- US1 (CLI output): steps 3 to 7.
- US2 (web screenshot, self-contained environment, cleanup): steps 1, 5 to 7, 12.
- US3 (text-only review, checks): steps 8 and 9.
- US4 (visual drift): steps 10 and 11.
- US5 (workflow integration): step 2 only (scaffold ships the toolkit); the skill flows are not covered, see above.
- US6 (CI): not covered, see above.

## Results

12 steps: 12 passed, 0 failed, 0 skipped (2026-11-22). The captured visuals feature works end to end on this machine: a scratch guide captures a colored CLI SVG and an annotated, cropped web screenshot in throwaway podman containers, redacts real host values from images and sidecars, passes `make check` with `visual:` citations and fails when an image is missing, reports no drift on an unchanged recipe, reports a changed column header as text drift without touching committed files, and leaves no container or network behind.
