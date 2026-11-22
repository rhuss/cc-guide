"""capture/render_cli.py: ANSI output to a self-contained SVG (FR-016, FR-018, FR-021)."""
import os
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "guide" / "toolkit" / "capture"))
import redact  # noqa: E402
import render_cli  # noqa: E402

FONT_DIR = REPO / "guide" / "adapters" / "antora" / "branding" / "fonts"
FONTS = {"regular": FONT_DIR / "RedHatMono-VF.woff2", "bold": FONT_DIR / "RedHatMono-VF.woff2",
         "italic": FONT_DIR / "RedHatMono-Italic-VF.woff2", "bolditalic": FONT_DIR / "RedHatMono-Italic-VF.woff2"}
VALUES = {"user": "alice", "home": "/home/alice", "host": "build-box"}
EMOJI_CANDIDATES = [os.environ.get("CCG_EMOJI_FONT", ""), "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
                    "/usr/share/fonts/noto/NotoColorEmoji.ttf", "/usr/share/fonts/google-noto-emoji/NotoColorEmoji.ttf"]

ESC = "\x1b"
SAMPLE = (f"{ESC}[1;32mPASS{ESC}[0m unit {ESC}[38;2;255;100;0mtruecolor{ESC}[0m {ESC}[38;5;27mblue256{ESC}[0m\r\n"
          f"███░░ 60%\r\n"
          f"progress 10%\rprogress 99%\r\n"
          f"{ESC}[2mdim{ESC}[22m {ESC}[3mitalic{ESC}[23m {ESC}[4munder{ESC}[24m {ESC}[7mrev{ESC}[27m\r\n").encode()


def render(raw=SAMPLE, command="tool --check", values=VALUES, **kw):
    rules = redact.resolve(redact.effective_rules(), values)
    kw.setdefault("emoji_font", None)
    return render_cli.render(raw, command, rules=rules, fonts=FONTS, **kw)


def tspans(svg: str) -> list[tuple[str, str]]:
    return re.findall(r"<tspan([^>]*)>([^<]*)</tspan>", svg)


def test_styled_runs():
    svg = render()["svg"].decode()
    spans = dict((text, attrs) for attrs, text in tspans(svg))
    assert 'fill="#4e9a06"' in spans["PASS"] and 'class="b"' in spans["PASS"]
    assert 'fill="#ff6400"' in spans["truecolor"]
    assert 'fill="#005fff"' in spans["blue256"]
    assert 'class="d"' in spans["dim"]
    assert 'class="i"' in spans["italic"]
    assert 'class="u"' in spans["under"]
    assert 'fill="#1e1e1e"' in spans["rev"]          # reverse video: background color as text


def test_reverse_draws_background_rect():
    svg = render()["svg"].decode()
    assert re.search(r'<rect x="[\d.]+" y="[\d.]+" width="[\d.]+" height="\d+" fill="#d4d4d4"/>', svg)


def test_carriage_return_overwrites():
    text = render()["text"]
    assert "progress 99%" in text and "progress 10%" not in text


def test_unicode_blocks_kept():
    result = render()
    assert "███░░ 60%" in result["text"]
    assert "███░░" in result["svg"].decode()


def test_prompt_line():
    result = render(prompt="$ ")
    assert result["text"].splitlines()[0] == "$ tool --check"
    assert render(prompt="% ")["text"].startswith("% tool --check")


def test_redaction_inside_colored_text_keeps_style():
    raw = f"saved {ESC}[1;33m/home/alice/x/report.md{ESC}[0m on {ESC}[36mbuild-box{ESC}[0m\r\n".encode()
    result = render(raw)
    svg = result["svg"].decode()
    assert "alice" not in svg and "build-box" not in svg and "alice" not in result["text"]
    spans = dict((text, attrs) for attrs, text in tspans(svg))
    assert 'fill="#c4a000"' in spans["/home/user/x/report.md"] and 'class="b"' in spans["/home/user/x/report.md"]
    assert 'fill="#06989a"' in spans["example-host"]
    assert result["redaction"]["home-path"] == 1 and result["redaction"]["hostname"] == 1


def test_command_line_is_redacted():
    result = render(b"ok\r\n", command="cat /home/alice/notes")
    assert result["text"].splitlines()[0] == "$ cat /home/user/notes"


def test_masks():
    raw = b"finished at 2025-03-04 05:06:07\r\n"
    result = render(raw, masks=[{"pattern": r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", "replacement": "2026-01-01 12:00:00"}])
    assert "2026-01-01 12:00:00" in result["text"] and result["masks"] == 1


def test_deterministic():
    a, b = render(), render()
    assert a["svg"] == b["svg"]
    assert a["style"] == b["style"] and len(a["style"]) == 16


def test_style_fingerprint_tracks_colors_not_only_text():
    plain = render(b"same text\r\n")["style"]
    colored = render(f"{ESC}[31msame text{ESC}[0m\r\n".encode())["style"]
    assert plain != colored
    assert render(b"same text\r\n")["text"] == render(f"{ESC}[31msame text{ESC}[0m\r\n".encode())["text"]


def test_self_contained_font():
    svg = render()["svg"].decode()
    assert "@font-face" in svg and "data:font/woff2;base64," in svg
    urls = re.findall(r"url\(([^)]*)\)", svg)
    assert urls and all(u.startswith("data:") for u in urls)
    assert not re.search(r"(?:href|src)=\"(?:https?:|//)", svg)
    assert "http://www.w3.org/" in svg            # only the namespaces
    assert not re.search(r"https?://(?!www\.w3\.org/)", svg)
    assert "<script" not in svg


def test_wraps_at_width():
    result = render(b"x" * 50 + b"\r\n", width=20)
    lines = result["text"].splitlines()[1:]
    assert lines == ["x" * 20, "x" * 20, "x" * 10]


def test_size_limit():
    with pytest.raises(render_cli.RenderError, match="byte limit"):
        render(max_bytes=1000)


def emoji_font() -> Path | None:
    for candidate in EMOJI_CANDIDATES:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    return None


def test_emoji_as_image():
    font = emoji_font()
    if font is None:
        pytest.skip("no CBDT emoji font (Noto Color Emoji) on this host")
    result = render("done \U0001F680 ok\r\n".encode(), emoji_font=font)
    svg = result["svg"].decode()
    assert "data:image/png;base64," in svg
    assert "\U0001F680" in result["text"]


def test_emoji_without_font_falls_back_to_text():
    svg = render("done \U0001F680\r\n".encode(), emoji_font=None)["svg"].decode()
    assert "<image" not in svg and "\U0001F680" in svg


def test_redaction_across_the_wrap_point():
    """A value the terminal would wrap is still redacted (checkpoint review finding 1)."""
    raw = ("x" * 35 + " /Users/alice/report.md\r\n").encode()
    result = render(raw, width=40, values={"user": "alice", "home": "/Users/alice", "host": "build-box"})
    assert "alice" not in result["text"] and "alice" not in result["svg"].decode()
    assert result["redaction"]["home-path"] == 1
    assert all(len(line) <= 40 for line in result["text"].splitlines())


def test_text_after_variation_selector_and_joiner_kept():
    """pyte 0.8.2 stops a chunk at U+FE0F or U+200D; clusters keep them (finding 2)."""
    text = render(("⚠" + chr(0xFE0F) + "  disk almost full\r\ndev \U0001F469" + chr(0x200D)
                   + "\U0001F4BB rest\r\n").encode())["text"]
    assert "disk almost full" in text and "rest" in text
    assert "⚠" + chr(0xFE0F) in text and "\U0001F469" + chr(0x200D) + "\U0001F4BB" in text


ZWJ_SEQUENCE = "\U0001F469" + chr(0x200D) + "\U0001F4BB"        # woman technologist
WARNING_EMOJI = "\u26a0" + chr(0xFE0F)                             # warning sign, emoji presentation
UNKNOWN_SEQUENCE = "\U0001F469" + chr(0x200D) + "\U0001F680" + chr(0x200D) + "\U0001F4BB"


def cells_of(text: str) -> list[tuple[str, int]]:
    line = render_cli.logical_lines(f"{text}\r\n".encode())[0]
    return [(c.ch, render_cli._width(c.ch)) for c in line]


def test_emoji_clusters_stay_in_one_cell():
    """ZWJ sequences, flags, keycaps, skin tones, and U+FE0F stay with their base."""
    flag = "\U0001F1E9\U0001F1EA"
    keycap = "1" + chr(0xFE0F) + chr(0x20E3)
    skin = "\U0001F44D\U0001F3FD"
    for cluster in (ZWJ_SEQUENCE, WARNING_EMOJI, flag, keycap, skin):
        assert cells_of(f"a{cluster}b") == [("a", 1), (cluster, 2), ("b", 1)]


def test_text_presentation_stays_narrow():
    assert cells_of("a\u26a0b") == [("a", 1), ("\u26a0", 1), ("b", 1)]
    assert cells_of("a\u26a0" + chr(0xFE0E) + "b") == [("a", 1), ("\u26a0" + chr(0xFE0E), 1), ("b", 1)]


def test_lone_format_characters_are_dropped():
    zwsp, zwj = chr(0x200B), chr(0x200D)
    assert cells_of(f"a{zwsp}b {zwj}c") == [("a", 1), ("b", 1), (" ", 1), ("c", 1)]
    assert cells_of(f"{zwj}a{zwj} " + chr(0xFE0F) + "b") == [("a", 1), (" ", 1), ("b", 1)]


def test_cluster_widths_drive_wrapping():
    line = render_cli.logical_lines(("x" * 9 + WARNING_EMOJI + "y\r\n").encode())[0]
    rows = render_cli.wrap(line, 10)
    assert ["".join(c.ch for c in row) for row in rows] == ["x" * 9, WARNING_EMOJI + "y"]


def test_command_line_keeps_clusters():
    cells = render_cli.text_cells("echo " + ZWJ_SEQUENCE)
    assert cells[-1].ch == ZWJ_SEQUENCE


def emoji_or_skip():
    font = emoji_font()
    if font is None:
        pytest.skip("no CBDT emoji font (Noto Color Emoji) on this host")
    return font, render_cli._Emoji(font)


def images(svg: str) -> list[str]:
    return re.findall(r'xlink:href="data:image/png;base64,([^"]+)"', svg)


def b64(png: bytes) -> str:
    import base64
    return base64.b64encode(png).decode()


def test_zwj_sequence_renders_its_ligature_glyph():
    font, emoji = emoji_or_skip()
    result = render(f"dev {ZWJ_SEQUENCE} rest\r\n".encode(), emoji_font=font)
    found = images(result["svg"].decode())
    ligature = emoji.png(ZWJ_SEQUENCE)
    assert found == [b64(ligature)]
    assert ligature != emoji.png("\U0001F469") and ligature != emoji.png("\U0001F4BB")
    assert ZWJ_SEQUENCE in result["text"]


def test_variation_selector_16_renders_as_emoji():
    font, emoji = emoji_or_skip()
    result = render(f"{WARNING_EMOJI} full\r\nplain \u26a0 sign\r\n".encode(), emoji_font=font)
    svg = result["svg"].decode()
    assert images(svg) == [b64(emoji.png(WARNING_EMOJI))]
    assert "plain \u26a0 sign" in svg                     # without U+FE0F: text presentation
    assert WARNING_EMOJI + " full" in result["text"]


def test_flag_keycap_and_skin_tone_are_single_glyphs():
    font, emoji = emoji_or_skip()
    for cluster in ("\U0001F1E9\U0001F1EA", "1" + chr(0xFE0F) + chr(0x20E3), "\U0001F44D\U0001F3FD"):
        names = [emoji.cmap[ord(c)] for c in cluster if ord(c) in emoji.cmap]
        assert emoji.glyph(cluster) not in names           # a ligature, not the first code point
        result = render(f"{cluster}\r\n".encode(), emoji_font=font)
        assert len(images(result["svg"].decode())) == 1


def test_unknown_sequence_falls_back_to_its_first_glyph():
    font, emoji = emoji_or_skip()
    result = render(f"{UNKNOWN_SEQUENCE}\r\n".encode(), emoji_font=font)
    assert len(images(result["svg"].decode())) == 1
    assert UNKNOWN_SEQUENCE in result["text"]


def test_long_prompt_and_lengthened_lines_wrap(tmp_path):
    """Nothing is clipped: the prompt and redaction-lengthened lines wrap at width (finding 3)."""
    command = "tool " + "--flag " * 20
    raw = ("y" * 38 + " mb\r\n").encode()
    result = render(raw, command=command.strip(), width=40, values={"user": "zz", "home": "/home/zz", "host": "mb"})
    lines = result["text"].splitlines()
    assert all(len(line) <= 40 for line in lines)
    assert "".join(lines).replace(" ", "").startswith("$tool--flag")
    assert "example-host" in result["text"].replace("\n", "")
    svg = result["svg"].decode()
    width = float(re.search(r'<svg[^>]* width="([\d.]+)"', svg).group(1))
    assert width < 40 * 14 * 0.7 + 2 * 12 + 1


def test_soft_wrapped_secret_is_redacted():
    # a line longer than the logical screen wraps inside pyte; the parts must be rejoined
    raw = b"A" * (render_cli.LOGICAL_COLUMNS - 6) + b" sk-" + b"B" * 32 + b"\r\nnext\r\n"
    lines = render_cli.logical_lines(raw)
    assert ["".join(c.ch for c in line)[-5:] for line in lines] == ["BBBBB", "next"]
    result = render(raw=raw, width=80)
    assert "sk-B" not in result["text"] and "<redacted>" in result["text"]
    assert result["redaction"]["api-key"] == 1


def test_too_many_lines_fail():
    with pytest.raises(render_cli.RenderError, match="more than"):
        render_cli.logical_lines(b"x\n" * (render_cli.MAX_ROWS + 1))
