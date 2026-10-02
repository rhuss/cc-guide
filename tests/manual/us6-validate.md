# User Story 6: validate (quickstart scenario 9)

Needs two cluster connections: a read-only kubeconfig for an existing cluster, and a disposable kind cluster. **Not run during implementation**: running commands against a cluster waits for the author's go-ahead.

The classifier, matcher, and redaction are covered by `tests/toolkit/test_classify.py` (173 tests), and the eval case `eval/cases/classify-mutating` checks that the validate flow classifies every mutating command as mutating.

## Setup

```bash
# disposable cluster, podman provider
KIND_EXPERIMENTAL_PROVIDER=podman kind create cluster --name guide-validate
kind get kubeconfig --name guide-validate > ~/.kube/kind-guide-validate
```

In the guide project's `guide.yaml`:

```yaml
clusters:
  readonly-test:
    kubeconfig: ~/.kube/<read-only kubeconfig>
  kind-disposable:
    kubeconfig: ~/.kube/kind-guide-validate
    disposable: true
```

Add one correct and one deliberately wrong check to a page (for example `kubectl get ns default` with `<!-- expect: contains "default" -->`, and the same command with `<!-- expect: contains "nope" -->`).

## Record

| Command | Expectation | Result |
|---|---|---|
| `/guide:validate --cluster readonly-test` | only queries run; the correct check `match`, the wrong one `mismatch`, checks without expectation `not-evaluable`, mutating steps `skipped` | |
| `/guide:validate --cluster readonly-test --tier full` | refused: not disposable, with the explanation | |
| `/guide:validate --cluster kind-disposable --tier full` | every mutating command shown and confirmed one by one | |
| `rg -n 'token\|client-key-data\|BEGIN' .guide runs findings` in the guide project | no secrets | |
| The run summary's validation section | counts only, no command output | |

Cleanup: `kind delete cluster --name guide-validate`.
