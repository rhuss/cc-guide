import shlex
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import attrs
import guidecfg

TOOLKIT = Path(__file__).resolve().parents[2] / "guide" / "toolkit"


def test_values(render_fixture_guide, fixture_repo):
    baseline = guidecfg.load_baseline(render_fixture_guide)
    v = attrs.values(baseline)
    first = fixture_repo[1]
    assert v["mini-commit"] == first
    assert v["mini-commit-short"] == first[:7]
    assert v["mini-repo"] == fixture_repo[0].as_uri()
    assert v["mini-blob"] == f"{fixture_repo[0].as_uri()}/blob/{first}"
    assert v["mini-tree"] == f"{fixture_repo[0].as_uri()}/tree/{first}"
    assert v["mini-version"] == "1.2.3"
    assert v["baseline-date"] == "2026-01-06"
    assert v["baseline-sources"] == f"mini {first[:7]}"


def test_github_shorthand_expands(tmp_guide):
    (tmp_guide / "baseline.yaml").write_text(yaml.safe_dump({
        "captured": "2026-09-30",
        "sources": [{"id": "saw", "repo": "validatedpatterns-sandbox/secure-agent-workspace.git",
                     "commit": "c84103d7eeb502a01930163d422051d5beb63432"}],
    }))
    v = attrs.values(guidecfg.load_baseline(tmp_guide))
    assert v["saw-repo"] == "https://github.com/validatedpatterns-sandbox/secure-agent-workspace"
    assert v["saw-blob"].endswith("/blob/c84103d7eeb502a01930163d422051d5beb63432")


def test_export_antora_every_source(render_fixture_guide):
    baseline = guidecfg.load_baseline(render_fixture_guide)
    tokens = attrs.export(baseline, "antora")
    pairs = dict(tokens[i + 1].split("=", 1) for i in range(0, len(tokens), 2))
    assert all(tokens[i] == "--attribute" for i in range(0, len(tokens), 2))
    for name in ("mini-commit", "mini-commit-short", "mini-blob", "mini-tree", "mini-repo",
                 "mini-version", "baseline-date"):
        assert name in pairs


def test_export_is_stable_and_shell_safe(render_fixture_guide):
    path = render_fixture_guide / "baseline.yaml"
    data = yaml.safe_load(path.read_text())
    data["sources"][0]["attributes"]["product"] = "minisvc's $HOME `x` service"
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    baseline = guidecfg.load_baseline(render_fixture_guide)
    assert attrs.export(baseline, "antora") == attrs.export(baseline, "antora")
    proc = subprocess.run([sys.executable, str(TOOLKIT / "attrs.py"), "export", "--format", "antora",
                           "--root", str(render_fixture_guide)], capture_output=True, text=True, check=True)
    parsed = shlex.split(proc.stdout)
    assert "mini-product=minisvc's $HOME `x` service" in parsed
    assert parsed == attrs.export(baseline, "antora")


REGION_PAGE = (
    "# Install\n\n"
    "Check out commit <!-- guide:attr mini-commit-short -->0000000<!-- /guide:attr --> "
    "of version <!-- guide:attr mini-version -->0.0.0<!-- /guide:attr -->.\n"
)


def test_regions_rewrite_and_idempotent(render_fixture_guide, fixture_repo):
    root = render_fixture_guide
    page = root / "docs" / "admin" / "install.md"
    page.parent.mkdir(parents=True)
    page.write_text(REGION_PAGE)
    baseline = guidecfg.load_baseline(root)

    stale = attrs.regions(root, baseline, write=False)
    assert [(c.name, c.line) for c in stale] == [("mini-commit-short", 3), ("mini-version", 3)]
    assert page.read_text() == REGION_PAGE  # not written without write=True

    changed = attrs.regions(root, baseline, write=True)
    assert len(changed) == 2
    text = page.read_text()
    assert f"<!-- guide:attr mini-commit-short -->{fixture_repo[1][:7]}<!-- /guide:attr -->" in text
    assert "<!-- guide:attr mini-version -->1.2.3<!-- /guide:attr -->" in text
    assert attrs.regions(root, baseline, write=True) == []
    assert page.read_text() == text


def test_regions_unknown_name_fails_without_writing(render_fixture_guide):
    root = render_fixture_guide
    page = root / "docs" / "index.md"
    page.parent.mkdir(parents=True)
    original = REGION_PAGE + "<!-- guide:attr mini-nope -->x<!-- /guide:attr -->\n"
    page.write_text(original)
    with pytest.raises(attrs.RegionError) as err:
        attrs.regions(root, guidecfg.load_baseline(root), write=True)
    assert "mini-nope" in str(err.value)
    assert page.read_text() == original


def test_regions_cli(render_fixture_guide):
    root = render_fixture_guide
    (root / "docs").mkdir()
    (root / "docs" / "index.md").write_text(REGION_PAGE)
    cmd = [sys.executable, str(TOOLKIT / "attrs.py"), "regions", "--root", str(root), "docs"]
    assert subprocess.run(cmd, capture_output=True, text=True).returncode == 1
    write = subprocess.run(cmd[:3] + ["--write"] + cmd[3:], capture_output=True, text=True)
    assert write.returncode == 0, write.stderr
    ok = subprocess.run(cmd, capture_output=True, text=True)
    assert ok.returncode == 0 and "up to date" in ok.stdout
    (root / "docs" / "bad.md").write_text("<!-- guide:attr nope -->x<!-- /guide:attr -->\n")
    bad = subprocess.run(cmd, capture_output=True, text=True)
    assert bad.returncode == 1 and "nope" in bad.stderr


def test_regions_stop_on_branding_block(render_fixture_guide):
    # FR-009, FR-010: the gfm build runs `attrs.py regions --write` first; a branding block
    # (which the gfm adapter does not support) stops it before any page is rewritten.
    root = render_fixture_guide
    tools = root / "tools" / "guide"
    tools.mkdir(parents=True)
    adapters = Path(__file__).resolve().parents[2] / "guide" / "adapters"
    (tools / "adapter.yaml").write_text((adapters / "gfm" / "adapter.yaml").read_text())
    data = yaml.safe_load((root / "guide.yaml").read_text())
    data.update(format="gfm", branding={"logo_text": "Kits"})
    (root / "guide.yaml").write_text(yaml.safe_dump(data, sort_keys=False))
    (root / "docs").mkdir()
    page = root / "docs" / "index.md"
    page.write_text(REGION_PAGE)
    proc = subprocess.run([sys.executable, str(TOOLKIT / "attrs.py"), "regions", "--write", "--root", str(root),
                           "docs"], capture_output=True, text=True)
    assert proc.returncode == 1
    assert "guide.yaml:branding.logo_text: not supported by the gfm adapter" in proc.stderr
    assert page.read_text() == REGION_PAGE
