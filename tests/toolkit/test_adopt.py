import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import adopt
import guidecfg

REPO = Path(__file__).resolve().parents[2]
TOOLKIT = REPO / "guide" / "toolkit"
SAW = REPO / "tests" / "fixtures" / "saw-baseline.yaml"
MAP = REPO / "guide" / "templates" / "adopt-map.example.yaml"


@pytest.fixture
def saw_root(tmp_path):
    root = tmp_path / "saw-guide"
    root.mkdir()
    shutil.copy(SAW, root / "baseline.yaml")
    return root


def test_migrate_saw_baseline(saw_root):
    baseline = adopt.migrate(saw_root, MAP)
    assert baseline.captured == "2026-09-30"
    assert [s.id for s in baseline.sources] == ["saw", "openshell", "openshell-main"]
    saw = baseline.source("saw")
    assert saw.repo == "https://github.com/validatedpatterns-sandbox/secure-agent-workspace"
    assert saw.commit == "c84103d7eeb502a01930163d422051d5beb63432"
    assert saw.ref == "main"
    assert saw.attributes == {"openshell-version": "0.0.116-rhaiv.0"}
    assert baseline.source("openshell").commit == "d1155aa70042d3e2ee49dbfa15346b108b7c1d92"
    assert baseline.source("openshell").ref == "v0.0.116"
    assert baseline.source("openshell-main").commit == "252882f37f2daa63ef4078b3bbb89adbcf43b409"
    assert baseline.source("openshell-main").attributes == {"latest-tag": "v0.1.2"}

    crs = baseline.change_requests
    assert [c.number for c in crs] == [33, 37, 52, 53, 55, 56]
    assert {c.source for c in crs} == {"saw"}
    assert {c.state for c in crs} == {"open"} and {c.tier for c in crs} == {"in-review"}
    assert baseline.change_request(56).anchor == "openshell-upgrade"
    assert baseline.change_request(56).head == "e9f78b05a4a1bf7ad2c294b03374d439b1413226"
    assert baseline.change_request(33).anchor == "rhdh-portal"

    assert (saw_root / "baseline.foreign.yaml").read_text() == SAW.read_text()
    # the written file is a valid cc-guide baseline
    assert guidecfg.load_baseline(saw_root).sources[0].id == "saw"


def test_migrate_twice_refused(saw_root):
    adopt.migrate(saw_root, MAP)
    with pytest.raises(adopt.AdoptError, match="already"):
        adopt.migrate(saw_root, MAP)


def test_bad_map_leaves_baseline_untouched(saw_root, tmp_path):
    bad = yaml.safe_load(MAP.read_text())
    bad["sources"][0]["commit"] = ".saw.no_such_key"
    path = tmp_path / "bad-map.yaml"
    path.write_text(yaml.safe_dump(bad))
    with pytest.raises(adopt.AdoptError, match="saw.no_such_key"):
        adopt.migrate(saw_root, path)
    assert (saw_root / "baseline.yaml").read_text() == SAW.read_text()
    assert not (saw_root / "baseline.foreign.yaml").exists()


def test_invalid_result_restores_original(saw_root, tmp_path):
    bad = yaml.safe_load(MAP.read_text())
    bad["sources"][0]["commit"] = "c84103d"  # short SHA: guidecfg rejects it
    path = tmp_path / "short-map.yaml"
    path.write_text(yaml.safe_dump(bad))
    with pytest.raises(adopt.AdoptError, match="commit"):
        adopt.migrate(saw_root, path)
    assert (saw_root / "baseline.yaml").read_text() == SAW.read_text()
    assert not (saw_root / "baseline.foreign.yaml").exists()


def test_value_forms():
    doc = {"a": {"b": [{"n": 1}, {"n": 2}]}, "top": "x"}
    assert adopt.resolve(".a.b[1].n", doc) == 2
    assert adopt.resolve("literal", doc) == "literal"
    assert adopt.resolve({"value": ".dot"}, doc) == ".dot"
    assert adopt.resolve({"path": ".a.missing", "default": "d"}, doc) == "d"
    assert adopt.resolve({"by": ".n", "map": {1: "one"}}, doc, item={"n": 1}) == "one"
    assert adopt.resolve({"by": ".n", "map": {"2": "two"}}, doc, item={"n": 2}) == "two"
    assert adopt.resolve("$.top", doc, item={"n": 1}) == "x"
    assert adopt.resolve(".", doc, item=5) == 5


ADAPTER = ("format: antora\ncontent_root: content\ninternal_root: internal\n"
           "page_glob: 'modules/*/pages/**/*.adoc'\ncomment: line\n")


def test_missing_blocks(tmp_path):
    root = tmp_path / "g"
    tools = root / "tools" / "guide"
    tools.mkdir(parents=True)
    (tools / "adapter.yaml").write_text(ADAPTER)
    pages = root / "content" / "modules" / "ROOT" / "pages"
    pages.mkdir(parents=True)
    (pages / "ok.adoc").write_text("= Ok\n\n// Sources:\n// saw:README.md:1-3\n\nText.\n")
    (pages / "nav.adoc").write_text("= Nav\n:guide-no-sources:\n\n* xref:ok.adoc[]\n")
    (pages / "none.adoc").write_text("= None\n\nText without sources.\n")
    (pages / "empty.adoc").write_text("= Empty\n\n// Sources:\n\nText.\n")
    (pages / "listing.adoc").write_text(
        "= Listing\n\nText first.\n\n----\n// Sources:\n// saw:README.md\n----\n")
    missing = [p.name for p in adopt.missing_blocks(root)]
    assert missing == ["empty.adoc", "listing.adoc", "none.adoc"]

    proc = subprocess.run([sys.executable, str(TOOLKIT / "adopt.py"), "report", "--root", str(root)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "content/modules/ROOT/pages/none.adoc" in proc.stdout
    assert "3 page(s) without a source block" in proc.stdout


def test_cli_migrate(saw_root):
    proc = subprocess.run([sys.executable, str(TOOLKIT / "adopt.py"), "migrate", "--map", str(MAP),
                           "--root", str(saw_root)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "saw" in proc.stdout and "6 change request(s)" in proc.stdout
    again = subprocess.run([sys.executable, str(TOOLKIT / "adopt.py"), "migrate", "--map", str(MAP),
                            "--root", str(saw_root)], capture_output=True, text=True)
    assert again.returncode == 1
    assert "Traceback" not in again.stderr
