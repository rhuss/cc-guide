import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import guidecfg
import drift

TOOLKIT = Path(__file__).resolve().parents[2] / "guide" / "toolkit"

ADAPTER = """format: gfm
content_root: docs
internal_root: internal
page_glob: "**/*.md"
comment: html
"""

GUIDE = {
    "schema": 1, "title": "Drift fixture", "format": "gfm",
    "personas": [{"id": "admin", "title": "Admin", "start": "index"}],
}

PAGES = {
    "docs/index.md": "# Index\n\n<!-- guide: no-sources -->\n\nSee [Configuration](config.md).\n",
    "docs/config.md": "# Configuration\n\n<!-- Sources:\nmini:config/defaults.yaml:2-4\n-->\n\nThe port is 9090.\n",
    "docs/setup.md": "# Setup\n\n<!-- Sources:\nmini:docs/setup.md:1-5\nmini:Makefile:3-4\n-->\n\nRun make install.\n",
    "docs/other.md": "# Other\n\n<!-- Sources:\nmini:README.md:1-3\n-->\n\nminisvc is small.\n",
    "docs/admin/deep.md": "# Deep\n\n<!-- guide: no-sources -->\n\nFollow [Setup](../setup.md#steps).\n",
}


def git(*args):
    subprocess.run(["git", *args], check=True, capture_output=True)


def make_guide(root: Path, repo: str, commit: str, ref: str = "main",
               change_requests=None, inputs=None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    tools = root / "tools" / "guide"
    tools.mkdir(parents=True, exist_ok=True)
    (tools / "adapter.yaml").write_text(ADAPTER)
    (root / "guide.yaml").write_text(yaml.safe_dump(GUIDE, sort_keys=False))
    baseline = {"captured": "2026-01-06",
                "sources": [{"id": "mini", "repo": repo, "ref": ref, "commit": commit}]}
    if change_requests:
        baseline["change_requests"] = change_requests
    (root / "baseline.yaml").write_text(yaml.safe_dump(baseline, sort_keys=False))
    if inputs is not None:
        (root / "inputs.yaml").write_text(yaml.safe_dump({"inputs": inputs}, sort_keys=False))
    for rel, text in PAGES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return root


def run_cli(root: Path, *args) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOLKIT / "drift.py"), "--check", "--root", str(root), *args],
                          capture_output=True, text=True)


def test_changed_cited_file_marks_citing_and_linking_pages(tmp_path, fixture_repo):
    repo, first, second, _ = fixture_repo
    git("-C", str(repo), "branch", "release", second)
    root = make_guide(tmp_path / "g", repo.as_uri(), first, ref="release")
    rep = drift.report(root)
    (src,) = rep.sources
    assert src.status == "moved" and src.head == second and src.commits_since == 1
    assert [c.describe() for c in rep.changed_files] == ["modified config/defaults.yaml"]
    assert rep.changed_files[0].pages == ["docs/config.md"]
    assert rep.affected_pages == ["docs/config.md", "docs/index.md"]
    assert rep.has_drift


def test_rename_and_delete_keep_their_status(tmp_path, fixture_repo):
    repo, _, second, third = fixture_repo
    root = make_guide(tmp_path / "g", repo.as_uri(), second)
    rep = drift.report(root)
    described = sorted(c.describe() for c in rep.changed_files)
    assert described == ["deleted Makefile", "renamed docs/setup.md -> docs/install.md"]
    for change in rep.changed_files:
        assert change.pages == ["docs/setup.md"]
    assert rep.affected_pages == ["docs/admin/deep.md", "docs/setup.md"]
    assert rep.sources[0].head == third


def test_no_drift_exit_zero(tmp_path, fixture_repo):
    repo, _, _, third = fixture_repo
    root = make_guide(tmp_path / "g", repo.as_uri(), third)
    rep = drift.report(root)
    assert rep.sources[0].status == "current"
    assert rep.changed_files == [] and rep.affected_pages == []
    assert not rep.has_drift
    proc = run_cli(root)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "No drift" in proc.stdout


def test_drift_exit_ten_and_formats(tmp_path, fixture_repo):
    repo, _, second, _ = fixture_repo
    root = make_guide(tmp_path / "g", repo.as_uri(), second)
    md = run_cli(root, "--format", "markdown")
    assert md.returncode == 10, md.stdout + md.stderr
    assert "renamed docs/setup.md -> docs/install.md" in md.stdout
    assert "docs/admin/deep.md" in md.stdout
    js = run_cli(root, "--format", "json")
    assert js.returncode == 10
    data = json.loads(js.stdout)
    assert data["has_drift"] is True
    assert data["affected_pages"] == ["docs/admin/deep.md", "docs/setup.md"]
    assert {c["change"] for c in data["changed_files"]} == {"renamed", "deleted"}
    assert data["sources"][0]["id"] == "mini"


def test_cwd_unchanged(tmp_path, fixture_repo):
    repo, first, _, _ = fixture_repo
    root = make_guide(tmp_path / "g", repo.as_uri(), first)
    before = os.getcwd()
    drift.report(root)
    assert os.getcwd() == before


def test_changed_and_unreadable_inputs(tmp_path, fixture_repo):
    repo, _, _, third = fixture_repo
    transcript = tmp_path / "inputs" / "t.txt"
    transcript.parent.mkdir()
    transcript.write_text("original\n")
    sha = hashlib.sha256(b"original\n").hexdigest()
    inputs = [
        {"id": "walk", "kind": "transcript", "location": str(transcript), "sha256": sha},
        {"id": "gone", "kind": "notes", "location": str(tmp_path / "inputs" / "missing.txt"), "sha256": sha},
        {"id": "page", "kind": "link", "location": "https://example.com/x", "sha256": ""},
    ]
    root = make_guide(tmp_path / "g", repo.as_uri(), third, inputs=inputs)
    rep = drift.report(root)
    status = {i.id: i.status for i in rep.inputs}
    assert status == {"walk": "unchanged", "gone": "unreadable", "page": "skipped"}
    assert rep.has_drift  # an unreadable input needs attention
    transcript.write_text("edited\n")
    rep = drift.report(root)
    status = {i.id: i.status for i in rep.inputs}
    assert status["walk"] == "changed"
    assert rep.has_drift


def test_unreachable_source_is_unchecked(tmp_path, fixture_repo):
    _, first, _, _ = fixture_repo
    root = make_guide(tmp_path / "g", (tmp_path / "does-not-exist").as_uri(), first)
    rep = drift.report(root)
    (src,) = rep.sources
    assert src.status == "unchecked"
    assert src.message
    proc = run_cli(root)
    assert "unchecked" in proc.stdout
    assert "Traceback" not in proc.stderr
    assert proc.returncode == 10


def _rewrite_history(repo: Path) -> None:
    shutil.rmtree(repo)
    repo.mkdir()
    env = {**os.environ, "GIT_AUTHOR_NAME": "x", "GIT_AUTHOR_EMAIL": "x@example.com",
           "GIT_COMMITTER_NAME": "x", "GIT_COMMITTER_EMAIL": "x@example.com"}
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True, env=env)
    (repo / "README.md").write_text("# rewritten\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, env=env)
    subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", "commit", "-q", "-m", "rewritten"],
                   check=True, env=env)


def test_pin_missing_with_fresh_cache(tmp_path, fixture_repo):
    repo, first, _, _ = fixture_repo
    _rewrite_history(repo)
    root = make_guide(tmp_path / "g", repo.as_uri(), first)
    rep = drift.report(root)
    (src,) = rep.sources
    assert src.status == "pin-missing"
    assert "no longer exists upstream; pin a new revision" in src.message
    proc = run_cli(root)
    assert proc.returncode == 10
    assert "Traceback" not in proc.stderr
    assert "pin-missing" in proc.stdout


def test_pin_missing_with_stale_cache(tmp_path, fixture_repo):
    repo, first, _, _ = fixture_repo
    root = make_guide(tmp_path / "g", repo.as_uri(), first)
    assert drift.report(root).sources[0].status == "moved"
    _rewrite_history(repo)
    rep = drift.report(root)
    assert rep.sources[0].status == "pin-missing"


def test_change_request_transitions():
    sha = lambda c: c * 40
    baseline = guidecfg.Baseline(
        root=Path("."), captured="2026-01-06",
        sources=[guidecfg.Source(id="saw", repo="acme/saw", commit=sha("a")),
                 guidecfg.Source(id="local", repo="file:///tmp/x", commit=sha("b"))],
        change_requests=[
            guidecfg.ChangeRequest("saw", 1, sha("1"), "open", "in-review", "one"),
            guidecfg.ChangeRequest("saw", 2, sha("2"), "open", "in-review", "two"),
            guidecfg.ChangeRequest("saw", 3, sha("3"), "open", "in-review", "three"),
            guidecfg.ChangeRequest("saw", 4, sha("4"), "open", "in-review", "four"),
            guidecfg.ChangeRequest("saw", 5, sha("5"), "open", "in-review", "five"),
            guidecfg.ChangeRequest("local", 6, sha("6"), "open", "in-review", "six"),
        ],
    )
    answers = {
        1: {"state": "open", "merged": False, "head": sha("1")},
        2: {"state": "open", "merged": False, "head": sha("9")},
        3: {"state": "closed", "merged": True, "head": sha("3")},
        4: {"state": "closed", "merged": False, "head": sha("4")},
        5: None,
    }
    calls = []

    def gh(slug, number):
        calls.append((slug, number))
        return answers[number]

    result = {c.number: c for c in drift.evaluate_change_requests(baseline, gh)}
    assert result[1].transition == "unchanged"
    assert result[2].transition == "head-moved" and result[2].head == sha("9")
    assert result[3].transition == "merged" and result[3].suggested_tier == "on-main"
    assert result[4].transition == "closed"
    assert result[5].transition == "unchecked"
    assert result[6].transition == "unchecked"
    assert all(slug == "acme/saw" for slug, _ in calls)


def test_antora_xref_inbound_links(tmp_path, fixture_repo):
    repo, first, second, _ = fixture_repo
    git("-C", str(repo), "branch", "release", second)
    root = tmp_path / "a"
    tools = root / "tools" / "guide"
    tools.mkdir(parents=True)
    (tools / "adapter.yaml").write_text(
        "format: antora\ncontent_root: content\ninternal_root: internal\n"
        "page_glob: 'modules/*/pages/**/*.adoc'\ncomment: line\n")
    (root / "guide.yaml").write_text(yaml.safe_dump(dict(GUIDE, format="antora")))
    (root / "baseline.yaml").write_text(yaml.safe_dump({"captured": "2026-01-06", "sources": [
        {"id": "mini", "repo": repo.as_uri(), "ref": "release", "commit": first}]}))
    pages = root / "content/modules/ROOT/pages"
    internal = root / "internal/modules/internal/pages"
    (pages / "admin").mkdir(parents=True)
    internal.mkdir(parents=True)
    (pages / "admin/config.adoc").write_text("= Config\n\n// Sources:\n// mini:config/defaults.yaml:2-4\n\nPort.\n")
    (pages / "index.adoc").write_text("= Index\n:guide-no-sources:\n\nSee xref:admin/config.adoc[config].\n")
    (pages / "admin/sibling.adoc").write_text("= Sibling\n:guide-no-sources:\n\nSee xref:./config.adoc#port[here].\n")
    (pages / "unrelated.adoc").write_text("= Unrelated\n:guide-no-sources:\n\nSee xref:index.adoc[index].\n")
    (internal / "notes.adoc").write_text("= Notes\n:guide-no-sources:\n\nSee xref:ROOT:admin/config.adoc[c].\n")
    rep = drift.report(root)
    assert rep.affected_pages == [
        "content/modules/ROOT/pages/admin/config.adoc",
        "content/modules/ROOT/pages/admin/sibling.adoc",
        "content/modules/ROOT/pages/index.adoc",
        "internal/modules/internal/pages/notes.adoc",
    ]
