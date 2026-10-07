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
    assert "clean" not in data["output"]           # unbranded: Antora's default as before


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


# --- branding (specs/002-antora-branding) ------------------------------------

GUIDE = {"schema": 1, "title": "T", "format": "antora", "personas": [{"id": "a", "title": "A", "start": "a"}]}


def write_guide(root: Path, block=None) -> None:
    data = dict(GUIDE, branding=block) if block is not None else dict(GUIDE)
    (root / "guide.yaml").write_text(yaml.safe_dump(data, sort_keys=False))


def commit_all(root: Path) -> None:
    git("add", "-A", cwd=root)
    git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "change", cwd=root)


def test_branded_main_checkout_generates_playbook(repo):
    site = dict(SITE, site={"title": "T", "start_page": "g::index.adoc", "keys": {"other": "kept"}})
    (repo / "site.yml").write_text(yaml.safe_dump(site, sort_keys=False))
    write_guide(repo, {"logo_text": "Agent Starter Kits"})
    out = playbook.path(repo, internal=False)
    assert out == repo.resolve() / "build" / "playbook.yml"
    data = yaml.safe_load(out.read_text())
    ui = (repo / "build" / "branding" / "shareable" / "ui").resolve()
    assert data["ui"]["supplemental_files"] == str(ui)
    assert (ui / "img" / "logo-guide.svg").is_file()
    # Antora lowercases playbook keys and camelCases them on _ and -, so the UI model
    # sees navbar_logo as site.keys.navbarLogo (a literal navbarLogo key would become navbarlogo).
    assert data["site"]["keys"] == {"other": "kept", "navbar_logo": "guide"}
    (src,) = data["content"]["sources"]
    assert src["url"] == str(repo.resolve())
    assert src["branches"] == "HEAD" and src["start_path"] == "content" and "worktrees" not in src
    assert data["output"]["dir"] == str((repo / "build" / "site").resolve())
    # No page of an earlier (unbranded) build survives to fail the branded-site check.
    assert data["output"]["clean"] is True
    assert data["ui"]["bundle"]["url"] == str((repo / "ui" / "ui-bundle.zip").resolve())
    assert data["antora"]["extensions"][0] == "@antora/html-single-extension"
    assert data["antora"]["extensions"][1] == str((repo / "lib" / "ext.js").resolve())


def test_branded_playbook_makes_dot_relative_paths_absolute(repo):
    # Antora resolves ./ and ../ paths against the playbook's directory, now build/.
    site = dict(SITE,
                content={"sources": [{"url": ".", "branches": "HEAD", "start_path": "content"},
                                     {"url": "../other-docs", "branches": "main"},
                                     {"url": "https://example.com/docs.git", "branches": "main"}]},
                asciidoc={"extensions": ["./lib/asciidoc-ext.js", "asciidoctor-kroki"]},
                runtime={"cache_dir": "./.cache/antora"},
                output={"dir": "./build/site", "destinations": [{"provider": "fs", "path": "./build/extra"}]})
    (repo / "site.yml").write_text(yaml.safe_dump(site, sort_keys=False))
    write_guide(repo, {"logo_text": "Kits"})
    data = yaml.safe_load(playbook.path(repo, internal=False).read_text())
    urls = [s["url"] for s in data["content"]["sources"]]
    assert urls == [str(repo.resolve()), str((repo / ".." / "other-docs").resolve()), "https://example.com/docs.git"]
    assert data["asciidoc"]["extensions"] == [str((repo / "lib" / "asciidoc-ext.js").resolve()), "asciidoctor-kroki"]
    assert data["runtime"]["cache_dir"] == str((repo / ".cache" / "antora").resolve())
    assert data["output"]["destinations"][0]["path"] == str((repo / "build" / "extra").resolve())


def test_branded_internal_view(repo):
    write_guide(repo, {"logo_text": "Kits"})
    out = playbook.path(repo, internal=True)
    assert out == repo.resolve() / "build" / "playbook-internal.yml"
    data = yaml.safe_load(out.read_text())
    assert data["ui"]["supplemental_files"] == str((repo / "build" / "branding" / "internal" / "ui").resolve())
    assert [s["url"] for s in data["content"]["sources"]] == [str(repo.resolve())] * 2
    assert data["output"]["dir"] == str((repo / "build" / "site-internal").resolve())
    assert data["site"]["keys"]["navbar_logo"] == "guide"


def test_overlay_only_guide(repo):
    write_guide(repo)
    css = repo / "ui" / "supplemental" / "css"
    css.mkdir(parents=True)
    (css / "extra.css").write_text("a{}\n")
    data = yaml.safe_load(playbook.path(repo, internal=False).read_text())
    assert data["ui"]["supplemental_files"] == str((repo / "build" / "branding" / "shareable" / "ui").resolve())
    assert "navbar_logo" not in (data["site"].get("keys") or {})
    assert data["output"]["clean"] is True
    assert not (repo / "build" / "branding" / "shareable" / "branding.json").exists()


def test_branded_linked_worktree(repo):
    write_guide(repo, {"logo_text": "Kits"})
    commit_all(repo)
    wt = repo / ".claude" / "worktrees" / "003-brand"
    git("worktree", "add", "-q", "-b", "003-brand", str(wt), cwd=repo)
    data = yaml.safe_load(playbook.path(wt, internal=False).read_text())
    (src,) = data["content"]["sources"]
    assert Path(src["url"]).resolve() == repo.resolve()
    assert src["branches"] == "003-brand" and src["worktrees"] == "003-brand"
    assert data["ui"]["supplemental_files"] == str((wt / "build" / "branding" / "shareable" / "ui").resolve())
    assert data["site"]["keys"]["navbar_logo"] == "guide"
    assert Path(data["output"]["dir"]) == (wt / "build" / "site").resolve()


def test_invalid_branding_stops_before_antora(repo):
    write_guide(repo, {"logo_text": "Kits", "logo": "branding/logo.svg", "logo_alt": "X"})
    proc = subprocess.run([sys.executable, str(TOOLKIT / "playbook.py"), "path", "--root", str(repo)],
                          capture_output=True, text=True)
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert "guide.yaml:branding: set exactly one of logo_text or logo" in proc.stderr
    assert "guide.yaml:branding.logo: file not found: branding/logo.svg" in proc.stderr
    assert not (repo / "build").exists()


def test_branding_warnings_go_to_stderr(repo):
    write_guide(repo, {"logo_text": "Kits"})
    partials = repo / "ui" / "supplemental" / "partials"
    partials.mkdir(parents=True)
    (partials / "footer-content.hbs").write_text('<footer class="footer">mine</footer>\n')
    proc = subprocess.run([sys.executable, str(TOOLKIT / "playbook.py"), "path", "--root", str(repo)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == str(repo.resolve() / "build" / "playbook.yml")
    assert "ui/supplemental/partials/footer-content.hbs: warning: shadows" in proc.stderr


def test_unbranded_guide_uses_committed_playbook_and_writes_nothing(repo):
    # SC-002: without a branding block and without ui/supplemental/, nothing changes.
    write_guide(repo)
    assert playbook.path(repo, internal=False) == repo.resolve() / "site.yml"
    assert playbook.path(repo, internal=True) == repo.resolve() / "site-internal.yml"
    assert not (repo / "build").exists()
    proc = subprocess.run([sys.executable, str(TOOLKIT / "playbook.py"), "path", "--root", str(repo)],
                          capture_output=True, text=True, check=True)
    assert proc.stdout.strip() == str(repo.resolve() / "site.yml") and proc.stderr == ""
    assert not (repo / "build").exists()


def test_branded_linked_worktree_renders_the_worktree_files(repo):
    # FR-022: the worktree's own guide.yaml and ui/supplemental/ apply, not the main checkout's.
    write_guide(repo, {"logo_text": "Main Brand"})
    commit_all(repo)
    wt = repo / ".claude" / "worktrees" / "004-brand"
    git("worktree", "add", "-q", "-b", "004-brand", str(wt), cwd=repo)
    write_guide(wt, {"logo_text": "Worktree Brand"})
    css = wt / "ui" / "supplemental" / "css"
    css.mkdir(parents=True)
    (css / "extra.css").write_text("/* WorktreeMarker */\n")
    data = yaml.safe_load(playbook.path(wt, internal=False).read_text())
    ui = Path(data["ui"]["supplemental_files"])
    assert ui == (wt / "build" / "branding" / "shareable" / "ui").resolve()
    logo = (ui / "img" / "logo-guide.svg").read_text()
    assert "Worktree Brand" in logo and "Main Brand" not in logo
    assert "WorktreeMarker" in (ui / "css" / "extra.css").read_text()
    assert not (repo / "build" / "branding").exists()
