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
    out = proc.stdout + proc.stderr
    assert "guide2" in out and str(embedded.name) in out


def test_discover_none_exits_4(tmp_path, embedded):
    assert discover(tmp_path / "nothing-here").returncode == 4
    (tmp_path / "empty").mkdir()
    assert discover(tmp_path / "empty").returncode == 4
    # a subdirectory with a non-embedded guide.yaml is not an embedded guide
    edit(embedded / "guide.yaml", lambda d: d.pop("embedded"))
    assert discover(embedded.parent).returncode == 4


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
