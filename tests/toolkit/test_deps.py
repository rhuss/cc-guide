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


def settings(project: Path, name: str, allow: list[str]) -> None:
    path = project / ".claude" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"permissions": {"allow": allow}}))


def deps(home: Path, project: Path | None, no_jq: bool, cwd: Path | None = None) -> dict:
    env = dict(os.environ, HOME=str(home))
    if no_jq:
        env["CC_GUIDE_NO_JQ"] = "1"
    args = ["bash", str(DEPS)] + (["--dir", str(project)] if project else [])
    proc = subprocess.run(args, capture_output=True, text=True, env=env, cwd=cwd, check=True)
    return json.loads(proc.stdout)


@pytest.mark.parametrize("no_jq", [False, True])
def test_all_present(tmp_path, no_jq):
    home, project = tmp_path / "home", tmp_path / "guide"
    registry(home, ["superpowers@claude-plugins-official", "prose@prose-plugin-development"])
    settings(project, "settings.local.json", ["Bash(make:*)", "mcp__excalidraw__export_scene"])
    assert deps(home, project, no_jq) == {"superpowers": True, "prose": True, "excalidraw_allowed": True}


@pytest.mark.parametrize("no_jq", [False, True])
def test_nothing_present(tmp_path, no_jq):
    home, project = tmp_path / "home", tmp_path / "guide"
    project.mkdir()
    assert deps(home, project, no_jq) == {"superpowers": False, "prose": False, "excalidraw_allowed": False}


@pytest.mark.parametrize("no_jq", [False, True])
def test_prose_absent_and_shared_settings(tmp_path, no_jq):
    home, project = tmp_path / "home", tmp_path / "guide"
    registry(home, ["superpowers@claude-plugins-official", "proselint@other"])
    settings(project, "settings.json", ["mcp__excalidraw"])
    settings(project, "settings.local.json", ["Bash(gh:*)"])
    assert deps(home, project, no_jq) == {"superpowers": True, "prose": False, "excalidraw_allowed": True}


def test_default_dir_is_cwd(tmp_path):
    home, project = tmp_path / "home", tmp_path / "guide"
    registry(home, [])
    settings(project, "settings.local.json", ["mcp__excalidraw__create_element"])
    assert deps(home, None, False, cwd=project)["excalidraw_allowed"] is True
