import subprocess
import sys
from pathlib import Path

import pytest

import guidecfg
import leakcheck

TOOLKIT = Path(__file__).resolve().parents[2] / "guide" / "toolkit"

CLEAN_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Install minisvc</title>
<script>var enc = "UTF-8"; var k = "ABC-123";</script>
<style>.x::after { content: "ZZ-9"; }</style>
</head><body>
<h1>Install minisvc</h1>
<p>Administrators install minisvc once.</p>
<a href="../user/start.html">Get started</a>
<a href="https://github.com/acme/other/tree/main/internal/pkg">upstream code</a>
<img src="_images/arch.svg" alt="Architecture">
</body></html>
"""


def write(root: Path, rel: str, text: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


@pytest.fixture
def guide(render_fixture_guide):
    return guidecfg.load_guide(render_fixture_guide)


@pytest.fixture
def site(tmp_path):
    root = tmp_path / "site"
    write(root, "minisvc/admin/install.html", CLEAN_HTML)
    write(root, "_/js/site.js", "var a = 'ACME Corp'; var b = 'XY-12';\n")
    return root


def kinds(leaks) -> list[str]:
    return sorted(leak.kind for leak in leaks)


def test_clean_build_passes(site, guide):
    assert leakcheck.scan_dir(site, guide) == []


def test_confidential_term_in_html(site, guide):
    write(site, "minisvc/index.html", "<html><body>\n<p>Built for <b>acme corp</b>.</p>\n</body></html>\n")
    leaks = leakcheck.scan_dir(site, guide)
    assert kinds(leaks) == ["term"]
    assert leaks[0].path.endswith("minisvc/index.html")
    assert leaks[0].line == 2


def test_term_in_alt_text_and_comment(site, guide):
    write(site, "minisvc/a.html", '<html><body><img src="x.svg" alt="ACME Corp setup">\n'
                                  "<!-- Sources: notes about ACME Corp -->\n</body></html>\n")
    assert kinds(leakcheck.scan_dir(site, guide)) == ["term", "term"]


def test_ticket_pattern_in_html(site, guide):
    write(site, "minisvc/b.html", "<html><body><p>See MINI-42 for details.</p></body></html>\n")
    leaks = leakcheck.scan_dir(site, guide)
    assert kinds(leaks) == ["pattern"]
    assert leaks[0].match == "MINI-42"


def test_link_into_internal_part(site, guide):
    write(site, "minisvc/c.html", '<html><body><a href="../internal/notes.html">notes</a></body></html>\n')
    leaks = leakcheck.scan_dir(site, guide)
    assert kinds(leaks) == ["internal-link"]
    assert leaks[0].match == "../internal/notes.html"


def test_internal_directory_in_site(site, guide):
    write(site, "minisvc/internal/notes.html", "<html><body><p>Notes.</p></body></html>\n")
    leaks = leakcheck.scan_dir(site, guide)
    assert kinds(leaks) == ["internal-path"]


def test_custom_internal_marker(site, guide):
    write(site, "minisvc/c.html", '<html><body><a href="team-only/notes.html">notes</a></body></html>\n')
    assert leakcheck.scan_dir(site, guide) == []
    assert kinds(leakcheck.scan_dir(site, guide, internal_marker="team-only")) == ["internal-link"]


def test_search_index_json(site, guide):
    write(site, "search/search_index.json", '{"docs": [{"text": "first customer ACME Corp"}]}\n')
    assert kinds(leakcheck.scan_dir(site, guide)) == ["term"]


def make_pdf(text: str, uri: str | None = None) -> bytes:
    """A minimal one-page PDF with one Helvetica text line and an optional link annotation."""
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    annots = " /Annots [6 0 R]" if uri else ""
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
         b"/Resources << /Font << /F1 5 0 R >> >>" + annots.encode() + b" >>"),
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    if uri:
        objs.append(b"<< /Type /Annot /Subtype /Link /Rect [72 700 300 730] /Border [0 0 0] "
                    b"/A << /S /URI /URI (" + uri.encode() + b") >> >>")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def test_pdf_term(tmp_path, guide):
    pdf = tmp_path / "guide.pdf"
    pdf.write_bytes(make_pdf("Rollout for ACME Corp is planned"))
    leaks = leakcheck.scan_pdf(pdf, guide)
    assert kinds(leaks) == ["term"]
    assert leaks[0].line == 1  # page number


def test_pdf_internal_link_and_clean(tmp_path, guide):
    pdf = tmp_path / "linked.pdf"
    pdf.write_bytes(make_pdf("Nothing secret here", uri="internal/notes.html"))
    assert kinds(leakcheck.scan_pdf(pdf, guide)) == ["internal-link"]
    clean = tmp_path / "clean.pdf"
    clean.write_bytes(make_pdf("Nothing secret here", uri="https://example.com/minisvc"))
    assert leakcheck.scan_pdf(clean, guide) == []


def test_cli(render_fixture_guide, site):
    root = render_fixture_guide
    cmd = [sys.executable, str(TOOLKIT / "leakcheck.py"), "--root", str(root), str(site)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    write(site, "minisvc/index.html", "<html><body><p>ACME Corp</p></body></html>\n")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 1
    assert "minisvc/index.html:1: [term]" in proc.stdout


def test_confidential_term_in_link_target(tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text(
        '<html><body><a href="https://portal.example.com/acme-corp/setup">setup</a>'
        '<a href="https://tracker.example.com/browse/MINI-42">ticket</a></body></html>')
    guide = guidecfg.Guide(root=tmp_path, schema=1, title="t", format="antora", personas=[], sections=[],
                           confidential_terms=["acme-corp"], confidential_patterns=[r"\b[A-Z]{2,}-\d+\b"])
    kinds = sorted(l.kind for l in leakcheck.scan_dir(site, guide))
    assert kinds == ["pattern", "term"]


def test_pdf_ticket_pattern(tmp_path, guide):
    pdf = tmp_path / "ticket.pdf"
    pdf.write_bytes(make_pdf("Questions are tracked in MINI-42 for now"))
    leaks = leakcheck.scan_pdf(pdf, guide)
    assert kinds(leaks) == ["pattern"] and leaks[0].match == "MINI-42"
