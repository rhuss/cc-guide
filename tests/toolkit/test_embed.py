"""tools/guide/embed.py: inventory, apply, stage, retarget, front-page-status (specs/005-embedded-guide)."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import guidecfg
from conftest import FRONT_PAGE, OWNERSHIP, commit_all, host_git, make_embedded_guide

TOOLKIT = Path(__file__).resolve().parents[2] / "guide" / "toolkit"


def embed(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOLKIT / "embed.py"), *args, "--root", str(root)],
                          capture_output=True, text=True, env=os.environ.copy())


@pytest.fixture
def host_guide(mini_host):
    """An embedded guide subdirectory in the mini host, committed together with the host."""
    host, commit = mini_host
    root = make_embedded_guide(host, commit)
    head = commit_all(host, "Add the guide subdirectory")
    return root, head


def snapshot(host: Path) -> dict[str, bytes]:
    """Every file of the host except .git, for byte-identical comparisons."""
    return {p.relative_to(host).as_posix(): p.read_bytes()
            for p in sorted(host.rglob("*")) if p.is_file() and ".git" not in p.relative_to(host).parts}


# --- inventory (T016) ------------------------------------------------------------------


def inventory(root: Path) -> dict:
    proc = embed(root, "inventory", "--format", "json")
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_inventory_lists_documentation(host_guide):
    root, head = host_guide
    data = inventory(root)
    kinds = {f["path"]: f["kind"] for f in data["files"]}
    assert kinds["README.md"] == "readme"
    assert kinds["CONTRIBUTING.md"] == "community"
    assert kinds["LICENSE"] == "license"
    assert kinds["docs/install.md"] == "doc-file"
    assert kinds["docs/"] == "doc-dir"
    assert kinds["USAGE.md"] == "doc-file"
    assert not any(p.startswith("guide/") for p in kinds)
    assert "src/cli.py" not in kinds and "Makefile" not in kinds
    readme = next(f for f in data["files"] if f["path"] == "README.md")
    assert [h["text"] for h in readme["headings"]] == [
        "Mini Host", "Install", "Usage", "Building from source", "Requirements", "Running tests"]
    assert readme["headings"][4]["level"] == 3
    assert data["manifests"] == [{"path": "pyproject.toml", "publishes_readme": True}]
    assert data["self_revision"] == head
    assert data["guide_dir"] == "guide"


def test_inventory_github_readme_and_doc_site(host_guide):
    root, _ = host_guide
    host = root.parent
    (host / ".github").mkdir()
    (host / ".github" / "README.md").write_text("# Shown instead of the root README\n")
    (host / "site" / "docs").mkdir(parents=True)
    (host / "site" / "mkdocs.yml").write_text("site_name: Mini Host\n")
    (host / "site" / "docs" / "index.md").write_text("# Site\n")
    commit_all(host, "more docs")
    kinds = {f["path"]: f["kind"] for f in inventory(root)["files"]}
    assert kinds[".github/README.md"] == "github-readme"
    assert kinds["site/"] == "doc-site"
    assert kinds["site/docs/index.md"] == "doc-file"


def test_inventory_reads_committed_files_only(host_guide):
    root, _ = host_guide
    (root.parent / "INSTALL.md").write_text("# Not committed\n")
    assert "INSTALL.md" not in {f["path"] for f in inventory(root)["files"]}


# --- apply (T017) ----------------------------------------------------------------------


def write_plan(root: Path, revision: str, entries: list[dict], developer_readme: str = "../DEVELOPMENT.md",
               name: str = "move-plan.yaml") -> Path:
    path = root / ".guide" / "runs" / "r1" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"self_revision": revision, "developer_readme": developer_readme,
                                    "developer_readme_exists": False, "entries": entries}, sort_keys=False))
    return path


DEV_ENTRIES = [
    {"path": "../README.md", "section": None, "destination": "input"},
    {"path": "../README.md", "section": "Building from source", "destination": "developer"},
    {"path": "../README.md", "section": "Running tests", "destination": "developer"},
]


def readme_section(host: Path, title: str) -> str:
    lines = (host / "README.md").read_text().splitlines(keepends=True)
    start = next(i for i, l in enumerate(lines) if l.strip() == f"## {title}")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "".join(lines[start:end]).rstrip("\n")


def test_apply_moves_developer_sections(host_guide):
    root, head = host_guide
    host = root.parent
    building, tests = readme_section(host, "Building from source"), readme_section(host, "Running tests")
    proc = embed(root, "apply", "--plan", str(write_plan(root, head, DEV_ENTRIES)))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    dev = (host / "DEVELOPMENT.md").read_text()
    assert dev.startswith("# Development\n")
    assert building in dev and tests in dev            # unchanged text, same heading levels
    assert dev.index("Building from source") < dev.index("Running tests")
    assert guidecfg.load_guide(root).embedded.developer_readme.resolve() == (host / "DEVELOPMENT.md").resolve()
    item = guidecfg.load_inputs(root).inputs[0]
    assert item.location == "self:README.md"
    assert item.revision == head
    assert item.blob == host_git(host, "rev-parse", f"{head}:README.md")
    # the old README stays until the front page replaces it
    assert "## Building from source" in (host / "README.md").read_text()


def test_apply_rewrites_relative_links_for_another_location(host_guide):
    root, head = host_guide
    host = root.parent
    plan = write_plan(root, head, DEV_ENTRIES, developer_readme="../docs/DEVELOPMENT.md")
    proc = embed(root, "apply", "--plan", str(plan))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    dev = (host / "docs" / "DEVELOPMENT.md").read_text()
    assert "[install notes](install.md)" in dev
    assert "[CONTRIBUTING.md](../CONTRIBUTING.md)" in dev
    assert "Clone the repository and run `make build`." in dev


def test_apply_appends_to_existing_developer_readme(host_guide):
    root, _ = host_guide
    host = root.parent
    (host / "DEVELOPMENT.md").write_text("# Hacking on Mini Host\n\nUse a virtual environment.\n")
    head = commit_all(host, "developer notes")
    proc = embed(root, "apply", "--plan", str(write_plan(root, head, DEV_ENTRIES)))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    dev = (host / "DEVELOPMENT.md").read_text()
    assert dev.startswith("# Hacking on Mini Host\n\nUse a virtual environment.\n")
    assert "\n## Moved from the README\n" in dev
    assert "\n### Building from source\n" in dev and "\n#### Requirements\n" in dev
    assert "\n### Running tests\n" in dev


def test_apply_relocates_github_readme(host_guide):
    root, _ = host_guide
    host = root.parent
    (host / ".github").mkdir()
    (host / ".github" / "README.md").write_text("# Shadow README\n")
    head = commit_all(host, "shadow")
    plan = write_plan(root, head, DEV_ENTRIES + [
        {"path": "../.github/README.md", "destination": "relocate", "to": "../.github/README.old.md"}])
    proc = embed(root, "apply", "--plan", str(plan))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not (host / ".github" / "README.md").exists()
    assert (host / ".github" / "README.old.md").read_text() == "# Shadow README\n"


def test_apply_dirty_check_ignores_guide_subdirectory(host_guide):
    root, head = host_guide
    host = root.parent
    (root / "docs" / "new-page.md").write_text("# New\n")      # uncommitted, inside the guide
    assert embed(root, "apply", "--dry-run", "--plan", str(write_plan(root, head, DEV_ENTRIES))).returncode == 0
    (host / "src" / "cli.py").write_text("# uncommitted\n")    # outside the guide
    proc = embed(root, "apply", "--plan", str(write_plan(root, head, DEV_ENTRIES)))
    assert proc.returncode == 2
    assert "uncommitted" in proc.stderr
    assert not (host / "DEVELOPMENT.md").exists()


@pytest.mark.parametrize("entries, message", [
    ([{"path": "../NOPE.md", "destination": "input"}], "does not exist"),
    ([{"path": "../LICENSE", "destination": "remove"}], "LICENSE"),
    ([{"path": "../README.md", "section": "No such section", "destination": "developer"}], "No such section"),
    ([{"path": "../src/cli.py", "destination": "remove"}], "not a documentation file"),
    ([{"path": "../README.md", "destination": "remove"}], "README"),
    ([{"path": "../README.md", "destination": "input", "stub": True}], "stub"),
    ([{"path": "../USAGE.md", "destination": "elsewhere"}], "destination"),
    ([{"path": "../USAGE.md", "destination": "relocate", "to": "../Makefile"}], "cannot relocate"),
    ([{"path": "../USAGE.md", "destination": "relocate"}], "needs a 'to' path"),
    ([{"path": "../USAGE.md", "destination": "input", "bogus": 1}], "unknown keys"),
    ([{"path": "../README.md", "section": "Install", "destination": "remove"}], "a section can only"),
    # a stub replaces a path that is gone; a relocated or kept file is not gone
    ([{"path": "../USAGE.md", "destination": "relocate", "to": "../docs/usage.md", "stub": True}],
     "stub: true cannot be combined with destination relocate"),
    ([{"path": "../USAGE.md", "destination": "keep", "stub": True}],
     "stub: true cannot be combined with destination keep"),
    # a section named twice, or nested in another one, would be moved twice
    ([{"path": "../README.md", "section": "Building from source", "destination": "developer"},
      {"path": "../README.md", "section": "Requirements", "destination": "developer"}], "overlaps"),
])
def test_apply_refuses_bad_plans(host_guide, entries, message):
    root, head = host_guide
    host = root.parent
    before = snapshot(host)
    plan = write_plan(root, head, entries)
    before[plan.relative_to(host).as_posix()] = plan.read_bytes()
    proc = embed(root, "apply", "--plan", str(plan))
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert message in proc.stderr
    assert snapshot(host) == before


def test_apply_refuses_stub_on_github_readme(host_guide):
    root, _ = host_guide
    host = root.parent
    (host / ".github").mkdir()
    (host / ".github" / "README.md").write_text("# Shadow README\n")
    head = commit_all(host, "shadow")
    plan = write_plan(root, head, [{"path": "../.github/README.md", "destination": "input", "stub": True}])
    proc = embed(root, "apply", "--plan", str(plan))
    assert proc.returncode == 2 and "stub" in proc.stderr
    assert (host / ".github" / "README.md").is_file()


def test_apply_non_markdown_readme(host_guide):
    root, _ = host_guide
    host = root.parent
    host_git(host, "mv", "README.md", "README.rst")
    head = commit_all(host, "rst readme")
    bad = [
        [{"path": "../README.rst", "destination": "input"}],                      # two root READMEs
        [{"path": "../README.rst", "section": "Install", "destination": "developer"}],
        [{"path": "../README.rst", "destination": "keep"}],
    ]
    for entries in bad:
        proc = embed(root, "apply", "--plan", str(write_plan(root, head, entries)))
        assert proc.returncode == 2, (entries, proc.stdout)
        assert (host / "README.rst").is_file()
    ok = [{"path": "../README.rst", "destination": "input"}, {"path": "../README.rst", "destination": "remove"}]
    proc = embed(root, "apply", "--plan", str(write_plan(root, head, ok)))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not (host / "README.rst").exists()
    assert guidecfg.load_inputs(root).inputs[0].location == "self:README.rst"
    relocate = [{"path": "../README.rst", "destination": "input"},
                {"path": "../README.rst", "destination": "relocate", "to": "../docs/README.old.rst"}]
    host_git(host, "checkout", "--", "README.rst")
    (root / "inputs.yaml").unlink()
    proc = embed(root, "apply", "--plan", str(write_plan(root, head, relocate)))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (host / "docs" / "README.old.rst").is_file() and not (host / "README.rst").exists()


def test_apply_dry_run_changes_nothing(host_guide):
    root, head = host_guide
    host = root.parent
    plan = write_plan(root, head, DEV_ENTRIES)
    before = snapshot(host)
    proc = embed(root, "apply", "--dry-run", "--plan", str(plan))
    assert proc.returncode == 0, proc.stderr
    assert "DEVELOPMENT.md" in proc.stdout
    assert snapshot(host) == before


def test_apply_registers_kept_doc_as_path_input(host_guide):
    root, head = host_guide
    proc = embed(root, "apply", "--plan", str(write_plan(root, head, [
        {"path": "../docs/install.md", "destination": "input"}])))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    item = guidecfg.load_inputs(root).inputs[0]
    assert item.location == "../docs/install.md" and len(item.sha256) == 64 and not item.revision


# --- stage (T019) ----------------------------------------------------------------------


STAGE_FRONT = FRONT_PAGE.replace(
    "Mini Host prints a greeting.",
    "Mini Host prints a greeting.\n\n![Architecture](guide/docs/assets/arch.svg)\n\n"
    "Start with [installing it](guide/docs/admin/install.md#steps).")


@pytest.fixture
def staged_guide(mini_host):
    host, commit = mini_host
    root = make_embedded_guide(host, commit, front_page=STAGE_FRONT)
    (root / "docs" / "assets").mkdir()
    (root / "docs" / "assets" / "arch.svg").write_text("<svg/>\n")
    (host / "DEVELOPMENT.md").write_text("# Development\n")
    data = yaml.safe_load((root / "baseline.yaml").read_text())
    data["sources"][0]["web"] = "https://github.com/acme/mini-host"
    (root / "baseline.yaml").write_text(yaml.safe_dump(data, sort_keys=False))
    return root


def test_stage_replaces_pointer_with_front_page(staged_guide):
    root = staged_guide
    proc = embed(root, "stage", "--out", "build/stage")
    assert proc.returncode == 0, proc.stderr
    docs = root / "build" / "stage" / "docs"
    front = (docs / "README.md").read_text()
    assert front.startswith(OWNERSHIP)
    assert "](admin/install.md)" in front and "](admin/install.md#steps)" in front
    assert "](assets/arch.svg)" in front
    assert "](https://github.com/acme/mini-host/blob/main/DEVELOPMENT.md)" in front
    assert "](https://github.com/acme/mini-host/blob/main/LICENSE)" in front
    assert "guide/docs/" not in front
    # links from staged pages back to the front page point at the staged README.md
    install = (docs / "admin" / "install.md").read_text()
    assert "[front page](../README.md)" in install
    assert (docs / "assets" / "arch.svg").is_file()
    assert (docs / "SUMMARY.md").is_file()
    # the committed pages are untouched
    assert "../../../README.md" in (root / "docs" / "admin" / "install.md").read_text()


def test_stage_without_web_keeps_host_link_text(staged_guide):
    """Without a GitHub origin there is no URL for host files: the built site and the PDF
    keep the link text and drop the link."""
    root = staged_guide
    data = yaml.safe_load((root / "baseline.yaml").read_text())
    data["sources"][0].pop("web")
    (root / "baseline.yaml").write_text(yaml.safe_dump(data, sort_keys=False))
    assert embed(root, "stage", "--out", "build/stage").returncode == 0
    front = (root / "build" / "stage" / "docs" / "README.md").read_text()
    assert "See DEVELOPMENT.md and the license." in front
    assert "](admin/install.md)" in front and "](assets/arch.svg)" in front


def test_stage_refuses_standalone_guides(render_fixture_guide):
    assert embed(render_fixture_guide, "stage", "--out", "build/stage").returncode == 2


# --- checkpoint 1 review fixes -------------------------------------------------------


def test_inventory_root_mkdocs_marks_docs_as_site(host_guide):
    root, _ = host_guide
    host = root.parent
    (host / "mkdocs.yml").write_text("site_name: Mini Host\n")
    commit_all(host, "mkdocs at the root")
    files = {f["path"]: f for f in inventory(root)["files"]}
    assert files["docs/"]["kind"] == "doc-site" and files["docs/"]["config"] == "mkdocs.yml"
    assert files["docs/install.md"]["kind"] == "doc-file"


def test_apply_directory_input_registers_each_file(host_guide):
    root, head = host_guide
    proc = embed(root, "apply", "--plan", str(write_plan(root, head, [
        {"path": "../docs/", "destination": "input"}])))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert [i.location for i in guidecfg.load_inputs(root).inputs] == ["../docs/install.md"]


@pytest.mark.parametrize("entry", [
    {"path": "../docs/", "destination": "remove"},
    {"path": "../docs/", "destination": "input", "stub": True},
])
def test_apply_refuses_directory_removal(host_guide, entry):
    root, head = host_guide
    proc = embed(root, "apply", "--dry-run", "--plan", str(write_plan(root, head, [entry])))
    assert proc.returncode == 2 and "directory" in proc.stderr
    assert (root.parent / "docs" / "install.md").is_file()


def test_apply_moves_sections_out_of_other_files(host_guide):
    root, _ = host_guide
    host = root.parent
    (host / "USAGE.md").write_text("# Usage\n\nRun it.\n\n## Releasing\n\nTag and push.\n\n## Flags\n\nNone.\n")
    head = commit_all(host, "usage with a release section")
    proc = embed(root, "apply", "--plan", str(write_plan(root, head, [
        {"path": "../USAGE.md", "destination": "input"},
        {"path": "../USAGE.md", "section": "Releasing", "destination": "developer"}])))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Tag and push." in (host / "DEVELOPMENT.md").read_text()
    usage = (host / "USAGE.md").read_text()
    assert "Releasing" not in usage and "## Flags" in usage
    item = guidecfg.load_inputs(root).inputs[0]
    assert item.location == "self:USAGE.md" and item.revision == head


def test_apply_refuses_nested_license_removal(host_guide):
    root, _ = host_guide
    host = root.parent
    (host / "docs" / "LICENSE").write_text("docs license\n")
    head = commit_all(host, "docs license")
    proc = embed(root, "apply", "--plan", str(write_plan(root, head, [{"path": "../docs/LICENSE", "destination": "remove"}])))
    assert proc.returncode == 2 and "license" in proc.stderr


# --- front-page-status (T034) --------------------------------------------------------


@pytest.fixture
def recorded(mini_host):
    host, commit = mini_host
    front = FRONT_PAGE + "\nPinned at <!-- guide:attr self-commit-short -->0000000<!-- /guide:attr -->.\n"
    root = make_embedded_guide(host, commit, front_page=front)
    proc = embed(root, "front-page-status", "--record")
    assert proc.returncode == 0, proc.stderr
    return root


def test_front_page_status_unchanged(recorded):
    blob = guidecfg.load_baseline(recorded).source("self").front_page_blob
    assert len(blob) == 40
    proc = embed(recorded, "front-page-status")
    assert proc.returncode == 0 and proc.stdout.strip() == "unchanged"


def test_front_page_status_reports_hand_edits(recorded):
    front = recorded.parent / "README.md"
    front.write_text(front.read_text().replace("Mini Host prints a greeting.", "Mini Host prints a warm greeting."))
    proc = embed(recorded, "front-page-status")
    assert proc.returncode == 10
    assert proc.stdout.splitlines()[0] == "edited"
    assert "-Mini Host prints a greeting." in proc.stdout and "+Mini Host prints a warm greeting." in proc.stdout


def test_front_page_diff_survives_gc_from_history(recorded):
    """The recorded text comes from the commit that changed baseline.yaml, not the loose object."""
    host = recorded.parent
    commit_all(host, "guide with recorded front page")
    host_git(host, "reflog", "expire", "--expire=now", "--all")
    host_git(host, "gc", "--quiet", "--prune=now")
    blob = guidecfg.load_baseline(recorded).source("self").front_page_blob
    loose = subprocess.run(["git", "-C", str(host), "cat-file", "-e", blob], capture_output=True)
    assert loose.returncode != 0, "the normalized blob should not survive gc on its own"
    front = host / "README.md"
    front.write_text(front.read_text().replace("Mini Host prints a greeting.", "Mini Host prints a warm greeting."))
    proc = embed(recorded, "front-page-status")
    assert proc.returncode == 10
    assert "+Mini Host prints a warm greeting." in proc.stdout and "no diff available" not in proc.stdout


def test_front_page_committed_separately_has_no_diff(recorded):
    host = recorded.parent
    commit_all(host, "guide with recorded front page")
    front = host / "README.md"
    front.write_text(front.read_text().replace("Mini Host prints a greeting.", "Mini Host prints a warm greeting."))
    commit_all(host, "hand edit")
    host_git(host, "reflog", "expire", "--expire=now", "--all")
    host_git(host, "gc", "--quiet", "--prune=now")
    # Rewrite baseline.yaml in a later commit without re-recording, so the last baseline
    # commit holds a front page that does not match front_page_blob.
    (recorded / "baseline.yaml").write_text((recorded / "baseline.yaml").read_text() + "\n")
    commit_all(host, "touch baseline")
    host_git(host, "gc", "--quiet", "--prune=now")
    proc = embed(recorded, "front-page-status")
    assert proc.returncode == 10
    assert "not committed together" in proc.stdout


def test_front_page_status_ignores_region_rewrites(recorded):
    import attrs
    assert attrs.regions(recorded, guidecfg.load_baseline(recorded), write=True)
    proc = embed(recorded, "front-page-status")
    assert proc.returncode == 0, proc.stdout


# --- stubs (T039) ----------------------------------------------------------------------

STUB_ENTRIES = DEV_ENTRIES + [
    {"path": "../docs/install.md", "destination": "input", "stub": True},
    {"path": "../USAGE.md", "destination": "input", "stub": True},
]


def stub_lines(path: Path) -> list[str]:
    return [l for l in path.read_text().splitlines() if l.strip()]


def test_apply_writes_stubs(host_guide):
    root, head = host_guide
    host = root.parent
    proc = embed(root, "apply", "--plan", str(write_plan(root, head, STUB_ENTRIES)))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    install = stub_lines(host / "docs" / "install.md")
    assert install == ["<!-- guide: moved -->", "# Installation", "This page moved to [Installation](../README.md)."]
    assert stub_lines(host / "USAGE.md") == ["<!-- guide: moved -->", "# Usage",
                                             "This page moved to [Usage](README.md)."]
    emb = guidecfg.load_guide(root).embedded
    assert sorted(p.resolve() for p in emb.stubs) == sorted(
        [(host / "docs" / "install.md").resolve(), (host / "USAGE.md").resolve()])
    inputs = {i.location: i for i in guidecfg.load_inputs(root).inputs}
    assert inputs["self:docs/install.md"].blob == host_git(host, "rev-parse", f"{head}:docs/install.md")
    assert inputs["self:USAGE.md"].revision == head
    assert "self:README.md" in inputs


def test_retarget_rewrites_one_stub(host_guide):
    root, head = host_guide
    host = root.parent
    assert embed(root, "apply", "--plan", str(write_plan(root, head, STUB_ENTRIES))).returncode == 0
    proc = embed(root, "retarget", "docs/install.md=guide/docs/admin/install.md")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "This page moved to [Installation](../guide/docs/admin/install.md)." in \
        (host / "docs" / "install.md").read_text()
    # a stub whose content no guide page covers keeps its link to the front page
    assert "This page moved to [Usage](README.md)." in (host / "USAGE.md").read_text()
    # a renamed page: stubs and front page links pointing at it follow
    (host / "README.md").write_text(FRONT_PAGE)
    (root / "docs" / "admin" / "install.md").rename(root / "docs" / "admin" / "setup.md")
    proc = embed(root, "retarget", "guide/docs/admin/install.md=guide/docs/admin/setup.md")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "](../guide/docs/admin/setup.md)" in (host / "docs" / "install.md").read_text()
    assert "](guide/docs/admin/setup.md)" in (host / "README.md").read_text()


def test_retarget_unknown_stub_fails(host_guide):
    root, head = host_guide
    assert embed(root, "apply", "--plan", str(write_plan(root, head, STUB_ENTRIES))).returncode == 0
    assert embed(root, "retarget", "nope.md=guide/docs/admin/install.md").returncode == 2
    assert embed(root, "retarget", "docs/install.md").returncode == 2


# --- checkpoint 2 review fixes -------------------------------------------------------


@pytest.mark.parametrize("entry, message", [
    ({"path": "../CONTRIBUTING.md", "destination": "remove", "stub": True}, "community health file"),
    ({"path": "../CONTRIBUTING.md", "destination": "relocate", "to": "../notes/CONTRIBUTING.md"}, "community"),
    ({"path": "../USAGE.md", "destination": "remove"}, "without a stub"),
])
def test_apply_refuses_more_plans(host_guide, entry, message):
    root, head = host_guide
    proc = embed(root, "apply", "--plan", str(write_plan(root, head, [entry])))
    assert proc.returncode == 2 and message in proc.stderr, proc.stderr


def test_apply_relocates_community_file_to_github(host_guide):
    root, head = host_guide
    proc = embed(root, "apply", "--plan", str(write_plan(root, head, [
        {"path": "../CONTRIBUTING.md", "destination": "relocate", "to": "../.github/CONTRIBUTING.md"}])))
    assert proc.returncode == 0, proc.stderr
    assert (root.parent / ".github" / "CONTRIBUTING.md").is_file()


def test_apply_refuses_a_second_root_readme(host_guide):
    root, _ = host_guide
    host = root.parent
    (host / "README.markdown").write_text("# Another README\n")
    head = commit_all(host, "second readme")
    proc = embed(root, "apply", "--plan", str(write_plan(root, head, [
        {"path": "../README.markdown", "destination": "input"}])))
    assert proc.returncode == 2 and "second root README" in proc.stderr
    proc = embed(root, "apply", "--plan", str(write_plan(root, head, [
        {"path": "../README.markdown", "destination": "input"},
        {"path": "../README.markdown", "destination": "remove"}])))
    assert proc.returncode == 0, proc.stderr


def test_apply_moves_last_section_without_final_newline(host_guide):
    root, _ = host_guide
    host = root.parent
    (host / "USAGE.md").write_text("# Usage\n\nRun it.\n\n## Releasing\n\nTag and push.")
    head = commit_all(host, "no final newline")
    proc = embed(root, "apply", "--plan", str(write_plan(root, head, [
        {"path": "../USAGE.md", "section": "Releasing", "destination": "developer"}])))
    assert proc.returncode == 0, proc.stderr
    assert "Releasing" not in (host / "USAGE.md").read_text()


def test_input_ids_keep_the_extension(host_guide):
    root, _ = host_guide
    host = root.parent
    (host / "docs" / "install.rst").write_text("Installation\n============\n")
    head = commit_all(host, "rst twin")
    proc = embed(root, "apply", "--plan", str(write_plan(root, head, [
        {"path": "../docs/install.md", "destination": "input"},
        {"path": "../docs/install.rst", "destination": "input"}])))
    assert proc.returncode == 0, proc.stderr
    assert len(guidecfg.load_inputs(root).inputs) == 2


def test_input_ids_do_not_collide(host_guide):
    # docs/a-b.md and docs/a/b.md share a slug; an existing input of another file holds a third
    root, _ = host_guide
    host = root.parent
    (host / "docs" / "a").mkdir()
    (host / "docs" / "a-b.md").write_text("# A-B\n")
    (host / "docs" / "a" / "b.md").write_text("# A/B\n")
    commit_all(host, "slug twins")
    other = {"id": "host-docs-install-md", "kind": "document", "location": "https://example.com/install-notes",
             "registered": "2026-04-01"}
    (root / "inputs.yaml").write_text(yaml.safe_dump({"inputs": [other]}, sort_keys=False))
    head = commit_all(host, "an input with a host-style id")
    proc = embed(root, "apply", "--plan", str(write_plan(root, head, [
        {"path": "../docs/a-b.md", "destination": "input"},
        {"path": "../docs/a/b.md", "destination": "input"},
        {"path": "../docs/install.md", "destination": "input"}])))
    assert proc.returncode == 0, proc.stderr
    items = {i.id: i.location for i in guidecfg.load_inputs(root).inputs}
    assert items == {"host-docs-install-md": "https://example.com/install-notes",
                     "host-docs-a-b-md": "../docs/a-b.md",
                     "host-docs-a-b-md-2": "../docs/a/b.md",
                     "host-docs-install-md-2": "../docs/install.md"}
    # a second apply for the same file keeps its id instead of adding another entry
    proc = embed(root, "apply", "--plan", str(write_plan(root, head, [
        {"path": "../docs/a/b.md", "destination": "input"}], name="again.yaml")))
    assert proc.returncode == 0, proc.stderr
    assert len(guidecfg.load_inputs(root).inputs) == 4


def test_apply_refuses_inline_embedded_block_before_writing(host_guide):
    root, head = host_guide
    host = root.parent
    path = root / "guide.yaml"
    path.write_text(path.read_text().replace("embedded:\n  front_page: ../README.md\n",
                                             "embedded: {front_page: ../README.md}\n"))
    commit_all(host, "inline block")
    head = host_git(host, "rev-parse", "HEAD")
    before = snapshot(host)
    plan = write_plan(root, head, DEV_ENTRIES)
    before[plan.relative_to(host).as_posix()] = plan.read_bytes()
    proc = embed(root, "apply", "--plan", str(plan))
    assert proc.returncode == 2
    assert snapshot(host) == before


DEV_ONLY = [{"path": "../README.md", "section": "Running tests", "destination": "developer"}]


@pytest.mark.parametrize("developer_readme, message", [
    ("../../OUTSIDE.md", "must lie in the host repository"),
    ("DEVELOPMENT.md", "outside the guide subdirectory"),     # host-relative by mistake
    ("../README.md", "the front page"),
    ("../USAGE.md", "a file the move plan changes"),
    ("../Makefile", "Markdown"),
])
def test_apply_refuses_bad_developer_readme(host_guide, developer_readme, message):
    root, head = host_guide
    host = root.parent
    before = snapshot(host)
    entries = DEV_ONLY + [{"path": "../USAGE.md", "destination": "input", "stub": True}]
    plan = write_plan(root, head, entries, developer_readme=developer_readme)
    before[plan.relative_to(host).as_posix()] = plan.read_bytes()
    guide_yaml = (root / "guide.yaml").read_bytes()
    proc = embed(root, "apply", "--plan", str(plan))
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert message in proc.stderr
    assert snapshot(host) == before
    assert (root / "guide.yaml").read_bytes() == guide_yaml
    assert not (host.parent / "OUTSIDE.md").exists()


def test_apply_refuses_a_stale_plan(host_guide):
    root, head = host_guide
    host = root.parent
    (host / "NOTES.txt").write_text("later\n")
    commit_all(host, "a later commit")
    before = snapshot(host)
    plan = write_plan(root, head, DEV_ENTRIES)
    before[plan.relative_to(host).as_posix()] = plan.read_bytes()
    proc = embed(root, "apply", "--plan", str(plan))
    assert proc.returncode == 2 and "moved since the inventory" in proc.stderr
    assert snapshot(host) == before


def test_stage_refuses_an_output_that_overlaps_docs(staged_guide):
    root = staged_guide
    host = root.parent
    before = snapshot(host)
    for out in (".", "..", "docs", str(host)):
        proc = embed(root, "stage", "--out", out)
        assert proc.returncode == 2, (out, proc.stdout + proc.stderr)
        assert "choose a build directory" in proc.stderr
    assert snapshot(host) == before


def test_relink_leaves_footnotes_alone():
    from embed import relink
    text = "See [notes][n].[^1]\n\n[n]: docs/notes.md\n[^1]: See the upstream notes.\n"
    out = relink(text, "", "docs")
    assert "[n]: notes.md" in out and "[^1]: See the upstream notes." in out
