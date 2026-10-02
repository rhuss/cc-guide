import json
import os
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "guide" / "scripts"
PROBE = SCRIPTS / "superpowers-probe.sh"
SKILLS = ["brainstorming", "writing-plans", "subagent-driven-development", "requesting-code-review"]
SCRIPT_NAMES = ["sdd-workspace", "task-brief", "review-package"]
GOOD_SCRIPT = '#!/usr/bin/env bash\nif [ $# -lt 1 ]; then echo "usage: {name} PLAN_FILE" >&2; exit 2; fi\n'


def fake_superpowers(home: Path, version: str = "6.4.1", scope: str = "user",
                     key: str = "superpowers@claude-plugins-official", extra: list | None = None) -> Path:
    install = home / ".claude/plugins/cache/claude-plugins-official/superpowers" / version
    for skill in SKILLS:
        (install / "skills" / skill).mkdir(parents=True, exist_ok=True)
        (install / "skills" / skill / "SKILL.md").write_text(f"# {skill}\n")
    scripts = install / "skills/subagent-driven-development/scripts"
    scripts.mkdir()
    for name in SCRIPT_NAMES:
        (scripts / name).write_text(GOOD_SCRIPT.format(name=name))
    entries = [{"scope": scope, "installPath": str(install), "version": version}] + (extra or [])
    write_registry(home, {key: entries})
    return install


def write_registry(home: Path, plugins: dict) -> None:
    reg = home / ".claude/plugins/installed_plugins.json"
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(json.dumps({"version": 2, "plugins": plugins}))


def probe(home: Path, no_jq: bool = False):
    env = dict(os.environ, HOME=str(home))
    if no_jq:
        env["CC_GUIDE_NO_JQ"] = "1"
    proc = subprocess.run(["bash", str(PROBE)], capture_output=True, text=True, env=env)
    return proc.returncode, json.loads(proc.stdout), proc


@pytest.mark.parametrize("no_jq", [False, True])
def test_ok_known_version(tmp_path, no_jq):
    install = fake_superpowers(tmp_path)
    code, out, _ = probe(tmp_path, no_jq)
    assert code == 0
    assert out == {"installPath": str(install), "version": "6.4.1", "known": True, "ok": True, "problems": []}


@pytest.mark.parametrize("no_jq", [False, True])
def test_unknown_version(tmp_path, no_jq):
    fake_superpowers(tmp_path, version="6.9.0")
    code, out, _ = probe(tmp_path, no_jq)
    assert code == 3
    assert out["ok"] is True and out["known"] is False and out["version"] == "6.9.0"


@pytest.mark.parametrize("no_jq", [False, True])
def test_missing_script(tmp_path, no_jq):
    install = fake_superpowers(tmp_path)
    (install / "skills/subagent-driven-development/scripts/review-package").unlink()
    code, out, _ = probe(tmp_path, no_jq)
    assert code == 4
    assert out["ok"] is False
    assert any("review-package" in p for p in out["problems"])


def test_changed_script_contract(tmp_path):
    install = fake_superpowers(tmp_path)
    (install / "skills/subagent-driven-development/scripts/task-brief").write_text("#!/usr/bin/env bash\nexit 1\n")
    code, out, _ = probe(tmp_path)
    assert code == 4
    assert any("task-brief" in p and "exited 1" in p for p in out["problems"])


def test_missing_skill(tmp_path):
    install = fake_superpowers(tmp_path)
    (install / "skills/writing-plans/SKILL.md").unlink()
    code, out, _ = probe(tmp_path)
    assert code == 4 and any("writing-plans" in p for p in out["problems"])


@pytest.mark.parametrize("no_jq", [False, True])
def test_not_installed(tmp_path, no_jq):
    write_registry(tmp_path, {"prose@prose-plugin-development": [{"scope": "user", "installPath": "/x"}]})
    code, out, _ = probe(tmp_path, no_jq)
    assert code == 4
    assert out["installPath"] is None
    assert any("claude plugin install superpowers" in p for p in out["problems"])


def test_no_registry(tmp_path):
    code, out, _ = probe(tmp_path)
    assert code == 4 and out["ok"] is False


@pytest.mark.parametrize("no_jq", [False, True])
def test_prefers_user_scope(tmp_path, no_jq):
    broken = {"scope": "project", "installPath": str(tmp_path / "missing"), "version": "6.3.0"}
    install = fake_superpowers(tmp_path, extra=[broken])
    # put the project entry first so the order of the list does not decide
    reg = tmp_path / ".claude/plugins/installed_plugins.json"
    data = json.loads(reg.read_text())
    data["plugins"]["superpowers@claude-plugins-official"].reverse()
    reg.write_text(json.dumps(data))
    code, out, _ = probe(tmp_path, no_jq)
    assert code == 0 and out["installPath"] == str(install)


def test_real_superpowers_if_installed():
    reg = Path.home() / ".claude/plugins/installed_plugins.json"
    if not reg.is_file() or "superpowers@" not in reg.read_text():
        pytest.skip("superpowers is not installed on this machine")
    code, out, proc = probe(Path.home())
    assert code in (0, 3), proc.stdout
    assert out["ok"] is True


@pytest.mark.parametrize("no_jq", [False, True])
def test_older_than_minimum_fails(tmp_path, no_jq):
    fake_superpowers(tmp_path, version="6.2.9")
    code, out, _ = probe(tmp_path, no_jq)
    assert code == 4
    assert out["ok"] is False and any("older than the minimum 6.3.0" in p for p in out["problems"])


def test_newer_unknown_version_passes(tmp_path):
    fake_superpowers(tmp_path, version="6.10.0")
    code, out, _ = probe(tmp_path)
    assert code == 3 and out["ok"] is True


def _real_superpowers_scripts():
    registry = Path.home() / ".claude/plugins/installed_plugins.json"
    if not registry.is_file():
        return None
    for key, entries in json.loads(registry.read_text()).get("plugins", {}).items():
        if key.startswith("superpowers@"):
            for entry in entries:
                scripts = Path(entry["installPath"]) / "skills/subagent-driven-development/scripts"
                if scripts.is_dir():
                    return scripts
    return None


def test_wrote_output_format_on_dry_fixture(tmp_path):
    """The implicit `wrote <path>: ...` API of task-brief and review-package (research R3)."""
    scripts = _real_superpowers_scripts()
    if scripts is None:
        pytest.skip("superpowers is not installed")
    repo = tmp_path / "guide"
    (repo / "docs" / "guide").mkdir(parents=True)
    git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com",
           "-c", "commit.gpgsign=false"]
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    plan = repo / "docs" / "guide" / "plan.md"
    plan.write_text("# Plan\n\n### Task 1: index page\n\nWrite the index.\n\n### Task 2: install page\n\nWrite it.\n")
    subprocess.run(git + ["add", "-A"], check=True)
    subprocess.run(git + ["commit", "-qm", "plan"], check=True)
    base = subprocess.run(git + ["rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    (repo / "index.md").write_text("# Index\n")
    subprocess.run(git + ["add", "-A"], check=True)
    subprocess.run(git + ["commit", "-qm", "index"], check=True)

    brief = subprocess.run(["bash", str(scripts / "task-brief"), "docs/guide/plan.md", "1"],
                           cwd=repo, capture_output=True, text=True)
    assert brief.returncode == 0, brief.stderr
    path, _, rest = brief.stdout.strip().partition(": ")
    assert path.startswith("wrote ") and Path(path[len("wrote "):]).is_file() and "lines" in rest
    assert "Task 1" in Path(path[len("wrote "):]).read_text()

    package = subprocess.run(["bash", str(scripts / "review-package"), "docs/guide/plan.md", base, "HEAD"],
                             cwd=repo, capture_output=True, text=True)
    assert package.returncode == 0, package.stderr
    path, _, rest = package.stdout.strip().partition(": ")
    assert path.startswith("wrote ") and Path(path[len("wrote "):]).is_file() and "commit" in rest
