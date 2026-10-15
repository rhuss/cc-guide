import os
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
