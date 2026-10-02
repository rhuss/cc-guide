---
name: validate
description: Validate a guide's recipes against a live cluster, opt-in. The read-only tier runs only commands positively identified as queries and compares each result with the expectation documented next to it; the full tier runs install and onboarding recipes end to end, only on a connection marked disposable, with confirmation before every mutating command. Output is redacted before it is recorded; mismatches become review findings. Use for /guide:validate.
argument-hint: "--cluster NAME [--tier read-only|full] [--page PATH]... [--dir PATH]"
allowed-tools: ["Bash", "Read", "Write", "AskUserQuestion"]
---

# /guide:validate

Source verification proves the guide matches the code; validation proves the commands work. This skill touches a live cluster, so it follows its safety rules literally (FR-037 to FR-040).

Run every command from the guide project root; never `cd` into `.guide/cache/`.

## 1. Preflight and connection (FR-037)

1. The command wrapper runs `guide:preflight` with `validate`; stop when it stops.
2. `--cluster NAME` is required. Read `clusters.<NAME>` from `guide.yaml`. When it is missing, stop and list the configured connection names, and how to add one:

   ```yaml
   clusters:
     <name>:
       kubeconfig: ~/.kube/<file>   # a reference only; its content is never read into the project
       context: <optional context>
       disposable: false            # true only for a throwaway cluster
   ```
3. The connection is used only for child processes: every command runs with `KUBECONFIG=<path>` in its own environment. Never export it in the session, never copy the kubeconfig, and never print or write its content.
4. When `context` is set, check it first: `KUBECONFIG=<path> kubectl config current-context`. When it differs, stop and ask the author to point the connection at a kubeconfig whose current context is `<context>` (the skill does not modify the author's kubeconfig).

## 2. Tier (FR-038, FR-039)

- `read-only` (default): only queries run.
- `full`: refuse unless `clusters.<NAME>.disposable` is `true`:
  > The full tier changes the cluster, so it runs only on a connection marked disposable. `<NAME>` is not. If this cluster is a throwaway one (for example a kind cluster), set `disposable: true` for it in guide.yaml and run the command again.

## 3. Collect the checks

`uv run tools/guide/classify.py extract` prints a JSON list of check steps (`page`, `line`, `commands`, `expectation`), using the adapter's comment style. Limit it to the `--page` arguments when given. For the full tier, collect every listing of the selected task pages in navigation order as well (install and onboarding recipes), not only the checks.

Classify every command with `uv run tools/guide/classify.py classify "<command>"` (the allowlist ships as `tools/guide/readonly.yaml`; `validate.extra_queries` in `guide.yaml` can only add query patterns). A listing counts as a query only when every command and every pipeline segment in it is a query; anything not positively identified is mutating.

Show the author the plan before anything runs: connection name, tier, number of checks, and the table of commands with their classification. Ask "Run these against `<NAME>`?" and continue only on yes.

## 4. Run

For each check step, in page and line order:

| Situation | Read-only tier | Full tier |
|---|---|---|
| No expectation | `not-evaluable`, not run | `not-evaluable`, not run |
| All commands are queries | run, then match | run, then match |
| Any command is mutating | `skipped` (mutating) | show the exact command and ask: run, skip, or stop. Run only on an explicit yes for that command (`confirmed-and-run`); skip records `declined`; stop ends the run |

Running a command: `KUBECONFIG=<path> bash -c '<command>'` with a timeout of 120 seconds, capturing stdout, stderr, and the exit status. Never chain several mutating commands under one confirmation; each one is confirmed on its own (SC-007).

Matching: the expectation applies to the stdout of the listing's last command and its exit status: `uv run tools/guide/classify.py match '<matcher>' --stdout-file <tmp> --exit <status>` (exit 0 match, 1 mismatch). Write the temporary stdout file under `.guide/runs/<run-id>/tmp/` and delete it right after matching.

Redaction (FR-039a): pipe every output through `uv run tools/guide/classify.py redact` before showing it or writing it anywhere. Never write tokens, kubeconfig content, client keys, or Authorization headers into the guide project, the run records, the findings, or upstream drafts.

## 5. Record (FR-040)

1. Get the run id with `uv run tools/guide/runs.py run-id --command validate`.
2. Write `.guide/runs/<run-id>/validation.md` (local, git-ignored) with a header (connection name, tier, date; never the kubeconfig path content) and one table row per command:

   `| page:line | command | tier | query or mutating | outcome | redacted output excerpt (at most 10 lines) |`

   where outcome is one of `match`, `mismatch`, `not-evaluable`, `skipped`, `confirmed-and-run`, `declined`.
3. Mismatches become review findings: list each under "Review findings" in `validation.md` with the page, line, command, expectation, and what was observed (redacted). The next `/guide:evolve` run adds those pages to its impact set.
4. When a mismatch is caused by the upstream project (for example a documented default that differs from the deployed behavior, and the guide matches the source), also record it with `uv run tools/guide/runs.py findings-add` as an upstream finding (FR-031), quoting the source location at the pinned commit.
5. Write the run summary: `uv run tools/guide/runs.py summary --workspace .guide/runs/<run-id> --run-id <run-id> --command validate --model "<model>"`. Its validation section contains counts only, never command output. Commit `runs/<run-id>.md` and any new findings (`docs(guide): validation run <run-id>`).
6. Report: counts per outcome, every mismatch with its page and line, the commands that were skipped or declined, and confirmation that nothing secret was written.

## Rules

- No command runs before the author approved the plan in section 3; no mutating command runs outside the full tier or without its own confirmation.
- Never write credentials, tokens, or kubeconfig content anywhere; redact before recording.
- No em dash or en dash characters in anything you write.
