# Quickstart: validate the author-owned region feature

Runnable validation scenarios proving the feature end to end. Prerequisites: `uv`, `git`, `node`/`npx`, `pandoc`, Playwright Chromium (the repo's standard toolchain, `make doctor` in a scaffolded guide checks them).

## 1. Unit and toolkit tests

```bash
make test
```

Expected: all of `tests/toolkit/` passes, including the new `test_region.py` (marker parsing, fence masking, splice byte-preservation) and `test_publish.py` (writer, check, rebase), plus the extended `test_embed.py`, `test_check.py`, `test_guidecfg.py`. This is the fastest signal; run it first.

## 2. Publish into an author-owned README (spec story 1)

```bash
# in a scratch gfm guide project created with /guide:create:
# 1. add to guide.yaml:
#      publish:
#        page: docs/intro.md
#        target: ../README.md
# 2. write author text into ../README.md and place the markers:
printf '<!-- guide:region -->\nplaceholder\n<!-- /guide:region -->\n' >> ../README.md
make -C . publish
uv run tools/guide/publish.py --check
```

Expected: `publish` splices the rendered `docs/intro.md` between the markers with links rebased to resolve from the repository root; `--check` exits 0. Edit author text above the markers and re-run `--check`: still 0. Edit text inside the region: exit 1 with a diff. Delete the markers: exit 1 with the missing-markers error and no write.

## 3. Embedded front page with an author region (spec story 2)

```bash
# in a scratch repository with an embedded guide (spec 005 quickstart):
# add markers to the root README with the guide content between them,
# author text above
uv run tools/guide/embed.py front-page-status        # unchanged
# edit author text above the markers
uv run tools/guide/embed.py front-page-status        # still unchanged
# edit text inside the region
uv run tools/guide/embed.py front-page-status        # edited, diff shows region only
make check                                            # region rules, structure, links pass
```

Expected: author edits are invisible to hand-edit detection; region edits are reported; `make check` validates the region's structure (ownership comment inside the region, persona links, section titles) and the whole file's links.

## 4. Embedded create keeps landing material (spec story 3)

```bash
# scratch repository whose README has a pitch section above instructional sections:
# run /guide:create from the repository root, choose embedded, approve the move plan
```

Expected: the move plan lists the pitch sections with destination `author-region` (the default for landing material) and instructional sections as `input`; after apply, the pitch text stands byte-identical above the markers and the front page task fills the region below; the run summary lists no dropped claims from the pitch sections.

## 5. Advisory contradiction (spec story 4)

```bash
# in the fixture from scenario 2 or 3: make the author text contradict a verified
# guide statement, then run the page review for the source page / front page
```

Expected: the review output lists the contradiction as a non-blocking finding; `make check` and every gate pass (only an unresolvable author link would fail, FR-008).

Full implementation steps per scenario live in `tasks.md`; this guide stays a validation script.
