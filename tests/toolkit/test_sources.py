import subprocess
import sys
from pathlib import Path

import pytest

import guidecfg
import sources
from sources import Ref

TOOLKIT = Path(__file__).resolve().parents[2] / "guide" / "toolkit"

ADOC = """= Install minisvc
:page-role: admin

// Sources:
// mini:Makefile:3-4
// mini:docs/setup.md
// url:https://example.com/minisvc
// input:walkthrough

Administrators install minisvc once.
"""

MD = """# Install minisvc

<!-- Sources:
mini:Makefile:3-4
mini:config/defaults.yaml:2-4,6-7
url:https://example.com/minisvc
-->

Administrators install minisvc once.
"""


def test_line_block():
    refs = sources.parse_block(ADOC, "line")
    assert [r.kind for r in refs] == ["source", "source", "url", "input"]
    assert refs[0] == Ref(kind="source", source_id="mini", path="Makefile", ranges=((3, 4),),
                          line=5, raw="mini:Makefile:3-4")
    assert refs[1].ranges == ()
    assert refs[2].url == "https://example.com/minisvc"
    assert refs[3].input_id == "walkthrough"


def test_html_block():
    refs = sources.parse_block(MD, "html")
    assert [r.raw for r in refs] == ["mini:Makefile:3-4", "mini:config/defaults.yaml:2-4,6-7",
                                     "url:https://example.com/minisvc"]
    assert refs[1].ranges == ((2, 4), (6, 7))
    assert refs[1].line == 5


def test_html_block_closing_on_last_line():
    text = "# T\n\n<!-- Sources:\nmini:README.md:1 -->\n\nBody.\n"
    assert [r.raw for r in sources.parse_block(text, "html")] == ["mini:README.md:1"]


def test_markdown_front_matter_is_skipped():
    text = "---\ntitle: x\n---\n# T\n\n<!-- Sources:\nmini:README.md\n-->\n"
    assert len(sources.parse_block(text, "html")) == 1


@pytest.mark.parametrize("bad", ["mini", "mini:", "url:not-a-url", "input:", "Mini:README.md",
                                 "mini:README.md:0", "mini:README.md:5-3", "mini:README.md:a-b"])
def test_grammar_rejects(bad):
    with pytest.raises(sources.BlockError):
        sources.parse_ref(bad)


def test_block_inside_listing_ignored():
    adoc = """= Page

Text first.

[source,asciidoc]
----
// Sources:
// mini:README.md
----
"""
    block = sources.find_block(adoc, "line")
    assert block is None
    md = "# Page\n\nText first.\n\n```markdown\n<!-- Sources:\nmini:README.md\n-->\n```\n"
    assert sources.find_block(md, "html") is None


def test_block_after_body_text_ignored():
    adoc = "= Page\n\nBody text.\n\n// Sources:\n// mini:README.md\n"
    assert sources.find_block(adoc, "line") is None


def test_no_sources_markers():
    adoc = "= Navigation\n:guide-no-sources:\n\n* xref:a.adoc[A]\n"
    block = sources.find_block(adoc, "line")
    assert block is not None and block.no_sources and block.refs == []
    md = "# Navigation\n\n<!-- guide: no-sources -->\n\n- [A](a.md)\n"
    block = sources.find_block(md, "html")
    assert block is not None and block.no_sources


def test_empty_block_without_marker_is_an_error():
    problems = sources.check_text("= Page\n\n// Sources:\n\nBody.\n", "line", page="p.adoc")
    assert any("empty" in p.message for p in problems)


def test_missing_block_is_an_error():
    problems = sources.check_text("= Page\n\nBody.\n", "line", page="p.adoc")
    assert any("missing" in p.message for p in problems)


@pytest.fixture
def cached(render_fixture_guide, fixture_repo):
    """A rendered fixture guide whose cache holds a clone of the mini repository."""
    root = render_fixture_guide
    cache = root / ".guide" / "cache"
    cache.mkdir(parents=True)
    subprocess.run(["git", "clone", "--quiet", str(fixture_repo[0]), str(cache / "mini")], check=True)
    return root, guidecfg.load_baseline(root), cache


def test_resolve_ok(cached):
    root, baseline, cache = cached
    res = sources.resolve(sources.parse_ref("mini:config/defaults.yaml:2-4"), baseline, cache)
    assert res.ok, res.message


def test_resolve_unknown_source(cached):
    _, baseline, cache = cached
    res = sources.resolve(sources.parse_ref("other:README.md"), baseline, cache)
    assert not res.ok and "unknown source" in res.message


def test_resolve_path_missing_at_pinned_commit(cached):
    _, baseline, cache = cached
    # docs/install.md only exists from the third commit on; the pin is the first commit.
    res = sources.resolve(sources.parse_ref("mini:docs/install.md"), baseline, cache)
    assert not res.ok and "not found" in res.message


def test_resolve_range_beyond_end(cached):
    _, baseline, cache = cached
    res = sources.resolve(sources.parse_ref("mini:config/defaults.yaml:6-40"), baseline, cache)
    assert not res.ok and "7 lines" in res.message


def test_resolve_input_ref_checks_register(cached):
    root, baseline, cache = cached
    inputs = guidecfg.load_inputs(root)
    assert sources.resolve(sources.parse_ref("input:walkthrough"), baseline, cache, inputs).ok
    res = sources.resolve(sources.parse_ref("input:nope"), baseline, cache, inputs)
    assert not res.ok and "nope" in res.message


def test_resolve_unfetched_source(render_fixture_guide):
    baseline = guidecfg.load_baseline(render_fixture_guide)
    res = sources.resolve(sources.parse_ref("mini:README.md"), baseline, render_fixture_guide / ".guide/cache")
    assert not res.ok and "fetch" in res.message


def test_cited_files(tmp_path):
    a = tmp_path / "a.md"
    a.write_text(MD)
    b = tmp_path / "b.md"
    b.write_text("# B\n\n<!-- Sources:\nmini:README.md:1-3\nother:x.txt\n-->\n")
    assert sources.cited_files([a, b], "html") == {
        "mini": {"Makefile", "config/defaults.yaml", "README.md"},
        "other": {"x.txt"},
    }


def test_cli_check(cached):
    root, _, _ = cached
    page = root / "page.md"
    page.write_text("# P\n\n<!-- Sources:\nmini:config/defaults.yaml:6-40\n-->\n")
    proc = subprocess.run([sys.executable, str(TOOLKIT / "sources.py"), "check", "--root", str(root),
                           "--style", "html", str(page)], capture_output=True, text=True)
    assert proc.returncode == 1
    assert "page.md:4:" in proc.stdout
