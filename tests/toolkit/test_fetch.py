import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import fetch
import guidecfg
import sources

TOOLKIT = Path(__file__).resolve().parents[2] / "guide" / "toolkit"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout.strip()


def set_repo(root: Path, repo: str) -> None:
    path = root / "baseline.yaml"
    data = yaml.safe_load(path.read_text())
    data["sources"][0]["repo"] = repo
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def test_pin_branch_writes_full_sha(tmp_guide, fixture_repo):
    repo, first, second, third = fixture_repo
    cwd = os.getcwd()
    baseline = fetch.pin(tmp_guide, [f"mini={repo.as_uri()}@main"])
    assert os.getcwd() == cwd
    (src,) = baseline.sources
    assert src.commit == third
    assert src.ref == "main"
    assert baseline.captured == dt.date.today().isoformat()
    # the written file loads with the validating loader
    assert guidecfg.load_baseline(tmp_guide).sources[0].commit == third


def test_pin_default_ref_is_head(tmp_guide, fixture_repo):
    repo, _, _, third = fixture_repo
    assert fetch.pin(tmp_guide, [f"mini={repo.as_uri()}"]).sources[0].commit == third


def test_pin_sha_ref(tmp_guide, fixture_repo):
    repo, first, _, _ = fixture_repo
    assert fetch.pin(tmp_guide, [f"mini={repo.as_uri()}@{first}"]).sources[0].commit == first


def test_pin_keeps_other_sources_and_change_requests(render_fixture_guide, fixture_repo):
    repo, first, second, _ = fixture_repo
    baseline = fetch.pin(render_fixture_guide, [f"other={repo.as_uri()}@{second}"])
    assert [s.id for s in baseline.sources] == ["mini", "other"]
    assert baseline.source("mini").commit == first
    assert baseline.source("mini").attributes == {"version": "1.2.3"}
    assert baseline.source("other").commit == second
    assert [c.number for c in baseline.change_requests] == [4, 5]


def test_pin_unknown_ref_fails(tmp_guide, fixture_repo):
    repo = fixture_repo[0]
    with pytest.raises(fetch.FetchError):
        fetch.pin(tmp_guide, [f"mini={repo.as_uri()}@no-such-branch"])


@pytest.mark.parametrize("spec, expected", [
    ("mini=owner/name", ("mini", "owner/name", None)),
    ("mini=owner/name@v1.2", ("mini", "owner/name", "v1.2")),
    ("mini=git@github.com:owner/name", ("mini", "git@github.com:owner/name", None)),
    ("mini=git@github.com:owner/name@main", ("mini", "git@github.com:owner/name", "main")),
    ("mini=https://github.com/o/n.git@release/1.0", ("mini", "https://github.com/o/n.git", "release/1.0")),
])
def test_parse_spec(spec, expected):
    assert fetch.parse_spec(spec) == expected


def test_clone_url_expands_github_shorthand(tmp_guide):
    assert fetch.clone_url("owner/name", tmp_guide) == "https://github.com/owner/name.git"
    assert fetch.clone_url("https://example.com/r.git", tmp_guide) == "https://example.com/r.git"


def test_fetch_creates_bare_clone_and_pinned_worktree(render_fixture_guide, fixture_repo):
    root = render_fixture_guide
    first = fixture_repo[1]
    cwd = os.getcwd()
    status = fetch.fetch(root)
    assert os.getcwd() == cwd
    assert status == {"mini": "verified"}
    bare = root / ".guide" / "cache" / "mini.git"
    worktree = root / ".guide" / "cache" / "mini"
    assert bare.is_dir()
    assert git("-C", str(bare), "rev-parse", "--is-bare-repository") == "true"
    assert git("-C", str(worktree), "rev-parse", "HEAD") == first
    # the pinned worktree serves source resolution
    baseline = guidecfg.load_baseline(root)
    res = sources.resolve(sources.parse_ref("mini:docs/setup.md:1-5"), baseline, root / ".guide" / "cache")
    assert res.ok, res.message
    # a second run reuses the cache
    assert fetch.fetch(root) == {"mini": "verified"}
    assert git("-C", str(worktree), "rev-parse", "HEAD") == first


def test_fetch_moves_existing_worktree_to_new_pin(render_fixture_guide, fixture_repo):
    root = render_fixture_guide
    fetch.fetch(root)
    path = root / "baseline.yaml"
    data = yaml.safe_load(path.read_text())
    data["sources"][0]["commit"] = fixture_repo[2]
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    fetch.fetch(root)
    assert git("-C", str(root / ".guide/cache/mini"), "rev-parse", "HEAD") == fixture_repo[2]


def test_fetch_unreachable_source_fails(render_fixture_guide):
    root = render_fixture_guide
    set_repo(root, "file:///nonexistent/cc-guide-fixture-repo")
    with pytest.raises(fetch.FetchError) as err:
        fetch.fetch(root)
    assert "mini" in str(err.value)
    assert guidecfg.load_baseline(root).sources[0].status == "verified"


def test_fetch_unreachable_source_allow_unverified(render_fixture_guide):
    root = render_fixture_guide
    set_repo(root, "file:///nonexistent/cc-guide-fixture-repo")
    assert fetch.fetch(root, allow_unverified=True) == {"mini": "unverified"}
    assert guidecfg.load_baseline(root).sources[0].status == "unverified"


def test_rebaseline_moves_pin(render_fixture_guide, fixture_repo):
    root = render_fixture_guide
    _, first, second, third = fixture_repo
    cwd = os.getcwd()
    baseline = fetch.rebaseline(root, ["mini=main"])
    assert os.getcwd() == cwd
    assert baseline.source("mini").commit == third
    assert baseline.captured == dt.date.today().isoformat()
    assert git("-C", str(root / ".guide/cache/mini"), "rev-parse", "HEAD") == third
    assert fetch.rebaseline(root, [f"mini={second}"]).source("mini").commit == second
    # change requests of non-GitHub sources stay as they were
    assert [c.state for c in baseline.change_requests] == ["open", "merged"]


def test_rebaseline_unknown_source_fails(render_fixture_guide):
    with pytest.raises(fetch.FetchError):
        fetch.rebaseline(render_fixture_guide, ["nope=main"])


def test_refresh_change_requests():
    data = {"change_requests": [
        {"source": "saw", "number": 52, "head": "a" * 40, "state": "open", "tier": "in-review", "anchor": "x"},
        {"source": "saw", "number": 56, "head": "b" * 40, "state": "open", "tier": "in-review", "anchor": "y"},
        {"source": "saw", "number": 33, "head": "c" * 40, "state": "open", "tier": "in-review", "anchor": "z"},
        {"source": "local", "number": 4, "head": "d" * 40, "state": "open", "tier": "in-review", "anchor": "w"},
    ]}
    answers = {
        52: {"state": "open", "merged": False, "head": "e" * 40},
        56: {"state": "closed", "merged": True, "head": "b" * 40},
        33: {"state": "closed", "merged": False, "head": "c" * 40},
    }
    calls = []

    def gh(slug, number):
        calls.append((slug, number))
        return answers[number]

    fetch.refresh_change_requests(data, {"saw": "owner/saw", "local": None}, gh)
    crs = {c["number"]: c for c in data["change_requests"]}
    assert crs[52]["head"] == "e" * 40 and crs[52]["state"] == "open"
    assert crs[56]["state"] == "merged" and crs[56]["tier"] == "on-main"
    assert crs[33]["state"] == "closed"
    assert crs[4]["state"] == "open"
    assert ("owner/saw", 4) not in calls and len(calls) == 3


def test_cli(tmp_guide, fixture_repo):
    repo = fixture_repo[0]
    run = lambda *a: subprocess.run([sys.executable, str(TOOLKIT / "fetch.py"), *a, "--root", str(tmp_guide)],
                                    capture_output=True, text=True)
    proc = run("pin", "--source", f"mini={repo.as_uri()}@main")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    proc = run("fetch")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    set_repo(tmp_guide, "file:///nonexistent/cc-guide-fixture-repo")
    proc = run("fetch")
    assert proc.returncode != 0
    assert "mini" in proc.stdout + proc.stderr
    proc = run("fetch", "--allow-unverified")
    assert proc.returncode == 0
    assert "unverified" in proc.stdout + proc.stderr


# --- the `self` source (specs/005-embedded-guide, research R4, R5) --------------------

from conftest import FRONT_PAGE, commit_all, host_git, make_embedded_guide  # noqa: E402

CITED = {"config/defaults.yaml", "src/cli.py", "pyproject.toml"}


@pytest.fixture
def xdg(tmp_path, monkeypatch):
    cache = tmp_path / "xdg-cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    return cache


@pytest.fixture
def emb(mini_host, xdg):
    host, commit = mini_host
    root = make_embedded_guide(host, commit, front_page=FRONT_PAGE)
    (root / "baseline.yaml").unlink()
    return root


def blob(host: Path, rev: str, path: str) -> str:
    return host_git(host, "rev-parse", f"{rev}:{path}")


def where(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOLKIT / "fetch.py"), "where", *args, "--root", str(root)],
                          capture_output=True, text=True, env=os.environ.copy())


def test_pin_self_writes_entry(emb):
    host = emb.parent
    head = host_git(host, "rev-parse", "HEAD")
    src = fetch.pin(emb, ["self=.."]).source("self")
    assert src.repo == ".." and src.ref == "main" and src.commit == head
    assert src.web == ""
    assert set(src.fingerprints) == CITED
    assert all(src.fingerprints[p] == blob(host, head, p) for p in CITED)
    raw = yaml.safe_load((emb / "baseline.yaml").read_text())["sources"][0]
    assert "web" not in raw


@pytest.mark.parametrize("url, web", [
    ("git@github.com:acme/mini-host.git", "https://github.com/acme/mini-host"),
    ("https://github.com/acme/mini-host.git", "https://github.com/acme/mini-host"),
    ("https://gitlab.example.com/acme/mini-host.git", ""),
])
def test_pin_self_web_from_origin(emb, url, web):
    host_git(emb.parent, "remote", "add", "origin", url)
    assert fetch.pin(emb, ["self=.."]).source("self").web == web


def test_pin_self_on_working_branch_records_default_branch(emb):
    host = emb.parent
    host_git(host, "checkout", "--quiet", "-b", "work")
    (host / "src" / "cli.py").write_text("# changed on the working branch\n")
    work = commit_all(host, "work")
    src = fetch.pin(emb, ["self=.."]).source("self")
    assert src.commit == work and src.ref == "main"
    assert src.fingerprints["src/cli.py"] == blob(host, work, "src/cli.py")
    # origin/HEAD wins over main
    host_git(host, "remote", "add", "origin", "https://github.com/acme/mini-host.git")
    host_git(host, "update-ref", "refs/remotes/origin/trunk", work)
    host_git(host, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
    assert fetch.pin(emb, ["self=.."]).source("self").ref == "trunk"


def test_pin_self_master_fallback(emb):
    host = emb.parent
    host_git(host, "branch", "-m", "main", "master")
    assert fetch.pin(emb, ["self=.."]).source("self").ref == "master"


def test_fetch_self_exports_snapshot(emb, xdg):
    host = emb.parent
    commit = fetch.pin(emb, ["self=.."]).source("self").commit
    cwd = os.getcwd()
    assert fetch.fetch(emb) == {"self": "verified"}
    assert os.getcwd() == cwd
    snaps = list((xdg / "cc-guide" / "self").glob(f"*/{commit}"))
    assert len(snaps) == 1
    snap = snaps[0]
    assert (snap / "src" / "cli.py").read_text() == (host / "src" / "cli.py").read_text()
    # the README in the working tree holds the uncommitted front page; the snapshot does not
    assert "guide: front page" in (host / "README.md").read_text()
    assert "guide: front page" not in (snap / "README.md").read_text()
    assert not (emb / ".guide" / "cache" / "self").exists()
    assert not (emb / ".guide" / "cache" / "self.git").exists()
    proc = where(emb, "self")
    assert proc.returncode == 0, proc.stderr
    assert Path(proc.stdout.strip()).resolve() == snap.resolve()


def test_where_other_source_and_unknown(emb, fixture_repo):
    repo, first, _, _ = fixture_repo
    fetch.pin(emb, ["self=..", f"mini={repo.as_uri()}@{first}"])
    proc = where(emb, "mini")
    assert proc.returncode == 0
    assert Path(proc.stdout.strip()).resolve() == (emb / ".guide" / "cache" / "mini").resolve()
    assert where(emb, "nope").returncode == 2


def test_where_self_commit_exports_that_commit(emb, xdg):
    host = emb.parent
    fetch.pin(emb, ["self=.."])
    (host / "src" / "cli.py").write_text("# next revision\n")
    nxt = commit_all(host, "next")
    proc = where(emb, "self", "--commit", nxt)
    assert proc.returncode == 0, proc.stderr
    snap = Path(proc.stdout.strip())
    assert snap.name == nxt
    assert (snap / "src" / "cli.py").read_text() == "# next revision\n"


def commit_paths(host: Path, message: str, *paths: str) -> str:
    """Commit only the named paths (the guide subdirectory stays untracked)."""
    host_git(host, "add", *paths)
    host_git(host, "commit", "--quiet", "-m", message)
    return host_git(host, "rev-parse", "HEAD")


def drop_commit(host: Path, branch: str) -> None:
    """Delete a branch and prune its commits, like a squash merge followed by branch deletion."""
    host_git(host, "checkout", "--quiet", "main")
    host_git(host, "branch", "-D", branch)
    host_git(host, "reflog", "expire", "--expire=now", "--all")
    host_git(host, "gc", "--quiet", "--prune=now")


def test_fetch_self_pin_unavailable_but_content_matches(emb, xdg):
    host = emb.parent
    host_git(host, "checkout", "--quiet", "-b", "work")
    (host / "NOTES.txt").write_text("not cited\n")
    work = commit_paths(host, "uncited change", "NOTES.txt")
    fetch.pin(emb, ["self=.."])
    drop_commit(host, "work")
    assert subprocess.run(["git", "-C", str(host), "cat-file", "-e", f"{work}^{{commit}}"]).returncode != 0
    assert fetch.fetch(emb) == {"self": "verified"}
    snap = Path(where(emb, "self").stdout.strip())
    assert (snap / "src" / "cli.py").is_file()


def test_pin_unavailable_fallback_is_keyed_by_the_head(emb, xdg, tmp_path):
    # the head export must not land in the pinned commit's directory: once the pinned
    # commit is available again, `where self` has to serve its content, not the head's
    host = emb.parent
    host_git(host, "checkout", "--quiet", "-b", "work")
    (host / "NOTES.txt").write_text("only in the pinned commit\n")
    work = commit_paths(host, "uncited change", "NOTES.txt")
    fetch.pin(emb, ["self=.."])
    bundle = tmp_path / "work.bundle"
    host_git(host, "bundle", "create", str(bundle), "work")
    drop_commit(host, "work")
    head = host_git(host, "rev-parse", "main")
    assert fetch.fetch(emb) == {"self": "verified"}
    snap = Path(where(emb, "self").stdout.strip())
    assert snap.name == head and not (snap / "NOTES.txt").exists()
    assert not fetch.self_snapshot_dir(host, work).exists()
    # the pinned commit comes back (for example, fetched from a fork)
    host_git(host, "fetch", "--quiet", str(bundle), "work:work")
    snap = Path(where(emb, "self").stdout.strip())
    assert snap.name == work
    assert (snap / "NOTES.txt").read_text() == "only in the pinned commit\n"


def test_fetch_self_pin_unavailable_and_drifted(emb, xdg, capsys):
    host = emb.parent
    host_git(host, "checkout", "--quiet", "-b", "work")
    (host / "src" / "cli.py").write_text("# changed and later dropped\n")
    commit_paths(host, "cited change", "src/cli.py")
    fetch.pin(emb, ["self=.."])
    drop_commit(host, "work")
    status = fetch.fetch(emb)
    assert status["self"] == "pin unavailable"
    assert "pin unavailable" in capsys.readouterr().err
    assert guidecfg.load_baseline(emb).source("self").status == "verified"
    proc = subprocess.run([sys.executable, str(TOOLKIT / "fetch.py"), "fetch", "--root", str(emb)],
                          capture_output=True, text=True, env=os.environ.copy())
    assert proc.returncode == 0, proc.stderr
    assert "pin unavailable, run /guide:evolve" in proc.stdout + proc.stderr


def test_rebaseline_self_recomputes_fingerprints(emb):
    host = emb.parent
    fetch.pin(emb, ["self=.."])
    (host / "src" / "cli.py").write_text("# rebaselined\n")
    nxt = commit_all(host, "next")
    cwd = os.getcwd()
    src = fetch.rebaseline(emb, ["self=HEAD"]).source("self")
    assert os.getcwd() == cwd
    assert src.commit == nxt and src.ref == "main"
    assert src.fingerprints["src/cli.py"] == blob(host, nxt, "src/cli.py")
    assert len(src.front_page_blob) == 40
    # the blob is stored in the host repository, so a later diff can show it
    stored = host_git(host, "cat-file", "-p", src.front_page_blob)
    assert "# Mini Host" in stored
    assert not (emb / ".guide" / "cache" / "self.git").exists()


def test_self_citation_resolves_from_the_host(emb):
    fetch.pin(emb, ["self=.."])
    baseline = guidecfg.load_baseline(emb)
    cache = emb / ".guide" / "cache"
    assert sources.resolve(sources.parse_ref("self:src/cli.py:1-5"), baseline, cache).ok
    res = sources.resolve(sources.parse_ref("self:src/cli.py:1-500"), baseline, cache)
    assert not res.ok and "beyond the end" in res.message
    assert not sources.resolve(sources.parse_ref("self:nope.py"), baseline, cache).ok
    assert not cache.exists()


def test_fetch_self_pin_unavailable_without_citations(emb, xdg):
    host = emb.parent
    for page in (emb / "docs").rglob("*.md"):
        page.write_text("# P\n\n<!-- guide: no-sources -->\n")
    (host / "README.md").write_text("# Mini Host\n")
    host_git(host, "checkout", "--quiet", "-b", "work")
    (host / "NOTES.txt").write_text("x\n")
    commit_paths(host, "work", "NOTES.txt")
    assert fetch.pin(emb, ["self=.."]).source("self").fingerprints == {}
    drop_commit(host, "work")
    assert fetch.fetch(emb) == {"self": "verified"}
    assert where(emb, "self").returncode == 0


def test_self_snapshot_keeps_export_ignored_files_and_outside_symlinks(emb, xdg):
    # git archive would drop export-ignore paths and the tar data filter would abort on
    # a symlink pointing outside the tree; the snapshot must hold every tracked file.
    host = emb.parent
    (host / ".gitattributes").write_text("/config export-ignore\n")
    os.symlink("/etc/hosts", host / "hosts-link")
    head = commit_all(host, "attributes and an absolute symlink")
    dest = fetch.export_snapshot(host, head, fetch.self_snapshot_dir(host, head))
    assert (dest / "config" / "defaults.yaml").read_text() == (host / "config" / "defaults.yaml").read_text()
    assert (dest / "hosts-link").is_symlink() and os.readlink(dest / "hosts-link") == "/etc/hosts"
    assert [p.name for p in dest.parent.iterdir() if p.name.startswith(".")] == []
    # a second call reuses the export
    assert fetch.export_snapshot(host, head, fetch.self_snapshot_dir(host, head)) == dest


def test_self_snapshot_failure_leaves_nothing_behind(emb, xdg):
    host = emb.parent
    dest = fetch.self_snapshot_dir(host, "f" * 40)
    with pytest.raises(fetch.FetchError):
        fetch.export_snapshot(host, "f" * 40, dest)
    assert not dest.exists()
    assert list(dest.parent.iterdir()) == []
