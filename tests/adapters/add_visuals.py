"""Add the committed fixture visuals to a scaffolded guide (specs/008-captured-visuals, T030a).

    usage: python3 tests/adapters/add_visuals.py <format> <guide dir> [--embed-only]

Copies tests/adapters/fixtures/visuals/visuals.yaml, its visuals/ directory (seed and demo
files, all fictional), and the captured static/ visuals (images into the adapter's visual
directory, sidecars into visuals/), then embeds both visuals on the user start page with
`visual:` citations in its source block. No podman needed: the images were produced once
by `make visuals` and checked for host values. --embed-only only edits the page (the
podman smoke test embeds the visuals it has just captured).
"""
import shutil
import sys
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "visuals"
LAYOUT = {
    "antora": ("content/modules/ROOT/images/visuals", "content/modules/ROOT/pages/user/start.adoc"),
    "mkdocs": ("docs/assets/visuals", "docs/user/start.md"),
    "gfm": ("docs/assets/visuals", "docs/user/start.md"),
}
ALT = {"colors": "Colored output of the demo script with a PASS line and a progress bar",
       "table": "Table of three demo runs, the accuracy column highlighted with callout 1"}


def main(fmt: str, guide: Path, embed_only: bool = False) -> None:
    visual_dir, page_rel = LAYOUT[fmt]
    if not embed_only:
        copy_fixture(guide, visual_dir)
    embed(fmt, guide, page_rel)


def copy_fixture(guide: Path, visual_dir: str) -> None:
    shutil.copy(FIXTURE / "visuals.yaml", guide / "visuals.yaml")
    shutil.copytree(FIXTURE / "visuals", guide / "visuals", dirs_exist_ok=True)
    (guide / visual_dir).mkdir(parents=True, exist_ok=True)
    for name in ("colors.svg", "table.png"):
        shutil.copy(FIXTURE / "static" / name, guide / visual_dir / name)
    for name in ("colors.visual.yaml", "table.visual.yaml"):
        shutil.copy(FIXTURE / "static" / name, guide / "visuals" / name)


def embed(fmt: str, guide: Path, page_rel: str) -> None:
    page = guide / page_rel
    lines = page.read_text().splitlines()
    if fmt == "antora":
        at = lines.index("// Sources:") + 1
        lines[at:at] = ["// visual:colors", "// visual:table"]
        body = ["", "The demo tools look like this.", "",
                f'image::visuals/colors.svg["{ALT["colors"]}"]', "",
                f'image::visuals/table.png["{ALT["table"]}"]']
    else:
        at = next(i for i, line in enumerate(lines) if line.startswith("<!-- Sources:")) + 1
        lines[at:at] = ["visual:colors", "visual:table"]
        body = ["", "The demo tools look like this.", "",
                f"![{ALT['colors']}](../assets/visuals/colors.svg)", "",
                f"![{ALT['table']}](../assets/visuals/table.png)"]
    page.write_text("\n".join(lines + body) + "\n")


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]), "--embed-only" in sys.argv[3:])
