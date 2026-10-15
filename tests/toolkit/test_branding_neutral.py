"""guide/toolkit/branding.py: wordmark, neutral theme, fonts, outlines (specs/003-neutral-branding)."""
import hashlib
import math
import shutil
from pathlib import Path

import pytest

import branding

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "branding"
KEYS = list(branding.KEYS)
EXCLUSIVE = "set exactly one of logo_text, wordmark, or logo"
HAN = chr(0x6F22)             # a CJK character Red Hat Display has no glyph for
REFRESH = "refresh the toolkit (scaffold-project.sh --toolkit-only)"


@pytest.fixture
def proj(tmp_path: Path) -> Path:
    root = tmp_path / "guide"
    (root / "branding").mkdir(parents=True)
    (root / "branding" / "logo.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n')
    return root


def problems_of(root, raw, fmt="antora", keys=None):
    return branding.check(root, raw, fmt, KEYS if keys is None else keys)[0]


def assert_problem(root, raw, loc, message, **kw):
    problems = problems_of(root, raw, **kw)
    assert (loc, message) in problems, problems


def assert_clean(root, raw):
    assert problems_of(root, raw) == []


# --- keys and validation (T008) -------------------------------------------------------------


@pytest.mark.parametrize("raw", [
    {"footer": "none"},
    {"logo_text": "A", "wordmark": "B"},
    {"wordmark": "B", "logo": "branding/logo.svg", "logo_alt": "x"},
    {"logo_text": "A", "wordmark": "B", "logo": "branding/logo.svg", "logo_alt": "x"},
])
def test_exactly_one_logo_key(proj, raw):
    assert_problem(proj, raw, "guide.yaml:branding", EXCLUSIVE)


@pytest.mark.parametrize("raw", [
    {"wordmark": "OpenClaw on OpenShift"},
    {"wordmark": "x" * 40, "theme": "neutral"},
    {"logo_text": "OpenShift AI", "theme": "neutral"},
    {"logo_text": "OpenShift AI", "theme": "stock"},
    {"logo": "branding/logo.svg", "logo_alt": "Mine", "theme": "neutral"},
])
def test_valid_blocks(proj, raw):
    assert_clean(proj, raw)


@pytest.mark.parametrize("value,got", [("", "0"), ("   ", "0"), ("a\nb", "3"), ("x" * 41, "41")])
def test_wordmark_length(proj, value, got):
    assert_problem(proj, {"wordmark": value}, "guide.yaml:branding.wordmark",
                   f"must be one line of 1 to 40 characters (got {got})")


@pytest.mark.parametrize("value,got", [("dark", "dark"), ("", '""'), (1, "1"), (None, "null")])
def test_theme_values(proj, value, got):
    assert_problem(proj, {"wordmark": "W", "theme": value}, "guide.yaml:branding.theme",
                   f"must be neutral or stock (got {got})")


def test_wordmark_without_glyph(proj):
    msg = f'no glyph for "{HAN}" (U+6F22) in Red Hat Display'
    assert_problem(proj, {"wordmark": f"A{HAN}B{HAN}"}, "guide.yaml:branding.wordmark", msg)
    assert len([p for p in problems_of(proj, {"wordmark": f"A{HAN}B{HAN}"}) if "no glyph" in p[1]]) == 1


def test_missing_glyphs_in_text_order(proj):
    other = chr(0x5B57)
    problems = problems_of(proj, {"wordmark": f"{other}{HAN}{other}"})
    glyphs = [m for loc, m in problems if "no glyph" in m]
    assert glyphs == [f'no glyph for "{other}" (U+5B57) in Red Hat Display',
                      f'no glyph for "{HAN}" (U+6F22) in Red Hat Display']


def test_logo_text_glyphs_checked_only_when_neutral(proj):
    assert_clean(proj, {"logo_text": f"A{HAN}"})
    assert_clean(proj, {"logo_text": f"A{HAN}", "theme": "stock"})
    assert_problem(proj, {"logo_text": f"A{HAN}", "theme": "neutral"}, "guide.yaml:branding.logo_text",
                   f'no glyph for "{HAN}" (U+6F22) in Red Hat Display')


@pytest.mark.parametrize("fmt", ["mkdocs", "gfm"])
@pytest.mark.parametrize("key,value", [("wordmark", "W"), ("theme", "neutral")])
def test_new_keys_not_supported_elsewhere(proj, fmt, key, value):
    assert_problem(proj, {key: value}, f"guide.yaml:branding.{key}", f"not supported by the {fmt} adapter",
                   fmt=fmt, keys=[])


# --- font manifest (T009) -------------------------------------------------------------------


def test_manifest_shape_and_checksums():
    manifest = branding.load_manifest()
    assert manifest["release"] == "5.0.0"
    assert len(manifest["files"]) == 6
    for entry in manifest["files"]:
        assert set(entry) == {"file", "upstream", "sha256", "family", "style", "weight"}
        data = (branding.fonts_dir() / entry["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"], entry["file"]
    assert (branding.fonts_dir() / "OFL.txt").is_file()


def test_display_coverage():
    manifest = branding.load_manifest()
    assert branding.missing_glyphs("".join(map(chr, range(0x20, 0x7F))), manifest) == []
    assert branding.missing_glyphs(chr(0xE9)) == []
    assert branding.missing_glyphs(f"Agent & Kits {HAN}") == [HAN]


@pytest.fixture
def vendored(proj, monkeypatch) -> Path:
    """A copy of the fonts inside the guide project, used as fonts_dir()."""
    fonts = proj / "tools" / "guide" / "branding" / "fonts"
    shutil.copytree(branding.fonts_dir(), fonts, ignore=shutil.ignore_patterns("update-fonts.py"))
    monkeypatch.setattr(branding, "fonts_dir", lambda: fonts)
    return fonts


def test_check_fonts_clean(proj, vendored):
    assert branding.check_fonts(proj) == []


def test_check_fonts_missing_and_mismatch(proj, vendored):
    (vendored / "RedHatText-VF.woff2").unlink()
    (vendored / "OFL.txt").unlink()
    with (vendored / "RedHatMono-VF.woff2").open("ab") as fh:
        fh.write(b"x")
    assert branding.check_fonts(proj) == [
        ("tools/guide/branding/fonts/RedHatText-VF.woff2", f"missing; {REFRESH}"),
        ("tools/guide/branding/fonts/RedHatMono-VF.woff2", f"checksum mismatch; {REFRESH}"),
        ("tools/guide/branding/fonts/OFL.txt", f"missing; {REFRESH}"),
    ]


def test_font_problems_reported_only_when_needed(proj, vendored):
    (vendored / "RedHatText-VF.woff2").unlink()
    loc = "tools/guide/branding/fonts/RedHatText-VF.woff2"
    assert_clean(proj, {"logo_text": "A"})
    assert_clean(proj, {"logo_text": "A", "theme": "stock"})
    assert_problem(proj, {"logo_text": "A", "theme": "neutral"}, loc, f"missing; {REFRESH}")
    assert_problem(proj, {"wordmark": "A"}, loc, f"missing; {REFRESH}")


def test_missing_manifest(proj, vendored):
    (vendored / "fonts.yaml").unlink()
    assert_problem(proj, {"wordmark": "A"}, "tools/guide/branding/fonts/fonts.yaml", f"missing; {REFRESH}")


def test_plugin_tree_location():
    root = Path(__file__).resolve().parents[2]
    assert branding.check_fonts(root / "nowhere") == []
    loc = branding._font_location(root / "nowhere", branding.fonts_dir() / "OFL.txt")
    assert loc == "guide/adapters/antora/branding/fonts/OFL.txt"


# --- resolve (T010) -------------------------------------------------------------------------


def test_resolve_wordmark(proj):
    brand = branding.resolve(proj, {"wordmark": "  OpenClaw on OpenShift  "})
    assert brand.wordmark == "OpenClaw on OpenShift"
    assert brand.alt == "OpenClaw on OpenShift"
    assert brand.theme == "stock"
    assert brand.logo_text is None


def test_resolve_wordmark_alt_markup(proj):
    text = 'Agent & <Kits> "x"'
    brand = branding.resolve(proj, {"wordmark": text, "theme": "neutral"})
    assert brand.alt == text
    assert brand.theme == "neutral"
    assert '"Agent & <Kits> \\"x\\""' in branding.alt_helper(brand.alt)


def test_resolve_explicit_alt_wins(proj):
    assert branding.resolve(proj, {"wordmark": "W", "logo_alt": "Own"}).alt == "Own"


def test_resolve_logo_text_alt_unchanged(proj):
    brand = branding.resolve(proj, {"logo_text": "OpenShift AI", "theme": "neutral"})
    assert brand.alt == "Red Hat OpenShift AI"
    assert brand.wordmark is None


# --- stock output stays byte-identical (T001, SC-004) ------------------------------------


def test_stock_logo_svg_matches_golden_files():
    cases = {
        "stock-logo-agent-starter-kits.svg": "Agent Starter Kits",
        "stock-logo-summit.svg": "Summit",
        "stock-logo-escaped.svg": 'Agent & <Starter> "Kits"',
    }
    for name, text in cases.items():
        assert branding.logo_svg(text) == (GOLDEN / name).read_text(), name


def test_stock_head_meta_matches_golden_file():
    assert branding.head_meta(branding.STOCK_FAVICON, True, True) == \
        (GOLDEN / "stock-head-meta-color-extra.hbs").read_text()


# --- outlines and the wordmark logo (T013) --------------------------------------------------

import json  # noqa: E402
import re  # noqa: E402
import time  # noqa: E402

import yaml  # noqa: E402

NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def path_numbers(svg: str) -> list[str]:
    return [n for d in re.findall(r' d="([^"]*)"', svg) for n in NUMBER_RE.findall(d)]


def test_outline_counts_and_advance():
    paths, advance = branding.outline("OpenClaw on OpenShift", 500)
    assert len(paths) == 19                              # 21 characters, two spaces
    assert advance == pytest.approx(897.4, abs=0.5)
    assert branding.outline("OpenClaw on OpenShift", 500) == (paths, advance)


def test_outline_weight_changes_glyphs():
    assert branding.outline("O", 500)[0] != branding.outline("O", 700)[0]


def test_outline_keeps_internal_spaces():
    a, b = branding.outline("A", 500)[1], branding.outline("B", 500)[1]
    space = branding.outline(" ", 500)[1]
    assert branding.outline("A  B", 500)[1] == pytest.approx(a + 2 * space + b, abs=0.01)
    assert len(branding.outline("A  B", 500)[0]) == 2


def test_wordmark_svg_structure():
    text = "OpenClaw on OpenShift"
    svg = branding.wordmark_svg(text)
    _, advance = branding.outline(text, branding.WORDMARK_WEIGHT)
    assert "<text" not in svg and "<style" not in svg and "font-" not in svg    # SC-003
    assert svg.count("<path") >= 19
    assert f'viewBox="0 0 {math.ceil(advance)} 178.739"' in svg
    assert '<g transform="translate(0 118.07)" fill="#fff">' in svg     # capitals centered: (178.739 + 57.4) / 2
    assert "Red Hat Display" in svg and "5.0.0" in svg and "Open Font License" in svg
    numbers = path_numbers(svg)
    assert numbers and all(n != "-0" for n in numbers)
    assert all(len(n.split(".")[1]) <= 2 for n in numbers if "." in n)


def test_wordmark_svg_golden():
    assert branding.wordmark_svg("OpenClaw on OpenShift") == (GOLDEN / "wordmark-openclaw.svg").read_text()


def test_wordmark_svg_speed():
    branding.wordmark_svg("warm up")
    start = time.perf_counter()
    branding.wordmark_svg("W" * 40)
    assert time.perf_counter() - start < 0.5


# --- the neutral overlay (T014) --------------------------------------------------------------


def write_guide(root: Path, block: dict) -> Path:
    data = {"schema": 1, "title": "T", "format": "antora", "personas": [{"id": "a", "title": "A", "start": "a"}],
            "branding": block}
    root.mkdir(parents=True, exist_ok=True)
    (root / "guide.yaml").write_text(yaml.safe_dump(data, sort_keys=False))
    return root


NEUTRAL = {"wordmark": "OpenClaw on OpenShift", "theme": "neutral", "footer": "none"}
FONT_NAMES = [e["file"] for e in branding.load_manifest()["files"]]


def test_neutral_overlay_files(proj):
    ui = branding.render(write_guide(proj, NEUTRAL), "shareable")
    for name in FONT_NAMES + ["OFL.txt"]:
        assert (ui / "font" / name).read_bytes() == (branding.fonts_dir() / name).read_bytes(), name
    assert (ui / "css" / "theme-neutral.css").read_text() == branding.theme_css()
    logo = (ui / "img" / "logo-guide.svg").read_text()
    assert logo == branding.wordmark_svg("OpenClaw on OpenShift")
    head = (ui / "partials" / "head-meta.hbs").read_text()
    assert head == branding.STOCK_FAVICON + '\n<link rel="stylesheet" href="{{{uiRootPath}}}/css/theme-neutral.css">\n'
    styles = (ui / "partials" / "head-styles.hbs").read_text()
    assert styles == '    <link rel="stylesheet" href="{{{uiRootPath}}}/css/site.css">\n'
    assert "googleapis" not in styles and "gstatic" not in styles


def test_neutral_head_styles_is_the_stock_partial_minus_google_fonts():
    contract = branding.load_contract()
    (rule,) = [r for r in contract["rules"] if r["id"] == "head-styles-stock"]
    stock = [line.strip() for line in rule["equals"].splitlines()]
    kept = [line for line in stock if "fonts.googleapis.com" not in line and "fonts.gstatic.com" not in line]
    assert len(stock) - len(kept) == 3
    assert [line.strip() for line in branding.NEUTRAL_HEAD_STYLES.splitlines()] == kept


def test_theme_css_content():
    css = branding.theme_css()
    lines = css.splitlines()
    assert lines[0] == "/* Generated by tools/guide/branding.py from the guide.yaml branding theme; do not edit. */"
    faces = [l for l in lines if l.startswith("@font-face")]
    assert len(faces) == 6
    entry = branding.load_manifest()["files"][2]
    lo, hi = entry["weight"]
    assert faces[2] == (f'@font-face {{ font-family: "{entry["family"]}"; src: url("../font/{entry["file"]}") '
                        f'format("woff2"); font-weight: {lo} {hi}; font-style: {entry["style"]}; '
                        'font-display: swap; }')
    assert lines[-1] == ".navbar { box-shadow: inset 0 -3px 0 #e00; }"
    assert len(lines) == 8
    for word in ("color:", " a ", "admonition", "code", "toc"):
        assert word not in css.lower().replace("font-", "")


def test_head_meta_order_with_color_and_extra(proj):
    write_guide(proj, dict(NEUTRAL, color="#3e8635"))
    (proj / "ui" / "supplemental" / "css").mkdir(parents=True)
    (proj / "ui" / "supplemental" / "css" / "extra.css").write_text("a{}\n")
    head = (branding.render(proj, "shareable") / "partials" / "head-meta.hbs").read_text().splitlines()
    assert [re.search(r"css/[\w-]+\.css", l).group(0) for l in head[1:]] == \
        ["css/branding.css", "css/theme-neutral.css", "css/extra.css"]


def test_branding_json_theme_fields(proj):
    ui = branding.render(write_guide(proj, NEUTRAL), "shareable")
    meta = json.loads((ui.parent / "branding.json").read_text())
    assert meta["theme"] == "neutral"
    assert meta["fonts"] == str(ui / "font")
    assert meta["font_faces"] == [{"family": e["family"], "file": e["file"], "weight": e["weight"],
                                   "style": e["style"]} for e in branding.load_manifest()["files"]]
    assert meta["alt"] == "OpenClaw on OpenShift"


def test_neutral_with_own_logo(proj):
    ui = branding.render(write_guide(proj, {"logo": "branding/logo.svg", "logo_alt": "Mine", "theme": "neutral"}),
                         "shareable")
    assert (ui / "img" / "logo-guide.svg").read_bytes() == (proj / "branding" / "logo.svg").read_bytes()
    assert (ui / "css" / "theme-neutral.css").is_file()
    assert (ui / "font" / "OFL.txt").is_file()


def test_author_theme_css_shadows(proj):
    write_guide(proj, NEUTRAL)
    (proj / "ui" / "supplemental" / "css").mkdir(parents=True)
    (proj / "ui" / "supplemental" / "css" / "theme-neutral.css").write_text("/* mine */\n")
    _, warnings = branding.check_guide(proj)
    assert "ui/supplemental/css/theme-neutral.css: warning: shadows the file generated for branding.theme" in warnings
    (proj / "ui" / "supplemental" / "partials").mkdir()
    (proj / "ui" / "supplemental" / "partials" / "head-styles.hbs").write_text("<!-- mine -->\n")
    _, warnings = branding.check_guide(proj)
    assert "ui/supplemental/partials/head-styles.hbs: warning: shadows the file generated for branding.theme" in warnings
    ui = branding.render(proj, "shareable")
    assert (ui / "css" / "theme-neutral.css").read_text() == "/* mine */\n"


def test_wordmark_with_stock_theme(proj):
    ui = branding.render(write_guide(proj, {"wordmark": "OpenClaw"}), "shareable")
    assert "<text" not in (ui / "img" / "logo-guide.svg").read_text()
    assert not (ui / "font").exists()
    assert not (ui / "css" / "theme-neutral.css").exists()
    assert not (ui / "partials" / "head-meta.hbs").exists()
    assert not (ui / "partials" / "head-styles.hbs").exists()
    meta = json.loads((ui.parent / "branding.json").read_text())
    assert meta["theme"] == "stock" and meta["fonts"] is None and meta["font_faces"] == []


# --- hat variant with outlined text (T025) ----------------------------------------------------

TEXT_RE = re.compile(r"<text\b[\s\S]*?</text>")


def test_neutral_logo_text_keeps_the_template():
    template = (branding.asset_dir() / "logo-text.svg.tmpl").read_text()
    svg = branding.logo_svg("OpenShift AI", "neutral")
    assert "<text" not in svg and "<style" not in svg
    outside = TEXT_RE.sub("", template).replace('viewBox="0 0 {{VIEWBOX_WIDTH}} 178.739"', "")
    for path in re.findall(r"<path\b[^>]*>", outside):
        assert path in svg
    assert "Mozilla Public License" in svg


def test_neutral_logo_text_outlines():
    text = "OpenShift AI"
    svg = branding.logo_svg(text, "neutral")
    paths, advance = branding.outline(text, branding.LOGO_TEXT_WEIGHT)
    group = re.search(r'<g transform="translate\(308 149\)" fill="#fff">([\s\S]*?)</g>', svg)
    assert group and group.group(1) == "".join(f'<path d="{d}"/>' for d in paths)
    assert len(paths) == 11                                    # 12 characters, one space
    assert f'viewBox="0 0 {max(780, math.ceil(308 + advance + 24))} 178.739"' in svg
    long = "W" * 40
    _, wide = branding.outline(long, branding.LOGO_TEXT_WEIGHT)
    assert f'viewBox="0 0 {math.ceil(308 + wide + 24)} 178.739"' in branding.logo_svg(long, "neutral")


def test_neutral_logo_text_golden():
    assert branding.logo_svg("OpenShift AI", "neutral") == \
        (GOLDEN / "logo-text-neutral-openshift-ai.svg").read_text()


def test_stock_logo_svg_unchanged_with_explicit_theme():
    for name, text in {"stock-logo-agent-starter-kits.svg": "Agent Starter Kits",
                       "stock-logo-summit.svg": "Summit"}.items():
        assert branding.logo_svg(text, "stock") == (GOLDEN / name).read_text()


def test_render_neutral_logo_text(proj):
    ui = branding.render(write_guide(proj, {"logo_text": "OpenShift AI", "theme": "neutral"}), "shareable")
    assert (ui / "img" / "logo-guide.svg").read_text() == branding.logo_svg("OpenShift AI", "neutral")
    meta = json.loads((ui.parent / "branding.json").read_text())
    assert meta["alt"] == "Red Hat OpenShift AI"


# --- stock guides stay as they were (T028, SC-004) ----------------------------------------


def test_logo_text_without_theme_renders_the_spec_002_file_set(proj):
    write_guide(proj, {"logo_text": "Agent Starter Kits", "color": "#3e8635"})
    (proj / "ui" / "supplemental" / "css").mkdir(parents=True)
    (proj / "ui" / "supplemental" / "css" / "extra.css").write_text("a{}\n")
    ui = branding.render(proj, "shareable")
    files = sorted(p.relative_to(ui).as_posix() for p in ui.rglob("*") if p.is_file())
    assert files == ["css/branding.css", "css/extra.css", "helpers/navbar-logo-alt.js", "img/logo-guide.svg",
                     "partials/footer-content.hbs", "partials/head-meta.hbs"]
    assert (ui / "img" / "logo-guide.svg").read_text() == (GOLDEN / "stock-logo-agent-starter-kits.svg").read_text()
    assert (ui / "partials" / "head-meta.hbs").read_text() == (GOLDEN / "stock-head-meta-color-extra.hbs").read_text()
    meta = json.loads((ui.parent / "branding.json").read_text())
    assert set(meta) == {"logo", "alt", "footer", "generated", "shadowed", "theme", "fonts", "font_faces"}
    assert (meta["theme"], meta["fonts"], meta["font_faces"]) == ("stock", None, [])


# --- deep review round 1: geometry, anchors, manifest, edge cases ----------------------------

import xml.dom.minidom  # noqa: E402

PATH_TOKEN_RE = re.compile(r"[MLHVCSQTAZmlhvcsqtaz]|-?\d+(?:\.\d+)?")


def ink_x(svg: str) -> tuple[float, float]:
    """Smallest and largest absolute x of all glyph path points, with the group's translate."""
    group = re.search(r'<g transform="translate\(([-\d.]+) [-\d.]+\)"[^>]*>([\s\S]*?)</g>', svg)
    shift = float(group.group(1))
    xs: list[float] = []
    for d in re.findall(r' d="([^"]*)"', group.group(2)):
        cmd, args = None, []
        for tok in PATH_TOKEN_RE.findall(d) + ["Z"]:
            if tok.isalpha():
                if cmd is not None:
                    assert cmd in "MLHVCSQTZ", f"relative or arc command {cmd} in {d[:40]}"
                    if cmd in "MLCSQT":
                        xs.extend(float(v) for v in args[0::2])
                    elif cmd == "H":
                        xs.extend(float(v) for v in args)
                cmd, args = tok, []
            else:
                args.append(tok)
    return shift + min(xs), shift + max(xs)


def viewbox_width(svg: str) -> float:
    return float(re.search(r'viewBox="0 0 ([\d.]+) ', svg).group(1))


# "Claw" + U+013E (l with caron) and "A\\" end in glyphs whose ink runs past their advance width.
OVERHANG = ["Claw" + chr(0x13E), "A\\"]


@pytest.mark.parametrize("text", ["jOpenClaw", "W" * 40, "OpenClaw on OpenShift", "fy", "j"] + OVERHANG)
def test_wordmark_never_clips(text):
    svg = branding.wordmark_svg(text)
    left, right = ink_x(svg)
    assert left >= 0 and right <= viewbox_width(svg), (left, right, viewbox_width(svg))


@pytest.mark.parametrize("text", ["jOpenClaw", "W" * 40, "fy"] + OVERHANG)
def test_neutral_hat_never_clips(text):
    svg = branding.logo_svg(text, "neutral")
    left, right = ink_x(svg)
    assert left > 260 and right <= viewbox_width(svg), (left, right)   # the divider sits at x 253.5


@pytest.mark.parametrize("text", OVERHANG)
def test_overhang_texts_really_overhang(text):
    """Keeps the overhang cases meaningful: their ink ends right of the advance width."""
    for weight in (branding.WORDMARK_WEIGHT, branding.LOGO_TEXT_WEIGHT):
        _, advance, _, right = branding._outline(text, weight)
        assert right > advance


def test_spec_weights_and_outlines_anchor():
    assert (branding.WORDMARK_WEIGHT, branding.LOGO_TEXT_WEIGHT) == (500, 700)      # FR-006, FR-007
    paths, _ = branding.outline("OpenClaw", 500)
    assert "".join(f'<path d="{d}"/>' for d in paths) in branding.wordmark_svg("OpenClaw")
    paths, _ = branding.outline("OpenShift AI", 700)
    assert "".join(f'<path d="{d}"/>' for d in paths) in branding.logo_svg("OpenShift AI", "neutral")


def test_manifest_matches_the_font_files():
    from fontTools.ttLib import TTFont
    manifest = branding.load_manifest()
    for entry in manifest["files"]:
        font = TTFont(branding.fonts_dir() / entry["file"])
        axis = next(a for a in font["fvar"].axes if a.axisTag == "wght")
        assert entry["weight"] == [int(axis.minValue), int(axis.maxValue)], entry["file"]
        assert (entry["style"] == "italic") == ("-Italic-" in entry["file"])
        assert entry["family"].replace(" ", "") == entry["file"].split("-")[0]
    covered = {cp for lo, hi in manifest["display_coverage"] for cp in range(lo, hi + 1)}
    assert covered == set(TTFont(branding.fonts_dir() / "RedHatDisplay-VF.woff2").getBestCmap())


def test_neutral_theme_size_budget():
    """SC-005: fonts, OFL.txt, and the theme stylesheet add at most 300 KB."""
    size = sum((branding.fonts_dir() / name).stat().st_size for name in branding.font_files())
    assert size + len(branding.theme_css().encode()) + len(branding.NEUTRAL_HEAD_STYLES) <= 300 * 1024


def test_wordmark_with_emoji_fails(proj):
    emoji = chr(0x1F600)
    assert_problem(proj, {"wordmark": f"Kits {emoji}"}, "guide.yaml:branding.wordmark",
                   f'no glyph for "{emoji}" (U+1F600) in Red Hat Display')


@pytest.mark.parametrize("render", [branding.wordmark_svg, lambda t: branding.logo_svg(t, "neutral")])
def test_markup_in_outlined_text_never_becomes_markup(render):
    svg = render('A & <B> "c"')
    xml.dom.minidom.parseString(svg)                  # well-formed
    assert "{{" not in svg and "<B>" not in svg and "&amp;" not in svg and "<text" not in svg


def test_author_font_file_shadows_the_vendored_one(proj):
    write_guide(proj, NEUTRAL)
    (proj / "ui" / "supplemental" / "font").mkdir(parents=True)
    (proj / "ui" / "supplemental" / "font" / "RedHatText-VF.woff2").write_bytes(b"mine")
    _, warnings = branding.check_guide(proj)
    assert "ui/supplemental/font/RedHatText-VF.woff2: warning: shadows the file generated for branding.theme" \
        in warnings
    assert (branding.render(proj, "shareable") / "font" / "RedHatText-VF.woff2").read_bytes() == b"mine"


def test_template_and_evolve_text_name_the_new_keys():
    repo = Path(__file__).resolve().parents[2]
    lines = (repo / "guide" / "templates" / "guide.yaml").read_text().splitlines()
    block = [line[2:] for line in lines[lines.index("# branding:"):] if line.startswith("# ") or line == "#"]
    assert yaml.safe_load("\n".join(block))["branding"]["theme"] == "neutral"            # FR-024
    assert "wordmark:" in "\n".join(lines)
    evolve = (repo / "guide" / "skills" / "evolve" / "SKILL.md").read_text()
    assert "Toolkit 0.4.0 adds the neutral theme" in evolve                              # FR-025
    assert "`theme: neutral`" in evolve and "`wordmark`" in evolve and "never edit the guide's `branding` block" in evolve


@pytest.mark.parametrize("text,detail", [
    ("release: [unclosed\n", "unreadable ("),
    ("release: 5.0.0\nfiles: {a: b}\ndisplay_coverage: []\n", "unreadable (files must be a non-empty list)"),
    ("release: 5.0.0\nfiles:\n- {file: RedHatText-VF.woff2}\ndisplay_coverage: []\n",
     "unreadable (files[0] is malformed)"),
    ("release: 5.0.0\nfiles:\n- {file: ../x.woff2, sha256: " + "0" * 64
     + ", family: Red Hat Text, style: normal, weight: [300, 700]}\ndisplay_coverage: []\n",
     "unreadable (files[0] is malformed)"),
    ("release: 5.0.0\nfiles:\n- {file: x.woff2, sha256: " + "0" * 64
     + ", family: 'Evil\"}', style: normal, weight: [300, 700]}\ndisplay_coverage: []\n",
     "unreadable (files[0] is malformed)"),
])
def test_damaged_manifest_is_a_problem_not_a_crash(proj, vendored, text, detail):
    (vendored / "fonts.yaml").write_text(text)
    problems = problems_of(proj, {"wordmark": "OpenClaw", "theme": "neutral"})
    assert [(loc, msg[:len(detail)]) for loc, msg in problems] == [("tools/guide/branding/fonts/fonts.yaml", detail)]
    assert problems[0][1].endswith(REFRESH)
    assert branding.generated_files({"wordmark": "W", "theme": "neutral"}, False)     # no crash


def test_missing_branding_directory_is_a_problem(proj, monkeypatch):
    def gone():
        raise FileNotFoundError("branding assets not found")
    monkeypatch.setattr(branding, "fonts_dir", gone)
    assert problems_of(proj, {"wordmark": "W"}) == [("tools/guide/branding", f"missing; {REFRESH}")]


def test_instance_cache_follows_the_font_file(proj, vendored):
    first = branding._display(500)
    font = vendored / "RedHatDisplay-VF.woff2"
    font.write_bytes(font.read_bytes())               # same bytes, new file: a new cache entry
    import os
    os.utime(font, ns=(font.stat().st_atime_ns, font.stat().st_mtime_ns + 1_000_000))
    assert branding._display(500) is not first
