"""Workflow templates: guide-drift.yml and guide-pr-check.yml (specs/005-embedded-guide, T044)."""
from pathlib import Path

import pytest
import yaml

TEMPLATES = Path(__file__).resolve().parents[2] / "guide" / "templates"


def render(name: str, guide_dir: str, branch: str = "main") -> dict:
    text = (TEMPLATES / name).read_text().replace("{{GUIDE_DIR}}", guide_dir).replace("{{BRANCH}}", branch)
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


def test_pages_workflow_runs_on_the_default_branch():
    assert render("guide-pages.yml", "docs/guide", branch="master")["on"]["push"]["branches"] == ["master"]
    assert "{{BRANCH}}" in (TEMPLATES / "guide-pages.yml").read_text()
    create = SKILL.read_text()
    assert "`{{BRANCH}}` as `main`" in create

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
    assert "without `--check`, `--pages`, or `--visuals`" in preflight
    assert "gh repo view --json visibility,defaultBranchRef" in evolve
    assert "`{{BRANCH}}` set to the default branch" in evolve
    section = evolve.split("## 3a.")[1].split("## 3b.")[0]
    order = [section.index(f"**{step}**") for step in
             ("Format", "Repository", "Existing workflow", "Remote", "Existing Pages site",
              "Visibility and branch", "Toolkit", "Build check", "Set up", "Report")]
    assert order == sorted(order), order          # every read-only refusal before the first commit
    assert (GUIDE / "toolkit" / "VERSION").read_text().strip() == "0.6.0"   # 0.6.0: captured visuals
    for text in (evolve, command, preflight):
        assert chr(0x2014) not in text and chr(0x2013) not in text


@pytest.mark.parametrize("guide_dir", [".", "guide"])
def test_visuals_workflow(guide_dir):
    """specs/008-captured-visuals FR-036: schedule and dispatch, read-only, no secrets, drift only."""
    data = render("guide-visuals.yml", guide_dir)
    text = (TEMPLATES / "guide-visuals.yml").read_text()
    assert "{{GUIDE_DIR}}" in text
    assert set(data["on"]) == {"schedule", "workflow_dispatch"}
    assert data["permissions"] == {"contents": "read"}
    assert data["defaults"] == {"run": {"working-directory": guide_dir}}
    job = data["jobs"]["visuals"]
    assert job["runs-on"] == "ubuntu-latest"
    checkout = next(s for s in job["steps"] if s.get("uses", "").startswith("actions/checkout"))
    assert checkout["with"] == {"persist-credentials": False}
    runs = [s["run"] for s in job["steps"] if "run" in s]
    assert len(runs) == 1
    assert "uv run tools/guide/visuals.py drift --format markdown" in runs[0]
    assert '"$GITHUB_STEP_SUMMARY"' in runs[0] and "exit $status" in runs[0]
    assert job["timeout-minutes"] == 60
    upload = next(s for s in job["steps"] if s.get("uses", "").startswith("actions/upload-artifact"))
    assert upload["if"] == "always()" and upload["with"]["include-hidden-files"] is True
    assert f"{guide_dir}/.guide/visuals/*/debug/" in upload["with"]["path"]
    assert "visuals.py capture" not in text and "git push" not in text
    assert "secrets." not in text
    assert "docker" not in text.lower()
    assert chr(0x2014) not in text and chr(0x2013) not in text


def test_visuals_workflow_offered_by_create_and_evolve():
    create = (GUIDE / "skills" / "create" / "SKILL.md").read_text()
    evolve = (GUIDE / "skills" / "evolve" / "SKILL.md").read_text()
    for text in (create, evolve):
        assert "$PLUGIN/templates/guide-visuals.yml" in text
        assert ".github/workflows/guide-visuals.yml" in text


def test_evolve_visuals_mode_requires_toolkit_0_6():
    evolve = (GUIDE / "skills" / "evolve" / "SKILL.md").read_text()
    section = evolve.split("## 3b.")[1].split("## 4.")[0]
    assert "below 0.6.0" in section and "visuals.py init" in section
    assert "Toolkit 0.6.0 adds captured visuals" in evolve
    assert (GUIDE / "toolkit" / "VERSION").read_text().strip() == "0.6.0"


def test_create_skill_offers_in_repo_guides():
    text = SKILL.read_text()
    for phrase in ("add an Antora or MkDocs guide in a subdirectory (README untouched)",
                   "default `docs/guide`", "--in-repo", "In-repo guide",
                   "`--format antora` or `--format mkdocs` at a repository root selects the in-repo guide",
                   "confidential.local.yaml", "no internal part",
                   "evolve section 3a steps 2 to 6", "`{{BRANCH}}` set to the default branch",
                   "inside a git repository but not at its root"):
        assert phrase in text, phrase
    assert "is inside the repository `<toplevel>` but not its root. Embedded guides live" not in text
    assert chr(0x2014) not in text and chr(0x2013) not in text


def test_evolve_keeps_in_repo_confidential_data_local():
    evolve = (GUIDE / "skills" / "evolve" / "SKILL.md").read_text()
    section = evolve.split("## 9. In-repo guides")[1].split("\n## ")[0]
    for phrase in ("guidecfg.py` `in_repo_guide`", "registered as `local:<id>`",
                   "`confidential.local.yaml`", "never into `guide.yaml`", "`--adopt`"):
        assert phrase in section, phrase


def test_create_keeps_separate_guides_possible_inside_a_parent_repository():
    text = SKILL.read_text()
    assert "a separate guide in its own repository nested here" in text
    assert "stop and suggest an empty directory outside the repository" not in text
