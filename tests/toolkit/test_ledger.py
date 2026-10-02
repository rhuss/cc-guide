import subprocess
import sys
from pathlib import Path

import pytest

import ledger

TOOLKIT = Path(__file__).resolve().parents[2] / "guide" / "toolkit"

ANTORA = ("format: antora\ncontent_root: content\ninternal_root: internal\n"
          "page_glob: 'modules/*/pages/**/*.adoc'\ncomment: line\n")
GFM = "format: gfm\ncontent_root: docs\ninternal_root: internal\npage_glob: '**/*.md'\ncomment: html\n"

PAGE = """= Install minisvc

// Sources:
// mini:Makefile:3-4
// mini:config/defaults.yaml:2-4

Administrators install minisvc once.
"""

ROWS = [
    ("C-INST-01", "The service listens on port 9090.", "admin/install", "mini:config/defaults.yaml:3", "CONFIRMED"),
    ("C-INST-02", "The README claims port 8080.", "admin/install",
     "mini:README.md:7; mini:config/defaults.yaml:3", "CONTRADICTED"),
    ("C-OVR-01", "There is no admin UI by default.", "-", "url:https://example.com/minisvc", "OPEN"),
]


def adoc_ledger(rows):
    cells = ["|ID", "|Claim", "|Page", "|Source", "|Status", ""]
    for row in rows:
        cells += [f"|{c}" for c in row] + [""]
    return ("= Claim ledger\n\n[cols=\"1,4,2,3,1\",options=\"header\"]\n|===\n"
            + "\n".join(cells) + "\n|===\n")


@pytest.fixture
def guide(render_fixture_guide, fixture_repo):
    root = render_fixture_guide
    tools = root / "tools" / "guide"
    tools.mkdir(parents=True)
    (tools / "adapter.yaml").write_text(ANTORA)
    pages = root / "content" / "modules" / "ROOT" / "pages"
    (pages / "admin").mkdir(parents=True)
    (pages / "admin" / "install.adoc").write_text(PAGE)
    (pages / "stub.adoc").write_text("= Later\n// STUB\n")
    led = root / "internal" / "modules" / "internal" / "pages"
    led.mkdir(parents=True)
    (led / "claim-ledger.adoc").write_text(adoc_ledger(ROWS))
    cache = root / ".guide" / "cache"
    cache.mkdir(parents=True)
    subprocess.run(["git", "clone", "--quiet", str(fixture_repo[0]), str(cache / "mini")], check=True)
    return root


def ledger_file(root):
    return root / "internal" / "modules" / "internal" / "pages" / "claim-ledger.adoc"


def test_valid_ledger(guide):
    errors, stats = ledger.check(guide)
    assert errors == []
    assert stats["claims"] == 3
    assert stats["pages"] == 1


@pytest.mark.parametrize("row,needle", [
    (("C-1", "x", "-", "url:https://example.com", "OPEN"), "bad ID"),
    (("C-INST-03", "x", "admin/missing", "url:https://example.com", "OPEN"), "page admin/missing"),
    (("C-INST-03", "x", "-", "other:README.md:1", "OPEN"), "unknown source"),
    (("C-INST-03", "x", "-", "mini:config/defaults.yaml:6-40", "OPEN"), "beyond the end"),
    (("C-INST-03", "x", "-", "mini:README.md", "MAYBE"), "status"),
    (("C-INST-03", "x", "-", "bogus", "OPEN"), "bad source reference"),
])
def test_bad_rows(guide, row, needle):
    ledger_file(guide).write_text(adoc_ledger(ROWS + [row]))
    errors, _ = ledger.check(guide)
    assert any(needle in e for e in errors), errors


def test_duplicate_id(guide):
    ledger_file(guide).write_text(adoc_ledger(ROWS + [ROWS[0]]))
    errors, _ = ledger.check(guide)
    assert any("duplicate ID" in e for e in errors)


def test_sources_block_inside_listing_not_counted(guide):
    page = guide / "content" / "modules" / "ROOT" / "pages" / "listing.adoc"
    page.write_text("= Example\n\nBody text.\n\n[source,asciidoc]\n----\n// Sources:\n// mini:README.md\n----\n")
    errors, _ = ledger.check(guide)
    assert any("listing" in e and "missing" in e for e in errors), errors


def test_page_source_out_of_range(guide):
    page = guide / "content" / "modules" / "ROOT" / "pages" / "admin" / "install.adoc"
    page.write_text(PAGE.replace("Makefile:3-4", "Makefile:3-400"))
    errors, _ = ledger.check(guide)
    assert any("admin/install" in e and "beyond the end" in e for e in errors)


def test_markdown_ledger(render_fixture_guide, fixture_repo):
    root = render_fixture_guide
    tools = root / "tools" / "guide"
    tools.mkdir(parents=True)
    (tools / "adapter.yaml").write_text(GFM)
    (root / "docs" / "admin").mkdir(parents=True)
    (root / "docs" / "admin" / "install.md").write_text(
        "# Install\n\n<!-- Sources:\nmini:Makefile:3-4\n-->\n\nText.\n")
    (root / "internal").mkdir()
    rows = "\n".join(f"| {' | '.join(r)} |" for r in ROWS)
    (root / "internal" / "claim-ledger.md").write_text(
        "# Claim ledger\n\n| ID | Claim | Page | Source | Status |\n|---|---|---|---|---|\n" + rows + "\n")
    cache = root / ".guide" / "cache"
    cache.mkdir(parents=True)
    subprocess.run(["git", "clone", "--quiet", str(fixture_repo[0]), str(cache / "mini")], check=True)
    errors, stats = ledger.check(root)
    assert errors == [], errors
    assert stats["claims"] == 3


def test_cli(guide):
    ledger_file(guide).write_text(adoc_ledger(ROWS + [ROWS[0]]))
    proc = subprocess.run([sys.executable, str(TOOLKIT / "ledger.py"), "--root", str(guide)],
                          capture_output=True, text=True)
    assert proc.returncode == 1
    assert "FAIL ledger:" in proc.stdout
    ok = guide / "ok.adoc"
    ok.write_text(adoc_ledger(ROWS))
    proc = subprocess.run([sys.executable, str(TOOLKIT / "ledger.py"), "--root", str(guide),
                           "--ledger", str(ok)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout
