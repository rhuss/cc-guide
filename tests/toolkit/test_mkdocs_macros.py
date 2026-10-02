from pathlib import Path

import pytest
import yaml

import guidecfg
import mkdocs_macros


class FakeEnv:
    """The parts of the mkdocs-macros environment that define_env uses."""

    def __init__(self, project_dir: Path):
        self.project_dir = str(project_dir)
        self.macros: dict = {}
        self.variables: dict = {}

    def macro(self, fn):
        self.macros[fn.__name__] = fn
        return fn


@pytest.fixture
def env(render_fixture_guide):
    e = FakeEnv(render_fixture_guide)
    mkdocs_macros.define_env(e)
    return e


def test_attr_returns_baseline_values(env, fixture_repo):
    assert env.macros["attr"]("mini-commit-short") == fixture_repo[1][:7]
    assert env.macros["attr"]("mini-version") == "1.2.3"
    assert env.variables["baseline_values"]["baseline-date"] == "2026-01-06"


def test_attr_unknown_name_fails_the_build(env):
    with pytest.raises(KeyError, match="mini-nope"):
        env.macros["attr"]("mini-nope")


def test_baseline_note(env, fixture_repo):
    note = env.macros["baseline_note"]()
    assert note.startswith('!!! note "Baseline"')
    assert f"mini {fixture_repo[1][:7]}" in note and "2026-01-06" in note


def test_experimental_tiers(env):
    review = env.macros["experimental"]("in-review", "Status history", 4)
    assert review.startswith('!!! experimental "Experimental: in review"')
    assert "Status history is not part of the baseline" in review
    assert "change request #4" in review
    merged = env.macros["experimental"]("on-main", "Admin UI", "5")
    assert merged.startswith('!!! experimental "Experimental: on main"')
    assert "merged on the default branch" in merged


def test_experimental_unknown_tier(env):
    with pytest.raises(ValueError, match="released"):
        env.macros["experimental"]("released", "X", 4)


def test_label_links_github_change_requests(tmp_guide):
    (tmp_guide / "baseline.yaml").write_text(yaml.safe_dump({
        "captured": "2026-09-30",
        "sources": [{"id": "saw", "repo": "validatedpatterns-sandbox/secure-agent-workspace",
                     "commit": "c84103d7eeb502a01930163d422051d5beb63432"}],
        "change_requests": [{"source": "saw", "number": 56, "head": "e9f78b05a4a1bf7ad2c294b03374d439b1413226",
                             "state": "open", "tier": "in-review", "anchor": "openshell-upgrade"}],
    }))
    baseline = guidecfg.load_baseline(tmp_guide)
    linked = mkdocs_macros.label("in-review", "Upgrade", 56, baseline, baseline.captured)
    assert "[change request #56](https://github.com/validatedpatterns-sandbox/secure-agent-workspace/pull/56)" in linked
    plain = mkdocs_macros.label("in-review", "Other", 99, baseline, baseline.captured)
    assert "change request #99" in plain and "](" not in plain


def test_label_does_not_link_local_repositories(render_fixture_guide):
    baseline = guidecfg.load_baseline(render_fixture_guide)
    text = mkdocs_macros.label("in-review", "Status history", 4, baseline, baseline.captured)
    assert "change request #4" in text and "](" not in text  # file:// repositories get no link
