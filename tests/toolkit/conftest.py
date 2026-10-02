"""Shared fixtures for the toolkit tests."""
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures"
TOOLKIT = REPO / "guide" / "toolkit"


@pytest.fixture
def tmp_guide(tmp_path: Path) -> Path:
    """An empty guide project directory."""
    root = tmp_path / "guide"
    root.mkdir()
    return root


def build_mini_repo(dest: Path) -> tuple[Path, str, str, str]:
    """Run make-mini-repo.sh and return (path, first, second, third)."""
    out = subprocess.run(
        ["bash", str(FIXTURES / "make-mini-repo.sh"), str(dest)],
        check=True, capture_output=True, text=True,
    ).stdout
    shas = dict(line.split("=", 1) for line in out.split() if "=" in line)
    return dest, shas["FIRST"], shas["SECOND"], shas["THIRD"]


@pytest.fixture
def fixture_repo(tmp_path: Path) -> tuple[Path, str, str, str]:
    """The mini-project as a git repository with three commits."""
    return build_mini_repo(tmp_path / "mini-repo")


def render(text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def render_guide(dest: Path, repo: tuple[Path, str, str, str]) -> Path:
    """Copy the neutral sample guide to dest and render its templates."""
    path, first, second, third = repo
    shutil.copytree(FIXTURES / "sample-guide", dest)
    values = {
        "MINI_REPO_URL": path.as_uri(),
        "MINI_FIRST_COMMIT": first,
        "MINI_SECOND_COMMIT": second,
        "MINI_THIRD_COMMIT": third,
        "FIXTURES_DIR": str(FIXTURES),
    }
    tmpl = dest / "baseline.yaml.tmpl"
    (dest / "baseline.yaml").write_text(render(tmpl.read_text(), values))
    tmpl.unlink()
    inputs = dest / "inputs.yaml"
    inputs.write_text(render(inputs.read_text(), values))
    return dest


@pytest.fixture
def render_fixture_guide(tmp_path: Path, fixture_repo) -> Path:
    """The sample guide with baseline.yaml pinned to the fixture repository's first commit."""
    return render_guide(tmp_path / "sample-guide", fixture_repo)
