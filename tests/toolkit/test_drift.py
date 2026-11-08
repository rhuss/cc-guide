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


# --- embedded mode (specs/005-embedded-guide) ----------------------------------

from conftest import FRONT_PAGE, OWNERSHIP, commit_all, host_git, make_embedded_guide  # noqa: E402


def test_report_lists_front_page_relative_to_root(tmp_path, fixture_repo, mini_host):
    """drift._rel used to raise for a page outside the guide root."""
    repo, first, second, _ = fixture_repo
    git("-C", str(repo), "branch", "release", second)
    host, commit = mini_host
    front = OWNERSHIP + "\n# Mini Host\n\n<!-- Sources:\nmini:config/defaults.yaml:2-4\n-->\n\nBody.\n"
    root = make_embedded_guide(host, commit, front_page=front)
    (root / "baseline.yaml").write_text(yaml.safe_dump({"captured": "2026-01-06", "sources": [
        {"id": "mini", "repo": repo.as_uri(), "ref": "release", "commit": first}]}))
    rep = drift.report(root)
    assert "../README.md" in rep.affected_pages
    assert rep.changed_files[0].pages == ["../README.md"]


# --- fingerprint mode for `self` (T033) ------------------------------------------------

import fetch  # noqa: E402


@pytest.fixture
def emb(mini_host, tmp_path, monkeypatch):
    """An embedded guide pinned to the host with fingerprints, committed together with the host."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    host, commit = mini_host
    root = make_embedded_guide(host, commit, front_page=FRONT_PAGE)
    fetch.pin(root, ["self=.."])
    commit_all(host, "Add the embedded guide")
    return root


def edrift(root: Path) -> drift.DriftReport:
    return drift.report(root)


def test_guide_only_commit_is_no_drift(emb):
    host = emb.parent
    (emb / "docs" / "admin" / "install.md").write_text(
        (emb / "docs" / "admin" / "install.md").read_text() + "\nMore words.\n")
    (host / "README.md").write_text((host / "README.md").read_text() + "\nA new paragraph.\n")
    commit_all(host, "guide only")
    rep = edrift(emb)
    (src,) = rep.sources
    assert src.mode == "fingerprint" and src.status in ("current", "moved")
    assert rep.changed_files == [] and not rep.has_drift
    proc = run_cli(emb)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not (emb / ".guide" / "cache" / "self.git").exists()


def test_cited_change_reports_the_front_page(emb):
    host = emb.parent
    (host / "src" / "cli.py").write_text((host / "src" / "cli.py").read_text().replace("hello", "hi"))
    commit_all(host, "change a cited file")
    rep = edrift(emb)
    assert [c.describe() for c in rep.changed_files] == ["modified src/cli.py"]
    assert rep.changed_files[0].pages == ["../README.md"]
    assert "../README.md" in rep.affected_pages
    proc = run_cli(emb, "--format", "json")
    assert proc.returncode == 10
    data = json.loads(proc.stdout)
    assert data["sources"][0]["mode"] == "fingerprint"
    assert "../README.md" in data["affected_pages"]


def test_rebaselined_working_branch_is_no_drift(emb):
    """FR-014: `self` is compared with the checked-out head, not the default branch."""
    host = emb.parent
    host_git(host, "checkout", "--quiet", "-b", "work")
    (host / "src" / "cli.py").write_text((host / "src" / "cli.py").read_text().replace("hello", "hi"))
    commit_all(host, "cited change on a working branch")
    fetch.rebaseline(emb, ["self=HEAD"])
    commit_all(host, "rebaseline on the working branch")
    rep = edrift(emb)
    assert rep.changed_files == [] and not rep.has_drift
    assert rep.sources[0].branch == "work"


def test_deleted_cited_file(emb):
    host = emb.parent
    host_git(host, "rm", "--quiet", "pyproject.toml")
    commit_all(host, "drop pyproject")
    rep = edrift(emb)
    assert [c.describe() for c in rep.changed_files] == ["deleted pyproject.toml"]


def drop_branch(host: Path, branch: str) -> None:
    host_git(host, "checkout", "--quiet", "main")
    host_git(host, "branch", "-D", branch)
    host_git(host, "reflog", "expire", "--expire=now", "--all")
    host_git(host, "gc", "--quiet", "--prune=now")


def squash(host: Path, emb: Path, change) -> None:
    """Pin on a working branch, squash-merge its content into main, delete the branch."""
    host_git(host, "checkout", "--quiet", "-b", "work")
    change()
    commit_all(host, "work")
    fetch.rebaseline(emb, ["self=HEAD"])
    commit_all(host, "rebaseline")
    tree = host_git(host, "rev-parse", "HEAD^{tree}")
    main = host_git(host, "rev-parse", "main")
    squashed = host_git(host, "commit-tree", tree, "-p", main, "-m", "squash")
    host_git(host, "update-ref", "refs/heads/main", squashed)
    drop_branch(host, "work")


def test_squash_merge_without_change_is_no_drift(emb):
    host = emb.parent
    pinned = guidecfg.load_baseline(emb).source("self").commit
    squash(host, emb, lambda: (host / "NOTES.txt").write_text("uncited\n"))
    src = guidecfg.load_baseline(emb).source("self")
    assert src.commit != pinned
    assert subprocess.run(["git", "-C", str(host), "cat-file", "-e", f"{src.commit}^{{commit}}"]).returncode != 0
    rep = edrift(emb)
    assert rep.sources[0].mode == "fingerprint" and rep.sources[0].status != "pin-missing"
    assert not rep.has_drift, drift.to_markdown(rep)
    assert run_cli(emb).returncode == 0


def test_squash_merge_then_cited_change_is_drift(emb):
    host = emb.parent
    squash(host, emb, lambda: (host / "NOTES.txt").write_text("uncited\n"))
    (host / "config" / "defaults.yaml").write_text("greeting: hi\n")
    commit_all(host, "cited change after the squash")
    rep = edrift(emb)
    assert [c.describe() for c in rep.changed_files] == ["modified config/defaults.yaml"]
    assert rep.changed_files[0].pages == ["docs/admin/install.md"]
    assert run_cli(emb).returncode == 10


def test_self_and_local_inputs(emb, tmp_path):
    secret = tmp_path / "secret-call.txt"
    secret.write_text("notes\n")
    (emb / "confidential.local.yaml").write_text(yaml.safe_dump({"inputs": {"call-1": str(secret)}}))
    head = host_git(emb.parent, "rev-parse", "HEAD")
    blob = host_git(emb.parent, "rev-parse", "HEAD:README.md")
    (emb / "inputs.yaml").write_text(yaml.safe_dump({"inputs": [
        {"id": "host-readme", "kind": "document", "location": "self:README.md", "revision": head, "blob": blob},
        {"id": "call-1", "kind": "transcript", "location": "local:call-1", "confidential": True,
         "sha256": hashlib.sha256(b"notes\n").hexdigest()},
    ]}))
    rep = edrift(emb)
    status = {i.id: i.status for i in rep.inputs}
    assert status == {"host-readme": "recorded", "call-1": "unchanged"}
    assert not rep.has_drift
    md = run_cli(emb).stdout
    js = run_cli(emb, "--format", "json").stdout
    for out in (md, js):
        assert str(secret) not in out and "secret-call" not in out
    assert "`call-1`" in md
    secret.write_text("changed\n")
    rep = edrift(emb)
    assert {i.id: i.status for i in rep.inputs}["call-1"] == "changed"
    assert str(secret) not in drift.to_markdown(rep)


def test_external_source_keeps_commit_mode(emb, fixture_repo):
    repo, first, second, _ = fixture_repo
    git("-C", str(repo), "branch", "release", second)
    data = yaml.safe_load((emb / "baseline.yaml").read_text())
    data["sources"].append({"id": "mini", "repo": repo.as_uri(), "ref": "release", "commit": first})
    (emb / "baseline.yaml").write_text(yaml.safe_dump(data, sort_keys=False))
    (emb / "docs" / "admin" / "cfg.md").write_text("# Cfg\n\n<!-- Sources:\nmini:config/defaults.yaml:2-4\n-->\n\nPort.\n")
    rep = edrift(emb)
    modes = {s.id: s.mode for s in rep.sources}
    assert modes == {"self": "fingerprint", "mini": "commit"}
    assert [(c.source, c.describe()) for c in rep.changed_files] == [("mini", "modified config/defaults.yaml")]


# --- pull request mode (T043) -----------------------------------------------------------


def pr_cli(root: Path, *args, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOLKIT / "drift.py"), "--root", str(root), *args],
                          capture_output=True, text=True, env={**os.environ, **(env or {})})


@pytest.fixture
def pr(emb):
    """A pull request branch `pr` off main; returns (guide root, base sha)."""
    host = emb.parent
    base = host_git(host, "rev-parse", "HEAD")
    host_git(host, "checkout", "--quiet", "-b", "pr")
    return emb, base


def pr_json(root: Path, base: str, env: dict | None = None, *extra) -> tuple[int, dict]:
    proc = pr_cli(root, "--pr", "--base", base, "--format", "json", *extra, env=env)
    assert proc.returncode in (0, 10), proc.stdout + proc.stderr
    return proc.returncode, json.loads(proc.stdout)


def test_pr_without_cited_change_passes(pr):
    root, base = pr
    (root.parent / "NOTES.txt").write_text("uncited\n")
    commit_all(root.parent, "uncited")
    code, data = pr_json(root, base)
    assert code == 0 and data["result"] == "pass" and data["cited_changed"] == []


def test_pr_cited_change_without_rebaseline_fails(pr):
    root, base = pr
    host = root.parent
    (host / "src" / "cli.py").write_text((host / "src" / "cli.py").read_text().replace("hello", "hi"))
    commit_all(host, "cited")
    code, data = pr_json(root, base)
    assert code == 10 and data["result"] == "fail"
    assert data["cited_changed"] == ["src/cli.py"]
    assert "../README.md" in data["affected_pages"]
    assert data["baseline_updated"] is False
    assert set(data) == {"base", "head", "cited_changed", "affected_pages", "baseline_updated",
                         "fingerprints_match", "skipped", "result"}
    md = pr_cli(root, "--pr", "--base", base)
    assert md.returncode == 10 and "src/cli.py" in md.stdout and "../README.md" in md.stdout


def test_pr_rebaselined_passes_until_a_further_push(pr):
    root, base = pr
    host = root.parent
    (host / "src" / "cli.py").write_text((host / "src" / "cli.py").read_text().replace("hello", "hi"))
    commit_all(host, "cited")
    fetch.rebaseline(root, ["self=HEAD"])
    commit_all(host, "rebaseline")
    code, data = pr_json(root, base)
    assert code == 0 and data["baseline_updated"] and data["fingerprints_match"], data
    (host / "src" / "cli.py").write_text((host / "src" / "cli.py").read_text().replace("hi", "hey"))
    commit_all(host, "further push")
    code, data = pr_json(root, base)
    assert code == 10 and data["baseline_updated"] and not data["fingerprints_match"]


def test_pr_skip_label(pr):
    root, base = pr
    host = root.parent
    (host / "src" / "cli.py").write_text("# rewritten\n")
    commit_all(host, "cited")
    code, data = pr_json(root, base, {"GUIDE_SKIP": "1"})
    assert code == 0 and data["skipped"] and data["result"] == "pass"
    md = pr_cli(root, "--pr", "--base", base, env={"GUIDE_SKIP": "1"})
    assert md.returncode == 0 and "skipped by request" in md.stdout


def test_pr_ignores_external_sources(pr, fixture_repo):
    root, base = pr
    repo, first, second, _ = fixture_repo
    git("-C", str(repo), "branch", "release", second)
    data = yaml.safe_load((root / "baseline.yaml").read_text())
    data["sources"].append({"id": "mini", "repo": repo.as_uri(), "ref": "release", "commit": first})
    (root / "baseline.yaml").write_text(yaml.safe_dump(data, sort_keys=False))
    (root / "docs" / "admin" / "cfg.md").write_text("# Cfg\n\n<!-- Sources:\nmini:config/defaults.yaml:2-4\n-->\n\nX.\n")
    commit_all(root.parent, "external source")
    code, out = pr_json(root, base)
    assert code == 0 and out["cited_changed"] == []
    assert not (root / ".guide" / "cache" / "mini.git").exists()


def test_check_source_self_limits_the_report(emb, fixture_repo):
    repo, first, second, _ = fixture_repo
    git("-C", str(repo), "branch", "release", second)
    data = yaml.safe_load((emb / "baseline.yaml").read_text())
    data["sources"].append({"id": "mini", "repo": repo.as_uri(), "ref": "release", "commit": first})
    (emb / "baseline.yaml").write_text(yaml.safe_dump(data, sort_keys=False))
    (emb / "docs" / "admin" / "cfg.md").write_text("# Cfg\n\n<!-- Sources:\nmini:config/defaults.yaml:2-4\n-->\n\nX.\n")
    assert run_cli(emb).returncode == 10
    proc = run_cli(emb, "--source", "self", "--format", "json")
    assert proc.returncode == 0, proc.stdout
    assert [s["id"] for s in json.loads(proc.stdout)["sources"]] == ["self"]


def test_pr_introducing_the_guide_counts_as_rebaselined(mini_host, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    host, base = mini_host
    host_git(host, "checkout", "--quiet", "-b", "pr")
    (host / "src" / "cli.py").write_text((host / "src" / "cli.py").read_text().replace("hello", "hi"))
    commit_all(host, "cited change")
    root = make_embedded_guide(host, base, front_page=FRONT_PAGE)
    fetch.pin(root, ["self=.."])
    commit_all(host, "add the guide")
    code, data = pr_json(root, base)
    assert code == 0 and data["baseline_updated"] and data["fingerprints_match"], data


def test_pr_cited_file_without_fingerprint_fails(pr):
    root, base = pr
    host = root.parent
    (root / "docs" / "admin" / "usage.md").write_text("# Usage\n\n<!-- Sources:\nself:USAGE.md\n-->\n\nGreet.\n")
    (host / "USAGE.md").write_text("# Usage\n\nChanged.\n")
    data = yaml.safe_load((root / "baseline.yaml").read_text())
    data["sources"][0]["front_page_blob"] = "f" * 40      # the self entry changed
    (root / "baseline.yaml").write_text(yaml.safe_dump(data, sort_keys=False))
    commit_all(host, "usage page without fingerprint")
    code, out = pr_json(root, base)
    assert code == 10 and out["baseline_updated"] and not out["fingerprints_match"]


def test_pr_deleted_cited_file(pr):
    root, base = pr
    host_git(root.parent, "rm", "--quiet", "pyproject.toml")
    commit_all(root.parent, "delete")
    code, data = pr_json(root, base)
    assert code == 10 and data["cited_changed"] == ["pyproject.toml"]


def test_pr_missing_base_exits_2(pr):
    root, _ = pr
    assert pr_cli(root, "--pr", "--base", "f" * 40).returncode == 2


def test_pr_ignores_cited_changes_that_reached_the_base_later(pr):
    # The base branch changes a cited file after the pull request branched off; the
    # pull request itself touches only an uncited file. Only the pull request's own
    # changes (from the merge base) count.
    root, _ = pr
    host = root.parent
    host_git(host, "checkout", "--quiet", "-")
    (host / "src" / "cli.py").write_text((host / "src" / "cli.py").read_text().replace("hello", "hi"))
    moved_base = commit_all(host, "cited change on the base branch")
    host_git(host, "checkout", "--quiet", "pr")
    (host / "NOTES.txt").write_text("uncited\n")
    commit_all(host, "uncited")
    code, data = pr_json(root, moved_base)
    assert code == 0 and data["result"] == "pass" and data["cited_changed"] == [], data
    assert data["base"] != moved_base


def test_local_input_without_local_file_is_skipped(emb):
    # A fresh clone or the scheduled workflow has no confidential.local.yaml.
    (emb / "inputs.yaml").write_text(yaml.safe_dump({"inputs": [
        {"id": "call-1", "kind": "transcript", "location": "local:call-1", "confidential": True,
         "sha256": hashlib.sha256(b"notes\n").hexdigest()},
    ]}))
    assert not (emb / "confidential.local.yaml").exists()
    rep = edrift(emb)
    assert {i.id: i.status for i in rep.inputs} == {"call-1": "skipped"}
    assert not rep.has_drift
    assert run_cli(emb).returncode == 0
