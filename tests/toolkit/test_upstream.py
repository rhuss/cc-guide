import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import guidecfg
import upstream

TOOLKIT = Path(__file__).resolve().parents[2] / "guide" / "toolkit"
PORT_QUOTE = "The service listens on port 8080 by default."


def write_findings(root: Path, findings: list[dict]) -> None:
    path = root / "findings" / "upstream.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"findings": findings}, sort_keys=False))


def read_findings(root: Path) -> dict[str, dict]:
    return {f["id"]: f for f in guidecfg.load_findings(root)}


def finding(fid: str, ref: str, quote: str | None = PORT_QUOTE, kind: str = "doc-drift", **extra) -> dict:
    loc = {"ref": ref}
    if quote is not None:
        loc["quote"] = quote
    return {"id": fid, "source": "mini", "kind": kind, "locations": [loc],
            "summary": "README states port 8080 while the default configuration uses 9090.",
            "evidence": "config/defaults.yaml sets server.port to 9090.", "status": "collected", **extra}


def commit_change(repo: Path, rel: str, old: str, new: str) -> str:
    path = repo / rel
    path.write_text(path.read_text().replace(old, new))
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
    subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", "commit", "-q", "-am", "change"],
                   check=True, env=env)
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True,
                          text=True).stdout.strip()


# --- reverify -------------------------------------------------------------------


def test_reverify_unchanged_quote(render_fixture_guide, fixture_repo):
    root = render_fixture_guide
    write_findings(root, [finding("UF-1", "README.md:8")])
    assert upstream.reverify(root, "UF-1") == "reverified"
    f = read_findings(root)["UF-1"]
    assert f["status"] == "reverified"
    assert f["reverified_commit"] == fixture_repo[3]  # head of main is the third commit
    assert (root / ".guide" / "cache" / "mini.git").is_dir()


def test_reverify_tolerates_moved_lines_and_whitespace(render_fixture_guide, fixture_repo):
    root = render_fixture_guide
    commit_change(fixture_repo[0], "README.md", "## Running\n", "## Running\n\nNew paragraph.\n")
    write_findings(root, [finding("UF-1", "README.md:8", quote="The service   listens on\nport 8080 by default.")])
    assert upstream.reverify(root, "UF-1") == "reverified"


def test_reverify_quote_gone(render_fixture_guide, fixture_repo):
    root = render_fixture_guide
    write_findings(root, [finding("UF-1", "README.md:8")])
    head = commit_change(fixture_repo[0], "README.md", "port 8080", "port 9090")
    assert upstream.reverify(root, "UF-1") == "needs-review"
    f = read_findings(root)["UF-1"]
    assert f["status"] == "needs-review"
    assert f["reverified_commit"] == head
    assert "README.md" in f["note"]


def test_reverify_file_gone(render_fixture_guide):
    root = render_fixture_guide
    write_findings(root, [finding("UF-1", "Makefile:7", quote="curl -s http://127.0.0.1:9090/status",
                                  kind="stale-reference")])
    assert upstream.reverify(root, "UF-1") == "needs-review"
    assert "Makefile" in read_findings(root)["UF-1"]["note"]


def test_reverify_without_quote_needs_review(render_fixture_guide):
    root = render_fixture_guide
    write_findings(root, [finding("UF-1", "README.md:8", quote=None)])
    assert upstream.reverify(root, "UF-1") == "needs-review"
    assert "quote" in read_findings(root)["UF-1"]["note"]


def test_reverify_unknown_finding(render_fixture_guide):
    write_findings(render_fixture_guide, [finding("UF-1", "README.md:8")])
    with pytest.raises(upstream.UpstreamError):
        upstream.reverify(render_fixture_guide, "UF-9")


# --- draft ----------------------------------------------------------------------


def test_draft_includes_provenance_and_sets_status(render_fixture_guide, fixture_repo):
    root = render_fixture_guide
    write_findings(root, [finding("UF-1", "README.md:8")])
    upstream.reverify(root, "UF-1")
    path = upstream.draft(root, "UF-1", run_id="2026-10-01-upstream")
    assert path == root / ".guide" / "runs" / "2026-10-01-upstream" / "drafts" / "UF-1.md"
    text = path.read_text()
    assert "automated, source-verified documentation review" in text
    assert "README states port 8080" in text
    assert fixture_repo[3] in text
    assert PORT_QUOTE in text
    assert "{{" not in text
    assert read_findings(root)["UF-1"]["status"] == "drafted"


def test_draft_default_run_id(render_fixture_guide):
    root = render_fixture_guide
    write_findings(root, [finding("UF-1", "README.md:8")])
    upstream.reverify(root, "UF-1")
    path = upstream.draft(root, "UF-1")
    assert path.parent.name == "drafts"
    assert path.parent.parent.name.endswith("-upstream")


def test_draft_github_links(render_fixture_guide):
    root = render_fixture_guide
    data = yaml.safe_load((root / "baseline.yaml").read_text())
    data["sources"][0]["repo"] = "acme-oss/minisvc"
    data.pop("change_requests")
    (root / "baseline.yaml").write_text(yaml.safe_dump(data, sort_keys=False))
    sha = "a" * 40
    write_findings(root, [finding("UF-1", "README.md:7-8", status="reverified", reverified_commit=sha)])
    text = upstream.draft(root, "UF-1", run_id="r1").read_text()
    assert f"https://github.com/acme-oss/minisvc/blob/{sha}/README.md#L7-L8" in text


def test_draft_naming_ux_is_issue_with_proposal(render_fixture_guide):
    root = render_fixture_guide
    write_findings(root, [finding("UF-1", "README.md:8", kind="naming-ux",
                                  proposal="Name the setting `server.port` in the README.")])
    upstream.reverify(root, "UF-1")
    text = upstream.draft(root, "UF-1", run_id="r1").read_text()
    assert "Name the setting `server.port` in the README." in text
    assert "issue" in text.lower() and "proposal" in text.lower()
    assert "renam" in text.lower()


def test_draft_without_proposal_has_placeholder(render_fixture_guide):
    root = render_fixture_guide
    write_findings(root, [finding("UF-1", "README.md:8")])
    upstream.reverify(root, "UF-1")
    text = upstream.draft(root, "UF-1", run_id="r1").read_text()
    assert "## Proposal" in text
    assert "author" in text.lower()


def test_draft_requires_reverification(render_fixture_guide):
    root = render_fixture_guide
    write_findings(root, [finding("UF-1", "README.md:8")])
    with pytest.raises(upstream.UpstreamError):
        upstream.draft(root, "UF-1", run_id="r1")


def test_draft_line_follows_moved_quote(render_fixture_guide, fixture_repo):
    root = render_fixture_guide
    commit_change(fixture_repo[0], "README.md", "## Running\n", "## Running\n\nNew paragraph.\n\n")
    write_findings(root, [finding("UF-1", "README.md:8")])
    upstream.reverify(root, "UF-1")
    text = upstream.draft(root, "UF-1", run_id="r1").read_text()
    assert "`README.md:11`" in text  # three lines were added above the old line 8


# --- sanitize -------------------------------------------------------------------


def public_or_private(slug: str):
    return {"acme/private-repo": True, "acme-oss/minisvc": False}.get(slug)


@pytest.mark.parametrize("text,kind", [
    ("The rollout for acme corp starts soon.", "term"),
    ("Tracked in MINI-42.", "pattern"),
    ("See https://guide.example.com/guide/internal/notes.html for context.", "internal-link"),
    ("See xref:internal:notes.adoc[notes].", "internal-link"),
    ("See [notes](../internal/notes.md).", "internal-link"),
    ("Compare https://github.com/acme/private-repo/blob/main/x.yaml.", "private-repo"),
])
def test_sanitize_rejects(render_fixture_guide, text, kind):
    guide = guidecfg.load_guide(render_fixture_guide)
    problems = upstream.sanitize(text, guide, private_check=public_or_private, own_remotes=[])
    assert any(p.kind == kind and p.severity == "error" for p in problems), problems


def test_sanitize_clean_and_public_links(render_fixture_guide):
    guide = guidecfg.load_guide(render_fixture_guide)
    text = "See https://github.com/acme-oss/minisvc/blob/" + "a" * 40 + "/README.md#L8 for the port."
    assert upstream.sanitize(text, guide, private_check=public_or_private, own_remotes=[]) == []


def test_sanitize_unknown_visibility_is_warning(render_fixture_guide):
    guide = guidecfg.load_guide(render_fixture_guide)
    problems = upstream.sanitize("https://github.com/someone/unknown", guide,
                                 private_check=lambda slug: None, own_remotes=[])
    assert [p.severity for p in problems] == ["warning"]


def test_sanitize_own_remote(render_fixture_guide):
    root = render_fixture_guide
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "remote", "add", "origin",
                    "git@github.com:rhuss/minisvc-guide.git"], check=True)
    guide = guidecfg.load_guide(root)
    problems = upstream.sanitize("Background: https://github.com/rhuss/minisvc-guide/pull/3", guide,
                                 private_check=lambda slug: False)
    assert any(p.kind == "own-repo" for p in problems)


def test_drafted_text_passes_sanitize(render_fixture_guide):
    root = render_fixture_guide
    write_findings(root, [finding("UF-1", "README.md:8")])
    upstream.reverify(root, "UF-1")
    text = upstream.draft(root, "UF-1", run_id="r1").read_text()
    guide = guidecfg.load_guide(root)
    assert upstream.sanitize(text, guide, private_check=lambda s: False, own_remotes=[]) == []


# --- dedupe ---------------------------------------------------------------------


def test_dedupe_merges_overlapping(render_fixture_guide):
    root = render_fixture_guide
    write_findings(root, [
        finding("UF-1", "README.md:8"),
        finding("UF-2", "README.md:7-9", quote="by default"),
        finding("UF-3", "config/defaults.yaml:3", quote="port: 9090"),
        finding("UF-4", "docs/setup.md:2", quote="The service listens on port 8080 by default."),
    ])
    merges = upstream.dedupe(root)
    assert {(m.merged, m.kept) for m in merges} == {("UF-2", "UF-1"), ("UF-4", "UF-1")}
    f = read_findings(root)
    assert f["UF-2"]["status"] == "merged" and f["UF-2"]["merged_into"] == "UF-1"
    assert f["UF-4"]["merged_into"] == "UF-1"
    assert f["UF-3"]["status"] == "collected"
    assert upstream.dedupe(root) == []


def test_dedupe_other_source_not_merged(render_fixture_guide):
    root = render_fixture_guide
    other = dict(finding("UF-2", "README.md:8"), source="other")
    path = root / "findings" / "upstream.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump({"findings": [finding("UF-1", "README.md:8"), other]}))
    assert upstream.dedupe(root) == []


# --- existing -------------------------------------------------------------------


def test_existing_uses_search(render_fixture_guide):
    root = render_fixture_guide
    data = yaml.safe_load((root / "baseline.yaml").read_text())
    data["sources"][0]["repo"] = "https://github.com/acme-oss/minisvc.git"
    data.pop("change_requests")
    (root / "baseline.yaml").write_text(yaml.safe_dump(data, sort_keys=False))
    calls = []

    def search(slug, query):
        calls.append((slug, query))
        return [{"url": "https://github.com/acme-oss/minisvc/issues/12", "title": "README port is wrong"}]

    urls = upstream.existing(finding("UF-1", "README.md:8"), search=search, root=root)
    assert urls == ["https://github.com/acme-oss/minisvc/issues/12"]
    assert calls[0][0] == "acme-oss/minisvc"
    assert "port" in calls[0][1]


def test_existing_non_github_source(render_fixture_guide):
    called = []
    urls = upstream.existing(finding("UF-1", "README.md:8"), search=lambda s, q: called.append(1) or [],
                             root=render_fixture_guide)
    assert urls == [] and not called


# --- CLI ------------------------------------------------------------------------


def run_cli(*args):
    return subprocess.run([sys.executable, str(TOOLKIT / "upstream.py"), *args], capture_output=True, text=True)


def test_cli_reverify_and_dedupe(render_fixture_guide):
    root = render_fixture_guide
    write_findings(root, [finding("UF-1", "README.md:8"), finding("UF-2", "README.md:8")])
    proc = run_cli("reverify", "--root", str(root), "UF-1")
    assert proc.returncode == 0, proc.stderr
    assert "UF-1 reverified" in proc.stdout
    proc = run_cli("dedupe", "--root", str(root))
    assert proc.returncode == 0
    assert "UF-2 merged into UF-1" in proc.stdout


def test_cli_sanitize_exit_code(render_fixture_guide, tmp_path):
    bad = tmp_path / "draft.md"
    bad.write_text("Customer ACME Corp asked for this.\n")
    proc = run_cli("sanitize", "--root", str(render_fixture_guide), "--offline", str(bad))
    assert proc.returncode == 1
    assert "ACME Corp" in proc.stdout
    good = tmp_path / "good.md"
    good.write_text("The README states port 8080.\n")
    assert run_cli("sanitize", "--root", str(render_fixture_guide), "--offline", str(good)).returncode == 0


def test_cli_draft_prints_path(render_fixture_guide):
    root = render_fixture_guide
    write_findings(root, [finding("UF-1", "README.md:8")])
    upstream.reverify(root, "UF-1")
    proc = run_cli("draft", "--root", str(root), "--run-id", "r1", "--offline", "UF-1")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.strip().endswith("drafts/UF-1.md")


def test_record_enforces_transitions(tmp_path):
    root = tmp_path / "g"
    (root / "findings").mkdir(parents=True)
    (root / "findings" / "upstream.yaml").write_text(yaml.safe_dump({"findings": [{
        "id": "UF-1", "source": "mini", "kind": "doc-drift",
        "locations": [{"ref": "README.md:8", "quote": "port 8080"}],
        "summary": "s", "evidence": "e", "status": "drafted"}]}))
    with pytest.raises(upstream.UpstreamError):
        upstream.record(root, "UF-1", "filed", filed="https://github.com/o/r/issues/1")
    with pytest.raises(upstream.UpstreamError):
        upstream.record(root, "UF-1", "rejected")
    upstream.record(root, "UF-1", "approved")
    with pytest.raises(upstream.UpstreamError):
        upstream.record(root, "UF-1", "filed")
    f = upstream.record(root, "UF-1", "filed", filed="https://github.com/o/r/issues/1")
    assert f["status"] == "filed" and f["filed"].endswith("/1")


def test_sanitize_flags_secrets():
    guide = guidecfg.Guide(root=Path("."), schema=1, title="t", format="antora", personas=[], sections=[])
    problems = upstream.sanitize("Evidence: Authorization: Bearer abc.def.ghi was printed",
                                 guide, private_check=lambda slug: False, own_remotes=[])
    assert any(p.kind == "secret" and p.severity == "error" for p in problems)


def test_dedupe_never_merges_drafted_findings(tmp_path):
    root = tmp_path / "g"
    (root / "findings").mkdir(parents=True)
    base = {"source": "mini", "kind": "doc-drift", "summary": "s", "evidence": "e",
            "locations": [{"ref": "README.md:8", "quote": "port 8080"}]}
    (root / "findings" / "upstream.yaml").write_text(yaml.safe_dump({"findings": [
        dict(base, id="UF-1", status="reverified"),
        dict(base, id="UF-2", status="drafted"),
        dict(base, id="UF-3", status="collected"),
    ]}))
    merges = upstream.dedupe(root)
    assert [(m.kept, m.merged) for m in merges] == [("UF-1", "UF-3")]


def test_sanitize_flags_token_after_private_key_block():
    guide = guidecfg.Guide(root=Path("."), schema=1, title="t", format="antora", personas=[], sections=[])
    text = ("-----BEGIN PRIVATE KEY-----\nMIIBVQIBADANBg\nkqhkiG9w0BAQEF\n-----END PRIVATE KEY-----\n"
            "summary line\nAuthorization: Bearer abc.def.ghi\n")
    problems = [p for p in upstream.sanitize(text, guide, private_check=lambda s: False, own_remotes=[])
                if p.kind == "secret"]
    assert any("Bearer" in p.match or "Authorization" in p.match for p in problems)
    assert not any(p.match == "summary line" for p in problems)
