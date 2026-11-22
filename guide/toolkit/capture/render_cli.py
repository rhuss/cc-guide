# /// script
# requires-python = ">=3.11"
# dependencies = ["pyte==0.8.2", "wcwidth==0.9.5", "fonttools[woff]==4.67.0", "brotli==1.1.0"]
# ///
"""Render raw terminal output into a self-contained SVG (specs/008-captured-visuals, R5).

The bytes a command wrote to its pseudo-terminal are fed into a pyte screen of the
visual's width, so carriage returns, cursor moves, and wrapping behave like a real
terminal. Each line becomes cells with a style; redaction rules and masks run on the
text of every line before anything is drawn, and a replacement takes the style of the
first replaced cell (FR-018, FR-021). The SVG has one <text> per line with a <tspan>
per style run, background rectangles, the monospaced font embedded as WOFF2 subsets in
@font-face data URLs, and emoji as embedded PNG bitmaps from the emoji font (FR-016).
A cell holds a whole grapheme cluster, so an emoji ZWJ sequence, a flag, a keycap, a
skin tone, or a base character with U+FE0F stays one emoji: its image is the font's
ligature glyph for the sequence (GSUB), and the sidecar text keeps every code point.
Output is deterministic: two renders of the same input are byte-identical.

    result = render(raw_bytes, command="ls", prompt="$ ", width=100, rules=resolved, masks=[])
    result["svg"]        bytes of the SVG
    result["text"]       plain text: the prompt line, then the output, right-trimmed
    result["style"]      16 hex over the text and its style runs (drift compares it)
    result["redaction"]  replacements per rule id; result["masks"] masked count
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pyte
from wcwidth import iter_graphemes, wcswidth, wcwidth

sys.path.insert(0, str(Path(__file__).resolve().parent))
import redact  # noqa: E402

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
DEFAULT_FONTS = {
    "regular": FONT_DIR / "DejaVuSansMono.ttf",
    "bold": FONT_DIR / "DejaVuSansMono-Bold.ttf",
    "italic": FONT_DIR / "DejaVuSansMono-Oblique.ttf",
    "bolditalic": FONT_DIR / "DejaVuSansMono-BoldOblique.ttf",
}
DEFAULT_EMOJI_FONT = Path("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf")
MAX_BYTES = 2 * 1024 * 1024
FONT_SIZE = 14
LINE_HEIGHT = 1.35
PADDING = 12
FAMILY = "ccg-mono"

BACKGROUND = "#1e1e1e"
FOREGROUND = "#d4d4d4"
PALETTE = {
    "black": "#2e3436", "red": "#cc0000", "green": "#4e9a06", "brown": "#c4a000",
    "blue": "#3465a4", "magenta": "#75507b", "cyan": "#06989a", "white": "#d3d7cf",
    "brightblack": "#555753", "brightred": "#ef2929", "brightgreen": "#8ae234", "brightbrown": "#fce94f",
    "brightblue": "#729fcf", "brightmagenta": "#ad7fa8", "brightcyan": "#34e2e2", "brightwhite": "#eeeeec",
}
# pyte names a few colors differently
ALIASES = {"yellow": "brown", "brightyellow": "brightbrown"}


class RenderError(Exception):
    pass


@dataclass(frozen=True)
class Style:
    fg: str = "default"
    bg: str = "default"
    bold: bool = False
    dim: bool = False
    italic: bool = False
    underline: bool = False
    reverse: bool = False

    def key(self) -> list:
        return [self.fg, self.bg, self.bold, self.dim, self.italic, self.underline, self.reverse]


@dataclass(frozen=True)
class Cell:
    ch: str
    style: Style


DEFAULT_STYLE = Style()


# --- terminal emulation -------------------------------------------------------


VS15, ZWJ = "\ufe0e", "\u200d"     # text presentation selector, zero width joiner
WIDE_STAND_IN = "\u4e00"     # any two-column character: pyte places it, the cluster replaces it


def _kept_in_cluster(ch: str) -> bool:
    """Format characters other than the emoji joiner and tag characters carry nothing visible."""
    cp = ord(ch)
    return unicodedata.category(ch) != "Cf" or ch == ZWJ or 0xE0020 <= cp <= 0xE007F


def clusters(text: str) -> list[str]:
    """The grapheme clusters of text as terminal cells hold them (NFC).

    A cluster keeps its joiners (U+200D), variation selectors (U+FE0F, U+FE0E), modifiers,
    keycap and tag characters; a joiner at its end and anything attached to a space are
    dropped. A lone zero-width character that is not a combining mark
    (a format character such as U+200B, a stray joiner or variation selector) is dropped:
    it has no cell, and pyte 0.8.2 stops drawing the rest of a chunk at one.
    """
    out: list[str] = []
    for g in iter_graphemes(text):
        g = unicodedata.normalize("NFC", g)
        if len(g) > 1:
            g = "".join(ch for ch in g if _kept_in_cluster(ch)).rstrip(ZWJ)   # a final joiner joins nothing
            if g and unicodedata.category(g[0]) == "Zs":
                g = g[0]          # a space with a stray selector or joiner is a space
        if len(g) == 1 and (unicodedata.category(g) == "Cf"
                            or (wcwidth(g) == 0 and not unicodedata.combining(g))):
            continue
        if g:
            out.append(g)
    return out


class _Screen(pyte.Screen):
    """pyte with grapheme clusters in cells, and dim (SGR 2) in the unused blink attribute."""

    def draw(self, data: str) -> None:
        for cluster in clusters(data):
            if len(cluster) == 1:
                super().draw(cluster)
                continue
            # pyte places one character per cell: draw a stand-in of the cluster's width
            # (wrapping, insert mode, and the stub slot of a wide cell stay pyte's), then
            # put the whole cluster into the cell it took
            width = _width(cluster)
            first = cluster[0]
            super().draw(first if wcwidth(first) == width else WIDE_STAND_IN if width == 2 else "x")
            line = self.buffer[self.cursor.y]
            x = self.cursor.x - 1
            if x > 0 and line[x].data == "":
                x -= 1
            if x >= 0:
                line[x] = line[x]._replace(data=cluster)

    def select_graphic_rendition(self, *attrs: int, private: bool = False) -> None:  # noqa: ARG002
        mapped: list[int] = []
        i = 0
        while i < len(attrs):
            a = attrs[i]
            if a in (38, 48) and i + 1 < len(attrs):
                n = 3 if attrs[i + 1] == 5 else 5 if attrs[i + 1] == 2 else 2
                mapped += list(attrs[i:i + n])
                i += n
                continue
            if a == 2:
                mapped.append(5)
            elif a in (5, 6):
                pass                       # real blink is not drawn
            elif a == 22:
                mapped += [22, 25]         # normal intensity ends bold and dim
            else:
                mapped.append(a)
            i += 1
        if attrs and not mapped:
            return
        super().select_graphic_rendition(*mapped)


def _style(char) -> Style:
    return Style(fg=char.fg, bg=char.bg, bold=bool(char.bold), dim=bool(char.blink), italic=bool(char.italics),
                 underline=bool(char.underscore), reverse=bool(char.reverse))


LOGICAL_COLUMNS = 4096
MAX_ROWS = 20000


def logical_lines(raw: bytes) -> list[list[Cell]]:
    """Emulate a terminal on a very wide screen and return its lines unwrapped.

    Redaction runs on these logical lines, so a value is found even where the real
    terminal would have wrapped it; wrap() then breaks them at the visual's width.
    """
    text = raw.decode("utf-8", "replace")
    # enough rows that nothing scrolls off the top: one per newline plus the soft wraps
    height = max(text.count("\n") + len(text) // LOGICAL_COLUMNS + 8, 8)
    if height > MAX_ROWS:
        raise RenderError(f"the output has more than {MAX_ROWS} lines; capture less output")
    screen = _Screen(LOGICAL_COLUMNS, height)
    screen.set_mode(pyte.modes.LNM)          # a bare \n also returns the carriage
    pyte.Stream(screen).feed(text)
    lines: list[list[Cell]] = []
    continued = False
    for y in range(screen.lines):
        row = screen.buffer[y]
        last = max(row.keys(), default=-1)
        cells = []
        for x in range(last + 1):
            char = row[x]
            if char.data == "":            # stub slot after a wide character
                continue
            cells.append(Cell(char.data, _style(char)))
        if continued:
            # the previous row was filled to the edge: this row is its soft-wrapped rest,
            # kept on the same logical line so redaction sees the value whole
            lines[-1].extend(cells)
        else:
            lines.append(cells)
        continued = last >= LOGICAL_COLUMNS - 2
    lines = [_rstrip(cells) for cells in lines]
    while lines and not lines[-1]:
        lines.pop()
    return lines


def wrap(cells: list[Cell], width: int) -> list[list[Cell]]:
    """Break a logical line into rows of at most width columns, like autowrap."""
    rows: list[list[Cell]] = [[]]
    used = 0
    for cell in cells:
        w = _width(cell.ch)
        if used + w > width and rows[-1]:
            rows.append([])
            used = 0
        rows[-1].append(cell)
        used += w
    return rows


def _rstrip(cells: list[Cell]) -> list[Cell]:
    end = len(cells)
    while end and cells[end - 1].ch == " " and cells[end - 1].style.bg == "default" and not cells[end - 1].style.reverse:
        end -= 1
    return cells[:end]


def text_cells(text: str, style: Style = DEFAULT_STYLE) -> list[Cell]:
    return [Cell(g, style) for g in clusters(text)]


# --- redaction on cells -------------------------------------------------------


def redact_cells(cells: list[Cell], rules: list[dict], masks: list[dict], counts: dict[str, int]) -> tuple[list[Cell], int]:
    masked = 0
    for rule in list(rules) + redact.mask_rules(masks):
        text = "".join(c.ch for c in cells)
        owner = [i for i, c in enumerate(cells) for _ in c.ch]
        found = redact.spans(text, rule)
        if rule.get("kind") == "mask":
            masked += len(found)
        else:
            counts[rule["id"]] = counts.get(rule["id"], 0) + len(found)
        for start, end, replacement in reversed(found):
            first, last = owner[start], owner[end - 1]
            style = cells[first].style
            cells = cells[:first] + text_cells(replacement, style) + cells[last + 1:]
    return _rstrip(cells), masked


# --- fonts --------------------------------------------------------------------


def _face(style: Style) -> str:
    if style.bold and style.italic:
        return "bolditalic"
    if style.bold:
        return "bold"
    if style.italic:
        return "italic"
    return "regular"


def _font_paths(fonts: dict[str, Path] | None) -> dict[str, Path]:
    paths = dict(DEFAULT_FONTS)
    paths.update({k: Path(v) for k, v in (fonts or {}).items()})
    regular = paths["regular"]
    if not regular.is_file():
        raise RenderError(f"monospaced font not found: {regular}")
    for face in ("bold", "italic", "bolditalic"):
        if not paths[face].is_file():
            paths[face] = paths["bold"] if face == "bolditalic" and paths["bold"].is_file() else regular
    return paths


def _metrics(path: Path) -> tuple[float, float, float]:
    """(advance, ascent, descent) per em of the regular face."""
    from fontTools.ttLib import TTFont

    font = TTFont(str(path), lazy=True, recalcTimestamp=False)
    upem = font["head"].unitsPerEm
    cmap = font.getBestCmap() or {}
    glyph = cmap.get(ord("M")) or cmap.get(ord("0")) or ".notdef"
    advance = font["hmtx"][glyph][0] / upem
    hhea = font["hhea"]
    return advance, hhea.ascent / upem, abs(hhea.descent) / upem


def _subset_woff2(path: Path, chars: str) -> bytes:
    from fontTools import subset
    from fontTools.ttLib import TTFont

    font = TTFont(str(path), recalcTimestamp=False)
    options = subset.Options()
    options.flavor = "woff2"
    options.hinting = False
    options.desubroutinize = True
    options.notdef_outline = True
    options.name_IDs = []
    options.layout_features = ["kern"]
    subsetter = subset.Subsetter(options)
    subsetter.populate(text=chars)
    subsetter.subset(font)
    font.flavor = "woff2"
    buf = io.BytesIO()
    font.save(buf, reorderTables=False)
    return buf.getvalue()


LIGATURE_FEATURES = ("ccmp", "liga", "rlig")


def _ligature_lookups(font) -> list[list[dict]]:
    """The ligature subtables (first glyph -> ligatures) of each GSUB lookup the
    ccmp, liga, and rlig features apply, in lookup order (the order a shaper uses)."""
    if "GSUB" not in font:
        return []
    table = font["GSUB"].table
    if not table.FeatureList or not table.LookupList:
        return []
    indexes = sorted({i for record in table.FeatureList.FeatureRecord if record.FeatureTag in LIGATURE_FEATURES
                      for i in record.Feature.LookupListIndex})
    lookups = []
    for i in indexes:
        lookup = table.LookupList.Lookup[i]
        subtables = []
        for sub in lookup.SubTable:
            sub = getattr(sub, "ExtSubTable", sub)        # extension lookups (type 7)
            if getattr(sub, "LookupType", lookup.LookupType) == 4 and hasattr(sub, "ligatures"):
                subtables.append(sub.ligatures)
        if subtables:
            lookups.append(subtables)
    return lookups


def _ligate(names: list[str], subtables: list[dict]) -> list[str]:
    """Apply one ligature lookup to a glyph sequence."""
    out: list[str] = []
    i = 0
    while i < len(names):
        match = None
        for ligatures in subtables:
            for lig in ligatures.get(names[i], ()):
                n = len(lig.Component)
                if names[i + 1:i + 1 + n] == list(lig.Component):
                    match = lig
                    break
            if match is not None:
                break
        if match is None:
            out.append(names[i])
            i += 1
        else:
            out.append(match.LigGlyph)
            i += 1 + len(match.Component)
    return out


class _Emoji:
    """PNG bitmaps from a CBDT color emoji font; None everywhere when the font is missing.

    A cluster is shaped the way a text shaper does it for this font: its code points map
    to glyphs through the cmap (a variation selector the font does not map is skipped),
    then the ligature lookups turn a ZWJ sequence, flag, keycap, or skin tone into its
    single glyph. A sequence the font has no ligature for shows its first emoji.
    """

    def __init__(self, path: Path | None):
        self.font = None
        self.cmap: dict[int, str] = {}
        self.lookups: list[list[dict]] = []
        path = Path(path) if path else None
        if path and path.is_file():
            from fontTools.ttLib import TTFont

            font = TTFont(str(path), lazy=True, recalcTimestamp=False)
            if "CBDT" in font:
                self.font = font
                self.cmap = font.getBestCmap() or {}
                self.lookups = _ligature_lookups(font)

    def _bitmap(self, name: str) -> bytes | None:
        for strike in reversed(self.font["CBDT"].strikeData):
            glyph = strike.get(name)
            if glyph is not None:
                data = getattr(glyph, "imageData", None)
                if data:
                    return bytes(data)
        return None

    def glyph(self, cluster: str) -> str | None:
        """The glyph that shows the cluster, None when the font has none for it."""
        if self.font is None or not cluster or ord(cluster[0]) not in self.cmap:
            return None
        names = [self.cmap[ord(ch)] for ch in cluster if ord(ch) in self.cmap]
        for subtables in self.lookups:
            names = _ligate(names, subtables)
        return next((name for name in names if self._bitmap(name) is not None), None)

    def png(self, cluster: str) -> bytes | None:
        name = self.glyph(cluster)
        return self._bitmap(name) if name is not None else None


def _is_emoji_cell(cell: Cell, emoji: _Emoji) -> bool:
    """A two-column cluster in emoji presentation (not U+FE0E) the emoji font can show.

    A base character with U+FE0F counts as two columns (wcwidth), so it is drawn as an
    emoji, while the same character alone keeps its text presentation."""
    if emoji.font is None or VS15 in cell.ch or _width(cell.ch) != 2:
        return False
    return emoji.glyph(cell.ch) is not None


# --- SVG ----------------------------------------------------------------------


def _num(value: float) -> str:
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _color(name: str, default: str) -> str:
    if name == "default" or not name:
        return default
    name = ALIASES.get(name, name)
    if name in PALETTE:
        return PALETTE[name]
    if len(name) == 6 and all(c in "0123456789abcdefABCDEF" for c in name):
        return "#" + name.lower()
    return default


def _colors(style: Style) -> tuple[str, str | None]:
    """(text color, background color or None for the default background)."""
    fg = _color(style.fg, FOREGROUND)
    bg = None if style.bg == "default" else _color(style.bg, BACKGROUND)
    if style.reverse:
        fg, bg = (bg or BACKGROUND), fg
    return fg, bg


def _width(ch: str) -> int:
    """Columns of a cell: its grapheme cluster's width (U+FE0F widens an emoji base)."""
    if not ch:
        return 1
    w = wcwidth(ch) if len(ch) == 1 else wcswidth(ch)
    return 2 if w >= 2 else 1


def _runs(cells: list[Cell], emoji: _Emoji) -> list[tuple[int, list[Cell], bool]]:
    """(start column, cells, is_emoji) groups of equal style; emoji stand alone."""
    runs: list[tuple[int, list[Cell], bool]] = []
    col = 0
    for cell in cells:
        is_emoji = _is_emoji_cell(cell, emoji)
        if runs and not is_emoji and not runs[-1][2] and runs[-1][1][-1].style == cell.style:
            runs[-1][1].append(cell)
        else:
            runs.append((col, [cell], is_emoji))
        col += _width(cell.ch)
    return runs


def style_fingerprint(lines: list[list[Cell]]) -> str:
    doc = []
    for cells in lines:
        row: list = []
        for cell in cells:
            key = cell.style.key()
            if row and row[-1][1] == key:
                row[-1][0] += cell.ch
            else:
                row.append([cell.ch, key])
        doc.append(row)
    return hashlib.sha256(json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()[:16]


def build_svg(lines: list[list[Cell]], fonts: dict[str, Path], emoji: _Emoji) -> bytes:
    advance, ascent, descent = _metrics(fonts["regular"])
    cell_w = advance * FONT_SIZE
    line_h = round(FONT_SIZE * LINE_HEIGHT)
    baseline = (line_h - (ascent + descent) * FONT_SIZE) / 2 + ascent * FONT_SIZE
    cols = max([sum(_width(c.ch) for c in cells) for cells in lines] + [20])   # rows are wrapped already
    width = PADDING * 2 + cols * cell_w
    height = PADDING * 2 + max(len(lines), 1) * line_h

    faces: dict[str, set[str]] = {}
    for cells in lines:
        for cell in cells:
            if not _is_emoji_cell(cell, emoji):
                faces.setdefault(_face(cell.style), set()).update(cell.ch)
    css = []
    face_css = {"regular": ("400", "normal"), "bold": ("700", "normal"), "italic": ("400", "italic"),
                "bolditalic": ("700", "italic")}
    for face in ("regular", "bold", "italic", "bolditalic"):
        if face not in faces:
            continue
        chars = "".join(sorted(faces[face] | {" "}))
        data = base64.b64encode(_subset_woff2(fonts[face], chars)).decode()
        weight, style = face_css[face]
        css.append(f'@font-face{{font-family:"{FAMILY}";src:url(data:font/woff2;base64,{data}) format("woff2");'
                   f"font-weight:{weight};font-style:{style}}}")
    css.append(f'text{{font-family:"{FAMILY}",monospace;font-size:{FONT_SIZE}px;white-space:pre;fill:{FOREGROUND}}}')
    css.append(".b{font-weight:700}.i{font-style:italic}.u{text-decoration:underline}.d{opacity:0.6}")

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
           f'width="{_num(width)}" height="{_num(height)}" viewBox="0 0 {_num(width)} {_num(height)}">',
           f"<style>{''.join(css)}</style>",
           f'<rect width="100%" height="100%" rx="6" fill="{BACKGROUND}"/>']
    texts: list[str] = []
    for y, cells in enumerate(lines):
        top = PADDING + y * line_h
        base = top + baseline
        spans: list[str] = []
        for col, group, is_emoji in _runs(cells, emoji):
            x = PADDING + col * cell_w
            ncols = sum(_width(c.ch) for c in group)
            fg, bg = _colors(group[0].style)
            if bg is not None:
                out.append(f'<rect x="{_num(x)}" y="{_num(top)}" width="{_num(ncols * cell_w)}" '
                           f'height="{line_h}" fill="{bg}"/>')
            if is_emoji:
                png = emoji.png(group[0].ch)
                if png is not None:
                    data = base64.b64encode(png).decode()
                    out.append(f'<image x="{_num(x)}" y="{_num(top)}" width="{_num(2 * cell_w)}" height="{line_h}" '
                               f'preserveAspectRatio="xMidYMid meet" xlink:href="data:image/png;base64,{data}"/>')
                    continue
            text = "".join(c.ch for c in group)
            if not text.strip() and bg is None and not group[0].style.underline:
                continue
            classes = [c for c, on in (("b", group[0].style.bold), ("i", group[0].style.italic),
                                       ("u", group[0].style.underline), ("d", group[0].style.dim)) if on]
            attrs = f' x="{_num(x)}"'
            if fg != FOREGROUND:
                attrs += f' fill="{fg}"'
            if classes:
                attrs += f' class="{" ".join(classes)}"'
            spans.append(f"<tspan{attrs}>{_esc(text)}</tspan>")
        if spans:
            texts.append(f'<text y="{_num(base)}">{"".join(spans)}</text>')
    out += texts
    out.append("</svg>")
    return ("\n".join(out) + "\n").encode()


# --- entry point --------------------------------------------------------------


def render(raw: bytes, command: str, prompt: str = "$ ", width: int = 100, rules: list[dict] | None = None,
           masks: list[dict] | None = None, fonts: dict[str, Path] | None = None,
           emoji_font: Path | None = DEFAULT_EMOJI_FONT, max_bytes: int = MAX_BYTES) -> dict:
    """Render a CLI capture; see the module docstring for the result."""
    paths = _font_paths(fonts)
    command_lines = (command or "").splitlines() or [""]
    logical = [text_cells(prompt + command_lines[0])] + [text_cells("> " + c) for c in command_lines[1:]]
    logical += logical_lines(raw)
    counts: dict[str, int] = {}
    masked = 0
    redacted = []
    for cells in logical:
        cells, n = redact_cells(cells, rules or [], masks or [], counts)
        masked += n
        redacted.extend(wrap(cells, width))
    for rule in rules or []:
        counts.setdefault(rule["id"], 0)
    svg = build_svg(redacted, paths, _Emoji(emoji_font))
    if len(svg) > max_bytes:
        raise RenderError(f"the SVG is {len(svg)} bytes, larger than the {max_bytes} byte limit (FR-016)")
    text = "\n".join("".join(c.ch for c in cells).rstrip() for cells in redacted)
    return {"svg": svg, "text": text, "style": style_fingerprint(redacted), "redaction": counts, "masks": masked}
