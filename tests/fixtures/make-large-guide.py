#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Generate a 25-page variant of the neutral fixture guide for timing checks.

usage: make-large-guide.py SRC_GUIDE DEST [--pages N]

SRC_GUIDE is tests/fixtures/sample-guide (or a rendered copy of it). The index
page stays; the admin and user pages are repeated under new names until the
shareable part has N pages (default 25). The internal part is copied as is.
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

import yaml


def retitle(text: str, suffix: str) -> str:
    return re.sub(r"^# (.+)$", lambda m: f"# {m.group(1)} ({suffix})", text, count=1, flags=re.M)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("src", type=Path)
    parser.add_argument("dest", type=Path)
    parser.add_argument("--pages", type=int, default=25)
    args = parser.parse_args(argv)

    if args.dest.exists() and any(args.dest.iterdir()):
        print(f"destination is not empty: {args.dest}", file=sys.stderr)
        return 2
    shutil.copytree(args.src, args.dest, dirs_exist_ok=True)
    pages = args.dest / "pages"
    nav = yaml.safe_load((pages / "nav.yaml").read_text())

    templates = [("admin", pages / "admin/install.md"), ("user", pages / "user/start.md")]
    extra = args.pages - 3
    if extra < 0:
        print("--pages must be at least 3", file=sys.stderr)
        return 2
    added: dict[str, list[str]] = {"admin": [], "user": []}
    for i in range(extra):
        persona, template = templates[i % 2]
        n = i // 2 + 2
        name = f"{template.stem}-{n:02d}"
        target = template.parent / f"{name}.md"
        target.write_text(retitle(template.read_text(), f"part {n}"))
        added[persona].append(f"{persona}/{name}")

    for section in nav["shareable"]:
        first = section["pages"][0]
        persona = first.split("/")[0]
        if persona in added:
            section["pages"].extend(added[persona])
    (pages / "nav.yaml").write_text(yaml.safe_dump(nav, sort_keys=False))
    total = sum(len(s["pages"]) for s in nav["shareable"])
    print(f"wrote {args.dest}: {total} shareable pages")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
