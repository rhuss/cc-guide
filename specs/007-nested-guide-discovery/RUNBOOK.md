---
runbook_version: 1
feature: 007-nested-guide-discovery
status: passed
mode: light
steps_total: 6
step_results: skipped,skipped,skipped,skipped,skipped,skipped
drafted_at: 0b55a75
drafted_fingerprint: 034b80b81b2eb2883be67e8cee0619d72b65b5d0562f1a017ee8add142aec91e
tested_at: 0b55a75
tested_fingerprint: 034b80b81b2eb2883be67e8cee0619d72b65b5d0562f1a017ee8add142aec91e
updated: 2026-11-19
---

# Try it: Discover guide projects in nested directories

<!-- runbook-status -->
> **Status:** passed · 6 of 6 steps (6 skipped) · Mode: light · Tested at 0b55a75 · 2026-11-19
<!-- /runbook-status -->







## What you're testing

`guidecfg.py discover` now finds a guide project kept up to three levels below the directory a command runs in, embedded or standalone, instead of only an embedded guide in an immediate subdirectory. The journey builds small throwaway layouts in the walkthrough scratch folder and runs discovery on each: first the cc-review layout from issue #4 (a standalone guide in `docs/guide/`), then how it is reported as not embedded, then the shallowest-wins rule, a tie that must stop and ask, pruned directories, and the depth limit.

All commands run from the worktree root (the repository root of this branch).

## Test environment

No fixtures. Every step creates its own directory under `specs/007-nested-guide-discovery/.walkthrough/demo/` (self-ignoring scratch folder) and copies the test fixture configuration `tests/fixtures/sample-guide/guide.yaml`.

## Steps

### Step 1 of 6: Find a standalone guide in docs/guide from the root (US1)

**Why this step:** This is the reported problem: cc-review keeps its guide at `docs/guide/guide.yaml`, and discovery from the repository root used to exit 4.

**Needs:** nothing

**Run:**

```
D=specs/007-nested-guide-discovery/.walkthrough/demo/s1; rm -rf "$D"; mkdir -p "$D/docs/guide" && cp tests/fixtures/sample-guide/guide.yaml "$D/docs/guide/" && uv run guide/toolkit/guidecfg.py discover --dir "$D"; echo "exit=$?"
```

**What you should see:** one absolute path ending in `.walkthrough/demo/s1/docs/guide`, then `exit=0`.

**If you see something else:** `exit=4` with "no guide project" means the nested search is not active (old toolkit); a Python traceback means the toolkit failed to load (check `uv` and the `pyyaml` dependency).

**Result:**

### Step 2 of 6: The nested standalone guide is reported as not embedded (US1)

**Why this step:** Preflight decides `embedded=yes|no` from the configuration, not from where discovery found it; a standalone guide must not be treated as embedded.

**Needs:** Step 1

**Run:**

```
uv run guide/toolkit/guidecfg.py get embedded.front_page --root specs/007-nested-guide-discovery/.walkthrough/demo/s1/docs/guide; echo "exit=$?"
```

**What you should see:** an empty line, then `exit=0` (no embedded block, so preflight reports `embedded=no`).

**If you see something else:** a printed path means the fixture configuration has an `embedded` block; a non-zero exit with a `file:key: message` line means the copied configuration is not valid on its own (then preflight falls back to checking for a top-level `embedded` key).

**Result:**

### Step 3 of 6: A shallower guide wins over a deeper one (US2)

**Why this step:** When guides exist at different depths, the closest one to the root is used without asking.

**Needs:** nothing

**Run:**

```
D=specs/007-nested-guide-discovery/.walkthrough/demo/s3; rm -rf "$D"; mkdir -p "$D/guide" "$D/docs/guide" && cp tests/fixtures/sample-guide/guide.yaml "$D/guide/" && cp tests/fixtures/sample-guide/guide.yaml "$D/docs/guide/" && uv run guide/toolkit/guidecfg.py discover --dir "$D"; echo "exit=$?"
```

**What you should see:** one path ending in `.walkthrough/demo/s3/guide` (not `docs/guide`), then `exit=0`.

**If you see something else:** the `docs/guide` path means depth ordering is wrong; `exit=3` means guides at different depths are treated as a tie.

**Result:**

### Step 4 of 6: Two equally close guides stop and list both (US2)

**Why this step:** Discovery must never silently pick one of two guides at the same depth; the command asks which one to use.

**Needs:** nothing

**Run:**

```
D=specs/007-nested-guide-discovery/.walkthrough/demo/s4; rm -rf "$D"; mkdir -p "$D/site/guide" "$D/docs/guide" && cp tests/fixtures/sample-guide/guide.yaml "$D/site/guide/" && cp tests/fixtures/sample-guide/guide.yaml "$D/docs/guide/" && uv run guide/toolkit/guidecfg.py discover --dir "$D"; echo "exit=$?"
```

**What you should see:** the line `several guide projects found; name one with --dir:`, then two absolute paths sorted alphabetically (the one ending in `docs/guide` before the one ending in `site/guide`), then `exit=3`.

**If you see something else:** a single path with `exit=0` means ties resolve silently; the old wording "several embedded guides" means the message was not updated.

**Result:**

### Step 5 of 6: Guides inside pruned directories are ignored (US4)

**Why this step:** Configurations inside dependency, build, or hidden trees (such as the guide's own `.guide/cache/`) must never be picked up.

**Needs:** nothing

**Run:**

```
D=specs/007-nested-guide-discovery/.walkthrough/demo/s5; rm -rf "$D"; mkdir -p "$D/node_modules/x" "$D/.guide/cache/x" "$D/build" && for d in node_modules/x .guide/cache/x build; do cp tests/fixtures/sample-guide/guide.yaml "$D/$d/"; done && uv run guide/toolkit/guidecfg.py discover --dir "$D"; echo "exit=$?"
```

**What you should see:** the message `no guide project in ... or the directories below it (up to 3 levels)` and `exit=4`, with no path printed.

**If you see something else:** any printed path means a pruned directory was searched or accepted as a candidate.

**Result:**

### Step 6 of 6: A guide four levels down is out of reach (US4)

**Why this step:** The search is bounded at three levels so it stays fast; deeper guides still need `--dir`.

**Needs:** nothing

**Run:**

```
D=specs/007-nested-guide-discovery/.walkthrough/demo/s6; rm -rf "$D"; mkdir -p "$D/a/b/c/guide" && cp tests/fixtures/sample-guide/guide.yaml "$D/a/b/c/guide/" && uv run guide/toolkit/guidecfg.py discover --dir "$D"; echo "exit=$?"
```

**What you should see:** the "no guide project ... (up to 3 levels)" message and `exit=4`.

**If you see something else:** a path ending in `a/b/c/guide` means the depth limit is not enforced.

**Result:**

## Not covered here

- Running a real `/guide:*` command (for example `/guide:preview`) from the cc-review repository root: it needs that repository checked out and the plugin installed from this branch; the preflight change is text in a skill, exercised indirectly by steps 1 and 2.
- Unreadable and symlinked directories: covered by the automated tests in `tests/toolkit/test_guidecfg.py` (permission changes are awkward to try by hand).

## Coverage

- US1 (nested standalone guide found and reported not embedded): steps 1 and 2.
- US2 (several guides never resolved silently): steps 3 and 4.
- US3 (existing embedded guides keep working): not in this journey; covered by the existing embedded discovery tests, which pass unchanged in intent.
- US4 (pruning and depth limit): steps 5 and 6.

## Results
