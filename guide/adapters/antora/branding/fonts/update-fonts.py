#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["fonttools[woff]==4.67.0", "pyyaml"]
# ///
"""Maintainer tool: vendor a Red Hat font release for the neutral theme.

Resolves a RedHatOfficial/RedHatFont release tag to its commit, downloads the six
variable web fonts and OFL.txt from that commit into a temporary directory, parses every
font, and only then moves them into this directory and rewrites fonts.yaml (release,
commit, checksums, wght axis ranges, and the code points Red Hat Display covers).
Re-running it for the release already recorded fails when the tag now points to another
commit or any recorded checksum (the fonts and OFL.txt) differs, so a moved tag or a
changed upstream file never slips in silently. Run it by hand when
adopting a new release, review the diff, and commit the result. It is never vendored
into a guide project (scaffold-project.sh excludes it).

Usage: uv run guide/adapters/antora/branding/fonts/update-fonts.py [--release TAG]
"""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import yaml
from fontTools.ttLib import TTFont

REPOSITORY = "https://github.com/RedHatOfficial/RedHatFont"
RAW = "https://raw.githubusercontent.com/RedHatOfficial/RedHatFont/{commit}/{path}"
RELEASE_RE = re.compile(r"[0-9A-Za-z]+(?:[._-][0-9A-Za-z]+)*")   # as in branding.py
FILES = (
    "fonts/Proportional/RedHatDisplay/webfonts/RedHatDisplay-VF.woff2",
    "fonts/Proportional/RedHatDisplay/webfonts/RedHatDisplay-Italic-VF.woff2",
    "fonts/Proportional/RedHatText/webfonts/RedHatText-VF.woff2",
    "fonts/Proportional/RedHatText/webfonts/RedHatText-Italic-VF.woff2",
    "fonts/Mono/RedHatMono/webfonts/RedHatMono-VF.woff2",
    "fonts/Mono/RedHatMono/webfonts/RedHatMono-Italic-VF.woff2",
)
FAMILIES = {"RedHatDisplay": "Red Hat Display", "RedHatText": "Red Hat Text", "RedHatMono": "Red Hat Mono"}
COVERAGE_FONT = "RedHatDisplay-VF.woff2"
HEADER = "# Written by update-fonts.py; do not edit by hand. Read by tools/guide/branding.py.\n"


def resolve_commit(release: str) -> str:
    """The commit a release tag points to (the peeled commit for an annotated tag)."""
    out = subprocess.run(["git", "ls-remote", REPOSITORY, f"refs/tags/{release}", f"refs/tags/{release}^{{}}"],
                         capture_output=True, text=True, check=True, timeout=60).stdout
    refs = dict(reversed(line.split("\t")) for line in out.splitlines() if "\t" in line)
    commit = refs.get(f"refs/tags/{release}^{{}}") or refs.get(f"refs/tags/{release}")
    if not commit or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise SystemExit(f"release {release}: tag not found in {REPOSITORY}")
    return commit


def download(commit: str, path: str, dest: Path) -> None:
    url = RAW.format(commit=commit, path=path)
    with urllib.request.urlopen(url, timeout=60) as resp:   # noqa: S310 (fixed https host)
        dest.write_bytes(resp.read())


def ranges(points: list[int]) -> list[list[int]]:
    """Sorted, merged inclusive ranges of code points."""
    out: list[list[int]] = []
    for cp in sorted(set(points)):
        if out and cp == out[-1][1] + 1:
            out[-1][1] = cp
        else:
            out.append([cp, cp])
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--release", default="5.0.0")
    args = ap.parse_args(argv)
    if not RELEASE_RE.fullmatch(args.release):
        raise SystemExit(f"--release must be a release tag (got {args.release!r})")
    here = Path(__file__).resolve().parent
    previous: dict[str, str] = {}
    commit = resolve_commit(args.release)
    if (here / "fonts.yaml").is_file():
        old = yaml.safe_load((here / "fonts.yaml").read_text()) or {}
        if old.get("release") == args.release:
            if old.get("commit") not in (None, commit):
                raise SystemExit(f"release {args.release} is recorded at commit {old['commit']}, but the tag "
                                 f"now points to {commit}; investigate before replacing the fonts")
            previous = {e["file"]: e["sha256"] for e in old.get("files") or []}
            if old.get("ofl_sha256"):
                previous["OFL.txt"] = old["ofl_sha256"]

    with tempfile.TemporaryDirectory() as tmp:
        staged = Path(tmp)
        entries = []
        for path in FILES:
            name = path.rsplit("/", 1)[1]
            download(commit, path, staged / name)
            font = TTFont(staged / name)                    # fails on anything but a font
            axis = next(a for a in font["fvar"].axes if a.axisTag == "wght")
            stem = name.split("-", 1)[0]
            entries.append({
                "file": name,
                "upstream": path,
                "sha256": hashlib.sha256((staged / name).read_bytes()).hexdigest(),
                "family": FAMILIES[stem],
                "style": "italic" if "-Italic-" in name else "normal",
                "weight": [int(axis.minValue), int(axis.maxValue)],
            })
        download(commit, "OFL.txt", staged / "OFL.txt")
        ofl_sha256 = hashlib.sha256((staged / "OFL.txt").read_bytes()).hexdigest()
        current = {e["file"]: e["sha256"] for e in entries} | {"OFL.txt": ofl_sha256}
        changed = [name for name, digest in current.items() if name in previous and previous[name] != digest]
        if changed:
            raise SystemExit(f"release {args.release} is already recorded, but these files changed upstream: "
                             f"{', '.join(changed)}; investigate before replacing them")
        cmap = TTFont(staged / COVERAGE_FONT).getBestCmap()
        for name in [e["file"] for e in entries] + ["OFL.txt"]:
            shutil.copyfile(staged / name, here / name)
    manifest = {
        "release": args.release,
        "commit": commit,
        "repository": REPOSITORY,
        "license": "OFL-1.1",
        "ofl_sha256": ofl_sha256,
        "files": entries,
        "display_coverage": ranges(list(cmap)),
    }
    text = yaml.safe_dump(manifest, sort_keys=False, default_flow_style=None, width=100)
    (here / "fonts.yaml").write_text(HEADER + text)
    for e in entries:
        print(f"{e['file']}: {e['family']} {e['style']} wght {e['weight'][0]}-{e['weight'][1]} {e['sha256'][:12]}")
    print(f"display_coverage: {len(manifest['display_coverage'])} ranges, {len(cmap)} code points")
    return 0


if __name__ == "__main__":
    sys.exit(main())
