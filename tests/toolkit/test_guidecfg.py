import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import guidecfg
from guidecfg import ConfigError

TOOLKIT = Path(__file__).resolve().parents[2] / "guide" / "toolkit"


def edit(path: Path, change) -> None:
    data = yaml.safe_load(path.read_text())
    change(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def test_valid_fixture_loads(render_fixture_guide, fixture_repo):
    root = render_fixture_guide
    guide = guidecfg.load_guide(root)
    assert guide.title == "minisvc guide"
    assert guide.format == "antora"
    assert [p.id for p in guide.personas] == ["admin", "user"]
    assert guide.personas[0].start == "admin/install"
    assert [s.voice for s in guide.sections] == ["concepts", "technical", "technical"]
    assert guide.rigor == "standard"
    assert guide.internal_enabled is True
    assert guide.confidential_terms == ["ACME Corp"]
    assert guide.confidential_patterns == [r"\b[A-Z]{2,}-\d+\b"]
    assert guide.drift_schedule == "off"
    assert guide.clusters["local"].kubeconfig == "~/.kube/fixture-readonly"

    baseline = guidecfg.load_baseline(root)
    assert baseline.captured == "2026-01-06"
    (src,) = baseline.sources
    assert src.id == "mini"
    assert src.commit == fixture_repo[1]
    assert src.status == "verified"
    assert src.attributes == {"version": "1.2.3"}
    assert [cr.number for cr in baseline.change_requests] == [4, 5]
    assert baseline.source("mini") is src

    inputs = guidecfg.load_inputs(root)
    assert [i.id for i in inputs.inputs] == ["walkthrough", "customer-notes"]
    assert inputs.get("customer-notes").confidential is True
    assert inputs.get("walkthrough").confidential is False


def test_unknown_key_fails(render_fixture_guide):
    edit(render_fixture_guide / "guide.yaml", lambda d: d.update(colour="blue"))
    with pytest.raises(ConfigError) as err:
        guidecfg.load_guide(render_fixture_guide)
    assert "colour" in str(err.value)


def test_unknown_nested_key_fails(render_fixture_guide):
    edit(render_fixture_guide / "baseline.yaml", lambda d: d["sources"][0].update(branch="main"))
    with pytest.raises(ConfigError) as err:
        guidecfg.load_baseline(render_fixture_guide)
    assert "sources[0].branch" in str(err.value)


def test_format_without_adapter_fails(render_fixture_guide):
    edit(render_fixture_guide / "guide.yaml", lambda d: d.update(format="hugo"))
    with pytest.raises(ConfigError) as err:
        guidecfg.load_guide(render_fixture_guide)
    assert "format" in str(err.value)


def test_format_must_match_vendored_adapter(render_fixture_guide):
    tools = render_fixture_guide / "tools" / "guide"
    tools.mkdir(parents=True)
    (tools / "adapter.yaml").write_text("format: mkdocs\n")
    with pytest.raises(ConfigError) as err:
        guidecfg.load_guide(render_fixture_guide)
    assert "adapter" in str(err.value)


def test_input_location_inside_project_rejected(render_fixture_guide):
    inside = render_fixture_guide / "notes.txt"
    inside.write_text("raw notes\n")
    edit(render_fixture_guide / "inputs.yaml",
         lambda d: d["inputs"][0].update(location=str(inside)))
    with pytest.raises(ConfigError) as err:
        guidecfg.load_inputs(render_fixture_guide)
    assert "inside the guide project" in str(err.value)


def test_relative_input_location_inside_project_rejected(render_fixture_guide):
    edit(render_fixture_guide / "inputs.yaml",
         lambda d: d["inputs"][0].update(location="raw/transcript.txt"))
    with pytest.raises(ConfigError):
        guidecfg.load_inputs(render_fixture_guide)


def test_url_input_location_allowed(render_fixture_guide):
    edit(render_fixture_guide / "inputs.yaml",
         lambda d: d["inputs"][0].update(location="https://example.com/t.txt", sha256=""))
    assert guidecfg.load_inputs(render_fixture_guide).inputs[0].location.startswith("https://")


def test_short_commit_fails(render_fixture_guide):
    edit(render_fixture_guide / "baseline.yaml", lambda d: d["sources"][0].update(commit="7ca3fb3"))
    with pytest.raises(ConfigError) as err:
        guidecfg.load_baseline(render_fixture_guide)
    assert "commit" in str(err.value)


def test_change_request_unknown_source_fails(render_fixture_guide):
    edit(render_fixture_guide / "baseline.yaml",
         lambda d: d["change_requests"][0].update(source="nope"))
    with pytest.raises(ConfigError) as err:
        guidecfg.load_baseline(render_fixture_guide)
    assert "nope" in str(err.value)


def test_disposable_defaults_to_false(render_fixture_guide):
    edit(render_fixture_guide / "guide.yaml",
         lambda d: d["clusters"].update(other={"kubeconfig": "/tmp/kc"}))
    guide = guidecfg.load_guide(render_fixture_guide)
    assert guide.clusters["other"].disposable is False
    assert guide.clusters["local"].disposable is False


def test_unquoted_off_schedule_is_off(render_fixture_guide):
    path = render_fixture_guide / "guide.yaml"
    path.write_text(path.read_text().replace('schedule: "off"', "schedule: off"))
    assert guidecfg.load_guide(render_fixture_guide).drift_schedule == "off"


def test_bad_confidential_pattern_fails(render_fixture_guide):
    edit(render_fixture_guide / "guide.yaml",
         lambda d: d["internal"].update(confidential_patterns=["[unclosed"]))
    with pytest.raises(ConfigError):
        guidecfg.load_guide(render_fixture_guide)


def test_cli_validate_reports_file_key_lines(render_fixture_guide):
    edit(render_fixture_guide / "guide.yaml", lambda d: d.update(colour="blue"))
    edit(render_fixture_guide / "baseline.yaml", lambda d: d["sources"][0].update(commit="abc"))
    proc = subprocess.run(
        [sys.executable, str(TOOLKIT / "guidecfg.py"), "validate", "--root", str(render_fixture_guide)],
        capture_output=True, text=True,
    )
    assert proc.returncode != 0
    lines = proc.stdout.splitlines() + proc.stderr.splitlines()
    assert any(line.startswith("guide.yaml:colour:") for line in lines)
    assert any(line.startswith("baseline.yaml:sources[0].commit:") for line in lines)


def test_cli_validate_ok(render_fixture_guide):
    proc = subprocess.run(
        [sys.executable, str(TOOLKIT / "guidecfg.py"), "validate", "--root", str(render_fixture_guide)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.parametrize("key,expected", [("internal.enabled", "true"), ("slug", "minisvc-guide"),
                                          ("title", "minisvc guide"), ("baseline.captured", "2026-01-06")])
def test_cli_get(render_fixture_guide, key, expected):
    proc = subprocess.run(
        [sys.executable, str(TOOLKIT / "guidecfg.py"), "get", key, "--root", str(render_fixture_guide)],
        capture_output=True, text=True, check=True,
    )
    assert proc.stdout.strip() == expected


def test_finding_schema(tmp_guide):
    good = {"id": "UF-1", "source": "mini", "kind": "doc-drift",
            "locations": [{"ref": "README.md:7", "quote": "listens on port 8080"}],
            "summary": "README states the wrong port.", "evidence": "config says 9090",
            "status": "collected"}
    assert guidecfg.check_finding(good, sources={"mini"}) == []
    bad = dict(good, kind="rant", status="posted")
    problems = guidecfg.check_finding(bad, sources={"mini"})
    assert any("kind" in p for p in problems) and any("status" in p for p in problems)
    assert guidecfg.check_finding(dict(good, source="other"), sources={"mini"})


def test_pages_by_view(tmp_guide):
    tools = tmp_guide / "tools" / "guide"
    tools.mkdir(parents=True)
    (tools / "adapter.yaml").write_text(
        "format: mkdocs\ncontent_root: docs\ninternal_root: docs/internal\n"
        "page_glob: '**/*.md'\ncomment: html\n")
    for rel in ["docs/index.md", "docs/admin/a.md", "docs/internal/n.md"]:
        p = tmp_guide / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# x\n")
    adapter = guidecfg.load_adapter(tmp_guide)
    rels = lambda view: sorted(p.relative_to(tmp_guide).as_posix() for p in guidecfg.pages(tmp_guide, adapter, view))
    assert rels("shareable") == ["docs/admin/a.md", "docs/index.md"]
    assert rels("internal") == ["docs/internal/n.md"]
    assert len(rels("all")) == 3
    assert guidecfg.is_internal(tmp_guide / "docs/internal/n.md", tmp_guide, adapter)


# --- branding (specs/002-antora-branding) ------------------------------------

ADAPTERS = Path(__file__).resolve().parents[2] / "guide" / "adapters"
BLOCK = {"logo_text": "Agent Starter Kits",
         "footer": {"text": "Agent Starter Kits on GitHub",
                    "url": "https://github.com/red-hat-data-services/agentic-starter-kits"}}


def vendor_adapter(root: Path, fmt: str) -> None:
    tools = root / "tools" / "guide"
    tools.mkdir(parents=True, exist_ok=True)
    (tools / "adapter.yaml").write_text((ADAPTERS / fmt / "adapter.yaml").read_text())


def run_cli(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOLKIT / "guidecfg.py"), *args, "--root", str(root)],
                          capture_output=True, text=True)


def test_branding_block_validates_for_antora(render_fixture_guide):
    root = render_fixture_guide
    vendor_adapter(root, "antora")
    edit(root / "guide.yaml", lambda d: d.update(branding=BLOCK))
    assert guidecfg.validate(root) == ([], [])
    assert guidecfg.load_guide(root).branding == BLOCK


@pytest.mark.parametrize("fmt", ["mkdocs", "gfm"])
def test_branding_block_fails_for_other_formats(render_fixture_guide, fmt):
    root = render_fixture_guide
    vendor_adapter(root, fmt)
    edit(root / "guide.yaml", lambda d: d.update(format=fmt, branding=BLOCK))
    problems, _ = guidecfg.validate(root)
    assert f"guide.yaml:branding.logo_text: not supported by the {fmt} adapter" in problems
    assert f"guide.yaml:branding.footer: not supported by the {fmt} adapter" in problems


def test_adapter_branding_list(tmp_guide):
    vendor_adapter(tmp_guide, "antora")
    assert guidecfg.load_adapter(tmp_guide).branding == ["logo_text", "wordmark", "logo", "logo_alt", "footer",
                                                         "favicon", "color", "theme"]
    (tmp_guide / "tools" / "guide" / "adapter.yaml").write_text("format: antora\n")
    assert guidecfg.load_adapter(tmp_guide).branding == []
    vendor_adapter(tmp_guide, "gfm")
    assert guidecfg.load_adapter(tmp_guide).branding == []


def test_invalid_branding_block_still_loads(render_fixture_guide):
    root = render_fixture_guide
    edit(root / "guide.yaml", lambda d: d.update(branding={"logo_text": "x" * 41, "logo": "nope.svg"}))
    guide = guidecfg.load_guide(root)
    assert guide.branding == {"logo_text": "x" * 41, "logo": "nope.svg"}
    proc = run_cli(root, "get", "internal.enabled")
    assert proc.returncode == 0 and proc.stdout.strip() == "true"


def test_branding_must_be_a_mapping(render_fixture_guide):
    # load_guide stays tolerant, so `get internal.enabled` works and the Makefile reaches
    # playbook.py, which stops the build (FR-010); validate reports the problem once.
    root = render_fixture_guide
    edit(root / "guide.yaml", lambda d: d.update(branding="Agent Starter Kits"))
    assert guidecfg.load_guide(root).branding is None
    proc = run_cli(root, "get", "internal.enabled")
    assert proc.returncode == 0 and proc.stdout.strip() == "true"
    problems, _ = guidecfg.validate(root)
    assert problems == ["guide.yaml:branding: must be a mapping"]


def test_guide_without_branding_validates_as_before(render_fixture_guide):
    assert guidecfg.load_guide(render_fixture_guide).branding is None
    assert guidecfg.validate(render_fixture_guide) == ([], [])
    proc = run_cli(render_fixture_guide, "validate")
    assert proc.returncode == 0
    assert proc.stdout == "guide configuration OK\n"   # the same output as before the feature


def test_cli_validate_prints_branding_problems(render_fixture_guide):
    root = render_fixture_guide
    edit(root / "guide.yaml", lambda d: d.update(branding={"logo_text": "Kits", "color": "green"}))
    proc = run_cli(root, "validate")
    assert proc.returncode == 1
    assert "guide.yaml:branding.color: must be a #rrggbb color (got green)" in proc.stdout.splitlines()


def test_cli_validate_prints_overlay_problem(render_fixture_guide, tmp_path):
    root = render_fixture_guide
    css = root / "ui" / "supplemental" / "css"
    css.mkdir(parents=True)
    (tmp_path / "outside.css").write_text("a{}\n")
    os.symlink(tmp_path / "outside.css", css / "x.css")
    proc = run_cli(root, "validate")
    assert proc.returncode == 1
    lines = proc.stdout.splitlines()
    assert any(line.startswith("ui/supplemental:css/x.css: ") for line in lines), lines
    assert not any(line.startswith("guide.yaml:ui/supplemental") for line in lines)


def test_cli_validate_prints_shadowing_warning(render_fixture_guide):
    root = render_fixture_guide
    edit(root / "guide.yaml", lambda d: d.update(branding={"logo_text": "Kits"}))
    partials = root / "ui" / "supplemental" / "partials"
    partials.mkdir(parents=True)
    (partials / "footer-content.hbs").write_text('<footer class="footer">mine</footer>\n')
    proc = run_cli(root, "validate")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ("ui/supplemental/partials/footer-content.hbs: warning: shadows the file generated for branding.footer"
            in proc.stdout.splitlines())


def run_uv_validate(root: Path) -> subprocess.CompletedProcess:
    """guidecfg.py validate in its own PEP 723 environment (pyyaml only), as guides run it."""
    return subprocess.run(["uv", "run", "--quiet", "--no-project", str(TOOLKIT / "guidecfg.py"), "validate",
                           "--root", str(root)], capture_output=True, text=True)


def test_validate_neutral_branding_with_pyyaml_only(render_fixture_guide):
    root = render_fixture_guide
    vendor_adapter(root, "antora")
    edit(root / "guide.yaml", lambda d: d.update(branding={"wordmark": "OpenClaw on OpenShift", "theme": "neutral"}))
    proc = run_uv_validate(root)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    edit(root / "guide.yaml", lambda d: d["branding"].update(theme="dark"))
    proc = run_uv_validate(root)
    assert proc.returncode == 1
    assert "guide.yaml:branding.theme: must be neutral or stock (got dark)" in proc.stdout


# --- embedded mode (specs/005-embedded-guide) --------------------------------

from conftest import FRONT_PAGE, commit_all, host_git, make_embedded_guide  # noqa: E402

SHA_A = "a" * 40


@pytest.fixture
def embedded(mini_host):
    host, commit = mini_host
    return make_embedded_guide(host, commit, front_page=FRONT_PAGE)


def set_embedded(root: Path, **values) -> None:
    edit(root / "guide.yaml", lambda d: d["embedded"].update(values))


def config_error(loader, root) -> str:
    with pytest.raises(ConfigError) as err:
        loader(root)
    return str(err.value)


def test_mini_host_fixture_is_deterministic(tmp_path):
    from conftest import build_mini_host
    _, one = build_mini_host(tmp_path / "a")
    _, two = build_mini_host(tmp_path / "b")
    assert one == two and len(one) == 40


def test_embedded_block_loads(embedded):
    guide = guidecfg.load_guide(embedded)
    emb = guide.embedded
    assert emb is not None
    assert emb.front_page.resolve() == (embedded.parent / "README.md").resolve()
    assert emb.developer_readme is None and emb.stubs == [] and emb.pr_check is False
    set_embedded(embedded, developer_readme="../DEVELOPMENT.md", stubs=["../docs/install.md"], pr_check="on")
    emb = guidecfg.load_guide(embedded).embedded
    assert emb.developer_readme.resolve() == (embedded.parent / "DEVELOPMENT.md").resolve()
    assert [p.resolve() for p in emb.stubs] == [(embedded.parent / "docs/install.md").resolve()]
    assert emb.pr_check is True


def test_standalone_guide_has_no_embedded(render_fixture_guide):
    assert guidecfg.load_guide(render_fixture_guide).embedded is None


def test_unquoted_off_pr_check(embedded):
    path = embedded / "guide.yaml"
    path.write_text(path.read_text().replace("embedded:\n", "embedded:\n  pr_check: off\n"))
    assert guidecfg.load_guide(embedded).embedded.pr_check is False


def test_embedded_unknown_key_fails(embedded):
    set_embedded(embedded, colour="blue")
    assert "embedded.colour" in config_error(guidecfg.load_guide, embedded)


@pytest.mark.parametrize("change, key", [
    (lambda d: d.update(format="mkdocs"), "format"),
    (lambda d: d["internal"].update(enabled=True), "internal.enabled"),
    (lambda d: d["internal"].update(confidential_terms=["ACME"]), "internal.confidential_terms"),
    (lambda d: d["internal"].update(confidential_patterns=["X-\\d+"]), "internal.confidential_patterns"),
])
def test_embedded_requires_gfm_without_internal_part(embedded, change, key):
    edit(embedded / "guide.yaml", change)
    assert key in config_error(guidecfg.load_guide, embedded)


@pytest.mark.parametrize("front", ["docs/front.md", "../../outside.md", "../README.txt"])
def test_front_page_location_rules(embedded, front):
    set_embedded(embedded, front_page=front)
    assert "embedded.front_page" in config_error(guidecfg.load_guide, embedded)


@pytest.mark.parametrize("key, value", [
    ("developer_readme", "DEVELOPMENT.md"),        # inside the guide root
    ("developer_readme", "../../DEVELOPMENT.md"),  # outside the host
    ("stubs", ["docs/old.md"]),
    ("stubs", ["../../old.md"]),
])
def test_developer_readme_and_stubs_location_rules(embedded, key, value):
    set_embedded(embedded, **{key: value})
    assert f"embedded.{key}" in config_error(guidecfg.load_guide, embedded)


def test_missing_front_page_fails_validate_unless_allowed(embedded):
    (embedded.parent / "README.md").unlink()
    guidecfg.load_guide(embedded)   # the schema load does not check existence
    problems, _ = guidecfg.validate(embedded)
    assert any("embedded.front_page" in p and "not found" in p for p in problems), problems
    assert guidecfg.validate(embedded, allow_missing_front_page=True) == ([], [])
    proc = run_cli(embedded, "validate", "--allow-missing-front-page")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert run_cli(embedded, "validate").returncode == 1


def test_cli_get_embedded_keys(embedded, render_fixture_guide):
    proc = run_cli(embedded, "get", "embedded.front_page")
    assert proc.returncode == 0 and proc.stdout.strip() == "../README.md"
    proc = run_cli(render_fixture_guide, "get", "embedded.front_page")
    assert proc.returncode == 0 and proc.stdout.strip() == ""
    set_embedded(embedded, developer_readme="../DEVELOPMENT.md", pr_check="on")
    assert run_cli(embedded, "get", "embedded.developer_readme").stdout.strip() == "../DEVELOPMENT.md"
    assert run_cli(embedded, "get", "embedded.pr_check").stdout.strip() == "on"


# --- discover (FR-031) ----------------------------------------------------------


def discover(path: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOLKIT / "guidecfg.py"), "discover", "--dir", str(path)],
                          capture_output=True, text=True)


def make_guide(directory: Path) -> Path:
    """A minimal guide configuration in directory (discovery only checks that guide.yaml exists)."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "guide.yaml").write_text("schema: 1\n")
    return directory


def test_discover_current_dir(embedded, render_fixture_guide):
    for root in (embedded, render_fixture_guide):
        proc = discover(root)
        assert proc.returncode == 0, proc.stderr
        assert Path(proc.stdout.strip()).resolve() == root.resolve()


def test_discover_one_embedded_subdirectory(embedded):
    proc = discover(embedded.parent)
    assert proc.returncode == 0, proc.stderr
    assert Path(proc.stdout.strip()).resolve() == embedded.resolve()
    assert guidecfg.discover(embedded.parent).resolve() == embedded.resolve()


def test_discover_several_exits_3(embedded):
    shutil.copytree(embedded, embedded.parent / "guide2")
    proc = discover(embedded.parent)
    assert proc.returncode == 3
    assert proc.stdout.splitlines() == sorted(str(p.resolve()) for p in (embedded, embedded.parent / "guide2"))
    assert "several guide projects" in proc.stderr


def test_discover_nested_standalone_guide(tmp_path, render_fixture_guide):
    """A standalone guide at docs/guide is found from the root and is not embedded (US1, FR-008)."""
    root = tmp_path / "repo"
    found = root / "docs" / "guide"
    shutil.copytree(render_fixture_guide, found)
    proc = discover(root)
    assert proc.returncode == 0, proc.stderr
    assert Path(proc.stdout.strip()) == found.resolve()
    assert guidecfg.discover(root).resolve() == found.resolve()
    proc = run_cli(found, "get", "embedded.front_page")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "\n"


def test_discover_depth_three(tmp_path):
    root = tmp_path / "repo"
    found = make_guide(root / "docs" / "user" / "guide")
    proc = discover(root)
    assert proc.returncode == 0, proc.stderr
    assert Path(proc.stdout.strip()) == found.resolve()


def test_discover_self_wins_over_nested(tmp_path):
    root = make_guide(tmp_path / "repo")
    make_guide(root / "docs" / "guide")
    proc = discover(root)
    assert proc.returncode == 0, proc.stderr
    assert Path(proc.stdout.strip()) == root.resolve()
    assert guidecfg.discover(root) == root


def test_discover_shallower_wins(tmp_path):
    root = tmp_path / "repo"
    shallow = make_guide(root / "guide")
    make_guide(root / "docs" / "guide")
    proc = discover(root)
    assert proc.returncode == 0, proc.stderr
    assert Path(proc.stdout.strip()) == shallow.resolve()
    assert guidecfg.discover(root) == shallow


def test_discover_tie_exits_3_sorted(tmp_path):
    """Equally shallow guides stop discovery; only they are listed, sorted (US2, FR-004)."""
    root = tmp_path / "repo"
    site = make_guide(root / "site" / "guide")
    docs = make_guide(root / "docs" / "guide")
    make_guide(root / "a" / "b" / "guide")   # deeper: never reported
    proc = discover(root)
    assert proc.returncode == 3
    expected = sorted(str(p.resolve()) for p in (docs, site))
    assert proc.stdout.splitlines() == expected
    assert "several guide projects" in proc.stderr
    with pytest.raises(guidecfg.DiscoverError) as err:
        guidecfg.discover(root)
    assert err.value.code == 3
    assert [str(p.resolve()) for p in err.value.candidates] == expected


def test_discover_standalone_immediate_subdirectory(embedded):
    """A standalone guide in an immediate subdirectory is found now and is not embedded (US3, FR-003)."""
    proc = run_cli(embedded, "get", "embedded.front_page")
    assert proc.returncode == 0 and proc.stdout.strip() != ""   # the unmodified fixture is embedded
    edit(embedded / "guide.yaml", lambda d: d.pop("embedded"))
    proc = discover(embedded.parent)
    assert proc.returncode == 0, proc.stderr
    assert Path(proc.stdout.strip()) == embedded.resolve()
    assert guidecfg.discover(embedded.parent).resolve() == embedded.resolve()
    proc = run_cli(embedded, "get", "embedded.front_page")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "\n"


def test_discover_embedded_at_depth_two(tmp_path, embedded):
    """An embedded guide deeper than depth 1 is found; its status comes from the configuration."""
    root = tmp_path / "repo"
    found = root / "docs" / "guide"
    shutil.copytree(embedded, found)
    proc = discover(root)
    assert proc.returncode == 0, proc.stderr
    assert Path(proc.stdout.strip()) == found.resolve()
    # the embedded block travels with the configuration, wherever discovery found it (FR-008)
    data = yaml.safe_load((found / "guide.yaml").read_text())
    assert isinstance(data, dict) and "embedded" in data


@pytest.mark.parametrize("inside", [".guide/cache/x", ".git/x", "node_modules/x", "build/x", "dist/x",
                                    "target/x", "docs/node_modules/x"])
def test_discover_pruned_inside(tmp_path, inside):
    """A guide configuration only inside a pruned directory is never found (US4, FR-005)."""
    root = tmp_path / "repo"
    make_guide(root / inside)
    proc = discover(root)
    assert proc.returncode == 4, proc.stdout
    assert proc.stdout == ""


def test_discover_pruning_is_exact(tmp_path):
    """Only the exact pruned names are skipped: Build and node_modules_old are searched."""
    for name in ("Build", "node_modules_old"):
        root = tmp_path / f"repo-{name}"
        found = make_guide(root / name)
        proc = discover(root)
        assert proc.returncode == 0, proc.stderr
        assert Path(proc.stdout.strip()) == found.resolve()


def test_discover_pruned_dirs_are_not_candidates(tmp_path):
    """Hidden, pruned-name, and symlinked directories are no candidates themselves (US4 AS2, AS4)."""
    root = tmp_path / "repo"
    make_guide(root / ".docs")
    make_guide(root / "build")
    (root / "shared").symlink_to(make_guide(tmp_path / "elsewhere" / "g"), target_is_directory=True)
    proc = discover(root)
    assert proc.returncode == 4, proc.stdout
    # a symlinked directory is not entered either
    other = tmp_path / "repo2"
    other.mkdir()
    make_guide(tmp_path / "outside" / "guide")
    (other / "link").symlink_to(tmp_path / "outside", target_is_directory=True)
    proc = discover(other)
    assert proc.returncode == 4, proc.stdout


def test_discover_not_below_a_guide(tmp_path):
    """A guide's own nested configurations never compete with it (US4 AS3, FR-006)."""
    root = tmp_path / "repo"
    found = make_guide(root / "docs" / "guide")
    make_guide(root / "docs" / "guide" / "examples")
    proc = discover(root)
    assert proc.returncode == 0, proc.stderr
    assert Path(proc.stdout.strip()) == found.resolve()


def test_discover_depth_four_not_found(tmp_path):
    root = tmp_path / "repo"
    make_guide(root / "a" / "b" / "c" / "guide")
    proc = discover(root)
    assert proc.returncode == 4
    assert proc.stdout == ""
    assert "or the directories below it (up to 3 levels)" in proc.stderr


def test_discover_guide_yaml_entry_kinds(tmp_path):
    """Only a regular file (or a symlink to one) named guide.yaml marks a candidate (FR-002)."""
    as_dir = tmp_path / "dir-case"
    (as_dir / "x" / "guide.yaml").mkdir(parents=True)
    assert discover(as_dir).returncode == 4

    as_link = tmp_path / "link-case"
    (as_link / "y").mkdir(parents=True)
    real = tmp_path / "real-guide.yaml"
    real.write_text("schema: 1\n")
    (as_link / "y" / "guide.yaml").symlink_to(real)
    proc = discover(as_link)
    assert proc.returncode == 0, proc.stderr
    assert Path(proc.stdout.strip()) == (as_link / "y").resolve()

    invalid = tmp_path / "invalid-case"
    (invalid / "z").mkdir(parents=True)
    (invalid / "z" / "guide.yaml").write_text("a: [")   # discovery does not parse the file
    proc = discover(invalid)
    assert proc.returncode == 0, proc.stderr
    assert Path(proc.stdout.strip()) == (invalid / "z").resolve()


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads directories regardless of their mode")
@pytest.mark.parametrize("mode", [0o000, 0o111])
def test_discover_unreadable_directory_skipped(tmp_path, mode):
    """A directory that cannot be read is skipped without failing the search (FR-007).

    0o111 lets a lookup of guide.yaml succeed but forbids listing: such a directory is
    still unreadable and must not shadow the readable guide deeper in the tree.
    """
    root = tmp_path / "repo"
    found = make_guide(root / "docs" / "guide")
    locked = make_guide(root / "locked")
    locked.chmod(mode)
    try:
        proc = discover(root)
        assert proc.returncode == 0, proc.stderr
        assert Path(proc.stdout.strip()) == found.resolve()
    finally:
        locked.chmod(0o755)


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads directories regardless of their mode")
def test_discover_unlistable_dir_exits_4(tmp_path):
    """DIR that can be entered but not listed: no traceback, exit 4 (FR-007)."""
    root = tmp_path / "repo"
    make_guide(root / "docs" / "guide")
    root.chmod(0o111)
    try:
        proc = discover(root)
    finally:
        root.chmod(0o755)
    assert proc.returncode == 4, proc.stderr
    assert proc.stdout == ""
    assert "Traceback" not in proc.stderr


def test_discover_does_not_list_pruned_trees(tmp_path, monkeypatch):
    """A pruned tree is never listed, so pruned trees add no work (SC-004)."""
    root = tmp_path / "repo"
    found = make_guide(root / "docs" / "guide")
    modules = root / "node_modules"
    make_guide(modules / "pkg")   # readable: only name pruning keeps discovery out of it
    listed: list[Path] = []
    real_scandir = os.scandir

    def recording_scandir(path):
        listed.append(Path(path))
        return real_scandir(path)

    monkeypatch.setattr(guidecfg.os, "scandir", recording_scandir)
    assert guidecfg.discover(root) == found
    monkeypatch.undo()
    assert listed, "discover lists directories with os.scandir"
    assert not [p for p in listed if p == modules or modules in p.parents], listed


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads directories regardless of their mode")
def test_discover_unreadable_pruned_tree_changes_nothing(tmp_path):
    """With a node_modules tree that cannot be read, discovery succeeds as without it (SC-004).

    This guards against a crash only; test_discover_does_not_list_pruned_trees shows that
    name pruning is what keeps discovery out of the tree.
    """
    root = tmp_path / "repo"
    found = make_guide(root / "docs" / "guide")
    modules = root / "node_modules"
    modules.mkdir()
    modules.chmod(0o000)
    try:
        proc = discover(root)
    finally:
        modules.chmod(0o755)
    assert proc.returncode == 0, proc.stderr
    assert Path(proc.stdout.strip()) == found.resolve()


def test_discover_none_exits_4(tmp_path):
    for target in (tmp_path / "nothing-here", tmp_path / "empty", tmp_path / "a-file"):
        if target.name == "empty":
            target.mkdir()
        elif target.name == "a-file":
            target.write_text("x")
        proc = discover(target)
        assert proc.returncode == 4, proc.stderr
        assert proc.stdout == ""
        assert f"no guide project in {target}" in proc.stderr


# --- confidential.local.yaml (FR-006, research R9) ------------------------------------


def write_local(root: Path, data: dict) -> None:
    (root / "confidential.local.yaml").write_text(yaml.safe_dump(data, sort_keys=False))


def test_local_confidential_terms_merge(embedded):
    assert guidecfg.load_guide(embedded).confidential_terms == []
    write_local(embedded, {"confidential_terms": ["ACME Corp"], "confidential_patterns": ["\\bACME-\\d+\\b"]})
    guide = guidecfg.load_guide(embedded)
    assert guide.confidential_terms == ["ACME Corp"]
    assert guide.confidential_patterns == ["\\bACME-\\d+\\b"]


def test_local_confidential_bad_regex_names_file(embedded):
    write_local(embedded, {"confidential_patterns": ["[unclosed"]})
    message = config_error(guidecfg.load_guide, embedded)
    assert "confidential.local.yaml" in message and "invalid regex" in message


def test_local_input_location_resolves(embedded, tmp_path):
    notes = tmp_path / "secret-notes.txt"
    notes.write_text("notes\n")
    write_local(embedded, {"inputs": {"call-1": str(notes)}})
    (embedded / "inputs.yaml").write_text(yaml.safe_dump({"inputs": [
        {"id": "call-1", "kind": "notes", "location": "local:call-1", "confidential": True}]}))
    item = guidecfg.load_inputs(embedded).get("call-1")
    assert item.path(embedded) == notes
    write_local(embedded, {"inputs": {}})
    message = config_error(guidecfg.load_inputs, embedded)
    assert "local:call-1" in message and "confidential.local.yaml" in message
    # without the git-ignored file (a fresh clone, CI) the input loads unresolved
    (embedded / "confidential.local.yaml").unlink()
    item = guidecfg.load_inputs(embedded).get("call-1")
    assert item.resolved == "" and item.path(embedded) is None


# --- baseline `self` and inputs `self:` (data-model.md) --------------------------------


def test_self_source_with_fingerprints_loads(embedded):
    edit(embedded / "baseline.yaml", lambda d: d["sources"][0].update(
        web="https://github.com/acme/mini-host", front_page_blob=SHA_A,
        fingerprints={"src/cli.py": "b" * 40}))
    src = guidecfg.load_baseline(embedded).source("self")
    assert src.web == "https://github.com/acme/mini-host"
    assert src.fingerprints == {"src/cli.py": "b" * 40}
    assert src.front_page_blob == SHA_A


def test_self_source_only_in_embedded_guides(embedded):
    edit(embedded / "guide.yaml", lambda d: d.pop("embedded"))
    assert "self" in config_error(guidecfg.load_baseline, embedded)


def test_self_source_at_most_once(embedded):
    edit(embedded / "baseline.yaml", lambda d: d["sources"].append(dict(d["sources"][0])))
    assert "self" in config_error(guidecfg.load_baseline, embedded)


@pytest.mark.parametrize("values, key", [
    ({"fingerprints": {"src/cli.py": "abc"}}, "fingerprints"),
    ({"front_page_blob": "xyz"}, "front_page_blob"),
])
def test_self_fingerprint_values(embedded, values, key):
    edit(embedded / "baseline.yaml", lambda d: d["sources"][0].update(values))
    assert key in config_error(guidecfg.load_baseline, embedded)


def test_fingerprints_only_on_self(embedded, fixture_repo):
    repo, first, _, _ = fixture_repo
    edit(embedded / "baseline.yaml", lambda d: d["sources"].append(
        {"id": "mini", "repo": repo.as_uri(), "commit": first, "fingerprints": {"x": "b" * 40}}))
    assert "fingerprints" in config_error(guidecfg.load_baseline, embedded)


def test_self_input_requires_revision_and_blob(embedded):
    entry = {"id": "host-readme", "kind": "document", "location": "self:README.md",
             "revision": SHA_A, "blob": "b" * 40}
    (embedded / "inputs.yaml").write_text(yaml.safe_dump({"inputs": [entry]}))
    item = guidecfg.load_inputs(embedded).get("host-readme")
    assert item.revision == SHA_A and item.blob == "b" * 40
    assert item.path(embedded) is None
    for missing in ("revision", "blob"):
        bad = {k: v for k, v in entry.items() if k != missing}
        (embedded / "inputs.yaml").write_text(yaml.safe_dump({"inputs": [bad]}))
        assert missing in config_error(guidecfg.load_inputs, embedded)


def test_self_input_path_inside_guide_is_not_refused(embedded):
    entry = {"id": "pointer", "kind": "document", "location": "self:guide/docs/README.md",
             "revision": SHA_A, "blob": "b" * 40}
    (embedded / "inputs.yaml").write_text(yaml.safe_dump({"inputs": [entry]}))
    assert guidecfg.load_inputs(embedded).get("pointer") is not None


def test_local_input_only_in_embedded_guides(embedded, tmp_path):
    write_local(embedded, {"inputs": {"call-1": str(tmp_path / "n.txt")}})
    (embedded / "inputs.yaml").write_text(yaml.safe_dump({"inputs": [
        {"id": "call-1", "kind": "notes", "location": "local:call-1"}]}))
    guidecfg.load_inputs(embedded)
    edit(embedded / "guide.yaml", lambda d: d.pop("embedded"))
    assert "local:" in config_error(guidecfg.load_inputs, embedded)



def test_confidential_input_of_embedded_guide_must_be_local(embedded, tmp_path):
    # FR-006: inputs.yaml is committed, so a confidential input never names its location there
    (embedded / "inputs.yaml").write_text(yaml.safe_dump({"inputs": [
        {"id": "call-1", "kind": "notes", "location": str(tmp_path / "acme-call.txt"), "confidential": True}]}))
    message = config_error(guidecfg.load_inputs, embedded)
    assert "local:<id>" in message and "confidential.local.yaml" in message
    edit(embedded / "guide.yaml", lambda d: d.pop("embedded"))
    guidecfg.load_inputs(embedded)   # a separate guide keeps confidential locations as today


# --- pages() with the front page --------------------------------------------------


def test_pages_include_front_page_only_when_embedded(embedded):
    adapter = guidecfg.load_adapter(embedded)
    front = (embedded.parent / "README.md").resolve()
    assert front in [p.resolve() for p in guidecfg.pages(embedded, adapter, "all")]
    assert front in [p.resolve() for p in guidecfg.pages(embedded, adapter, "shareable")]
    assert front not in [p.resolve() for p in guidecfg.pages(embedded, adapter, "internal")]
    edit(embedded / "guide.yaml", lambda d: d.pop("embedded"))
    assert front not in [p.resolve() for p in guidecfg.pages(embedded, adapter, "all")]


def test_helpers(embedded):
    host = embedded.parent
    assert guidecfg.host_toplevel(embedded).resolve() == host.resolve()
    assert guidecfg.host_toplevel(Path("/")) is None
    assert guidecfg.embedded_front_page(embedded).resolve() == (host / "README.md").resolve()
    (embedded / "guide.yaml").unlink()
    assert guidecfg.embedded_front_page(embedded) is None


def test_is_guide_owned(embedded):
    set_embedded(embedded, developer_readme="../DEVELOPMENT.md", stubs=["../docs/install.md"])
    owned = lambda p: guidecfg.is_guide_owned(embedded, p)
    assert owned("guide/docs/admin/install.md") and owned("guide/guide.yaml")
    assert owned("README.md") and owned("DEVELOPMENT.md") and owned("docs/install.md")
    assert not owned("src/cli.py") and not owned("USAGE.md") and not owned("guidebook.md")



def test_developer_readme_need_not_be_markdown(embedded):
    set_embedded(embedded, developer_readme="../HACKING.txt")
    assert guidecfg.load_guide(embedded).embedded.developer_readme.name == "HACKING.txt"


def test_local_confidential_file_ignored_by_separate_guides(render_fixture_guide):
    write_local(render_fixture_guide, {"confidential_terms": ["Stray Term"], "confidential_patterns": ["[bad"]})
    guide = guidecfg.load_guide(render_fixture_guide)
    assert "Stray Term" not in guide.confidential_terms


def test_discover_empty_directory_means_a_new_separate_guide(tmp_path):
    """create on an empty directory follows the standalone flow: discover finds nothing (exit 4)."""
    target = tmp_path / "new-guide"
    target.mkdir()
    proc = discover(target)
    assert proc.returncode == 4 and proc.stdout == ""
    with pytest.raises(guidecfg.DiscoverError) as err:
        guidecfg.discover(target)
    assert err.value.code == 4


# --- publish block (specs/006-author-owned-front-page-region) -----------------------


def make_gfm_guide(root: Path) -> Path:
    """A minimal standalone gfm guide with one docs page and a baseline."""
    vendor_adapter(root, "gfm")
    (root / "guide.yaml").write_text(yaml.safe_dump({
        "schema": 1, "title": "Pub Guide", "format": "gfm",
        "personas": [{"id": "admin", "title": "Administrator", "start": "docs/intro"}],
        "sections": [{"id": "overview", "title": "Overview", "voice": "concepts"}],
    }, sort_keys=False))
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "intro.md").write_text("# Intro\n")
    (root / "baseline.yaml").write_text(yaml.safe_dump(
        {"captured": "2026-11-09", "sources": [{"id": "mini", "repo": "example/mini",
                                                "commit": "a" * 40}]}, sort_keys=False))
    return root


def set_publish(root: Path, **values) -> None:
    edit(root / "guide.yaml", lambda d: d.update(publish=values))


def test_publish_block_loads(tmp_guide):
    root = make_gfm_guide(tmp_guide)
    set_publish(root, page="docs/intro.md", target="../README.md")
    guide = guidecfg.load_guide(root)
    assert guide.publish is not None
    assert guide.publish.page == (root / "docs" / "intro.md").resolve()
    assert guide.publish.target == (root.parent / "README.md").resolve()
    problems, _ = guidecfg.validate(root)
    assert problems == [], problems


def test_guide_without_publish_block_loads_as_before(tmp_guide):
    root = make_gfm_guide(tmp_guide)
    assert guidecfg.load_guide(root).publish is None
    assert guidecfg.validate(root) == ([], [])


@pytest.mark.parametrize("values, key", [
    ({"page": "docs/intro.md"}, "publish.target"),            # missing key
    ({"target": "../README.md"}, "publish.page"),             # missing key
    ({"page": "", "target": "../README.md"}, "publish.page"),  # empty value
    ({"page": "docs/intro.md", "target": "../README.md", "style": "fancy"}, "publish.style"),
])
def test_publish_block_rejects_bad_keys(tmp_guide, values, key):
    root = make_gfm_guide(tmp_guide)
    set_publish(root, **values)
    assert key in config_error(guidecfg.load_guide, root)


def test_publish_page_must_stay_inside_the_content_root(tmp_guide):
    root = make_gfm_guide(tmp_guide)
    set_publish(root, page="README.md", target="../README.md")
    assert "publish.page" in config_error(guidecfg.load_guide, root)


def test_publish_target_must_leave_the_content_root(tmp_guide):
    root = make_gfm_guide(tmp_guide)
    set_publish(root, page="docs/intro.md", target="docs/README.md")
    assert "publish.target" in config_error(guidecfg.load_guide, root)


@pytest.mark.parametrize("fmt", ["antora", "mkdocs"])
def test_publish_requires_the_gfm_format(tmp_guide, fmt):
    root = make_gfm_guide(tmp_guide)
    vendor_adapter(root, fmt)
    edit(root / "guide.yaml", lambda d: d.update(format=fmt))
    set_publish(root, page="docs/intro.md", target="../README.md")
    assert "gfm" in config_error(guidecfg.load_guide, root)


def test_publish_page_existence_checked_by_validate_only(tmp_guide):
    root = make_gfm_guide(tmp_guide)
    set_publish(root, page="docs/gone.md", target="../README.md")
    assert guidecfg.load_guide(root).publish is not None   # load stays tolerant
    problems, _ = guidecfg.validate(root)
    assert "guide.yaml:publish.page: docs/gone.md not found" in problems, problems



# --- pages block (brainstorm/08-pages-deploy) ---------------------------------------


def set_pages(root: Path, **values) -> None:
    edit(root / "guide.yaml", lambda d: d.update(pages=values))


def antora_guide(root: Path) -> Path:
    root = make_gfm_guide(root)
    vendor_adapter(root, "antora")
    edit(root / "guide.yaml", lambda d: d.update(format="antora"))
    return root


def test_pages_block_loads(tmp_guide):
    root = antora_guide(tmp_guide)
    set_pages(root, enabled=True, url="https://rhuss.github.io/my-guide/")
    g = guidecfg.load_guide(root)
    assert g.pages == guidecfg.Pages(enabled=True, url="https://rhuss.github.io/my-guide/")


def test_guide_without_pages_block(tmp_guide):
    assert guidecfg.load_guide(antora_guide(tmp_guide)).pages is None


@pytest.mark.parametrize("values, key", [
    ({"enabled": "yes"}, "pages.enabled"),
    ({"enabled": True, "url": "http://x.github.io/r/"}, "pages.url"),
    ({"enabled": True, "url": "https://x.github.io/r"}, "pages.url"),
    ({"enabled": True, "url": 42}, "pages.url"),
    ({"enabled": True, "branch": "gh-pages"}, "pages.branch"),
])
def test_pages_block_rejects_bad_values(tmp_guide, values, key):
    root = antora_guide(tmp_guide)
    set_pages(root, **values)
    assert key in config_error(guidecfg.load_guide, root)


def test_pages_rejected_for_gfm(tmp_guide):
    root = make_gfm_guide(tmp_guide)
    set_pages(root, enabled=True)
    msg = config_error(guidecfg.load_guide, root)
    assert "pages" in msg and "antora or mkdocs" in msg


def test_pages_enabled_without_url_is_valid(tmp_guide):   # no remote yet
    root = antora_guide(tmp_guide)
    set_pages(root, enabled=True)
    assert guidecfg.load_guide(root).pages == guidecfg.Pages(enabled=True, url="")


def test_get_pages_keys(tmp_guide):
    root = antora_guide(tmp_guide)
    assert guidecfg.GET_KEYS["pages.enabled"](guidecfg.load_guide(root)) == "false"
    assert guidecfg.GET_KEYS["pages.url"](guidecfg.load_guide(root)) == ""
    set_pages(root, enabled=True, url="https://o.github.io/r/")
    g = guidecfg.load_guide(root)
    assert guidecfg.GET_KEYS["pages.enabled"](g) == "true"
    assert guidecfg.GET_KEYS["pages.url"](g) == "https://o.github.io/r/"


def test_visual_source_id_reserved(render_fixture_guide):
    """visual:<name> cites a captured visual, so no baseline source may be called visual (FR-026)."""
    def add(d):
        d["sources"].append(dict(d["sources"][0], id="visual"))
    edit(render_fixture_guide / "baseline.yaml", add)
    with pytest.raises(ConfigError) as err:
        guidecfg.load_baseline(render_fixture_guide)
    assert "the source id 'visual' is reserved for visual citations" in str(err.value) + " ".join(err.value.lines())
