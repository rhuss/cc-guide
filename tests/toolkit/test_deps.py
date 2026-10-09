import json
import os
import subprocess
from pathlib import Path

import pytest

DEPS = Path(__file__).resolve().parents[2] / "guide" / "scripts" / "deps.sh"


def registry(home: Path, keys: list[str]) -> None:
    reg = home / ".claude/plugins/installed_plugins.json"
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(json.dumps({"version": 2, "plugins": {k: [{"scope": "user", "installPath": "/x"}] for k in keys}}))


def settings(project: Path, name: str, allow: list[str]) -> Path:
    path = project / ".claude" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"permissions": {"allow": allow}}))
    return path


def deps(
    home: Path,
    project: Path | None,
    no_jq: bool,
    cwd: Path | None = None,
    session: Path | None = None,
) -> dict:
    env = dict(os.environ, HOME=str(home))
    if no_jq:
        env["CC_GUIDE_NO_JQ"] = "1"
    if cwd is None:
        # Never let the default session directory fall back to the test runner's
        # working directory (the cc-guide checkout has its own .claude settings).
        cwd = home.parent / "session-default"
    cwd.mkdir(parents=True, exist_ok=True)
    args = ["bash", str(DEPS)] + (["--dir", str(project)] if project else [])
    args += ["--session-dir", str(session)] if session else []
    proc = subprocess.run(args, capture_output=True, text=True, env=env, cwd=cwd, check=True)
    return json.loads(proc.stdout)


def real(path: Path) -> str:
    return str(path.resolve())


@pytest.mark.parametrize("no_jq", [False, True])
def test_all_present(tmp_path, no_jq):
    home, project = tmp_path / "home", tmp_path / "guide"
    registry(home, ["superpowers@claude-plugins-official", "prose@prose-plugin-development"])
    local = settings(project, "settings.local.json", ["Bash(make:*)", "mcp__excalidraw__export_scene"])
    assert deps(home, project, no_jq) == {
        "superpowers": True,
        "prose": True,
        "excalidraw_allowed": True,
        "excalidraw_allowed_in": [real(local)],
    }


@pytest.mark.parametrize("no_jq", [False, True])
def test_nothing_present(tmp_path, no_jq):
    home, project = tmp_path / "home", tmp_path / "guide"
    project.mkdir()
    assert deps(home, project, no_jq) == {
        "superpowers": False,
        "prose": False,
        "excalidraw_allowed": False,
        "excalidraw_allowed_in": [],
    }


@pytest.mark.parametrize("no_jq", [False, True])
def test_prose_absent_and_shared_settings(tmp_path, no_jq):
    home, project = tmp_path / "home", tmp_path / "guide"
    registry(home, ["superpowers@claude-plugins-official", "proselint@other"])
    shared = settings(project, "settings.json", ["mcp__excalidraw"])
    settings(project, "settings.local.json", ["Bash(gh:*)"])
    assert deps(home, project, no_jq) == {
        "superpowers": True,
        "prose": False,
        "excalidraw_allowed": True,
        "excalidraw_allowed_in": [real(shared)],
    }


def test_default_dir_is_cwd(tmp_path):
    home, project = tmp_path / "home", tmp_path / "guide"
    registry(home, [])
    local = settings(project, "settings.local.json", ["mcp__excalidraw__create_element"])
    result = deps(home, None, False, cwd=project)
    assert result["excalidraw_allowed"] is True
    # The guide project and the default session directory are the same; listed once.
    assert result["excalidraw_allowed_in"] == [real(local)]


@pytest.mark.parametrize("no_jq", [False, True])
def test_session_dir_settings(tmp_path, no_jq):
    home, project, session = tmp_path / "home", tmp_path / "guide", tmp_path / "checkout"
    project.mkdir()
    local = settings(session, "settings.local.json", ["mcp__excalidraw"])
    result = deps(home, project, no_jq, session=session)
    assert result["excalidraw_allowed"] is True
    assert result["excalidraw_allowed_in"] == [real(local)]


@pytest.mark.parametrize("no_jq", [False, True])
def test_session_dir_defaults_to_cwd(tmp_path, no_jq):
    home, project, session = tmp_path / "home", tmp_path / "guide", tmp_path / "checkout"
    project.mkdir()
    shared = settings(session, "settings.json", ["mcp__excalidraw__*"])
    result = deps(home, project, no_jq, cwd=session)
    assert result["excalidraw_allowed_in"] == [real(shared)]
    # Started anywhere else, the same settings are not the session's settings.
    assert deps(home, project, no_jq)["excalidraw_allowed"] is False


@pytest.mark.parametrize("no_jq", [False, True])
def test_session_dir_uses_git_toplevel(tmp_path, no_jq):
    home, project, repo = tmp_path / "home", tmp_path / "guide", tmp_path / "repo"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    sub = repo / "docs" / "notes"
    sub.mkdir(parents=True)
    local = settings(repo, "settings.local.json", ["mcp__excalidraw"])
    settings(sub, "settings.local.json", ["mcp__excalidraw"])  # not read by Claude Code
    result = deps(home, project, no_jq, session=sub)
    assert result["excalidraw_allowed_in"] == [real(local)]
    assert deps(home, project, no_jq, cwd=sub)["excalidraw_allowed_in"] == [real(local)]


@pytest.mark.parametrize("no_jq", [False, True])
def test_user_settings(tmp_path, no_jq):
    home, project = tmp_path / "home", tmp_path / "guide"
    project.mkdir()
    user = settings(home, "settings.json", ["Read", "mcp__excalidraw"])
    settings(home, "settings.local.json", ["mcp__excalidraw"])  # not a user settings file
    result = deps(home, project, no_jq)
    assert result["excalidraw_allowed"] is True
    assert result["excalidraw_allowed_in"] == [real(user)]


@pytest.mark.parametrize("no_jq", [False, True])
def test_user_settings_follow_home(tmp_path, no_jq):
    home, other, project = tmp_path / "home", tmp_path / "other-home", tmp_path / "guide"
    project.mkdir()
    other.mkdir()
    settings(home, "settings.json", ["mcp__excalidraw"])
    assert deps(other, project, no_jq)["excalidraw_allowed"] is False


@pytest.mark.parametrize("no_jq", [False, True])
def test_all_locations_in_order(tmp_path, no_jq):
    home, project, session = tmp_path / "home", tmp_path / "guide", tmp_path / "checkout"
    guide_shared = settings(project, "settings.json", ["mcp__excalidraw"])
    session_local = settings(session, "settings.local.json", ["mcp__excalidraw__import_scene"])
    settings(session, "settings.json", ["Bash(make:*)"])
    user = settings(home, "settings.json", ["mcp__excalidraw"])
    result = deps(home, project, no_jq, session=session)
    assert result["excalidraw_allowed"] is True
    assert result["excalidraw_allowed_in"] == [real(guide_shared), real(session_local), real(user)]


@pytest.mark.parametrize("no_jq", [False, True])
def test_session_dir_without_entry(tmp_path, no_jq):
    home, project, session = tmp_path / "home", tmp_path / "guide", tmp_path / "checkout"
    project.mkdir()
    settings(session, "settings.local.json", ["Bash(make:*)", "mcp__other__tool"])
    settings(home, "settings.json", ["Read"])
    assert deps(home, project, no_jq, session=session) == {
        "superpowers": False,
        "prose": False,
        "excalidraw_allowed": False,
        "excalidraw_allowed_in": [],
    }
