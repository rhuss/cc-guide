#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdf"]
# ///
"""Assertions on a guide PDF for the adapter smoke tests (tests/adapters/test_pdf.sh).

usage:
  pdftext.py text PDF
      print the text of every page, each preceded by a "== page N" line
  pdftext.py check PDF --title T --date D [--commit SHA]... [--page-title T]...
                   [--forbid TERM]... [--footer TEXT]
      --page-title (repeatable, in navigation order): every page title appears in the
      body in this order, and the table of contents links to every page in one click
      --forbid: a term that must not appear anywhere (case-insensitive)
      --footer: text that must appear on every page (for example INTERNAL)
      Every page must carry "Page N of M". Prints PASS/FAIL lines; exit 1 on a failure.
"""
import argparse
import re
import sys

from pypdf import PdfReader


def page_texts(reader: PdfReader) -> list[str]:
    return [(p.extract_text() or "") for p in reader.pages]


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def outline_titles(reader: PdfReader) -> list[str]:
    titles: list[str] = []

    def walk(items):
        for item in items:
            if isinstance(item, list):
                walk(item)
            else:
                titles.append(norm(str(item.title)))
    walk(reader.outline)
    return titles


def internal_links(page) -> int:
    count = 0
    for annot in page.get("/Annots") or []:
        obj = annot.get_object()
        if obj.get("/Subtype") != "/Link":
            continue
        action = obj.get("/A")
        if obj.get("/Dest") is not None or (action is not None and action.get_object().get("/S") == "/GoTo"):
            count += 1
    return count


def check(args) -> int:
    reader = PdfReader(args.pdf)
    texts = page_texts(reader)
    flat = [norm(t) for t in texts]
    failures = 0

    def result(ok: bool, message: str) -> None:
        nonlocal failures
        print(("PASS " if ok else "FAIL ") + message)
        failures += 0 if ok else 1

    first = flat[0] if flat else ""
    result(args.title in first, f"title page shows the title {args.title!r}")
    result(args.date in first, f"title page shows the baseline date {args.date}")
    for sha in args.commit:
        result(sha in first.replace(" ", ""), f"title page shows commit {sha[:7]}")

    total = len(texts)
    missing = [i + 1 for i, t in enumerate(flat) if not re.search(rf"Page\s*{i + 1}\s*of\s*{total}\b", t)]
    result(not missing, f"every page has a page number ({total} pages)" + (f"; missing on {missing}" if missing else ""))

    if args.footer:
        missing = [i + 1 for i, t in enumerate(flat) if args.footer not in t]
        result(not missing, f"every page footer shows {args.footer!r}" + (f"; missing on {missing}" if missing else ""))

    whole = " ".join(flat)
    for term in args.forbid:
        hits = [i + 1 for i, t in enumerate(flat) if term.lower() in t.lower()]
        result(not hits, f"no {term!r} in the PDF" + (f"; found on pages {hits}" if hits else ""))

    if args.page_title:
        toc_pages = [i for i, t in enumerate(flat) if t.startswith("Contents") or " Contents " in t[:40]]
        body_start = (toc_pages[-1] + 1) if toc_pages else 1
        body = " ".join(flat[body_start:])
        pos = 0
        order_ok = True
        for title in args.page_title:
            at = body.find(title, pos)
            if at < 0:
                result(False, f"page title {title!r} in the body after position {pos}")
                order_ok = False
                break
            pos = at + len(title)
        if order_ok:
            result(True, f"all {len(args.page_title)} page titles appear in navigation order")
        outline = outline_titles(reader)
        idx = 0
        for title in outline:
            if idx < len(args.page_title) and title == args.page_title[idx]:
                idx += 1
        result(idx == len(args.page_title), f"PDF outline lists the pages in order ({idx}/{len(args.page_title)})")
        links = sum(internal_links(reader.pages[i]) for i in (toc_pages or [1]))
        result(links >= len(args.page_title),
               f"table of contents has {links} in-document links for {len(args.page_title)} pages")
    print(f"{args.pdf}: {failures} failure(s)")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("text")
    t.add_argument("pdf")
    c = sub.add_parser("check")
    c.add_argument("pdf")
    c.add_argument("--title", required=True)
    c.add_argument("--date", required=True)
    c.add_argument("--commit", action="append", default=[])
    c.add_argument("--page-title", action="append", default=[])
    c.add_argument("--forbid", action="append", default=[])
    c.add_argument("--footer")
    args = parser.parse_args(argv)
    if args.cmd == "text":
        for i, text in enumerate(page_texts(PdfReader(args.pdf)), 1):
            print(f"== page {i}")
            print(text)
        return 0
    return check(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
