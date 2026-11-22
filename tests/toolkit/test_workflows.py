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


def test_pages_workflow():
    data = render("guide-pages.yml", ".")
    text = (TEMPLATES / "guide-pages.yml").read_text()
    assert data["on"]["push"]["branches"] == ["main"] and "workflow_dispatch" in data["on"]
    assert data["permissions"] == {"contents": "read"}
    assert data["concurrency"] == {"group": "pages", "cancel-in-progress": False}
    assert data["defaults"] == {"run": {"working-directory": "."}}
    steps = data["jobs"]["build"]["steps"]
    checkout = next(s for s in steps if s.get("uses", "").startswith("actions/checkout"))
    assert checkout["with"] == {"fetch-depth": 0, "persist-credentials": False}
    runs = [s.get("run", "") for s in steps]
    site = next(i for i, r in enumerate(runs) if r.strip() == "make site")
    leak = next(i for i, r in enumerate(runs) if "leakcheck.py build/site" in r)
    upload = next(i for i, s in enumerate(steps) if s.get("uses", "").startswith("actions/upload-pages-artifact"))
    assert site < leak < upload
    assert steps[upload]["with"]["path"] == "./build/site"
    assert not any(s.get("continue-on-error") for s in steps)
    deploy = data["jobs"]["deploy"]
    assert deploy["needs"] == "build" and deploy["environment"]["name"] == "github-pages"
    assert "permissions" not in data["jobs"]["build"]   # npm install never holds the deploy token
    assert deploy["permissions"] == {"pages": "write", "id-token": "write"}
    assert not any(s.get("uses", "").startswith("actions/configure-pages") for s in steps)
    assert any(s.get("uses", "").startswith("actions/deploy-pages") for s in deploy["steps"])
    assert "secrets." not in text and "site-internal" not in text and "fetch-baseline" not in text
    assert chr(0x2014) not in text and chr(0x2013) not in text



def test_pages_workflow_for_a_guide_in_a_subdirectory():
    data = render("guide-pages.yml", "docs/guide")
    assert data["defaults"] == {"run": {"working-directory": "docs/guide"}}
    upload = next(s for s in data["jobs"]["build"]["steps"]
                  if s.get("uses", "").startswith("actions/upload-pages-artifact"))
    assert upload["with"]["path"] == "docs/guide/build/site"

SKILL = Path(__file__).resolve().parents[2] / "guide" / "skills" / "create" / "SKILL.md"


def test_create_skill_offers_pages():
    text = SKILL.read_text()
    assert "Publish the shareable view on GitHub Pages? (default no)" in text
    assert "public on the web" in text and "paid GitHub plan" in text
    assert "guide-pages.yml" in text and "pages.enabled: true" in text
    assert "gh api -X POST repos/<owner>/<repo>/pages -f build_type=workflow" in text
    assert "deploys fail until Pages is switched on" in text
    assert "for a private remote, that the site is public on the web" in text
    assert "`site.url` in `site.yml`" in text and "`site_url` in `mkdocs.yml`" in text
    assert chr(0x2014) not in text and chr(0x2013) not in text


GUIDE = Path(__file__).resolve().parents[2] / "guide"


def test_evolve_pages_mode():
    evolve = (GUIDE / "skills" / "evolve" / "SKILL.md").read_text()
    command = (GUIDE / "commands" / "evolve.md").read_text()
    preflight = (GUIDE / "skills" / "preflight" / "SKILL.md").read_text()
    for text in (evolve, command):
        assert "[--pages]" in text.split("argument-hint:")[1].splitlines()[0]
    assert "## 3a. GitHub Pages (`--pages`)" in evolve
    for phrase in ("git rev-parse --show-toplevel", "gh api repos/<owner>/<repo>/pages",
                   "gh repo view --json visibility", "one Pages site per repository",
                   "`{{GUIDE_DIR}}` set to the guide's path inside the repository",
                   "not a GitHub remote", "`make site` and the leak check",
                   "create section 9 step 2", "Toolkit 0.5.0 adds"):
        assert phrase in evolve, phrase
    assert "without `--check` or `--pages`" in preflight
    assert (GUIDE / "toolkit" / "VERSION").read_text().strip() == "0.5.0"
    for text in (evolve, command, preflight):
        assert chr(0x2014) not in text and chr(0x2013) not in text
