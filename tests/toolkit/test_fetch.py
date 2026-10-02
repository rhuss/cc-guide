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
