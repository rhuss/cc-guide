import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import classify
import guidecfg

REPO = Path(__file__).resolve().parents[2]
TOOLKIT = REPO / "guide" / "toolkit"
READONLY = REPO / "guide" / "validate" / "readonly.yaml"
SAMPLE_PAGES = REPO / "tests" / "fixtures" / "sample-guide" / "pages"


@pytest.fixture(scope="module")
def allow():
    return classify.load_allowlist()


# --- allowlist sources ---------------------------------------------------------


def test_yaml_and_builtin_agree():
    assert yaml.safe_load(READONLY.read_text()) == classify.DEFAULT_ALLOWLIST


def test_allowlist_lookup_order(tmp_path):
    toolkit = tmp_path / "toolkit"
    toolkit.mkdir()
    (tmp_path / "validate").mkdir()
    assert classify.allowlist_path(toolkit) is None
    (tmp_path / "validate" / "readonly.yaml").write_text("version: 1\n")
    assert classify.allowlist_path(toolkit) == tmp_path / "validate" / "readonly.yaml"
    (toolkit / "readonly.yaml").write_text("version: 1\n")
    assert classify.allowlist_path(toolkit) == toolkit / "readonly.yaml"


def test_builtin_used_without_file(tmp_path):
    data = tmp_path / "x.yaml"
    data.write_text(yaml.safe_dump(classify.DEFAULT_ALLOWLIST))
    assert classify.load_allowlist(path=data).queries == classify.load_allowlist().queries


# --- queries -------------------------------------------------------------------

QUERIES = [
    "oc get pods -n saw",
    "oc -n saw get pods -o wide",
    "oc describe pod/x",
    "oc logs -f deploy/governance-interceptor -c main",
    "oc explain pod.spec",
    "oc api-resources",
    "oc api-versions",
    "oc version",
    "oc whoami",
    "oc auth can-i create pods --as alice",
    "oc adm top nodes",
    "oc config view --minify",
    "oc config current-context",
    "kubectl get pods",
    "kubectl describe svc x",
    "kubectl logs pod/x",
    "kubectl explain deploy",
    "kubectl api-resources",
    "kubectl api-versions",
    "kubectl version --client",
    "kubectl whoami",
    "kubectl auth can-i get pods",
    "kubectl adm top pods",
    "kubectl config view --minify -o json",
    "kubectl config current-context",
    "curl -s http://127.0.0.1:9090/status",
    "curl -X GET https://example.com/api",
    "curl --request HEAD https://example.com",
    "curl --request=get https://example.com",
    "curl -sI https://example.com",
    "curl -s -o /dev/null -w '%{http_code}' http://x/#frag",
    "curl -H 'Authorization: Bearer abc' https://x",
    "openshell status",
    "openshell version",
    "openshell whoami",
    "openshell list",
    "openshell get x",
    "openshell sandbox list",
    "openshell gateway get main",
    "grep -c Running pods.txt",
    "rg -n port config/",
    "jq -r '.items[] | .metadata.name' pods.json",
    "yq '.server.port' config/defaults.yaml",
    "head -n 5 file",
    "tail -n 20 file",
    "wc -l file",
    "sort -u file",
    "uniq -c file",
    "cut -d: -f1 /etc/passwd",
    "awk '{print $1}' file",
]


@pytest.mark.parametrize("cmd", QUERIES)
def test_queries(cmd, allow):
    assert classify.classify(cmd, allow) == "query", classify.explain(cmd, allow)


def test_every_allowlist_entry_is_exercised(allow):
    used = set()
    for cmd in QUERIES:
        for segment in classify.explain(cmd, allow):
            if segment.rule is not None:
                used.add(segment.rule.source)
    entries = {classify.Rule.from_entry(e).source for e in classify.DEFAULT_ALLOWLIST["queries"]}
    assert entries - used == set()


PIPELINES = [
    "oc get pods -o json | jq '.items | length'",
    "oc get pods | grep Running | wc -l",
    "oc get pods 2>/dev/null | head -1",
    "oc get pods 2>&1 | grep -c x",
    "oc get pods &>/dev/null",
    "KUBECONFIG=/tmp/kc oc get pods",
    "oc get pods; oc get svc",
    "oc get pods && oc get svc || oc whoami",
    "oc get pods \\\n  -n saw | \\\n  grep Running",
    "oc get pods\noc get svc",
    "oc get pods   # list them > out.txt",
    "oc get pods < /dev/null",
    "grep x <<< 'a b x'",
]


@pytest.mark.parametrize("cmd", PIPELINES)
def test_query_pipelines(cmd, allow):
    assert classify.classify(cmd, allow) == "query", classify.explain(cmd, allow)


MUTATING = [
    "oc debug node/worker-0",
    "oc exec pod/x -- ls",
    "oc rsh pod/x",
    "oc port-forward svc/x 8080:80",
    "kubectl exec -it x -- sh",
    "kubectl debug node/x",
    "kubectl port-forward svc/x 1:2",
    "make status",
    "make",
    "oc get pods > pods.txt",
    "oc get pods >> pods.txt",
    "oc get pods 2> err.txt",
    "oc get pods | tee pods.txt",
    "oc delete pod x",
    "oc apply -f x.yaml",
    "oc -n debug delete pod x",
    "oc config view",
    "oc config view --minify --raw",
    "oc get pods | sh",
    "oc get pods $(cat names)",
    "oc get pods `cat names`",
    "sudo oc get pods",
    "oc get pods &",
    "(oc get pods)",
    "oc get pods && oc delete pod x",
    "oc get pods | xargs oc delete pod",
    "curl -X POST http://x",
    "curl -XPOST http://x",
    "curl --request=PUT http://x",
    "curl --request DELETE http://x",
    "curl -d a=b http://x",
    "curl -sd a=b http://x",
    "curl --data-raw x http://x",
    "curl --data-urlencode a=b http://x",
    "curl --json '{}' http://x",
    "curl -F f=@x http://x",
    "curl --form f=@x http://x",
    "curl -T f http://x",
    "curl --upload-file f http://x",
    "awk 'BEGIN { system(\"rm x\") }'",
    "awk '{print $1 | \"sh\"}' f",
    "yq -i '.a = 1' f.yaml",
    "sort -o f f",
    "rg --pre cat x",
    "grep '#x' > f",
    "echo hi",
    "ls -l",
    "oc get 'pods",
    "",
    "cat <<EOF\nx\nEOF",
    "diff <(oc get pods) <(oc get svc)",
]


@pytest.mark.parametrize("cmd", MUTATING)
def test_mutating(cmd, allow):
    assert classify.classify(cmd, allow) == "mutating", classify.explain(cmd, allow)


def test_extra_queries_are_additive_only(render_fixture_guide):
    path = render_fixture_guide / "guide.yaml"
    data = yaml.safe_load(path.read_text())
    data["validate"] = {"extra_queries": ["oc debug", "echo", "make status", "openshell sandbox logs"]}
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    guide = guidecfg.load_guide(render_fixture_guide)
    allow = classify.load_allowlist(guide)
    assert classify.classify("echo hi", allow) == "query"
    assert classify.classify("openshell sandbox logs x", allow) == "query"
    assert classify.classify("oc debug node/x", allow) == "mutating"
    assert classify.classify("make status", allow) == "mutating"
    assert classify.classify("echo hi > f", allow) == "mutating"


# --- matcher -------------------------------------------------------------------

MATCHES = [
    ("exit 0", "anything", 0, True),
    ("exit 7", "", 0, False),
    ("exit 7", "", 7, True),
    ('contains "ok"', "status: ok\n", 0, True),
    ('contains "ok"', "fail\n", 0, False),
    ('contains "say \\"hi\\""', 'they say "hi"\n', 0, True),
    ('not-contains "200"', "404", 0, True),
    ('not-contains "200"', "200", 0, False),
    ("matches /^ok$/", "first\nok\n", 0, True),
    ("matches /a\\/b/", "x a/b y", 0, True),
    ("matches /^[0-9]+$/", "12a", 0, False),
    ("lines >= 3", "a\nb\nc\n", 0, True),
    ("lines >= 3", "a\n\nb\n", 0, False),
    ("lines == 1", "ok", 0, True),
    ("lines <= 0", "", 0, True),
    ("lines==2", "a\nb", 0, True),
    ('contains "ok" and lines == 1', "ok", 0, True),
    ('contains "ok" and lines == 1', "ok\nok", 0, False),
    ('exit 0 and contains " and "', "x and y", 0, True),
    ("exit 0 and matches /a and b/ and not-contains \"zz\"", "a and b", 0, True),
]


@pytest.mark.parametrize("matcher,stdout,code,expected", MATCHES)
def test_match(matcher, stdout, code, expected):
    assert classify.match(matcher, stdout, code) is expected


@pytest.mark.parametrize("bad", ["", "contains ok", "lines > 1", "exit x", "matches /open",
                                 'contains "a" or exit 0', "exit 0 and", "equals 3", 'contains "x'])
def test_match_bad_syntax(bad):
    with pytest.raises(classify.MatcherError):
        classify.match(bad, "", 0)


# --- redaction -----------------------------------------------------------------

JWT = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJhbGljZSJ9.c2lnbmF0dXJlLXZhbHVl"


@pytest.mark.parametrize("text,secret", [
    ("Authorization: Bearer abc123", "abc123"),
    ("curl -H 'Authorization: Basic dXNlcjpwYXNz' x", "dXNlcjpwYXNz"),
    ("using bearer s3cr3t-token now", "s3cr3t-token"),
    ("    token: sha256~AbCdEf_123", "AbCdEf_123"),
    ("oc login --token=sha256~QwErTy", "QwErTy"),
    ("oc login --token sha256~QwErTy2", "QwErTy2"),
    ("client-key-data: LS0tLS1CRUdJTi", "LS0tLS1CRUdJTi"),
    ("client-certificate-data: Q0VSVA==", "Q0VSVA=="),
    ("certificate-authority-data: Q0FDQQ==", "Q0FDQQ=="),
    ('{"token": "abc.def"}', "abc.def"),
    ("password: hunter2", "hunter2"),
    (f"id_token={JWT}", JWT),
    (f"see {JWT} here", JWT),
    ("-----BEGIN RSA PRIVATE KEY-----\nMIIEow\nxyz\n-----END RSA PRIVATE KEY-----", "MIIEow"),
])
def test_redact(text, secret):
    out = classify.redact(text)
    assert secret not in out
    assert "REDACTED" in out


def test_redact_leaves_plain_text():
    text = "NAME   READY   STATUS\npod-a  1/1     Running\nport: 9090\n"
    assert classify.redact(text) == text


# --- extraction ----------------------------------------------------------------


def test_extract_fixture_pages():
    pages = sorted(SAMPLE_PAGES.rglob("*.md"))
    steps = classify.extract(pages, "html")
    by_page = {(s.page.relative_to(SAMPLE_PAGES).as_posix(), s.line): s for s in steps}
    assert len(steps) == 4
    index = by_page[("index.md", 29)]
    assert index.commands == ["curl -s http://127.0.0.1:9090/status"]
    assert index.expectation == 'contains "ok"'
    start = next(s for s in steps if s.page.name == "start.md")
    assert start.expectation == 'contains "ok" and lines == 1'
    notes = next(s for s in steps if s.page.name == "notes.md")
    assert notes.commands == ["curl -s http://127.0.0.1:7070/"]
    assert notes.expectation == "exit 7"
    install = next(s for s in steps if s.page.name == "install.md")
    assert install.commands == ["curl -s http://127.0.0.1:9090/status"]
    assert "make install" not in install.commands


def test_extract_check_without_expectation(tmp_path):
    page = tmp_path / "p.md"
    page.write_text("# P\n\nCheck: pods run.\n\n```bash\noc get pods\n```\n\nNext paragraph.\n")
    (step,) = classify.extract([page], "html")
    assert step.expectation is None
    assert step.commands == ["oc get pods"]
    assert step.text == "pods run."


def test_extract_asciidoc(tmp_path):
    page = tmp_path / "p.adoc"
    page.write_text(
        "= P\n\n"
        ". Install it.\n"
        "+\n"
        "Check: the gateway answers.\n"
        "+\n"
        "[source,bash,subs=\"attributes+\"]\n"
        "----\n"
        "$ oc get route gateway \\\n"
        "    -n saw\n"
        "gateway   gateway.apps.example.com\n"
        "$ curl -s https://x/healthz\n"
        "----\n"
        "// expect: contains \"ok\"\n\n"
        "Check: no expectation here.\n\n"
        "[source,bash]\n"
        "----\n"
        "# a comment\n"
        "oc whoami\n"
        "----\n\n"
        "[source,asciidoc]\n"
        "----\n"
        "Check: inside a listing, ignored.\n"
        "----\n"
    )
    first, second = classify.extract([page], "line")
    assert first.line == 5
    assert first.commands == ["oc get route gateway -n saw", "curl -s https://x/healthz"]
    assert first.expectation == 'contains "ok"'
    assert second.commands == ["oc whoami"]
    assert second.expectation is None


def test_extract_check_without_listing(tmp_path):
    page = tmp_path / "p.md"
    page.write_text("# P\n\nCheck: the page shows a banner.\n\nThen continue.\n")
    (step,) = classify.extract([page], "html")
    assert step.commands == [] and step.expectation is None


# --- CLI -----------------------------------------------------------------------


def run(*args, stdin=None):
    return subprocess.run([sys.executable, str(TOOLKIT / "classify.py"), *args],
                          capture_output=True, text=True, input=stdin)


def test_cli_classify():
    assert run("classify", "oc get pods").stdout.strip() == "query"
    assert run("classify", "oc delete pod x").stdout.strip() == "mutating"


def test_cli_match(tmp_path):
    out = tmp_path / "out.txt"
    out.write_text("ok\n")
    assert run("match", 'contains "ok"', "--stdout-file", str(out), "--exit", "0").returncode == 0
    assert run("match", 'contains "no"', "--stdout-file", str(out), "--exit", "0").returncode == 1
    assert run("match", "bogus", "--stdout-file", str(out), "--exit", "0").returncode == 2


def test_cli_redact():
    proc = run("redact", stdin="token: sha256~abc\nplain\n")
    assert "sha256~abc" not in proc.stdout and "plain" in proc.stdout


def test_cli_extract(tmp_guide):
    tools = tmp_guide / "tools" / "guide"
    tools.mkdir(parents=True)
    (tools / "adapter.yaml").write_text(
        "format: gfm\ncontent_root: docs\ninternal_root: internal\npage_glob: '**/*.md'\ncomment: html\n")
    (tmp_guide / "docs").mkdir()
    (tmp_guide / "docs" / "a.md").write_text(
        "# A\n\nCheck: status ok.\n\n```bash\ncurl -s http://x/status\n```\n<!-- expect: contains \"ok\" -->\n\n"
        "Check: install.\n\n```bash\nmake install\n```\n")
    proc = run("extract", "--root", str(tmp_guide))
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert [d["classification"] for d in data] == ["query", "mutating"]
    assert data[0] == {
        "page": "docs/a.md", "line": 3, "text": "status ok.", "commands": ["curl -s http://x/status"],
        "classifications": ["query"], "classification": "query", "expectation": 'contains "ok"',
        "evaluable": True, "internal": False,
    }
    assert data[1]["evaluable"] is False


SECRET_YAML = """apiVersion: v1
data:
  api-key: c2VjcmV0dmFsdWU=
  username: YWRtaW4=
kind: Secret
metadata:
  name: x
"""

SECRET_JSON = """{
    "apiVersion": "v1",
    "data": {
        "api-key": "c2VjcmV0dmFsdWU=",
        "username": "YWRtaW4="
    },
    "kind": "Secret"
}"""


def test_redact_secret_data_yaml_and_json():
    for text in (SECRET_YAML, SECRET_JSON):
        out = classify.redact(text)
        assert "c2VjcmV0dmFsdWU=" not in out and "YWRtaW4=" not in out
        assert "kind" in out and "Secret" in out


@pytest.mark.parametrize("text,secret", [
    ("aws_secret_access_key = wJalrXUtnFEMI/K7MDENG", "wJalrXUtnFEMI"),
    ("token ghp_" + "a" * 36, "ghp_" + "a" * 36),
    ("github_pat_" + "B" * 40, "B" * 40),
    ("SLACK=xoxb-123456789012-abcdefghij", "xoxb-123456789012"),
    ("key AKIAIOSFODNN7EXAMPLE used", "AKIAIOSFODNN7EXAMPLE"),
    ("myApiKey: abc123def456", "abc123def456"),
])
def test_redact_more_token_shapes(text, secret):
    assert secret not in classify.redact(text)


@pytest.mark.parametrize("cmd", [
    "oc get pods --kubeconfig /other/kubeconfig",
    "oc --context=prod get pods",
    "kubectl get ns --server https://other:6443",
    "kubectl --context prod get deploy",
    "oc --kubeconfig=/tmp/kc get nodes",
    "curl -s -o out.html https://example.com/",
    "curl -K cfg https://example.com/",
    "curl -s https://example.com/ --output=x",
    "uniq in.txt out.txt",
])
def test_queries_that_leave_the_connection_or_write_files_are_mutating(cmd):
    assert classify.classify(cmd, classify.load_allowlist()) == "mutating"


def test_tool_deny_flags_also_bind_extra_queries():
    allow = classify.load_allowlist(["oc adm inspect"])
    assert classify.classify("oc adm inspect ns/x", allow) == "query"
    assert classify.classify("oc adm inspect ns/x --kubeconfig /x", allow) == "mutating"


@pytest.mark.parametrize("cmd", ["oc get pods -n saw", "kubectl get ns", "curl -s https://example.com/",
                                 "sort | uniq -c", "uniq in.txt"])
def test_plain_queries_still_queries(cmd):
    assert classify.classify(cmd, classify.load_allowlist()) == "query"


def test_awk_program_file_is_mutating():
    allow = classify.load_allowlist()
    assert classify.classify("awk -f prog.awk data.txt", allow) == "mutating"
    assert classify.classify("awk '{print $1}' data.txt", allow) == "query"
