"""guide/toolkit/branding.py: schema checks, overlay checks, resolve (specs/002-antora-branding)."""
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import branding

TOOLKIT = Path(__file__).resolve().parents[2] / "guide" / "toolkit"
ANTORA_KEYS = list(branding.KEYS)
FOOTER_MSG = "must be rhdp, none, or a mapping with text and optional url"
SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><text>OwnLogoMarker</text></svg>\n'


@pytest.fixture
def proj(tmp_path: Path) -> Path:
    """A guide project with an own logo and a favicon under branding/."""
    root = tmp_path / "guide"
    (root / "branding").mkdir(parents=True)
    (root / "branding" / "logo.svg").write_text(SVG)
    (root / "branding" / "favicon.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    return root


def run_check(root: Path, raw, fmt: str = "antora", keys=None):
    return branding.check(root, raw, fmt, ANTORA_KEYS if keys is None else keys)


def has(pairs, loc: str, prefix: str) -> bool:
    return any(l == loc and m.startswith(prefix) for l, m in pairs)


def assert_problem(root, raw, loc, prefix, **kw):
    problems, _ = run_check(root, raw, **kw)
    assert has(problems, loc, prefix), problems


def assert_ok(root, raw, **kw):
    problems, _ = run_check(root, raw, **kw)
    assert problems == []


# --- logo keys ---------------------------------------------------------------


def test_minimal_logo_text_block_passes(proj):
    assert_ok(proj, {"logo_text": "Agent Starter Kits"})


def test_both_logo_keys_fail(proj):
    assert_problem(proj, {"logo_text": "X", "logo": "branding/logo.svg", "logo_alt": "X"},
                   "guide.yaml:branding", "set exactly one of logo_text or logo")


def test_neither_logo_key_fails(proj):
    assert_problem(proj, {"footer": "none"}, "guide.yaml:branding", "set exactly one of logo_text or logo")


def test_empty_block_fails_for_antora(proj):
    assert_problem(proj, {}, "guide.yaml:branding", "set exactly one of logo_text or logo")


@pytest.mark.parametrize("text", ["", "   ", "Agent\nStarter", "x" * 41])
def test_bad_logo_text(proj, text):
    assert_problem(proj, {"logo_text": text}, "guide.yaml:branding.logo_text",
                   "must be one line of 1 to 40 characters")


def test_logo_text_reports_length(proj):
    assert_problem(proj, {"logo_text": "x" * 41}, "guide.yaml:branding.logo_text",
                   "must be one line of 1 to 40 characters (got 41)")


def test_logo_text_of_40_characters_passes(proj):
    assert_ok(proj, {"logo_text": "x" * 40})
    assert_ok(proj, {"logo_text": "  " + "x" * 40 + "  "})  # trimmed first


def test_logo_without_alt_fails(proj):
    assert_problem(proj, {"logo": "branding/logo.svg"}, "guide.yaml:branding.logo_alt",
                   "required with branding.logo")


def test_logo_with_alt_passes(proj):
    assert_ok(proj, {"logo": "branding/logo.svg", "logo_alt": "Example product"})


# --- paths -------------------------------------------------------------------


def test_missing_logo_file(proj):
    assert_problem(proj, {"logo": "branding/missing.svg", "logo_alt": "X"}, "guide.yaml:branding.logo",
                   "file not found: branding/missing.svg")


def test_missing_favicon_file(proj):
    assert_problem(proj, {"logo_text": "X", "favicon": "branding/missing.ico"}, "guide.yaml:branding.favicon",
                   "file not found: branding/missing.ico")


def test_absolute_path_rejected(proj):
    path = str(proj / "branding" / "logo.svg")
    assert_problem(proj, {"logo": path, "logo_alt": "X"}, "guide.yaml:branding.logo",
                   f"must be a path inside the guide project (got {path})")


def test_dotdot_path_rejected(proj):
    (proj.parent / "outside.svg").write_text(SVG)
    assert_problem(proj, {"logo": "../outside.svg", "logo_alt": "X"}, "guide.yaml:branding.logo",
                   "must be a path inside the guide project (got ../outside.svg)")


def test_symlink_outside_rejected(proj):
    (proj.parent / "outside.png").write_bytes(b"png")
    os.symlink(proj.parent / "outside.png", proj / "branding" / "linked.png")
    assert_problem(proj, {"logo_text": "X", "favicon": "branding/linked.png"}, "guide.yaml:branding.favicon",
                   "must be a path inside the guide project (got branding/linked.png)")


def test_symlink_inside_passes(proj):
    os.symlink(proj / "branding" / "favicon.png", proj / "branding" / "alias.png")
    assert_ok(proj, {"logo_text": "X", "favicon": "branding/alias.png"})


def test_logo_must_be_svg(proj):
    (proj / "branding" / "logo.png").write_bytes(b"png")
    assert_problem(proj, {"logo": "branding/logo.png", "logo_alt": "X"}, "guide.yaml:branding.logo",
                   "must be an .svg file (got branding/logo.png)")


def test_favicon_type(proj):
    (proj / "branding" / "favicon.gif").write_bytes(b"gif")
    assert_problem(proj, {"logo_text": "X", "favicon": "branding/favicon.gif"}, "guide.yaml:branding.favicon",
                   "must be an .ico, .png, or .svg file (got branding/favicon.gif)")


@pytest.mark.parametrize("name", ["favicon.ico", "favicon.png", "favicon.svg"])
def test_favicon_types_pass(proj, name):
    (proj / "branding" / name).write_bytes(b"icon")
    assert_ok(proj, {"logo_text": "X", "favicon": f"branding/{name}"})


# --- footer ------------------------------------------------------------------


@pytest.mark.parametrize("footer", ["rhdp", "none", {"text": "On GitHub"},
                                    {"text": "On GitHub", "url": "https://github.com/example/repo"},
                                    {"text": "Docs", "url": "http://example.com/docs"}])
def test_footer_values_pass(proj, footer):
    assert_ok(proj, {"logo_text": "X", "footer": footer})


@pytest.mark.parametrize("footer", [{"url": "https://example.com"}, "stock", ["a"], 3])
def test_bad_footer(proj, footer):
    assert_problem(proj, {"logo_text": "X", "footer": footer}, "guide.yaml:branding.footer", FOOTER_MSG)


@pytest.mark.parametrize("url", ["ftp://example.com/x", "/docs/index.html", "example.com", "https://"])
def test_footer_url_must_be_absolute_http(proj, url):
    assert_problem(proj, {"logo_text": "X", "footer": {"text": "T", "url": url}}, "guide.yaml:branding.footer.url",
                   "must be an absolute http or https URL")


# --- color, unknown keys, adapter capability ---------------------------------


def test_color_passes(proj):
    assert_ok(proj, {"logo_text": "X", "color": "#3e8635"})


@pytest.mark.parametrize("color", ["3e8635", "#fff", "#gggggg"])
def test_bad_color(proj, color):
    assert_problem(proj, {"logo_text": "X", "color": color}, "guide.yaml:branding.color",
                   f"must be a #rrggbb color (got {color})")


def test_color_with_trailing_newline_fails(proj):
    assert_problem(proj, {"logo_text": "X", "color": "#3e8635\n"}, "guide.yaml:branding.color",
                   "must be a #rrggbb color")


def test_unquoted_color_is_reported(proj):
    # `color: #3e8635` without quotes is a YAML comment: the key is present without a value.
    assert_problem(proj, {"logo_text": "X", "color": None}, "guide.yaml:branding.color", "must be a #rrggbb color")


def test_unknown_branding_key(proj):
    assert_problem(proj, {"logo_text": "X", "colour": "#3e8635"}, "guide.yaml:branding.colour", "unknown key")


def test_branding_not_a_mapping(proj):
    assert_problem(proj, ["logo_text"], "guide.yaml:branding", "must be a mapping")


@pytest.mark.parametrize("fmt", ["mkdocs", "gfm"])
def test_unsupported_adapter_rejects_every_key(proj, fmt):
    problems, _ = run_check(proj, {"logo_text": "X", "footer": "none", "color": "#3e8635"}, fmt=fmt, keys=[])
    for key in ("logo_text", "footer", "color"):
        assert has(problems, f"guide.yaml:branding.{key}", f"not supported by the {fmt} adapter"), problems


@pytest.mark.parametrize("fmt", ["mkdocs", "gfm"])
def test_unsupported_adapter_reports_only_the_format(proj, fmt):
    problems, _ = run_check(proj, {"foo": 1}, fmt=fmt, keys=[])
    assert problems == [("guide.yaml:branding.foo", f"not supported by the {fmt} adapter")]


@pytest.mark.parametrize("fmt", ["mkdocs", "gfm"])
def test_unsupported_adapter_rejects_empty_block(proj, fmt):
    assert_problem(proj, {}, "guide.yaml:branding", f"not supported by the {fmt} adapter", fmt=fmt, keys=[])


def test_no_block_no_overlay_no_problems(proj):
    assert run_check(proj, None) == ([], [])


# --- overlay directory and playbook conflict ---------------------------------


def write_site(root: Path, name: str = "site.yml", supplemental: str | None = "./supplemental-ui") -> None:
    data = {"site": {"title": "T"}, "ui": {"bundle": {"url": "https://example.com/ui.zip"}}}
    if supplemental is not None:
        data["ui"]["supplemental_files"] = supplemental
    (root / name).write_text(yaml.safe_dump(data))


@pytest.mark.parametrize("name", ["site.yml", "site-internal.yml"])
def test_playbook_supplemental_files_conflict_with_branding(proj, name):
    write_site(proj, name)
    assert_problem(proj, {"logo_text": "X"}, f"{name}:ui.supplemental_files",
                   "already set; move these files into ui/supplemental/")


def test_playbook_supplemental_files_conflict_with_overlay(proj):
    write_site(proj)
    (proj / "ui" / "supplemental" / "css").mkdir(parents=True)
    (proj / "ui" / "supplemental" / "css" / "extra.css").write_text("a{}\n")
    assert_problem(proj, None, "site.yml:ui.supplemental_files", "already set; move these files into ui/supplemental/")


def test_playbook_supplemental_files_alone_is_fine(proj):
    write_site(proj)
    assert run_check(proj, None) == ([], [])


def test_playbook_without_supplemental_files_is_fine(proj):
    write_site(proj, supplemental=None)
    assert_ok(proj, {"logo_text": "X"})


def test_overlay_must_be_a_directory(proj):
    (proj / "ui").mkdir()
    (proj / "ui" / "supplemental").write_text("not a directory\n")
    assert_problem(proj, None, "ui/supplemental", "must be a directory")


def test_overlay_file_linking_outside(proj):
    css = proj / "ui" / "supplemental" / "css"
    css.mkdir(parents=True)
    (proj.parent / "outside.css").write_text("a{}\n")
    os.symlink(proj.parent / "outside.css", css / "x.css")
    assert_problem(proj, None, "ui/supplemental:css/x.css", "links outside the guide project")


def test_overlay_regular_files_pass(proj):
    css = proj / "ui" / "supplemental" / "css"
    css.mkdir(parents=True)
    (css / "extra.css").write_text("a{}\n")
    assert run_check(proj, None) == ([], [])
    assert_ok(proj, {"logo_text": "X"})


@pytest.mark.parametrize("fmt", ["mkdocs", "gfm"])
def test_overlay_and_playbook_checks_only_for_antora(proj, fmt):
    write_site(proj)
    (proj / "ui").mkdir()
    (proj / "ui" / "supplemental").write_text("not a directory\n")
    assert run_check(proj, None, fmt=fmt, keys=[]) == ([], [])


# --- check_guide and the CLI -------------------------------------------------


def write_guide(root: Path, fmt: str = "antora", block=None) -> None:
    data = {"schema": 1, "title": "T", "format": fmt, "personas": [{"id": "a", "title": "A", "start": "a"}]}
    if block is not None:
        data["branding"] = block
    root.mkdir(parents=True, exist_ok=True)
    (root / "guide.yaml").write_text(yaml.safe_dump(data, sort_keys=False))


def test_check_guide_without_guide_yaml(tmp_path):
    assert branding.check_guide(tmp_path) == ([], [])


def test_check_guide_defaults_to_antora_keys_without_adapter(proj):
    write_guide(proj, "antora", {"logo_text": "X"})
    assert branding.check_guide(proj) == ([], [])
    write_guide(proj, "antora", {"logo_text": "x" * 41})
    problems, _ = branding.check_guide(proj)
    assert problems == ["guide.yaml:branding.logo_text: must be one line of 1 to 40 characters (got 41)"]


def test_check_guide_default_keys_for_other_formats(proj):
    write_guide(proj, "mkdocs", {"logo_text": "X"})
    problems, _ = branding.check_guide(proj)
    assert problems == ["guide.yaml:branding.logo_text: not supported by the mkdocs adapter"]


def test_check_guide_reads_adapter_keys(proj):
    write_guide(proj, "antora", {"logo_text": "X"})
    tools = proj / "tools" / "guide"
    tools.mkdir(parents=True)
    (tools / "adapter.yaml").write_text("format: antora\nbranding: [logo_text, logo, logo_alt]\n")
    assert branding.check_guide(proj) == ([], [])
    write_guide(proj, "antora", {"logo_text": "X", "color": "#3e8635"})
    problems, _ = branding.check_guide(proj)
    assert problems == ["guide.yaml:branding.color: not supported by the antora adapter"]
    # A vendored descriptor from before the feature has no list: nothing is supported.
    (tools / "adapter.yaml").write_text("format: antora\n")
    problems, _ = branding.check_guide(proj)
    assert "guide.yaml:branding.logo_text: not supported by the antora adapter" in problems


def test_check_guide_formats_warnings(proj):
    write_guide(proj, "antora", {"logo_text": "X"})
    partials = proj / "ui" / "supplemental" / "partials"
    partials.mkdir(parents=True)
    (partials / "footer-content.hbs").write_text("<footer class=\"footer\">mine</footer>\n")
    problems, warnings = branding.check_guide(proj)
    assert problems == []
    assert warnings == ["ui/supplemental/partials/footer-content.hbs: warning: "
                        "shadows the file generated for branding.footer"]


def test_cli_validate(proj):
    write_guide(proj, "antora", {"logo_text": "X", "logo": "branding/logo.svg", "logo_alt": "X"})
    cmd = [sys.executable, str(TOOLKIT / "branding.py"), "validate", "--root", str(proj)]
    bad = subprocess.run(cmd, capture_output=True, text=True)
    assert bad.returncode == 1
    assert "guide.yaml:branding: set exactly one of logo_text or logo" in bad.stdout
    write_guide(proj, "antora", {"logo_text": "X"})
    ok = subprocess.run(cmd, capture_output=True, text=True)
    assert ok.returncode == 0, ok.stdout + ok.stderr


# --- resolve and hover_shade -------------------------------------------------


def test_resolve_without_block():
    assert branding.resolve(Path("."), None) is None


def test_resolve_defaults(proj):
    r = branding.resolve(proj, {"logo_text": "  Agent Starter Kits "})
    assert r.logo_text == "Agent Starter Kits"
    assert r.logo is None
    assert r.alt == "Red Hat Agent Starter Kits"
    assert r.footer == "none"
    assert r.favicon is None and r.color is None and r.hover is None


def test_resolve_explicit_values(proj):
    r = branding.resolve(proj, {"logo": "branding/logo.svg", "logo_alt": "Example product",
                                "footer": {"text": "On GitHub"}, "favicon": "branding/favicon.png",
                                "color": "#3E8635"})
    assert r.logo_text is None
    assert r.logo == proj / "branding" / "logo.svg"
    assert r.alt == "Example product"
    assert r.footer == {"text": "On GitHub", "url": None}
    assert r.favicon == proj / "branding" / "favicon.png"
    assert r.color == "#3e8635"
    assert r.hover == "#2f6528"


def test_resolve_footer_values(proj):
    assert branding.resolve(proj, {"logo_text": "X", "footer": "rhdp"}).footer == "rhdp"
    assert branding.resolve(proj, {"logo_text": "X", "footer": "none"}).footer == "none"
    url = "https://github.com/red-hat-data-services/agentic-starter-kits"
    r = branding.resolve(proj, {"logo_text": "X", "footer": {"text": "Kits", "url": url}})
    assert r.footer == {"text": "Kits", "url": url}


def test_resolve_explicit_alt_with_logo_text(proj):
    assert branding.resolve(proj, {"logo_text": "X", "logo_alt": "Custom"}).alt == "Custom"


def test_hover_shade_rounds_half_up():
    # 0x66 * 0.75 = 76.5 must round to 0x4d (77); Python's round() would give 76 (#004c99).
    assert branding.hover_shade("#0066cc") == "#004d99"
    assert branding.hover_shade("#3e8635") == "#2f6528"
    assert branding.hover_shade("#FFFFFF") == "#bfbfbf"


# --- rendering: logo, alt helper, footer (T011) --------------------------------

import json  # noqa: E402
import math  # noqa: E402
import shutil  # noqa: E402
import time  # noqa: E402
import xml.etree.ElementTree as ET  # noqa: E402

SVG_NS = "{http://www.w3.org/2000/svg}"


def svg_text(svg: str) -> ET.Element:
    return ET.fromstring(svg).find(f"{SVG_NS}text")


def viewbox_width(svg: str) -> float:
    return float(ET.fromstring(svg).get("viewBox").split()[2])


def test_logo_svg_escapes_markup():
    text = "A&B <C> \"D\" 'E'"
    svg = branding.logo_svg(text)
    assert "A&amp;B &lt;C&gt; &quot;D&quot; &apos;E&apos;" in svg
    assert "<C>" not in svg
    el = svg_text(svg)                      # well-formed XML
    assert el.get("data-name") == text
    assert el.find(f"{SVG_NS}tspan").text == text


def test_logo_svg_keeps_notice_and_never_says_demo_platform():
    svg = branding.logo_svg("Agent Starter Kits")
    assert "<!--" in svg and "Mozilla Public License, v. 2.0" in svg
    assert "Demo Platform" not in svg
    assert "Agent Starter Kits" in svg


def test_logo_svg_text_length_is_the_estimate():
    for text in ("Summit", "Agent Starter Kits", "W" * 40):
        el = svg_text(branding.logo_svg(text))
        assert el.get("lengthAdjust") == "spacingAndGlyphs"
        assert float(el.get("textLength")) == pytest.approx(branding.text_width(text), abs=0.01)
        # the stock text attributes stay
        assert el.get("transform") == "translate(308 149)"
        assert el.get("fill") == "#fff" and el.get("font-size") == "82" and el.get("font-weight") == "700"


def test_logo_svg_viewbox_width():
    assert viewbox_width(branding.logo_svg("Summit")) == 780      # the width of the stock logo-summit.svg
    text = "W" * 40
    assert viewbox_width(branding.logo_svg(text)) == math.ceil(308 + branding.text_width(text) + 24)
    assert branding.text_width("W" * 40) == pytest.approx(3096.32, abs=0.01)


def test_text_width_grows_with_every_character():
    text = ""
    previous = branding.text_width(text)
    for ch in "Agent Starter Kits 3.0 {x}|~" + chr(0xe9) + chr(0x4e2d):
        text += ch
        width = branding.text_width(text)
        assert width > previous
        previous = width


def test_logo_svg_placeholder_text_stays_literal():
    svg = branding.logo_svg("{{TEXT_LENGTH}}")
    assert svg_text(svg).find(f"{SVG_NS}tspan").text == "{{TEXT_LENGTH}}"
    assert "{{VIEWBOX_WIDTH}}" not in svg


ALT = "Red Hat \"Kits\" & 'more' </script>"


def test_alt_helper_returns_the_exact_text(tmp_path):
    js = branding.alt_helper(ALT)
    assert js.startswith("'use strict'")
    helper = tmp_path / "navbar-logo-alt.js"
    helper.write_text(js)
    node = shutil.which("node")
    if node:
        proc = subprocess.run([node, "-e", f"process.stdout.write(require({json.dumps(str(helper))})('guide', {{}}))"],
                              capture_output=True, text=True, check=True)
        assert proc.stdout == ALT
    literal = js.split("module.exports = () => ", 1)[1].strip()
    assert json.loads(literal) == ALT


def test_footer_partials():
    assert branding.footer_partial("none").strip() == '<footer class="footer"></footer>'
    url = "https://github.com/red-hat-data-services/agentic-starter-kits?a=1&b=2"
    linked = branding.footer_partial({"text": "Kits <on> GitHub", "url": url})
    assert linked.startswith('<footer class="footer">')
    assert "Kits &lt;on&gt; GitHub" in linked
    assert 'href="https://github.com/red-hat-data-services/agentic-starter-kits?a=1&amp;b=2"' in linked
    assert 'target="_blank" rel="noopener"' in linked
    plain = branding.footer_partial({"text": "Kits", "url": None})
    assert "Kits" in plain and "<a " not in plain
    braces = branding.footer_partial({"text": "{{x}}", "url": None})
    assert "&#123;&#123;x&#125;&#125;" in braces and "{{" not in braces


# --- render(root, view) (T012) ---------------------------------------------------


def branded(root: Path, block: dict) -> Path:
    write_guide(root, "antora", block)
    return root


def ui_files(ui: Path) -> list[str]:
    return sorted(p.relative_to(ui).as_posix() for p in ui.rglob("*") if p.is_file())


def test_render_writes_the_overlay(proj):
    branded(proj, {"logo_text": "Agent Starter Kits", "footer": {"text": "Kits", "url": "https://example.com"}})
    ui = branding.render(proj, "shareable")
    assert ui == (proj / "build" / "branding" / "shareable" / "ui").resolve()
    assert ui_files(ui) == ["helpers/navbar-logo-alt.js", "img/logo-guide.svg", "partials/footer-content.hbs"]
    assert "Agent Starter Kits" in (ui / "img" / "logo-guide.svg").read_text()
    meta = json.loads((ui.parent / "branding.json").read_text())
    assert meta["logo"] == str(ui / "img" / "logo-guide.svg")
    assert Path(meta["logo"]).is_absolute() and Path(meta["logo"]).is_file()
    assert meta["alt"] == "Red Hat Agent Starter Kits"
    assert meta["shadowed"] == []
    assert sorted(meta["generated"]) == ui_files(ui)


def test_render_rhdp_footer_keeps_the_stock_partial(proj):
    branded(proj, {"logo_text": "Kits", "footer": "rhdp"})
    ui = branding.render(proj, "internal")
    assert ui == (proj / "build" / "branding" / "internal" / "ui").resolve()
    assert not (ui / "partials" / "footer-content.hbs").exists()
    assert (ui.parent / "branding.json").is_file()


def test_render_copies_an_own_logo_byte_for_byte(proj):
    branded(proj, {"logo": "branding/logo.svg", "logo_alt": "Example product"})
    ui = branding.render(proj, "shareable")
    assert (ui / "img" / "logo-guide.svg").read_bytes() == (proj / "branding" / "logo.svg").read_bytes()
    assert json.loads((ui.parent / "branding.json").read_text())["alt"] == "Example product"


def test_render_overlay_wins_and_is_reported(proj):
    branded(proj, {"logo_text": "Kits"})
    overlay = proj / "ui" / "supplemental"
    (overlay / "partials").mkdir(parents=True)
    (overlay / "img").mkdir()
    (overlay / "partials" / "footer-content.hbs").write_text('<footer class="footer">mine</footer>\n')
    (overlay / "img" / "extra.png").write_bytes(b"png")
    ui = branding.render(proj, "shareable")
    assert (ui / "partials" / "footer-content.hbs").read_text() == '<footer class="footer">mine</footer>\n'
    assert (ui / "img" / "extra.png").read_bytes() == b"png"
    meta = json.loads((ui.parent / "branding.json").read_text())
    assert meta["shadowed"] == ["partials/footer-content.hbs"]


def test_render_replaces_the_previous_overlay(proj):
    branded(proj, {"logo_text": "Kits"})
    first = branding.render(proj, "shareable")
    (first / "stale.txt").write_text("left over\n")
    second = branding.render(proj, "shareable")
    assert second == first
    assert not (second / "stale.txt").exists()
    leftovers = [p.name for p in (proj / "build" / "branding").iterdir() if ".tmp-" in p.name or ".old-" in p.name]
    assert leftovers == []


def test_render_overlay_only(proj):
    write_guide(proj, "antora")
    css = proj / "ui" / "supplemental" / "css"
    css.mkdir(parents=True)
    (css / "extra.css").write_text(".doc{font-size:1.1em}\n")
    ui = branding.render(proj, "shareable")
    assert ui_files(ui) == ["css/extra.css", "partials/head-meta.hbs"]
    meta = (ui / "partials" / "head-meta.hbs").read_text()
    assert '<link rel="icon" href="{{uiRootPath}}/img/favicon.ico" type="image/x-icon">' in meta
    assert '<link rel="stylesheet" href="{{{uiRootPath}}}/css/extra.css">' in meta
    assert not (ui.parent / "branding.json").exists()
    (css / "extra.css").unlink()
    (css / "more.css").write_text("a{}\n")
    assert ui_files(branding.render(proj, "shareable")) == ["css/more.css"]


def test_render_changes_nothing_outside_build(proj):
    branded(proj, {"logo_text": "Kits", "footer": {"text": "Kits"}})
    (proj / "ui" / "supplemental").mkdir(parents=True)
    (proj / "ui" / "supplemental" / "x.txt").write_text("x\n")

    def snapshot():
        return {p.relative_to(proj).as_posix(): p.read_bytes() for p in proj.rglob("*")
                if p.is_file() and "build" not in p.relative_to(proj).parts}
    before = snapshot()
    branding.render(proj, "shareable")
    branding.render(proj, "internal")
    assert snapshot() == before


def test_render_every_key_under_one_second(proj):
    branded(proj, {"logo_text": "Agent Starter Kits", "logo_alt": "Red Hat Agent Starter Kits",
                   "footer": {"text": "Kits", "url": "https://example.com"},
                   "favicon": "branding/favicon.png", "color": "#3e8635"})
    started = time.perf_counter()
    branding.render(proj, "shareable")
    assert time.perf_counter() - started < 5.0     # about 10 ms; generous for a loaded runner


# --- favicon, accent color, head partials (T026) -----------------------------------

import re  # noqa: E402

MIMES = {"ico": "image/x-icon", "png": "image/png", "svg": "image/svg+xml"}


@pytest.mark.parametrize("ext", ["ico", "png", "svg"])
def test_render_favicon(proj, ext):
    (proj / "branding" / f"icon.{ext}").write_bytes(b"icon-bytes")
    branded(proj, {"logo_text": "Kits", "favicon": f"branding/icon.{ext}"})
    ui = branding.render(proj, "shareable")
    assert (ui / "img" / f"favicon-guide.{ext}").read_bytes() == b"icon-bytes"
    icons = (ui / "partials" / "head-icons.hbs").read_text()
    assert f'<link rel="icon" href="{{{{{{uiRootPath}}}}}}/img/favicon-guide.{ext}" type="{MIMES[ext]}">' in icons
    meta = (ui / "partials" / "head-meta.hbs").read_text().splitlines()
    assert meta[0] == f'<link rel="icon" href="{{{{uiRootPath}}}}/img/favicon-guide.{ext}" type="{MIMES[ext]}">'
    assert "branding.css" not in "".join(meta)


def test_render_color_css(proj):
    branded(proj, {"logo_text": "Kits", "color": "#3e8635"})
    ui = branding.render(proj, "shareable")
    css = (ui / "css" / "branding.css").read_text()
    contract = yaml.safe_load((branding.asset_dir() / "contract.yaml").read_text())
    assert contract["accent_selectors"] and contract["accent_hover_selectors"]

    def rule(entry, value):
        return re.compile(re.escape(entry["selector"]) + r"\s*\{\s*" + re.escape(entry["property"])
                          + r"\s*:\s*" + re.escape(value) + r"\s*;?\s*\}")
    for entry in contract["accent_selectors"]:
        assert rule(entry, "#3e8635").search(css), entry
    for entry in contract["accent_hover_selectors"]:
        assert rule(entry, "#2f6528").search(css), entry
    # Rules that follow the accent rules in site.css with the same specificity keep their
    # stock color (an unresolved link stays red on hover): restated after the hover rules.
    assert contract["accent_restore_selectors"]
    last_hover = max(css.index(e["selector"] + " {") for e in contract["accent_hover_selectors"])
    for entry in contract["accent_restore_selectors"]:
        match = rule(entry, entry["value"]).search(css)
        assert match and match.start() > last_hover, entry
    assert "#06c" not in css.lower() and "#004d99" not in css.lower()
    # US6-2: note admonitions (and everything else outside the contract) keep the stock blue.
    assert "admonition" not in css and "note" not in css
    assert all("admonition" not in e["selector"] for key in ("accent_selectors", "accent_hover_selectors")
               for e in contract[key])
    # The active table-of-contents entry keeps its dark text when hovered.
    assert ".toc .toc-menu a.is-active { color: #151515; }" in css
    meta = (ui / "partials" / "head-meta.hbs").read_text().splitlines()
    assert meta == ['<link rel="icon" href="{{uiRootPath}}/img/favicon.ico" type="image/x-icon">',
                    '<link rel="stylesheet" href="{{{uiRootPath}}}/css/branding.css">']
    assert not (ui / "partials" / "head-icons.hbs").exists()


def test_head_meta_links_branding_then_extra_css(proj):
    (proj / "branding" / "icon.png").write_bytes(b"png")
    branded(proj, {"logo_text": "Kits", "color": "#3e8635", "favicon": "branding/icon.png"})
    css = proj / "ui" / "supplemental" / "css"
    css.mkdir(parents=True)
    (css / "extra.css").write_text(".doc{font-size:1.1em}\n")
    ui = branding.render(proj, "shareable")
    meta = (ui / "partials" / "head-meta.hbs").read_text().splitlines()
    assert meta == ['<link rel="icon" href="{{uiRootPath}}/img/favicon-guide.png" type="image/png">',
                    '<link rel="stylesheet" href="{{{uiRootPath}}}/css/branding.css">',
                    '<link rel="stylesheet" href="{{{uiRootPath}}}/css/extra.css">']
    assert (ui / "css" / "extra.css").is_file() and (ui / "css" / "branding.css").is_file()


def test_no_head_meta_without_color_favicon_or_extra_css(proj):
    branded(proj, {"logo_text": "Kits"})
    ui = branding.render(proj, "shareable")
    assert not (ui / "partials" / "head-meta.hbs").exists()
    assert not (ui / "partials" / "head-icons.hbs").exists()
    assert not (ui / "css" / "branding.css").exists()


def test_shadowing_warning_for_the_footer(proj):
    partials = proj / "ui" / "supplemental" / "partials"
    partials.mkdir(parents=True)
    (partials / "footer-content.hbs").write_text('<footer class="footer">mine</footer>\n')
    _, warnings = run_check(proj, {"logo_text": "Kits", "footer": {"text": "Kits"}})
    assert warnings == [("ui/supplemental/partials/footer-content.hbs", "shadows the file generated for branding.footer")]
    _, none = run_check(proj, {"logo_text": "Kits", "footer": "rhdp"})
    assert none == []


def test_shadowing_warnings_for_color_and_favicon(proj):
    (proj / "branding" / "icon.png").write_bytes(b"png")
    overlay = proj / "ui" / "supplemental"
    (overlay / "css").mkdir(parents=True)
    (overlay / "img").mkdir()
    (overlay / "css" / "branding.css").write_text("a{}\n")
    (overlay / "img" / "favicon-guide.png").write_bytes(b"png")
    _, warnings = run_check(proj, {"logo_text": "Kits", "color": "#3e8635", "favicon": "branding/icon.png"})
    assert ("ui/supplemental/css/branding.css", "shadows the file generated for branding.color") in warnings
    assert ("ui/supplemental/img/favicon-guide.png", "shadows the file generated for branding.favicon") in warnings


# --- bundle contract (T031) ----------------------------------------------------------

import zipfile  # noqa: E402

CONTRACT = branding.asset_dir() / "contract.yaml"


def _literal(regex: str) -> str:
    """Text that a contract regex matches: [\\s\\S]* becomes a newline, escapes are dropped."""
    return re.sub(r"\\(.)", r"\1", regex.replace(r"[\s\S]*", "\n"))


def contract_parts(contract: dict) -> list[tuple[str, str]]:
    """(rule id, part) for every part a synthetic bundle can leave out or change."""
    parts = []
    for rule in contract["rules"]:
        parts.append((rule["id"], "rule"))
    for key, prefix in (("accent_selectors", "accent"), ("accent_hover_selectors", "accent"),
                        ("accent_restore_selectors", "restore")):
        for entry in contract[key]:
            parts.append((f"{prefix}:{entry['selector']}", prefix))
    return parts


def rule_needles(rule: dict) -> list[str]:
    """Every string and regular expression of a contract rule, in check order."""
    return list(rule.get("contains") or []) + list(rule.get("matches") or [])


def synthetic_bundle(dest: Path, contract: dict, broken: str | None = None, needle: int = 0) -> Path:
    """A minimal bundle that satisfies contract, or breaks exactly the rule `broken`
    (by leaving out its needle-th string or regular expression)."""
    files: dict[str, list[str]] = {}
    for rule in contract["rules"]:
        lines = files.setdefault(rule["file"], [])
        hit = rule["id"] == broken
        if "equals" in rule:
            lines.append(rule["equals"] + (" changed" if hit else ""))
        for i, text in enumerate(rule.get("contains") or []):
            if not (hit and i == needle):
                lines.append(text)
        offset = len(rule.get("contains") or [])
        for i, regex in enumerate(rule.get("matches") or []):
            text = _literal(regex)
            assert re.search(regex, text), regex
            if not (hit and offset + i == needle):
                lines.append(text)
        if hit and rule.get("exists") and len([r for r in contract["rules"] if r["file"] == rule["file"]]) == 1:
            files.pop(rule["file"])
    # Accent rules first: everything between two rules is selector text in CSS, so the
    # bare contains strings of the site-css rule must not precede a rule.
    css: list[str] = []
    for key, color, prefix in (("accent_selectors", contract["accent_color"], "accent"),
                               ("accent_hover_selectors", contract["accent_hover_color"], "accent"),
                               ("accent_restore_selectors", None, "restore")):
        for entry in contract[key]:
            if f"{prefix}:{entry['selector']}" != broken:
                css.append(f"{entry['selector']}{{{entry['property']}:{color or entry['value']}}}")
    files["css/site.css"] = css + files.get("css/site.css", [])
    for rel, lines in files.items():
        path = dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n")
    return dest


def zip_dir(src: Path, dest: Path) -> Path:
    with zipfile.ZipFile(dest, "w") as zf:
        for path in sorted(src.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(src).as_posix())
    return dest


def test_contract_passes_for_a_complete_bundle(tmp_path):
    contract = branding.load_contract(CONTRACT)
    bundle = synthetic_bundle(tmp_path / "bundle", contract)
    assert branding.check_bundle(bundle, CONTRACT) == []
    assert branding.check_bundle(zip_dir(bundle, tmp_path / "ui-bundle.zip"), CONTRACT) == []


def test_contract_names_every_missing_part(tmp_path):
    contract = branding.load_contract(CONTRACT)
    parts = contract_parts(contract)
    assert len(parts) == len(contract["rules"]) + 9
    for i, (rule_id, _) in enumerate(parts):
        bundle = synthetic_bundle(tmp_path / f"b{i}", contract, broken=rule_id)
        lines = branding.check_bundle(bundle, CONTRACT)
        assert len(lines) == 1 and lines[0].startswith(f"contract: {rule_id}: "), (rule_id, lines)
        zipped = branding.check_bundle(zip_dir(bundle, tmp_path / f"b{i}.zip"), CONTRACT)
        assert zipped == lines


def test_contract_names_every_missing_string(tmp_path):
    # SC-007: leaving out any one string or pattern of a rule fails that rule, not only the first.
    contract = branding.load_contract(CONTRACT)
    checked = 0
    for rule in contract["rules"]:
        for n, _ in enumerate(rule_needles(rule)):
            bundle = synthetic_bundle(tmp_path / f"{rule['id']}-{n}", contract, broken=rule["id"], needle=n)
            lines = branding.check_bundle(bundle, CONTRACT)
            assert len(lines) == 1 and lines[0].startswith(f"contract: {rule['id']}: "), (rule["id"], n, lines)
            checked += 1
    assert checked > len(contract["rules"])


def test_contract_guards_the_include_chain():
    # The overlay replaces partials that the layouts reach through header.hbs and footer.hbs.
    contract = branding.load_contract(CONTRACT)
    needles = {(r["file"], n) for r in contract["rules"] for n in rule_needles(r)}
    assert ("partials/header.hbs", "{{> header-content}}") in needles
    assert ("partials/footer.hbs", "{{> footer-content}}") in needles
    for layout in ("layouts/default.hbs", "layouts/404.hbs"):
        assert {(layout, "{{> header}}"), (layout, "{{> footer}}"), (layout, "{{> head ")} <= needles


@pytest.mark.parametrize("rule", [{"id": "x", "file": "a.hbs", "exist": True},
                                  {"id": "x", "file": "a.hbs", "exists": False}])
def test_contract_rejects_unknown_rule_keys(tmp_path, rule):
    contract = tmp_path / "contract.yaml"
    contract.write_text(yaml.safe_dump({"accent_color": "#06c", "accent_hover_color": "#004d99", "rules": [rule]}))
    (tmp_path / "bundle").mkdir()
    (tmp_path / "bundle" / "a.hbs").write_text("x\n")
    with pytest.raises(ValueError, match="contract rule x"):
        branding.check_bundle(tmp_path / "bundle", contract)


def test_contract_failure_messages(tmp_path):
    contract = branding.load_contract(CONTRACT)
    missing = synthetic_bundle(tmp_path / "a", contract, broken="alt-helper")
    assert branding.check_bundle(missing, CONTRACT) == ["contract: alt-helper: helpers/navbar-logo-alt.js: missing file"]
    changed = synthetic_bundle(tmp_path / "b", contract, broken="head-meta-stock")
    assert branding.check_bundle(changed, CONTRACT) == [
        "contract: head-meta-stock: partials/head-meta.hbs: content differs from the recorded stock content"]
    gone = synthetic_bundle(tmp_path / "c", contract, broken="footer-partial")
    assert branding.check_bundle(gone, CONTRACT) == [
        'contract: footer-partial: partials/footer-content.hbs: missing "<footer class="footer">"']
    nomatch = synthetic_bundle(tmp_path / "d", contract, broken="logo-lookup")
    (line,) = branding.check_bundle(nomatch, CONTRACT)
    assert line.startswith("contract: logo-lookup: partials/header-content.hbs: no match for /")


def test_contract_cli(tmp_path):
    contract = branding.load_contract(CONTRACT)
    good = synthetic_bundle(tmp_path / "good", contract)
    bad = synthetic_bundle(tmp_path / "bad", contract, broken="logo-lookup")
    cmd = [sys.executable, str(TOOLKIT / "branding.py"), "contract", "--contract", str(CONTRACT), "--bundle"]
    ok = subprocess.run(cmd + [str(zip_dir(good, tmp_path / "good.zip"))], capture_output=True, text=True)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    fail = subprocess.run(cmd + [str(bad)], capture_output=True, text=True)
    assert fail.returncode == 1
    assert "contract: logo-lookup: partials/header-content.hbs" in fail.stdout


# --- review fixes: render cleanup, create intake guards --------------------------------


def test_render_leaves_no_temporary_directory_on_failure(proj, monkeypatch):
    branded(proj, {"logo_text": "Kits"})

    def broken(*args, **kwargs):
        raise OSError("disk full")
    monkeypatch.setattr(branding, "alt_helper", broken)
    with pytest.raises(OSError, match="disk full"):
        branding.render(proj, "shareable")
    leftovers = sorted(p.name for p in (proj / "build" / "branding").iterdir())
    assert leftovers == []


REPO = TOOLKIT.parent.parent


def test_template_branding_example_validates(tmp_path):
    # The commented example in templates/guide.yaml is what create writes (FR-028).
    lines = (REPO / "guide" / "templates" / "guide.yaml").read_text().splitlines()
    start = lines.index("# branding:")
    block = [line[2:] for line in lines[start:] if line.startswith("# ") or line == "#"]
    data = yaml.safe_load("\n".join(block))
    raw = data["branding"]
    assert raw["logo_text"] == "Agent Starter Kits" and raw["color"] == "#3e8635"
    (tmp_path / "branding").mkdir()
    (tmp_path / "branding" / "favicon.png").write_bytes(b"png")
    problems, warnings = branding.check(tmp_path, raw, "antora", list(branding.KEYS))
    assert problems == [] and warnings == []


def test_create_intake_states_the_branding_rules():
    # FR-028, FR-030: the intake asks only for Antora, says logo_text renders the Red Hat
    # logo for Red Hat products, copies own files into branding/, and leaves out color.
    skill = (REPO / "guide" / "skills" / "create" / "SKILL.md").read_text()
    intake = skill[skill.index("**Branding** (Antora only"):]
    intake = intake[:intake.index("\n6. ")]
    assert "do not ask for `mkdocs` or `gfm`" in intake
    assert "Red Hat products" in intake and "own logo file" in intake
    assert "Alt text" in intake and "required for an own logo file" in intake
    assert "Favicon" in intake and "Footer" in intake
    assert "accent color (`color`) and the overlay directory `ui/supplemental/` are not part of the intake" in intake
    assert "Copy an own logo or favicon file into `GUIDE/branding/`" in skill
    docs = (REPO / "guide" / "docs" / "branding.md").read_text()
    assert "It is meant for guides about Red Hat products. A guide about another product uses its own `logo` instead." in docs
