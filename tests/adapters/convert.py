#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Convert the format-neutral fixture guide into an adapter's project layout.

usage: convert.py FORMAT SRC_GUIDE DEST

FORMAT is antora, mkdocs, or gfm. SRC_GUIDE is a neutral guide such
as tests/fixtures/sample-guide (pages/*.md plus pages/nav.yaml); DEST already holds
the adapter scaffold and a rendered baseline.yaml (needed to link change requests).

Neutral page format:
  # Title / ## Heading                      headings
  <!-- Sources: ... -->                     source block (one reference per line)
  <!-- guide: no-sources -->, <!-- STUB --> markers
  ```lang ... ```                           listings; <!-- expect: M --> after a listing
  :::note|tip|important|warning|caution ... :::   admonitions
  :::experimental feature="X" pr=N anchor=A tier=in-review|on-main   experimental label
  {{attr:name}}                             baseline value
  [text](rel/path.md), [text](https://...)  links; 1. numbered and - bullet list items

Each page is parsed into a small block list, then rendered by one function per format.
"""
from __future__ import annotations

import argparse
import posixpath
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ADMONITIONS = ("note", "tip", "important", "warning", "caution")
ATTR_RE = re.compile(r"\{\{attr:([a-z0-9][a-z0-9_-]*)\}\}")
LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)\s]+)\)")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
EXPERIMENTAL_RE = re.compile(r'^:::experimental\s+(.*)$')
KV_RE = re.compile(r'(\w+)=(?:"([^"]*)"|(\S+))')


# --- neutral model ----------------------------------------------------------


@dataclass
class Block:
    kind: str  # title heading sources para item code expect admonition experimental blank stub nosources
    text: str = ""
    level: int = 0
    lines: list[str] = field(default_factory=list)
    lang: str = ""
    attrs: dict[str, str] = field(default_factory=dict)


@dataclass
class Page:
    path: str  # neutral path without extension, for example admin/install
    title: str
    blocks: list[Block]
    internal: bool = False


def parse_page(path: str, text: str) -> Page:
    lines = text.splitlines()
    blocks: list[Block] = []
    title = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if s.startswith("```"):
            lang = s[3:].strip() or "text"
            body = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            blocks.append(Block("code", lang=lang, lines=body))
        elif s.startswith("<!-- Sources:"):
            refs = []
            rest = s[len("<!-- Sources:"):].strip()
            closed = rest.endswith("-->")
            rest = rest[:-3].strip() if closed else rest
            if rest:
                refs.append(rest)
            while not closed and i + 1 < len(lines):
                i += 1
                entry = lines[i].strip()
                closed = entry.endswith("-->")
                entry = entry[:-3].strip() if closed else entry
                if entry:
                    refs.append(entry)
            blocks.append(Block("sources", lines=refs))
        elif re.match(r"^<!--\s*guide:\s*no-sources\s*-->$", s):
            blocks.append(Block("nosources"))
        elif re.match(r"^<!--\s*STUB\s*-->$", s):
            blocks.append(Block("stub"))
        elif m := re.match(r"^<!--\s*expect:\s*(.*?)\s*-->$", s):
            blocks.append(Block("expect", text=m.group(1)))
        elif m := EXPERIMENTAL_RE.match(s):
            attrs = {kv.group(1): kv.group(2) if kv.group(2) is not None else kv.group(3)
                     for kv in KV_RE.finditer(m.group(1))}
            blocks.append(Block("experimental", attrs=attrs))
        elif s.startswith(":::") and s[3:].strip() in ADMONITIONS:
            body = []
            i += 1
            while i < len(lines) and lines[i].strip() != ":::":
                body.append(lines[i].strip())
                i += 1
            blocks.append(Block("admonition", text=s[3:].strip(), lines=body))
        elif m := re.match(r"^(#{1,6})\s+(.*)$", line):
            level = len(m.group(1))
            if level == 1 and not title:
                title = m.group(2).strip()
                blocks.append(Block("title", text=title))
            else:
                blocks.append(Block("heading", level=level, text=m.group(2).strip()))
        elif m := re.match(r"^(\d+)\.\s+(.*)$", s):
            blocks.append(Block("item", text=m.group(2), attrs={"type": "ordered"}))
        elif m := re.match(r"^[-*]\s+(.*)$", s):
            blocks.append(Block("item", text=m.group(1), attrs={"type": "bullet"}))
        elif not s:
            blocks.append(Block("blank"))
        else:
            blocks.append(Block("para", text=s))
        i += 1
    return Page(path=path, title=title, blocks=blocks)


def load_guide(src: Path) -> tuple[list[Page], dict]:
    nav = yaml.safe_load((src / "pages" / "nav.yaml").read_text())
    internal_paths = {p for sec in nav.get("internal") or [] for p in sec["pages"]}
    pages = []
    for md in sorted((src / "pages").rglob("*.md")):
        rel = md.relative_to(src / "pages").with_suffix("").as_posix()
        page = parse_page(rel, md.read_text())
        page.internal = rel in internal_paths
        pages.append(page)
    return pages, nav


def change_request_sources(dest: Path) -> dict[str, str]:
    """Change request number -> source id, from the rendered baseline.yaml."""
    path = dest / "baseline.yaml"
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    return {str(cr["number"]): cr["source"] for cr in data.get("change_requests") or []}


def copy_guide_yaml(src: Path, dest: Path, fmt: str) -> None:
    text = (src / "guide.yaml").read_text()
    text = re.sub(r"^format:.*$", f"format: {fmt}", text, count=1, flags=re.M)
    (dest / "guide.yaml").write_text(text)


# --- antora -----------------------------------------------------------------


def antora_page_file(page_path: str, internal: bool) -> str:
    if internal:
        return f"internal/modules/internal/pages/{posixpath.basename(page_path)}.adoc"
    return f"content/modules/ROOT/pages/{page_path}.adoc"


def antora_xref(target: str, from_page: Page, internal_paths: set[str]) -> str:
    """Neutral page path (no extension) -> Antora xref target."""
    if target in internal_paths:
        name = posixpath.basename(target) + ".adoc"
        return name if from_page.internal else f"internal:{name}"
    return f"ROOT:{target}.adoc" if from_page.internal else f"{target}.adoc"


def antora_inline(text: str, page: Page, internal_paths: set[str]) -> str:
    def link(m: re.Match) -> str:
        label, href = m.group(1), m.group(2)
        if re.match(r"^[a-z]+://", href):
            return f"{href}[{label}^]"
        anchor = ""
        if "#" in href:
            href, anchor = href.split("#", 1)
            anchor = "#" + anchor
        target = posixpath.normpath(posixpath.join(posixpath.dirname(page.path), href))
        target = re.sub(r"\.md$", "", target)
        return f"xref:{antora_xref(target, page, internal_paths)}{anchor}[{label}]"

    def image(m: re.Match) -> str:
        return f'image:{posixpath.basename(m.group(2))}["{m.group(1)}"]'

    text = IMAGE_RE.sub(image, text)
    text = LINK_RE.sub(link, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"*\1*", text)
    return ATTR_RE.sub(lambda m: "{" + m.group(1) + "}", text)


def auto_id(title: str) -> str:
    """Asciidoctor's automatic section id with idprefix '' and idseparator '-'."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def place_anchors(page: Page) -> None:
    """Give the section that holds an experimental label the change request's anchor.

    The anchor (baseline.yaml change_requests[].anchor) names the section; when the
    heading's automatic id differs, the heading gets an explicit id. A label before
    any heading anchors the label block itself.
    """
    heading = None
    for b in page.blocks:
        if b.kind == "heading":
            heading = b
        elif b.kind == "experimental" and b.attrs.get("anchor"):
            anchor = b.attrs["anchor"]
            if heading is None:
                b.attrs["block_id"] = anchor
            elif auto_id(heading.text) != anchor:
                heading.attrs["id"] = anchor


def render_antora(page: Page, internal_paths: set[str], cr_sources: dict[str, str]) -> str:
    place_anchors(page)
    out: list[str] = []
    for b in page.blocks:
        if b.kind == "title":
            out.append(f"= {b.text}")
        elif b.kind == "heading":
            if b.attrs.get("id"):
                out.append(f"[#{b.attrs['id']}]")
            out.append(f"{'=' * b.level} {antora_inline(b.text, page, internal_paths)}")
        elif b.kind == "sources":
            out.append("// Sources:")
            out.extend(f"// {ref}" for ref in b.lines)
        elif b.kind == "nosources":
            out.append(":guide-no-sources:")
        elif b.kind == "stub":
            out.append("// STUB")
        elif b.kind == "para":
            out.append(antora_inline(b.text, page, internal_paths))
        elif b.kind == "item":
            marker = "." if b.attrs.get("type") == "ordered" else "*"
            out.append(f"{marker} {antora_inline(b.text, page, internal_paths)}")
        elif b.kind == "code":
            uses_attrs = any(ATTR_RE.search(line) for line in b.lines)
            subs = ',subs="attributes+"' if uses_attrs else ""
            out.append(f"[source,{b.lang}{subs}]")
            out.append("----")
            out.extend(ATTR_RE.sub(lambda m: "{" + m.group(1) + "}", line) for line in b.lines)
            out.append("----")
        elif b.kind == "expect":
            out.append(f"// expect: {b.text}")
        elif b.kind == "admonition":
            out.append(f"[{b.text.upper()}]")
            out.append("====")
            out.extend(antora_inline(line, page, internal_paths) for line in b.lines if line)
            out.append("====")
        elif b.kind == "experimental":
            a = b.attrs
            tier = a.get("tier", "in-review")
            if tier not in ("in-review", "on-main"):
                raise SystemExit(f"{page.path}: unknown experimental tier {tier!r}")
            names = ["feature-name", "feature-pr", "feature-anchor"]
            out.append(f":feature-name: {a['feature']}")
            out.append(f":feature-pr: {a['pr']}")
            out.append(f":feature-anchor: {a['anchor']}")
            source = cr_sources.get(str(a["pr"]))
            if source:
                out.append(f":feature-repo: {{{source}-repo}}")
                names.append("feature-repo")
            if a.get("block_id"):
                out.append(f"[[{a['block_id']}]]")
            out.append(f"include::ROOT:partial$experimental-{tier}.adoc[]")
            out.extend(f":{n}!:" for n in names)
        elif b.kind == "blank":
            out.append("")
    text = "\n".join(out).rstrip() + "\n"
    return re.sub(r"\n{3,}", "\n\n", text)


def antora_nav(sections: list[dict], titles: dict[str, str], internal: bool) -> str:
    out = []
    for sec in sections:
        out.append(f".{sec['title']}")
        for p in sec["pages"]:
            target = posixpath.basename(p) if internal else p
            out.append(f"* xref:{target}.adoc[{titles[p]}]")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def convert_antora(src: Path, dest: Path) -> None:
    pages, nav = load_guide(src)
    internal_paths = {p.path for p in pages if p.internal}
    cr_sources = change_request_sources(dest)
    titles = {p.path: p.title for p in pages}
    for page in pages:
        out = dest / antora_page_file(page.path, page.internal)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_antora(page, internal_paths, cr_sources))
    (dest / "content/modules/ROOT/nav.adoc").write_text(antora_nav(nav.get("shareable") or [], titles, False))
    if nav.get("internal"):
        (dest / "internal/modules/internal/nav.adoc").write_text(antora_nav(nav["internal"], titles, True))
    images = src / "images"
    if images.is_dir():
        shutil.copytree(images, dest / "content/modules/ROOT/images", dirs_exist_ok=True)
    copy_guide_yaml(src, dest, "antora")


# --- Markdown formats (mkdocs, gfm) -------------------------------------------

REPO = Path(__file__).resolve().parents[2]
EXPERIMENTAL_TITLES = {"in-review": "Experimental: in review", "on-main": "Experimental: on main"}
GFM_ALERTS = {"note": "NOTE", "tip": "TIP", "important": "IMPORTANT", "warning": "WARNING", "caution": "CAUTION"}


def baseline_values(dest: Path) -> dict[str, str]:
    """Baseline values from DEST/baseline.yaml, computed by the toolkit's attrs.py."""
    sys.path.insert(0, str(REPO / "guide" / "toolkit"))
    import attrs
    import guidecfg
    return attrs.values(guidecfg.load_baseline(dest))


def md_page_file(page_path: str, internal: bool, fmt: str) -> str:
    """Neutral page path -> Markdown file of the guide project."""
    if internal:
        root = "docs/internal" if fmt == "mkdocs" else "internal"
        return f"{root}/{posixpath.basename(page_path)}.md"
    return f"docs/{page_path}.md"


def md_link(href: str, page: Page, files: dict[str, str], fmt: str) -> str:
    """Rewrite a neutral relative link for the page's place in the guide project."""
    if re.match(r"^[a-z]+://", href) or href.startswith("#"):
        return href
    anchor = ""
    if "#" in href:
        href, anchor = href.split("#", 1)
        anchor = "#" + anchor
    target = re.sub(r"\.md$", "", posixpath.normpath(posixpath.join(posixpath.dirname(page.path), href)))
    if target not in files:
        raise SystemExit(f"{page.path}: link to unknown page {href!r}")
    here = posixpath.dirname(files[page.path])
    return posixpath.relpath(files[target], here) + anchor


def md_inline(text: str, page: Page, files: dict[str, str], fmt: str, values: dict[str, str]) -> str:
    def attr(m: re.Match) -> str:
        name = m.group(1)
        if name not in values:
            raise SystemExit(f"{page.path}: unknown baseline attribute {name!r}")
        if fmt == "mkdocs":
            return '{{= attr("' + name + '") }}'
        return f"<!-- guide:attr {name} -->{values[name]}<!-- /guide:attr -->"

    def image(m: re.Match) -> str:
        alt, src = m.group(1), m.group(2)
        here = posixpath.dirname(files[page.path])
        path = posixpath.relpath(f"docs/assets/diagrams/{posixpath.basename(src)}", here)
        return f"![{alt}]({path})" if fmt == "mkdocs" else f"[![{alt}]({path})]({path})"

    text = IMAGE_RE.sub(image, text)
    text = LINK_RE.sub(lambda m: f"[{m.group(1)}]({md_link(m.group(2), page, files, fmt)})", text)
    return ATTR_RE.sub(attr, text)


def md_anchor_slug(title: str) -> str:
    """Heading id as MkDocs (toc) and GitHub derive it for simple titles."""
    return re.sub(r"[\s]+", "-", re.sub(r"[^\w\s-]", "", title.lower()).strip())


def render_markdown(page: Page, fmt: str, files: dict[str, str], values: dict[str, str],
                    cr_repos: dict[str, str]) -> str:
    out: list[str] = []
    heading_anchor: dict[int, str] = {}
    current = None
    for idx, b in enumerate(page.blocks):
        if b.kind == "heading":
            current = idx
        elif b.kind == "experimental" and fmt == "mkdocs" and current is not None:
            anchor = b.attrs.get("anchor", "")
            if anchor and md_anchor_slug(page.blocks[current].text) != anchor:
                heading_anchor[current] = anchor
    inline = lambda text: md_inline(text, page, files, fmt, values)  # noqa: E731
    for idx, b in enumerate(page.blocks):
        if b.kind == "title":
            out.append(f"# {b.text}")
        elif b.kind == "heading":
            suffix = f" {{ #{heading_anchor[idx]} }}" if idx in heading_anchor else ""
            out.append(f"{'#' * b.level} {inline(b.text)}{suffix}")
        elif b.kind == "sources":
            out.append("<!-- Sources:")
            out.extend(b.lines)
            out.append("-->")
        elif b.kind == "nosources":
            out.append("<!-- guide: no-sources -->")
        elif b.kind == "stub":
            out.append("<!-- STUB -->")
        elif b.kind == "para":
            out.append(inline(b.text))
        elif b.kind == "item":
            marker = "1." if b.attrs.get("type") == "ordered" else "-"
            out.append(f"{marker} {inline(b.text)}")
        elif b.kind == "code":
            if fmt == "gfm" and any(ATTR_RE.search(line) for line in b.lines):
                raise SystemExit(f"{page.path}: gfm listings cannot hold baseline values "
                                 "(GitHub shows comments in code verbatim); move the value into the text")
            out.append(f"```{b.lang}")
            out.extend(ATTR_RE.sub(lambda m: '{{= attr("' + m.group(1) + '") }}', line) for line in b.lines)
            out.append("```")
        elif b.kind == "expect":
            out.append(f"<!-- expect: {b.text} -->")
        elif b.kind == "admonition":
            body = [inline(line) for line in b.lines if line]
            if fmt == "mkdocs":
                out.append(f"!!! {b.text}")
                out.append("")
                out.extend(f"    {line}" for line in body)
            else:
                out.append(f"> [!{GFM_ALERTS[b.text]}]")
                out.extend(f"> {line}" for line in body)
        elif b.kind == "experimental":
            a = b.attrs
            tier = a.get("tier", "in-review")
            if tier not in EXPERIMENTAL_TITLES:
                raise SystemExit(f"{page.path}: unknown experimental tier {tier!r}")
            if fmt == "mkdocs":
                out.append(f'{{{{= experimental("{tier}", "{a["feature"]}", {a["pr"]}) }}}}')
            else:
                repo = cr_repos.get(str(a["pr"]))
                ref = f"[change request #{a['pr']}]({repo}/pull/{a['pr']})" if repo else f"change request #{a['pr']}"
                date = f"<!-- guide:attr baseline-date -->{values['baseline-date']}<!-- /guide:attr -->"
                out.append(f'<a id="{a["anchor"]}"></a>')
                out.append("")
                out.append("> [!IMPORTANT]")
                if tier == "in-review":
                    out.append(f"> **{EXPERIMENTAL_TITLES[tier]}.** {a['feature']} is not part of the baseline. "
                               f"It is proposed in {ref} (status as of {date}) and may change or be dropped "
                               "before it merges.")
                else:
                    out.append(f"> **{EXPERIMENTAL_TITLES[tier]}.** {a['feature']} is an experimental feature. "
                               f"It is merged on the default branch ({ref}) but not part of the pinned release, "
                               "and its behavior may change.")
        elif b.kind == "blank":
            out.append("")
    text = "\n".join(out).rstrip() + "\n"
    return re.sub(r"\n{3,}", "\n\n", text)


def change_request_repos(dest: Path, values: dict[str, str]) -> dict[str, str]:
    return {num: values.get(f"{src}-repo", "") for num, src in change_request_sources(dest).items()}


def mkdocs_nav(sections: list[dict], files: dict[str, str], prefix: str = "docs/") -> list[str]:
    out = []
    for sec in sections:
        out.append(f"  - {json_str(sec['title'])}:")
        for p in sec["pages"]:
            out.append(f"      - {files[p][len(prefix):]}")
    return out


def json_str(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def replace_nav(config: Path, nav_lines: list[str]) -> None:
    """Replace the trailing `nav:` block of an MkDocs config file."""
    text = config.read_text()
    head, sep, _ = text.partition("\nnav:\n")
    if not sep:
        raise SystemExit(f"{config}: no trailing nav: block to replace")
    config.write_text(head + "\nnav:\n" + "\n".join(nav_lines) + "\n")


def convert_markdown(src: Path, dest: Path, fmt: str) -> None:
    pages, nav = load_guide(src)
    files = {p.path: md_page_file(p.path, p.internal, fmt) for p in pages}
    titles = {p.path: p.title for p in pages}
    values = baseline_values(dest)
    cr_repos = change_request_repos(dest, values)
    for page in pages:
        out = dest / files[page.path]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_markdown(page, fmt, files, values, cr_repos))
    shareable = nav.get("shareable") or []
    internal = nav.get("internal") or []
    if fmt == "mkdocs":
        replace_nav(dest / "mkdocs.yml", mkdocs_nav(shareable, files))
        replace_nav(dest / "mkdocs-internal.yml", mkdocs_nav(shareable + internal, files))
    else:
        title = yaml.safe_load((src / "guide.yaml").read_text())["title"]
        toc, summary = [], []
        for sec in shareable:
            toc += ["", f"## {sec['title']}", ""]
            summary += ["", f"## {sec['title']}", ""]
            for p in sec["pages"]:
                rel = files[p][len("docs/"):]
                toc.append(f"- [{titles[p]}]({rel})")
                summary.append(f"- [{titles[p]}]({rel})")
        (dest / "docs/README.md").write_text(
            f"# {title}\n\n<!-- guide: no-sources -->\n\n"
            "This table of contents defines the reading order; [SUMMARY.md](SUMMARY.md) lists the same pages.\n"
            + "\n".join(toc) + "\n")
        (dest / "docs/SUMMARY.md").write_text(
            "# Summary\n\n<!-- guide: no-sources -->\n" + "\n".join(summary) + "\n")
        lines = []
        for sec in internal:
            lines += ["", f"### {sec['title']}", ""]
            lines += [f"- [{titles[p]}]({posixpath.basename(files[p])})" for p in sec["pages"]]
        readme = dest / "internal/README.md"
        readme.write_text(readme.read_text().rstrip() + "\n" + "\n".join(lines) + "\n")
    images = src / "images"
    if images.is_dir():
        shutil.copytree(images, dest / "docs/assets/diagrams", dirs_exist_ok=True)
    copy_guide_yaml(src, dest, fmt)


def convert_mkdocs(src: Path, dest: Path) -> None:
    convert_markdown(src, dest, "mkdocs")


def convert_gfm(src: Path, dest: Path) -> None:
    convert_markdown(src, dest, "gfm")


# --- CLI ----------------------------------------------------------------------

CONVERTERS = {
    "antora": convert_antora,
    "mkdocs": convert_mkdocs,
    "gfm": convert_gfm,
}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Convert the neutral fixture guide into an adapter layout")
    parser.add_argument("format", choices=sorted(CONVERTERS))
    parser.add_argument("src", type=Path)
    parser.add_argument("dest", type=Path)
    args = parser.parse_args(argv)
    CONVERTERS[args.format](args.src, args.dest)
    print(f"converted {args.src} to {args.format} in {args.dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
