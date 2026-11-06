"""guide/scripts/deps.sh: the capability-detection record (FR-007, FR-010, FR-012).

deps.sh no longer reads a plugin registry. The capability booleans are decided by
in-session capability exposure and passed in by the controller; deps.sh only
assembles the JSON record and computes the Claude-only excalidraw_allowed settings
wiring (and only when harness == claude).
"""
import json
import os
import subprocess
from pathlib import Path

import pytest

DEPS = Path(__file__).resolve().parents[2] / "guide" / "scripts" / "deps.sh"

# The fields the pre-feature deps.sh emitted; their Claude values must be unchanged
# (FR-012). harness, superpowers_version, and multi_agent are additive.
LEGACY_FIELDS = {"superpowers", "prose", "excalidraw_allowed", "excalidraw_allowed_in"}


def settings(project: Path, name: str, allow: list[str]) -> Path:
    path = project / ".claude" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"permissions": {"allow": allow}}))
    return path


def deps(
    *,
    home: Path | None = None,
    harness: str = "claude",
    superpowers: bool = False,
    prose: bool = False,
    excalidraw: bool = False,
    multi_agent: bool = False,
    version: str | None = None,
    project: Path | None = None,
    session: Path | None = None,
    cwd: Path | None = None,
    no_jq: bool = False,
) -> dict:
    env = dict(os.environ)
    if home is not None:
        env["HOME"] = str(home)
    if no_jq:
        env["CC_GUIDE_NO_JQ"] = "1"
    if cwd is None:
        # Never let the default session directory fall back to the test runner's
        # working directory (the cc-guide checkout has its own .claude settings).
        base = home.parent if home is not None else (project.parent if project else Path("/tmp"))
        cwd = base / "session-default"
    cwd.mkdir(parents=True, exist_ok=True)
    args = ["bash", str(DEPS), "--harness", harness,
            "--superpowers", "true" if superpowers else "false",
            "--prose", "true" if prose else "false",
            "--excalidraw", "true" if excalidraw else "false",
            "--multi-agent", "true" if multi_agent else "false"]
    if version is not None:
        args += ["--superpowers-version", version]
    if project:
        args += ["--dir", str(project)]
    if session:
        args += ["--session-dir", str(session)]
    proc = subprocess.run(args, capture_output=True, text=True, env=env, cwd=cwd, check=True)
    return json.loads(proc.stdout)


def real(path: Path) -> str:
    return str(path.resolve())


@pytest.mark.parametrize("no_jq", [False, True])
def test_capability_booleans_round_trip(tmp_path, no_jq):
    result = deps(home=tmp_path / "home", harness="claude", superpowers=True, prose=True,
                  excalidraw=True, multi_agent=True, version="7.0.0",
                  project=tmp_path / "guide", no_jq=no_jq)
    assert result == {
        "harness": "claude",
        "superpowers": True,
        "superpowers_version": "7.0.0",
        "multi_agent": True,
        "prose": True,
        "excalidraw": True,
        "excalidraw_allowed": False,
        "excalidraw_allowed_in": [],
    }


@pytest.mark.parametrize("no_jq", [False, True])
def test_defaults_everything_absent(tmp_path, no_jq):
    project = tmp_path / "guide"
    project.mkdir()
    result = deps(home=tmp_path / "home", project=project, no_jq=no_jq)
    assert result == {
        "harness": "claude",
        "superpowers": False,
        "superpowers_version": None,
        "multi_agent": False,
        "prose": False,
        "excalidraw": False,
        "excalidraw_allowed": False,
        "excalidraw_allowed_in": [],
    }


@pytest.mark.parametrize("no_jq", [False, True])
def test_version_omitted_is_null(tmp_path, no_jq):
    result = deps(home=tmp_path / "home", superpowers=True, project=tmp_path / "g", no_jq=no_jq)
    assert result["superpowers"] is True and result["superpowers_version"] is None


# --- Claude-only excalidraw settings wiring (FR-010, FR-012) -------------------


@pytest.mark.parametrize("no_jq", [False, True])
def test_excalidraw_allowed_from_guide_settings(tmp_path, no_jq):
    home, project = tmp_path / "home", tmp_path / "guide"
    local = settings(project, "settings.local.json", ["Bash(make:*)", "mcp__excalidraw__export_scene"])
    result = deps(home=home, harness="claude", excalidraw=True, project=project, no_jq=no_jq)
    assert result["excalidraw"] is True
    assert result["excalidraw_allowed"] is True
    assert result["excalidraw_allowed_in"] == [real(local)]


@pytest.mark.parametrize("no_jq", [False, True])
def test_default_dir_is_cwd(tmp_path, no_jq):
    home, project = tmp_path / "home", tmp_path / "guide"
    local = settings(project, "settings.local.json", ["mcp__excalidraw__create_element"])
    result = deps(home=home, harness="claude", project=None, cwd=project, no_jq=no_jq)
    assert result["excalidraw_allowed"] is True
    assert result["excalidraw_allowed_in"] == [real(local)]


@pytest.mark.parametrize("no_jq", [False, True])
def test_session_dir_settings(tmp_path, no_jq):
    home, project, session = tmp_path / "home", tmp_path / "guide", tmp_path / "checkout"
    project.mkdir()
    local = settings(session, "settings.local.json", ["mcp__excalidraw"])
    result = deps(home=home, project=project, session=session, no_jq=no_jq)
    assert result["excalidraw_allowed_in"] == [real(local)]


@pytest.mark.parametrize("no_jq", [False, True])
def test_session_dir_uses_git_toplevel(tmp_path, no_jq):
    home, project, repo = tmp_path / "home", tmp_path / "guide", tmp_path / "repo"
    project.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    sub = repo / "docs" / "notes"
    sub.mkdir(parents=True)
    local = settings(repo, "settings.local.json", ["mcp__excalidraw"])
    settings(sub, "settings.local.json", ["mcp__excalidraw"])  # not read by Claude Code
    assert deps(home=home, project=project, session=sub, no_jq=no_jq)["excalidraw_allowed_in"] == [real(local)]
    assert deps(home=home, project=project, cwd=sub, no_jq=no_jq)["excalidraw_allowed_in"] == [real(local)]


@pytest.mark.parametrize("no_jq", [False, True])
def test_user_settings(tmp_path, no_jq):
    home, project = tmp_path / "home", tmp_path / "guide"
    project.mkdir()
    user = settings(home, "settings.json", ["Read", "mcp__excalidraw"])
    settings(home, "settings.local.json", ["mcp__excalidraw"])  # not a user settings file
    result = deps(home=home, project=project, no_jq=no_jq)
    assert result["excalidraw_allowed_in"] == [real(user)]


@pytest.mark.parametrize("no_jq", [False, True])
def test_all_locations_in_order(tmp_path, no_jq):
    home, project, session = tmp_path / "home", tmp_path / "guide", tmp_path / "checkout"
    guide_shared = settings(project, "settings.json", ["mcp__excalidraw"])
    session_local = settings(session, "settings.local.json", ["mcp__excalidraw__import_scene"])
    settings(session, "settings.json", ["Bash(make:*)"])
    user = settings(home, "settings.json", ["mcp__excalidraw"])
    result = deps(home=home, project=project, session=session, no_jq=no_jq)
    assert result["excalidraw_allowed_in"] == [real(guide_shared), real(session_local), real(user)]


# --- excalidraw settings wiring is Claude-only (FR-010) ------------------------


@pytest.mark.parametrize("harness", ["codex", "opencode"])
@pytest.mark.parametrize("no_jq", [False, True])
def test_non_claude_harness_skips_settings_wiring(tmp_path, harness, no_jq):
    home, project = tmp_path / "home", tmp_path / "guide"
    settings(project, "settings.local.json", ["mcp__excalidraw__export_scene"])
    result = deps(home=home, harness=harness, excalidraw=True, project=project, no_jq=no_jq)
    assert result["harness"] == harness
    # The capability boolean still reflects exposure; the settings wiring does not run.
    assert result["excalidraw"] is True
    assert result["excalidraw_allowed"] is False
    assert result["excalidraw_allowed_in"] == []


# --- backward compatibility: the legacy field subset is unchanged (FR-012) -----


@pytest.mark.parametrize("no_jq", [False, True])
def test_legacy_fields_present_with_same_values_on_claude(tmp_path, no_jq):
    home, project = tmp_path / "home", tmp_path / "guide"
    local = settings(project, "settings.local.json", ["mcp__excalidraw__export_scene"])
    result = deps(home=home, harness="claude", superpowers=True, prose=False,
                  excalidraw=True, project=project, no_jq=no_jq)
    # Every legacy field is still emitted ...
    assert LEGACY_FIELDS <= set(result)
    # ... with the values the pre-feature deps.sh would have produced.
    assert result["superpowers"] is True
    assert result["prose"] is False
    assert result["excalidraw_allowed"] is True
    assert result["excalidraw_allowed_in"] == [real(local)]
    # ... and the new fields are additive.
    assert set(result) - LEGACY_FIELDS == {"harness", "superpowers_version", "multi_agent", "excalidraw"}
