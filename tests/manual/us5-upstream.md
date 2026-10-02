# User Story 5: upstream (quickstart scenario 8)

Needs a throwaway GitHub repository you own, because the scenario files a real issue after approval. **Not run during implementation**: creating the repository and filing an issue are outward actions that wait for the author.

The re-verification and dedupe logic is covered by `tests/toolkit/test_upstream.py` (31 tests, local repositories), and the offline rehearsal is the eval case `eval/cases/upstream-stale-finding` (UF-2 fixed on the default branch must be dropped; nothing may be filed).

## Procedure

1. Push the fixture source repository (`tests/fixtures/make-mini-repo.sh`) to a new **private** repository you own, for example `<you>/minisvc-upstream-test`.
2. Run scenario 3 of `us1-create.md` against that repository (`--source mini=<you>/minisvc-upstream-test@<first commit>`), so `findings/upstream.yaml` holds the README port drift.
3. Push one more commit to the test repository that fixes a second finding (or add a second finding by hand that the new commit fixes).
4. Run `/guide:upstream`.

## Record

| Expectation | Result |
|---|---|
| Each finding is re-verified on the default branch; the fixed one is dropped with a note | |
| Every draft is shown in full and ends with the provenance note | |
| No draft contains `ACME Corp`, a ticket key, an internal link, or a private repository link | |
| Nothing is posted before approval; declining leaves the finding `rejected` | |
| An approved draft becomes an issue; its URL is recorded as `filed` in `findings/upstream.yaml` | |
| With `--pr` on a doc-drift finding: fork, branch, diff shown, pull request only after approval | |
