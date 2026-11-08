"""Shared fixtures for the toolkit tests."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

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


# --- embedded mode (specs/005-embedded-guide) ----------------------------------

HOST_ENV = {
    "GIT_AUTHOR_NAME": "Fixture Author", "GIT_AUTHOR_EMAIL": "fixture@example.com",
    "GIT_COMMITTER_NAME": "Fixture Author", "GIT_COMMITTER_EMAIL": "fixture@example.com",
    "GIT_AUTHOR_DATE": "2026-04-01T10:00:00+00:00", "GIT_COMMITTER_DATE": "2026-04-01T10:00:00+00:00",
    "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
}


def host_git(host: Path, *args: str) -> str:
    """Run git in a host repository with a fixed identity, no hooks, and no signing."""
    env = {**os.environ, **HOST_ENV}
    return subprocess.run(["git", "-C", str(host), "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
                           *args], check=True, capture_output=True, text=True, env=env).stdout.strip()


def commit_all(host: Path, message: str) -> str:
    """Stage everything in the host repository, commit, and return the new HEAD."""
    host_git(host, "add", "-A")
    host_git(host, "commit", "--quiet", "--allow-empty", "-m", message)
    return host_git(host, "rev-parse", "HEAD")


def build_mini_host(dest: Path) -> tuple[Path, str]:
    """Copy tests/fixtures/mini-host to dest, make it a git repository on main, and commit it."""
    shutil.copytree(FIXTURES / "mini-host", dest)
    subprocess.run(["git", "init", "--quiet", "-b", "main", str(dest)], check=True, capture_output=True,
                   env={**os.environ, **HOST_ENV})
    return dest, commit_all(dest, "Initial Mini Host")


@pytest.fixture
def mini_host(tmp_path: Path) -> tuple[Path, str]:
    """The mini-host fixture as a git repository with one commit: (path, commit SHA)."""
    return build_mini_host(tmp_path / "host")


OWNERSHIP = ("<!-- guide: front page. This file is generated and maintained by cc-guide; "
             "change it with /guide:evolve. -->")


def make_embedded_guide(host: Path, commit: str, name: str = "guide", front_page: str | None = None,
                        extra_guide: dict | None = None, sources: list[dict] | None = None,
                        fingerprints: dict | None = None) -> Path:
    """An embedded gfm guide project in host/<name> with `self` pinned to commit.

    front_page, when given, is written to the host README.md (the guide owns it).
    """
    root = host / name
    tools = root / "tools" / "guide"
    tools.mkdir(parents=True, exist_ok=True)
    (tools / "adapter.yaml").write_text((REPO / "guide/adapters/gfm/adapter.yaml").read_text())
    guide = {
        "schema": 1, "title": "Mini Host", "format": "gfm",
        "personas": [{"id": "admin", "title": "Administrator", "start": "admin/install"}],
        "sections": [{"id": "overview", "title": "Overview", "voice": "concepts"},
                     {"id": "admin", "title": "Admin guide", "voice": "technical"}],
        "internal": {"enabled": False, "confidential_terms": [], "confidential_patterns": []},
        "embedded": {"front_page": "../README.md"},
    }
    guide.update(extra_guide or {})
    (root / "guide.yaml").write_text(yaml.safe_dump(guide, sort_keys=False))
    entry = {"id": "self", "repo": "..", "ref": "main", "commit": commit, "status": "verified"}
    if fingerprints is not None:
        entry["fingerprints"] = fingerprints
    (root / "baseline.yaml").write_text(yaml.safe_dump(
        {"captured": "2026-04-01", "sources": [entry] + (sources or [])}, sort_keys=False))
    docs = root / "docs"
    (docs / "admin").mkdir(parents=True, exist_ok=True)
    (docs / "README.md").write_text("<!-- guide: no-sources -->\n\nThis guide starts at the "
                                    "[repository front page](../../README.md).\n")
    (docs / "SUMMARY.md").write_text("# Summary\n\n<!-- guide: no-sources -->\n\n## Overview\n\n"
                                     "- [Mini Host](README.md)\n\n## Admin guide\n\n- [Install](admin/install.md)\n")
    (docs / "admin" / "install.md").write_text(
        "# Install\n\n<!-- Sources:\nself:config/defaults.yaml:1-3\n-->\n\n"
        "The greeting comes from the defaults file. Back to the [front page](../../../README.md).\n")
    if front_page is not None:
        (host / "README.md").write_text(front_page)
    return root


FRONT_PAGE = OWNERSHIP + """
# Mini Host

[![CI](https://img.shields.io/badge/ci-passing-brightgreen.svg)](https://example.com/ci)

<!-- Sources:
self:src/cli.py:1-12
self:pyproject.toml
-->

Mini Host prints a greeting.

## Overview

Read the guide in this order.

## Admin guide

- [Install](guide/docs/admin/install.md)

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) and the [license](LICENSE).
"""
