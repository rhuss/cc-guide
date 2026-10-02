import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import playbook

TOOLKIT = Path(__file__).resolve().parents[2] / "guide" / "toolkit"

SITE = {
    "site": {"title": "T", "start_page": "g::index.adoc"},
    "content": {"sources": [{"url": ".", "branches": "HEAD", "start_path": "content"}]},
    "ui": {"bundle": {"url": "./ui/ui-bundle.zip", "snapshot": False}},
    "antora": {"extensions": ["@antora/html-single-extension", "./lib/ext.js"]},
    "output": {"dir": "./build/site"},
}
SITE_INTERNAL = {
    **SITE,
    "content": {"sources": [{"url": ".", "branches": "HEAD", "start_path": "content"},
                            {"url": ".", "branches": "HEAD", "start_path": "internal"}]},
    "output": {"dir": "./build/site-internal"},
}


def git(*args, cwd):
    subprocess.run(["git", "-C", str(cwd), "-c", "commit.gpgsign=false", *args], check=True,
                   capture_output=True)


@pytest.fixture
def repo(tmp_path):
    main = tmp_path / "guide-repo"
    main.mkdir()
    git("init", "-q", "-b", "main", cwd=main)
    (main / "site.yml").write_text(yaml.safe_dump(SITE, sort_keys=False))
    (main / "site-internal.yml").write_text(yaml.safe_dump(SITE_INTERNAL, sort_keys=False))
    (main / ".gitignore").write_text(".claude/\n")
    git("add", "-A", cwd=main)
    git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "init", cwd=main)
    return main


def test_main_checkout_uses_site_yml(repo):
    assert not playbook.is_linked_worktree(repo)
    assert playbook.path(repo, internal=False) == repo / "site.yml"
    assert playbook.path(repo, internal=True) == repo / "site-internal.yml"


def test_linked_worktree_generates_playbook(repo):
    wt = repo / ".claude" / "worktrees" / "001-feature"
    git("worktree", "add", "-q", "-b", "001-feature", str(wt), cwd=repo)
    assert playbook.is_linked_worktree(wt)

    out = playbook.path(wt, internal=False)
    assert out == wt / "build" / "playbook.yml"
    data = yaml.safe_load(out.read_text())
    (src,) = data["content"]["sources"]
    assert Path(src["url"]).resolve() == repo.resolve()
    assert src["branches"] == "001-feature"
    assert src["worktrees"] == "001-feature"
    assert src["start_path"] == "content"
    assert Path(data["output"]["dir"]).is_absolute()
    assert Path(data["output"]["dir"]) == (wt / "build" / "site").resolve()
    assert Path(data["ui"]["bundle"]["url"]) == (wt / "ui" / "ui-bundle.zip").resolve()
    assert data["antora"]["extensions"][0] == "@antora/html-single-extension"
    assert Path(data["antora"]["extensions"][1]) == (wt / "lib" / "ext.js").resolve()

    internal = yaml.safe_load(playbook.path(wt, internal=True).read_text())
    assert [s["start_path"] for s in internal["content"]["sources"]] == ["content", "internal"]
    assert all(s["worktrees"] == "001-feature" for s in internal["content"]["sources"])
    assert internal["output"]["dir"].endswith("build/site-internal")


def test_remote_ui_bundle_kept(repo):
    wt = repo / ".claude" / "worktrees" / "002-x"
    git("worktree", "add", "-q", "-b", "002-x", str(wt), cwd=repo)
    site = dict(SITE, ui={"bundle": {"url": "https://example.com/ui.zip"}})
    (wt / "site.yml").write_text(yaml.safe_dump(site))
    data = yaml.safe_load(playbook.path(wt, internal=False).read_text())
    assert data["ui"]["bundle"]["url"] == "https://example.com/ui.zip"


def test_cli_path(repo):
    proc = subprocess.run([sys.executable, str(TOOLKIT / "playbook.py"), "path", "--internal",
                           "--root", str(repo)], capture_output=True, text=True, check=True)
    assert proc.stdout.strip() == str(repo / "site-internal.yml")
