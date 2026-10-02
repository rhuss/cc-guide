import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import check
import guidecfg

TOOLKIT = Path(__file__).resolve().parents[2] / "guide" / "toolkit"
EM = chr(0x2014)
EN = chr(0x2013)

ANTORA_ADAPTER = """format: antora
content_root: content
internal_root: internal
page_glob: "modules/*/pages/**/*.adoc"
comment: line
"""

MKDOCS_ADAPTER = """format: mkdocs
content_root: docs
internal_root: docs/internal
page_glob: "**/*.md"
comment: html
"""

PAGES = "content/modules/ROOT/pages"
INTERNAL = "internal/modules/internal/pages"

GOOD_ADOC = """= Install minisvc

// Sources:
// mini:Makefile:3-4
// mini:config/defaults.yaml:2-4

Administrators install minisvc once on each host.
Use a container tool, e.g. Podman, if the host has no package.
The guide describes version {mini-version} from the baseline.
It listens on 127.0.0.1 and reads config/defaults.yaml at start.

[source,bash]
----
make install. Then make status. Both run here.
----

|===
|Key |Value. Second.
|===
"""


def write(root: Path, rel: str, text: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def adoc(body: str, refs: str = "// mini:Makefile:3-4") -> str:
    return f"= Page\n\n// Sources:\n{refs}\n\n{body}\n"


@pytest.fixture
def antora(render_fixture_guide):
    root = render_fixture_guide
    write(root, "tools/guide/adapter.yaml", ANTORA_ADAPTER)
    return root


@pytest.fixture
def mkdocs(render_fixture_guide):
    root = render_fixture_guide
    write(root, "tools/guide/adapter.yaml", MKDOCS_ADAPTER)
    path = root / "guide.yaml"
    data = yaml.safe_load(path.read_text())
    data["format"] = "mkdocs"
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    return root


def run(root: Path, strict: bool = False):
    return check.check_pages(root, guidecfg.load_guide(root), guidecfg.load_baseline(root), strict)


def rules(violations) -> list[str]:
    return sorted(v.rule for v in violations)


def test_clean_page_passes(antora):
    write(antora, f"{PAGES}/install.adoc", GOOD_ADOC)
    assert run(antora) == []


def test_dashes_in_pages_and_partials(antora):
    write(antora, f"{PAGES}/a.adoc", adoc(f"The service starts {EM} quickly."))
    write(antora, "content/modules/ROOT/partials/note.adoc", f"Range 1{EN}3 applies.\n")
    found = [v for v in run(antora) if v.rule == "dash"]
    assert sorted(v.path for v in found) == ["content/modules/ROOT/pages/a.adoc",
                                             "content/modules/ROOT/partials/note.adoc"]
    assert found[0].line > 0


def test_one_sentence_per_line(antora):
    body = "\n".join([
        "First sentence here. Second sentence here.",
        "Use a tool, e.g. Podman, for this.",
        "Pick one container tool, i.e. Podman.",
        "Version 1.2.3 reads config.yaml at start.",
        "// A comment. With two sentences.",
        ".Block title. With a period",
        ":attr: Value. Value.",
        "* A list item. And another sentence.",
    ])
    write(antora, f"{PAGES}/s.adoc", adoc(body))
    found = [v for v in run(antora) if v.rule == "sentence-per-line"]
    assert [v.line for v in found] == [6, 13]


def test_markdown_pages_skip_sentence_rule(mkdocs):
    write(mkdocs, "docs/index.md", "# P\n\n<!-- Sources:\nmini:Makefile\n-->\n\nOne. Two.\n")
    assert run(mkdocs) == []


def test_typed_values(antora, fixture_repo):
    first = fixture_repo[1]
    body = "\n".join([
        f"Check out {first} first.",
        f"Short form {first[:7]} also counts.",
        "This is version 1.2.3 of the service.",
        "Prefixed v1.2.3 counts too.",
        "But 1.2.30 and 11.2.3 do not.",
    ])
    write(antora, f"{PAGES}/t.adoc", adoc(body))
    found = [v for v in run(antora) if v.rule == "typed-value"]
    assert [v.line for v in found] == [6, 7, 8, 9]


def test_generated_region_values_are_not_typed(mkdocs, fixture_repo):
    """gfm generated regions hold values written by attrs.py; text outside them still counts."""
    short = fixture_repo[1][:7]
    write(mkdocs, "docs/index.md", "# P\n\n<!-- Sources:\nmini:Makefile\n-->\n\n"
          f"Commit <!-- guide:attr mini-commit-short -->{short}<!-- /guide:attr --> is pinned.\n"
          f"But a typed {short} still fails.\n")
    found = [v for v in run(mkdocs) if v.rule == "typed-value"]
    assert [v.line for v in found] == [8]


def test_typed_value_in_source_block_is_ignored(antora):
    write(antora, f"{PAGES}/t.adoc", adoc("Body text.", "// mini:docs/1.2.3/notes.md"))
    assert "typed-value" not in rules(run(antora))


def test_missing_source_block(antora):
    write(antora, f"{PAGES}/m.adoc", "= Page\n\nBody without sources.\n")
    found = run(antora)
    assert rules(found) == ["source-block"]
    assert "missing" in found[0].message


def test_no_sources_marker_passes(antora):
    write(antora, f"{PAGES}/nav.adoc", "= Navigation\n:guide-no-sources:\n\n* xref:a.adoc[A]\n")
    assert run(antora) == []


def test_stub_only_fails_under_strict(antora):
    write(antora, f"{PAGES}/stub.adoc", "= Stub\n// STUB\n\n// Sources:\n// mini:Makefile\n\nLater.\n")
    assert run(antora) == []
    assert rules(run(antora, strict=True)) == ["stub"]


def test_markdown_stub(mkdocs):
    write(mkdocs, "docs/s.md", "# S\n\n<!-- Sources:\nmini:Makefile\n-->\n\n<!-- STUB -->\n")
    assert run(mkdocs) == []
    assert rules(run(mkdocs, strict=True)) == ["stub"]


def test_rule_file(antora):
    write(antora, f"{PAGES}/admin/install.adoc", adoc("\n".join([
        "Run make status.",
        "Then run make install.",
        "Never use sudo here.",
    ])))
    write(antora, "guide-rules.yaml", yaml.safe_dump({"rules": [
        {"glob": f"{PAGES}/admin/*.adoc",
         "require": ["make install", {"pattern": "^Check:", "message": "admin pages need checks"}],
         "forbid": ["\\bsudo\\b"],
         "require_order": ["make install", "make status"]},
        {"glob": f"{PAGES}/missing/*.adoc", "require": ["x"]},
    ]}))
    found = run(antora)
    by_rule = {}
    for v in found:
        by_rule.setdefault(v.rule, []).append(v)
    assert len(by_rule["rule-require"]) == 2  # missing ^Check: and an empty glob
    assert any("admin pages need checks" in v.message for v in by_rule["rule-require"])
    assert [v.line for v in by_rule["rule-forbid"]] == [8]
    assert len(by_rule["rule-order"]) == 1


def test_input_reference_on_shareable_page_fails(antora):
    write(antora, f"{PAGES}/a.adoc", adoc("Body.", "// mini:Makefile\n// input:walkthrough"))
    assert rules(run(antora)) == ["input-on-shareable"]


def test_input_reference_on_internal_page(antora):
    write(antora, f"{INTERNAL}/notes.adoc", adoc("Body.", "// input:walkthrough"))
    assert run(antora) == []
    write(antora, f"{INTERNAL}/notes.adoc", adoc("Body.", "// input:nope"))
    found = run(antora)
    assert rules(found) == ["unknown-input"]
    assert "nope" in found[0].message


def test_confidential_terms_and_patterns_on_shareable(antora):
    body = "Our first customer is acme corp.\nTracked in MINI-42 for now."
    write(antora, f"{PAGES}/c.adoc", adoc(body))
    write(antora, f"{INTERNAL}/c.adoc", adoc(body))
    found = run(antora)
    assert rules(found) == ["confidential", "confidential"]
    assert all(v.path.startswith("content/") for v in found)


def test_internal_xref_on_shareable(antora):
    write(antora, f"{INTERNAL}/notes.adoc", adoc("Notes."))
    write(antora, f"{PAGES}/a.adoc", adoc("See xref:internal:notes.adoc[the notes] for more."))
    write(antora, f"{PAGES}/b.adoc", adoc("See xref:a.adoc[page A] for more."))
    found = run(antora)
    assert rules(found) == ["internal-link"]
    assert found[0].path.endswith("a.adoc")


def test_markdown_internal_link_on_shareable(mkdocs):
    write(mkdocs, "docs/internal/notes.md", "# N\n\n<!-- Sources:\nmini:Makefile\n-->\n\nNotes.\n")
    write(mkdocs, "docs/user/start.md", "# S\n\n<!-- Sources:\nmini:Makefile\n-->\n\nStart.\n")
    write(mkdocs, "docs/index.md",
          "# I\n\n<!-- Sources:\nmini:Makefile\n-->\n\nSee [notes](internal/notes.md) and [start](user/start.md).\n")
    found = run(mkdocs)
    assert rules(found) == ["internal-link"]
    assert found[0].path == "docs/index.md"


def test_image_alt_text_with_unquoted_comma(antora):
    body = "\n".join([
        'image::arch.svg[Overview, with commas]',
        'image::arch.svg["Overview, with commas"]',
        'image::arch.svg[Overview,role=expand]',
        'image::arch.svg[Overview,300,200]',
        'An inline image:icon.png[Icon, small] here.',
    ])
    write(antora, f"{PAGES}/i.adoc", adoc(body))
    found = [v for v in run(antora) if v.rule == "image-alt"]
    assert [v.line for v in found] == [6, 10]


def test_diagram_without_role_expand(antora):
    write(antora, "diagrams/01-architecture.excalidraw", "{}")
    body = "\n".join([
        'image::01-architecture.svg["Architecture"]',
        'image::01-architecture.svg["Architecture",role=expand]',
        'image::photo.png["A photo"]',
    ])
    write(antora, f"{PAGES}/d.adoc", adoc(body))
    found = [v for v in run(antora) if v.rule == "diagram-expand"]
    assert [v.line for v in found] == [6]


def test_source_resolution_when_cache_exists(antora, fixture_repo):
    cache = antora / ".guide" / "cache"
    cache.mkdir(parents=True)
    subprocess.run(["git", "clone", "--quiet", str(fixture_repo[0]), str(cache / "mini")], check=True)
    write(antora, f"{PAGES}/a.adoc", adoc("Body.", "// mini:config/defaults.yaml:6-40"))
    found = run(antora)
    assert rules(found) == ["source-ref"]
    assert found[0].line == 4


def cli(root: Path, *args: str, env: dict | None = None):
    return subprocess.run([sys.executable, str(TOOLKIT / "check.py"), "--root", str(root), *args],
                          capture_output=True, text=True, env={**os.environ, **(env or {})})


def test_cli(antora):
    write(antora, f"{PAGES}/install.adoc", GOOD_ADOC)
    proc = cli(antora)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    write(antora, f"{PAGES}/a.adoc", adoc(f"Bad {EM} dash."))
    proc = cli(antora)
    assert proc.returncode == 1
    assert f"{PAGES}/a.adoc:6: [dash]" in proc.stdout


def test_cli_strict_env(antora):
    write(antora, f"{PAGES}/stub.adoc", "= Stub\n// STUB\n\n// Sources:\n// mini:Makefile\n")
    assert cli(antora).returncode == 0
    assert cli(antora, env={"STRICT": "1"}).returncode == 1
    assert cli(antora, "--strict").returncode == 1


def _md_project(tmp_path):
    root = tmp_path / "md"
    (root / "tools" / "guide").mkdir(parents=True)
    (root / "tools" / "guide" / "adapter.yaml").write_text(
        "format: gfm\ncontent_root: docs\ninternal_root: internal\npage_glob: '**/*.md'\ncomment: html\n")
    (root / "guide.yaml").write_text(
        "schema: 1\ntitle: T\nformat: gfm\npersonas:\n  - {id: admin, title: Admin, start: admin/install}\n"
        "sections:\n  - {id: admin, title: Admin guide, voice: technical}\n")
    (root / "baseline.yaml").write_text(
        "captured: '2026-01-01'\nsources:\n  - {id: mini, repo: x/y, commit: " + "a" * 40 + "}\n")
    (root / "docs").mkdir()
    (root / "docs" / "index.md").write_text(
        "# Index\n\n<!-- guide: no-sources -->\n\nSee [missing](nope.md) and [here](index.md).\n\n"
        "```markdown\n[example](not-checked.md)\n```\n")
    return root


def test_broken_relative_markdown_link(tmp_path):
    root = _md_project(tmp_path)
    v = check.check_pages(root, guidecfg.load_guide(root), guidecfg.load_baseline(root))
    broken = [x for x in v if x.rule == "broken-link"]
    assert [x.message for x in broken] == ["nope.md does not exist"]


def test_structure_check(tmp_path):
    root = _md_project(tmp_path)
    guide, baseline = guidecfg.load_guide(root), guidecfg.load_baseline(root)
    assert not [x for x in check.check_pages(root, guide, baseline) if x.rule == "guide-structure"]
    v = [x for x in check.check_pages(root, guide, baseline, structure=True) if x.rule == "guide-structure"]
    assert len(v) == 2  # admin/install missing, "Admin guide" not in a navigation file
    (root / "docs" / "admin").mkdir()
    (root / "docs" / "admin" / "install.md").write_text("# Install\n\n<!-- guide: no-sources -->\n")
    (root / "docs" / "SUMMARY.md").write_text("# Summary\n\n<!-- guide: no-sources -->\n\n## Admin guide\n\n- [Install](admin/install.md)\n")
    assert not [x for x in check.check_pages(root, guide, baseline, structure=True) if x.rule == "guide-structure"]


def test_links_inside_nested_fences_are_not_checked(tmp_path):
    root = _md_project(tmp_path)
    (root / "docs" / "index.md").write_text(
        "# Index\n\n<!-- guide: no-sources -->\n\n"
        "````markdown\nAn example with an opening fence only:\n```bash\n[example](inside-outer-fence.md)\n````\n\n"
        "[real](missing-after-fence.md)\n")
    v = check.check_pages(root, guidecfg.load_guide(root), guidecfg.load_baseline(root))
    assert [x.message for x in v if x.rule == "broken-link"] == ["missing-after-fence.md does not exist"]
