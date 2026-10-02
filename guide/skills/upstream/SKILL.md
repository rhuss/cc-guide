---
name: upstream
description: Report problems found in a guide's sources back to their owners. Re-verifies every collected finding against the current default branch, merges duplicates, shows existing upstream reports, drafts each issue with a provenance note, sanitizes it for public repositories, shows every draft in full, and files only what the author approves; optionally prepares a change proposal from a fork for mechanical documentation fixes. Use for /guide:upstream.
argument-hint: "[--finding UF-N]... [--pr] [--dir PATH]"
allowed-tools: ["Bash", "Read", "Write", "Edit", "AskUserQuestion"]
---

# /guide:upstream

Findings live in `findings/upstream.yaml` (collected by create, evolve, and validate). This skill turns them into upstream reports. **Nothing is posted without the author's explicit approval of the exact text** (FR-033, SC-006). Run every command from the guide project root; never `cd` into `.guide/cache/`.

## Arguments

| Argument | Meaning |
|---|---|
| `--finding UF-N` | Repeatable; limit to these findings. Default: all with status `collected`, `needs-review`, `reverified`, or `drafted` |
| `--pr` | Offer change proposals (pull requests from a fork) for mechanical documentation fixes |

## 1. Preflight

The command wrapper runs `guide:preflight` with `upstream`. Then check `gh auth status`; when it fails, stop and ask the author to run `! gh auth login`. Get a run id with `uv run tools/guide/runs.py run-id --command upstream`.

## 2. Re-verify (FR-032)

1. Mechanical: `uv run tools/guide/upstream.py reverify <ids>` (or `--all`). It fetches each source's default-branch head and searches every location's quote there, tolerating moved lines. Each line of output is `UF-n <status> <sha7>[: note]`.
2. Semantic, for every finding (not only `needs-review`): open the cited files at the reverified commit (`git -C .guide/cache/<id>.git show <sha>:<path>`) and decide whether the problem still holds. Test behavior claims empirically where you can (a ten-line Makefile, a one-line script) instead of trusting a reading; two of four candidates in the SAW run did not hold.
   - Still holds, text unchanged: keep `reverified`.
   - Still holds, but the text moved or changed: update the finding's `locations` (`ref` and `quote`) in `findings/upstream.yaml` and run `reverify` again.
   - No longer holds (fixed, intentional, or wrong): `uv run tools/guide/upstream.py record UF-n --status dropped --note "<why, with the commit>"`.

## 3. Duplicates and existing reports (FR-036)

1. `uv run tools/guide/upstream.py dedupe` merges findings with the same source and overlapping locations.
2. `uv run tools/guide/upstream.py existing <ids>` searches the source repository's issues. For each match, show it to the author and ask whether it covers the finding. When it does, do not draft a duplicate: `record UF-n --status dropped --note "covered by existing report <url>"`, and link that URL from the guide's internal part (step 6).

## 4. Draft and sanitize (FR-034, FR-035)

1. `uv run tools/guide/upstream.py draft --run-id <run-id> <ids>` writes `.guide/runs/<run-id>/drafts/<UF-n>.md` (first line `# <issue title>`, then the body with the provenance note) and sanitizes it. It refuses findings that were not re-verified.
2. A `naming-ux` finding is always an issue with a proposal, never a change (renames affect existing users); its draft says so.
3. Fill the proposal section with a concrete suggestion when the finding has none. Keep the draft short: what is wrong, where (links to the default-branch lines), the evidence, the proposal.
4. When sanitize reports an error-level problem (a confidential term or pattern such as a ticket key, a link into the internal part, a link to a private repository, the guide's own repository), rewrite the draft without it and run `uv run tools/guide/upstream.py sanitize .guide/runs/<run-id>/drafts/<UF-n>.md` again until it passes. Warnings (repository visibility unknown) need the author's look.

## 5. Approval and filing (FR-033)

For each draft, show the **full** title and body exactly as they would be posted, the target repository, and whether it is public. Ask: approve, edit, or reject.
- Edit: apply the author's changes, sanitize again, and show it again.
- Reject: `record UF-n --status rejected --note "<author's reason>"`.
- Approve: `record UF-n --status approved`, then file it:

  ```bash
  gh issue create --repo <owner>/<name> --title "<title>" --body-file <body file without the title line>
  ```

  and `record UF-n --status filed --filed <issue URL>`.

Never batch approvals: each draft gets its own explicit approval.

### Change proposals (`--pr`, FR-034)

Offer a pull request only for mechanical documentation fixes (`doc-drift`, `stale-reference`, `dead-config`, typos, stale versions), never for `naming-ux` or behavior changes. Each outward step is shown and approved on its own:
1. Fork: `gh repo fork <owner>/<name> --clone=false` (approve).
2. Clone the fork into `.guide/runs/<run-id>/pr-<UF-n>/` (local, outside the cache), create branch `docs/<short-slug>`, make the minimal change, commit with the trailer `Assisted-By: 🤖 Claude Code`.
3. Show the full diff and the pull request title and body (the draft text, sanitized). On approval, push the branch to the fork and run `gh pr create --repo <owner>/<name> --head <fork-owner>:<branch> --title "<title>" --body-file <file>`.
4. Record the pull request URL with `record UF-n --status filed --filed <url>` (after `approved`).

## 6. Link from the guide (FR-036)

When the guide has an internal part, add or update an internal page section listing the filed reports (finding summary and URL), cited with a source block entry `url:<issue url>`. Run `make check` and commit `findings/upstream.yaml` and the page (`docs(guide): record upstream reports`). Without an internal part, commit only `findings/upstream.yaml`.

## 7. Report

List each finding with its final status: filed (URL), dropped (reason), rejected, still drafted. Confirm that nothing was posted without approval.

## Rules

- Post nothing, fork nothing, push nothing without the author's explicit approval of that exact action and text.
- Public drafts never contain ticket keys, customer names, internal links, or links to private repositories.
- No em dash or en dash characters in drafts or anything you write.
