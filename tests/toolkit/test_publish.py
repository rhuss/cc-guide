"""tools/guide/publish.py: writing and checking an author-owned README region (specs/006, story 1)."""
import os
import subprocess
import sys
from pathlib import Path

import yaml

import guidecfg

TOOLKIT = Path(__file__).resolve().parents[2] / "guide" / "toolkit"
ADAPTERS = Path(__file__).resolve().parents[2] / "guide" / "adapters"

BEGIN = "<!-- guide:region -->"
END = "<!-- /guide:region -->"

# The source page: a sources block, generated attr regions, and every link form.
INTRO = (
    "# Intro\n\n"
    "<!-- Sources:\n"
    "mini:config/defaults.yaml:2-4\n"
    "-->\n\n"
    "Version <!-- guide:attr mini-version -->0.0.0<!-- /guide:attr -->.\n\n"
    "Start with the [install steps](admin/install.md), see the\n"
    "[architecture](<assets/arch.svg>), the [notes][notes], and\n"
    "[the project](https://example.com/mini). The [summary](#intro) is above.\n\n"
    "[notes]: notes.md\n"
)

README = (
    "# My Project\n\n"
    "Hand-written pitch. Every byte here is the author's.\n"
    "\n"
    + BEGIN + "\n"
    "placeholder\n"
    + END + "\n"
    "\n"
    "Trailing author text, also untouchable.\n"
)


def make_guide(dest: Path, readme: str = README, page: str = INTRO, publish: dict | None = None) -> Path:
    """A standalone gfm guide at dest/guide publishing docs/intro.md into dest/README.md."""
    root = dest / "guide"
    tools = root / "tools" / "guide"
    tools.mkdir(parents=True)
    (tools / "adapter.yaml").write_text((ADAPTERS / "gfm" / "adapter.yaml").read_text())
    (root / "docs").mkdir()
    (root / "docs" / "intro.md").write_text(page)
    (root / "guide.yaml").write_text(yaml.safe_dump({
        "schema": 1, "title": "Pub Guide", "format": "gfm",
        "personas": [{"id": "admin", "title": "Administrator", "start": "docs/intro"}],
        "sections": [{"id": "overview", "title": "Overview", "voice": "concepts"}],
        "publish": publish if publish is not None else {"page": "docs/intro.md", "target": "../README.md"},
    }, sort_keys=False))
    (root / "baseline.yaml").write_text(yaml.safe_dump(
        {"captured": "2026-11-09", "sources": [{"id": "mini", "repo": "example/mini", "commit": "a" * 40,
                                                "attributes": {"version": "1.2.3"}}]}, sort_keys=False))
    (dest / "README.md").write_text(readme)
    return root


def publish(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOLKIT / "publish.py"), *args, "--root", str(root)],
                          capture_output=True, text=True)


def readme(root: Path) -> str:
    return (root.parent / "README.md").read_text()


# --- writer (T006) ----------------------------------------------------------------------


def test_write_splices_only_the_region(tmp_path):
    root = make_guide(tmp_path)
    before = readme(root)
    proc = publish(root, "--write")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    after = readme(root)
    # every byte outside the markers is unchanged, and the placeholder is gone
    prefix, _, rest = after.partition(BEGIN)
    content, _, suffix = rest.partition(END)
    assert prefix == "# My Project\n\nHand-written pitch. Every byte here is the author's.\n\n"
    assert suffix == "\n\nTrailing author text, also untouchable.\n"
    assert "placeholder" not in content
    assert before != after
    # a second write is a no-op (the rendered region is already current)
    assert publish(root, "--write").returncode == 0
    assert readme(root) == after


def test_write_rebases_links_for_the_target_location(tmp_path):
    root = make_guide(tmp_path)
    assert publish(root, "--write").returncode == 0
    content = readme(root).partition(BEGIN)[2].partition(END)[0]
    assert "](guide/docs/admin/install.md)" in content
    assert "](<guide/docs/assets/arch.svg>)" in content
    assert "[notes]: guide/docs/notes.md" in content
    # absolute URLs and pure fragments pass through untouched
    assert "[the project](https://example.com/mini)" in content
    assert "[summary](#intro)" in content


def test_write_keeps_sources_block_and_attr_regions(tmp_path):
    root = make_guide(tmp_path)
    assert publish(root, "--write").returncode == 0
    content = readme(root).partition(BEGIN)[2].partition(END)[0]
    assert "<!-- Sources:\nmini:config/defaults.yaml:2-4\n-->" in content
    assert "<!-- guide:attr mini-version -->0.0.0<!-- /guide:attr -->" in content


def test_write_without_markers_errors_and_writes_nothing(tmp_path):
    root = make_guide(tmp_path, readme="# My Project\n\nNo markers here.\n")
    before = readme(root)
    proc = publish(root, "--write")
    assert proc.returncode == 1
    assert "guide:region" in proc.stderr and "README.md" in proc.stderr
    assert readme(root) == before


def test_write_with_malformed_markers_errors_and_writes_nothing(tmp_path):
    bad = "# My Project\n\n" + BEGIN + "\nguide text with no end marker\n"
    root = make_guide(tmp_path, readme=bad)
    proc = publish(root, "--write")
    assert proc.returncode == 1
    assert "README.md" in proc.stderr and "no matching counterpart" in proc.stderr
    assert readme(root) == bad


def test_without_a_publish_block_is_a_no_op(tmp_path):
    root = make_guide(tmp_path, publish={})
    # an empty publish block is invalid; use a guide.yaml without the block instead
    data = yaml.safe_load((root / "guide.yaml").read_text())
    data.pop("publish")
    (root / "guide.yaml").write_text(yaml.safe_dump(data, sort_keys=False))
    before = readme(root)
    for mode in ("--write", "--check"):
        proc = publish(root, mode)
        assert proc.returncode == 0, (mode, proc.stdout + proc.stderr)
        assert "publish" in proc.stdout.lower()
    assert readme(root) == before


# --- check (T007) -----------------------------------------------------------------------


def test_check_passes_after_write(tmp_path):
    root = make_guide(tmp_path)
    assert publish(root, "--write").returncode == 0
    proc = publish(root, "--check")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "up to date" in proc.stdout


def test_check_fails_with_a_diff_when_the_region_was_edited(tmp_path):
    root = make_guide(tmp_path)
    assert publish(root, "--write").returncode == 0
    front = root.parent / "README.md"
    front.write_text(front.read_text().replace("# Intro", "# Hand-edited intro"))
    proc = publish(root, "--check")
    assert proc.returncode == 1
    assert "differs" in proc.stdout
    assert "-# Hand-edited intro" in proc.stdout and "+# Intro" in proc.stdout


def test_check_passes_when_only_author_text_was_edited(tmp_path):
    root = make_guide(tmp_path)
    assert publish(root, "--write").returncode == 0
    front = root.parent / "README.md"
    front.write_text(front.read_text().replace("Hand-written pitch.",
                                               "Hand-written pitch, now edited by the author."))
    assert publish(root, "--check").returncode == 0


def test_check_fails_when_the_region_is_stale_after_a_page_edit(tmp_path):
    root = make_guide(tmp_path)
    assert publish(root, "--write").returncode == 0
    (root / "docs" / "intro.md").write_text(INTRO.replace("# Intro", "# New intro"))
    proc = publish(root, "--check")
    assert proc.returncode == 1 and "differs" in proc.stdout


def test_missing_source_page_fails_naming_the_page(tmp_path):
    root = make_guide(tmp_path)
    (root / "docs" / "intro.md").unlink()
    for mode in ("--check", "--write"):
        proc = publish(root, mode)
        assert proc.returncode == 1, mode
        assert "docs/intro.md" in proc.stderr and "not found" in proc.stderr
