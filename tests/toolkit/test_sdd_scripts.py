"""guide/toolkit/sdd/: the vendored superpowers SDD helper scripts (D8, FR-006).

These assert the usage/exit-code contract the probe used to check against the
superpowers install path (no args -> exit 2 with a usage: line), plus a light
functional check that the vendored copies still extract a task and build a review
package. The scripts travel into guide projects as tools/guide/sdd/.
"""
import subprocess
from pathlib import Path

import pytest

SDD = Path(__file__).resolve().parents[2] / "guide" / "toolkit" / "sdd"
SCRIPTS = ["sdd-workspace", "task-brief", "review-package"]


@pytest.mark.parametrize("name", SCRIPTS)
def test_no_args_exits_2_with_usage_line(name):
    proc = subprocess.run(["bash", str(SDD / name)], capture_output=True, text=True,
                          stdin=subprocess.DEVNULL)
    assert proc.returncode == 2, (name, proc.stdout, proc.stderr)
    assert proc.stderr.splitlines()[0].startswith("usage:"), proc.stderr


@pytest.mark.parametrize("name", SCRIPTS)
def test_scripts_are_executable(name):
    import os
    assert os.access(SDD / name, os.X_OK), f"{name} lost its executable bit"


def _git(repo: Path):
    return ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com",
            "-c", "commit.gpgsign=false"]


def test_task_brief_and_review_package_functional(tmp_path):
    repo = tmp_path / "guide"
    (repo / "docs" / "guide").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    plan = repo / "docs" / "guide" / "plan.md"
    plan.write_text("# Plan\n\n### Task 1: index page\n\nWrite the index.\n\n### Task 2: install page\n\nWrite it.\n")
    subprocess.run(_git(repo) + ["add", "-A"], check=True)
    subprocess.run(_git(repo) + ["commit", "-qm", "plan"], check=True)
    base = subprocess.run(_git(repo) + ["rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    (repo / "index.md").write_text("# Index\n")
    subprocess.run(_git(repo) + ["add", "-A"], check=True)
    subprocess.run(_git(repo) + ["commit", "-qm", "index"], check=True)

    # sdd-workspace prints an absolute workspace path under .superpowers/sdd/
    ws = subprocess.run(["bash", str(SDD / "sdd-workspace"), "docs/guide/plan.md"],
                        cwd=repo, capture_output=True, text=True)
    assert ws.returncode == 0, ws.stderr
    ws_dir = ws.stdout.strip()
    assert ws_dir.startswith("/") and ".superpowers/sdd" in ws_dir and Path(ws_dir).is_dir()

    # task-brief extracts just one task
    brief = subprocess.run(["bash", str(SDD / "task-brief"), "docs/guide/plan.md", "1"],
                           cwd=repo, capture_output=True, text=True)
    assert brief.returncode == 0, brief.stderr
    path, _, rest = brief.stdout.strip().partition(": ")
    out = Path(path[len("wrote "):])
    assert path.startswith("wrote ") and out.is_file() and "lines" in rest
    text = out.read_text()
    assert "Task 1" in text and "Task 2" not in text

    # review-package builds a diff package over the recorded base..HEAD
    package = subprocess.run(["bash", str(SDD / "review-package"), "docs/guide/plan.md", base, "HEAD"],
                             cwd=repo, capture_output=True, text=True)
    assert package.returncode == 0, package.stderr
    path, _, rest = package.stdout.strip().partition(": ")
    assert path.startswith("wrote ") and Path(path[len("wrote "):]).is_file() and "commit" in rest
