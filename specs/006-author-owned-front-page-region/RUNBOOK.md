---
runbook_version: 1
feature: 006-author-owned-front-page-region
status: passed
mode: light
steps_total: 12
step_results: skipped,skipped,skipped,skipped,skipped,skipped,skipped,skipped,skipped,skipped,skipped,skipped
drafted_at: e2effea
drafted_fingerprint: 86bacbb3afb77a4ea95cfb70956e649adf3413d080631a12dafcfed72cd36880
tested_at: e2effea
tested_fingerprint: 86bacbb3afb77a4ea95cfb70956e649adf3413d080631a12dafcfed72cd36880
updated: 2026-11-09
---

# Try it: author-owned region on the generated front page

<!-- runbook-status -->
> **Status:** passed · 12 of 12 steps (12 skipped) · Mode: light · Tested at e2effea · 2026-11-09
<!-- /runbook-status -->













## What you're testing

A gfm guide can own exactly one region of a README, delimited by
`<!-- guide:region -->` and `<!-- /guide:region -->` markers, while the author
owns every byte outside the markers. The journey exercises both consumers:

1. A plain gfm guide that publishes `docs/intro.md` into an author README
   (US1): the writer splices only the region, the checker compares only the
   region, author edits are tolerated, region edits and missing markers are
   refused.
2. An embedded guide whose front page is the host README (US2): hand-edit
   detection sees the region only, and structure checks validate the region.

Run all steps in one terminal session; the steps share shell variables
(`$REPO`, `$WORK`, `$HOST`) and the working directory. Commands use macOS sed
(`sed -i ''`); on Linux, drop the empty string argument. `$REPO` is this
cc-guide checkout on the merged branch.

## Test environment

None. The steps create throwaway scratch directories under `$(mktemp -d)` and
a throwaway git repository; delete `$WORK` when done.

## Steps

### Step 1 of 12: Set up a scratch playground (US1)

**Why this step:** The feature is tried on throwaway copies of the toolkit,
never on a real guide project.

**Needs:** A shell in this cc-guide checkout.

**Run:**

```
REPO="$(pwd)"
WORK="$(mktemp -d)"
mkdir -p "$WORK/play/guide/tools/guide" "$WORK/play/guide/docs"
cp "$REPO"/guide/toolkit/*.py "$WORK/play/guide/tools/guide/"
cp "$REPO/guide/adapters/gfm/adapter.yaml" "$WORK/play/guide/tools/guide/adapter.yaml"
ls "$WORK/play/guide/tools/guide" | sort | head
```

**What you should see:** No errors, and the listing includes `adapter.yaml`,
`embed.py`, `guidecfg.py`, `publish.py`, and `region.py`.

**If you see something else:** A missing file means the checkout is not on the
branch that carries the feature; check `git log --oneline -1` mentions specs/006.

**Result:**

### Step 2 of 12: Declare the guide and its source page (US1)

**Why this step:** The publish declaration in guide.yaml is what ties a guide
page to an author-owned README region.

**Needs:** Step 1.

**Run:**

```
cat > "$WORK/play/guide/guide.yaml" <<'EOF'
schema: 1
title: Pub Guide
format: gfm
personas:
  - id: admin
    title: Administrator
    start: docs/intro
sections:
  - id: overview
    title: Overview
    voice: concepts
publish:
  page: docs/intro.md
  target: ../README.md
EOF
cat > "$WORK/play/guide/docs/intro.md" <<'EOF'
# Overview

Start with the [install steps](admin/install.md) and see the
[architecture](assets/arch.svg).
EOF
```

**What you should see:** No output; both files are written
(`guide.yaml` names `../README.md` as the publish target).

**If you see something else:** A YAML parse error means an indentation slip in
the heredoc; redo the step.

**Result:**

### Step 3 of 12: Write the author README with markers (US1)

**Why this step:** The target README carries the author's text and one marker
pair marking where guide content belongs.

**Needs:** Step 2.

**Run:**

```
cat > "$WORK/play/README.md" <<'EOF'
# My Project

Hand-written pitch. Every byte here is the author's.

<!-- guide:region -->
placeholder
<!-- /guide:region -->

Trailing author text, also untouchable.
EOF
cat "$WORK/play/README.md"
```

**What you should see:** The README with the pitch above the begin marker,
`placeholder` between the markers, and trailing text below the end marker.

**If you see something else:** A typo in either marker line (the exact strings
`<!-- guide:region -->` and `<!-- /guide:region -->`) makes every later step
fail with a region error; redo the step.

**Result:**

### Step 4 of 12: Publish the page into the region (US1)

**Why this step:** This is the core write: only the text between the markers
changes, and relative links are rebased so they resolve from the README's
directory.

**Needs:** Steps 1 to 3.

**Run:**

```
cd "$WORK/play/guide"
uv run tools/guide/publish.py --write
cat "$WORK/play/README.md"
```

**What you should see:** The line `publish: ../README.md updated`, then the
README with the pitch and trailing text byte-identical to step 3, the
`placeholder` gone, and between the markers the rendered page with links
rebased: `[install steps](docs/admin/install.md)` and
`[architecture](docs/assets/arch.svg)`.

**If you see something else:** An error naming a marker problem means the
target lost or doubled a marker; an unrebased link (`admin/install.md`)
means the checkout predates the feature.

**Result:**

### Step 5 of 12: Check the published region (US1)

**Why this step:** The check mode is what a CI or `make check` runs: it must
be quiet when the region is current.

**Needs:** Step 4.

**Run:**

```
uv run tools/guide/publish.py --check; echo "exit: $?"
```

**What you should see:** `publish: ../README.md up to date` and `exit: 0`.

**If you see something else:** A diff and exit 1 means the region drifted from
the source page; rerun with `--write` to refresh it.

**Result:**

### Step 6 of 12: Author edits are tolerated (US1)

**Why this step:** The whole point of the region: the author can edit their
own text without the guide noticing.

**Needs:** Step 5.

**Run:**

```
sed -i '' 's/Hand-written pitch/Hand-written pitch, edited by hand/' "$WORK/play/README.md"
uv run tools/guide/publish.py --check; echo "exit: $?"
```

**What you should see:** `publish: ../README.md up to date` and `exit: 0`
even though the README changed above the markers.

**If you see something else:** A diff and exit 1 means the check compared
whole-file content instead of the region only; that would be a bug.

**Result:**

### Step 7 of 12: Region edits are detected (US1)

**Why this step:** Guide-owned content must not be hand-edited; the check
fails with a diff pointing at the region.

**Needs:** Step 6.

**Run:**

```
sed -i '' 's/# Overview/# Overview (edited)/' "$WORK/play/README.md"
uv run tools/guide/publish.py --check; echo "exit: $?"
```

**What you should see:** `publish: ../README.md differs (1 lines)` followed by
a unified diff from `../README.md (region)` to `docs/intro.md (rendered)`
showing the heading change, and `exit: 1`.

**If you see something else:** Exit 0 means a region edit went undetected;
that would be a bug.

**Result:**

### Step 8 of 12: A README without markers is refused (US1)

**Why this step:** The writer must never guess where guide content belongs;
without markers it refuses and writes nothing.

**Needs:** Step 7.

**Run:**

```
grep -v 'guide:region' "$WORK/play/README.md" > "$WORK/play/README.stripped"
cksum "$WORK/play/README.md"
cp "$WORK/play/README.stripped" "$WORK/play/README.md"
uv run tools/guide/publish.py --write; echo "exit: $?"
cksum "$WORK/play/README.md"
```

**What you should see:** An error on stderr naming the missing
`<!-- guide:region -->` / `<!-- /guide:region -->` pair, `exit: 1`, and the
two cksum lines identical (nothing was written).

**If you see something else:** A changed second cksum means the writer touched
a file it refused; that would be a bug.

**Result:**

### Step 9 of 12: Build an embedded scratch host (US2)

**Why this step:** The second consumer needs a host repository whose README is
the guide's front page, with the guide pinned to a commit of that repository.

**Needs:** Step 1 (for `$REPO` and `$WORK`).

**Run:**

```
HOST="$WORK/host"
mkdir -p "$HOST/guide/docs/admin" "$HOST/guide/tools/guide" "$HOST/config"
cp "$REPO"/guide/toolkit/*.py "$HOST/guide/tools/guide/"
cp "$REPO/guide/adapters/gfm/adapter.yaml" "$HOST/guide/tools/guide/adapter.yaml"
printf 'greeting: hello\n' > "$HOST/config/defaults.yaml"
cat > "$HOST/guide/docs/admin/install.md" <<'EOF'
# Install

<!-- Sources:
self:config/defaults.yaml:1-1
-->

The greeting comes from the defaults file.
EOF
cat > "$HOST/guide/docs/README.md" <<'EOF'
<!-- guide: no-sources -->

This guide starts at the [repository front page](../../README.md).
EOF
cat > "$HOST/guide/docs/SUMMARY.md" <<'EOF'
# Summary

<!-- guide: no-sources -->

## Overview

- [Mini Host](README.md)

## Admin guide

- [Install](admin/install.md)
EOF
cat > "$HOST/guide/guide.yaml" <<'EOF'
schema: 1
title: Mini Host
format: gfm
personas:
  - id: admin
    title: Administrator
    start: admin/install
sections:
  - id: overview
    title: Overview
    voice: concepts
  - id: admin
    title: Admin guide
    voice: technical
embedded:
  front_page: ../README.md
EOF
git -C "$HOST" init -q
git -C "$HOST" add -A
git -C "$HOST" -c user.name=scratch -c user.email=scratch@example.com commit -qm scratch
COMMIT="$(git -C "$HOST" rev-parse HEAD)"
cat > "$HOST/guide/baseline.yaml" <<EOF
captured: 2026-11-09
sources:
  - id: self
    repo: ..
    ref: main
    commit: $COMMIT
    status: verified
EOF
printf '# Mini Host\n\nplaceholder front page\n' > "$HOST/README.md"
echo "host ready at $HOST (commit $COMMIT)"
```

**What you should see:** The final line `host ready at ...` with a 40-character
commit SHA.

**If you see something else:** A git identity error means your global git
config lacks user.name; the inline `-c` flags cover it, so a failure here is
likely a missing directory from an earlier line; redo the step.

**Result:**

### Step 10 of 12: Put the front page in a region and record it (US2)

**Why this step:** Markers on the embedded front page scope every guide
command to the region; recording stores the region as the reference for
hand-edit detection.

**Needs:** Step 9.

**Run:**

```
cat > "$HOST/README.md" <<'EOF'
# Mini Host

Author text above the region: a pitch line the guide must never touch.

<!-- guide:region -->
<!-- guide: front page. This file is generated and maintained by cc-guide; change it with /guide:evolve. -->

# Mini Host

<!-- guide: no-sources -->

Mini Host prints a greeting.

## Overview

Read the guide in this order.

## Admin guide

- [Install](guide/docs/admin/install.md)
<!-- /guide:region -->

Trailing author text, also untouchable.
EOF
cd "$HOST/guide"
uv run tools/guide/embed.py front-page-status --record
uv run tools/guide/embed.py front-page-status; echo "exit: $?"
```

**What you should see:** The record run reports success, and the plain
front-page-status run reports the front page as unchanged with `exit: 0`.

**If you see something else:** An `unrecorded` message means the record run
did not write the blob; check its error output before continuing.

**Result:**

### Step 11 of 12: Author edits stay invisible to hand-edit detection (US2)

**Why this step:** With markers present, author text is outside every check;
editing it must not be reported.

**Needs:** Step 10.

**Run:**

```
sed -i '' 's/a pitch line the guide must never touch/a pitch line, edited by hand/' "$HOST/README.md"
uv run tools/guide/embed.py front-page-status; echo "exit: $?"
```

**What you should see:** The front page still reported as unchanged with
`exit: 0`, although the README changed above the markers.

**If you see something else:** An `edited` report with a diff in the author
text means the normalization compared whole-file content; that would be a bug.

**Result:**

### Step 12 of 12: A region edit is reported and the checks stay green (US2)

**Why this step:** Guide-owned region content must be reported as a hand edit,
while the structure check validates the region (ownership comment, section
titles, links) and passes.

**Needs:** Step 11.

**Run:**

```
sed -i '' 's/Mini Host prints a greeting./Mini Host prints a modified greeting./' "$HOST/README.md"
uv run tools/guide/embed.py front-page-status; echo "exit: $?"
uv run tools/guide/check.py --structure; echo "exit: $?"
```

**What you should see:** front-page-status exits 10 with an `edited` report
whose diff shows only the greeting line inside the region; check.py --structure
reports no violations (at most fingerprint warnings) and exits 0.

**If you see something else:** A structure violation pointing at author text
means the structure rules escaped the region; that would be a bug.

**Result:**

## Not covered here

- US3 (embedded create keeps landing material as the author region): the
  apply mechanics are covered by the pytest suite
  (`tests/toolkit/test_embed.py`); trying them by hand needs an interactive
  `/guide:create` session with intake, the classification table, and move-plan
  approval.
- US4 (advisory contradiction findings): the reviewer behavior lives in skill
  markdown and is only visible in a live page review session; `make check`
  passing over contradicting author text is covered by
  `tests/toolkit/test_check.py`.

## Coverage

- US1 (publish into an author-owned README): covered end to end by steps 1 to
  8 (write, check, author-edit tolerance, region-edit detection, missing
  markers).
- US2 (author-owned region on the embedded front page): covered by steps 9 to
  12 (record, author-edit invisibility, region-edit report, structure check).
  The `make publish` / `make check` Makefile wiring is exercised through the
  same CLIs the targets call.
- US3 (create move-plan destination): not covered, see Not covered here.
- US4 (advisory contradictions): not covered, see Not covered here.

## Results
