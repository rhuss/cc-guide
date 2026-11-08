"""Workflow templates: guide-drift.yml and guide-pr-check.yml (specs/005-embedded-guide, T044)."""
from pathlib import Path

import yaml

TEMPLATES = Path(__file__).resolve().parents[2] / "guide" / "templates"


def render(name: str, guide_dir: str) -> dict:
    text = (TEMPLATES / name).read_text().replace("{{GUIDE_DIR}}", guide_dir)
    assert "{{" not in text.replace("${{", "")
    data = yaml.safe_load(text)
    data["on"] = data.pop(True, data.get("on"))   # YAML 1.1 reads the key `on` as true
    return data


def test_drift_workflow_separate_guide_runs_from_the_root():
    data = render("guide-drift.yml", ".")
    assert data["defaults"] == {"run": {"working-directory": "."}}
    assert data["permissions"] == {"contents": "read", "issues": "write"}
    assert set(data["on"]) == {"schedule", "workflow_dispatch"}
    steps = data["jobs"]["drift"]["steps"]
    assert any("drift.py --check" in s.get("run", "") for s in steps)


def test_drift_workflow_embedded_guide_runs_from_the_subdirectory():
    embedded, separate = render("guide-drift.yml", "guide"), render("guide-drift.yml", ".")
    assert embedded["defaults"] == {"run": {"working-directory": "guide"}}
    assert embedded["jobs"] == separate["jobs"]


def test_pr_check_workflow():
    data = render("guide-pr-check.yml", "guide")
    assert data["permissions"] == {"contents": "read"}
    assert data["defaults"] == {"run": {"working-directory": "guide"}}
    assert data["on"]["pull_request"]["types"] == ["opened", "synchronize", "reopened", "labeled", "unlabeled"]
    steps = data["jobs"]["guide"]["steps"]
    checkout = next(s for s in steps if s.get("uses", "").startswith("actions/checkout"))
    assert checkout["with"]["fetch-depth"] == 0 and checkout["with"]["persist-credentials"] is False
    run = next(s for s in steps if "run" in s)
    assert "guide-skip" in run["env"]["GUIDE_SKIP"]
    assert "drift.py --pr --base" in run["run"] and "--head" in run["run"]
    assert "pipefail" in run["run"]
    assert "secrets." not in (TEMPLATES / "guide-pr-check.yml").read_text()
