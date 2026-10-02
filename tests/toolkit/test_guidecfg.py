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
