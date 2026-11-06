"""guide/scripts/superpowers-probe.sh: advisory-only version check (FR-016).

The probe no longer reads a plugin registry or an install path. Presence of
superpowers is decided by capability exposure in the session, not here. The probe
only compares a best-effort reported version against the single known-good
threshold in guide/compat.yaml and never blocks.
"""
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PROBE = REPO / "guide" / "scripts" / "superpowers-probe.sh"
COMPAT = REPO / "guide" / "compat.yaml"


def threshold() -> str:
    m = re.search(r'^known_good_version:\s*"?([0-9][0-9.]*)"?', COMPAT.read_text(), re.M)
    assert m, "compat.yaml must record a known_good_version"
    return m.group(1)


def bump(version: str, delta: int) -> str:
    parts = [int(p) for p in version.split(".")]
    parts[0] += delta
    return ".".join(str(p) for p in parts)


def probe(version: str | None = None, no_jq: bool = False):
    env = dict(os.environ)
    if no_jq:
        env["CC_GUIDE_NO_JQ"] = "1"
    args = ["bash", str(PROBE)] + ([version] if version is not None else [])
    proc = subprocess.run(args, capture_output=True, text=True, env=env)
    return proc.returncode, json.loads(proc.stdout), proc


@pytest.mark.parametrize("no_jq", [False, True])
def test_known_good_version(no_jq):
    code, out, _ = probe(threshold(), no_jq)
    assert code == 0
    assert out == {"version": threshold(), "known": True, "ok": True, "problems": []}


@pytest.mark.parametrize("no_jq", [False, True])
def test_newer_version_is_known_good(no_jq):
    v = bump(threshold(), 1)
    code, out, _ = probe(v, no_jq)
    assert code == 0
    assert out["version"] == v and out["known"] is True and out["ok"] is True and out["problems"] == []


@pytest.mark.parametrize("no_jq", [False, True])
def test_below_threshold_warns_but_never_blocks(no_jq):
    v = bump(threshold(), -1)
    code, out, _ = probe(v, no_jq)
    assert code == 3                      # advisory, not a block
    assert out["known"] is False
    assert out["ok"] is True             # ok stays true: the probe never blocks
    assert any("older than the known-good" in p for p in out["problems"])


@pytest.mark.parametrize("no_jq", [False, True])
def test_no_version_skips_the_comparison(no_jq):
    code, out, _ = probe(None, no_jq)
    assert code == 0
    assert out == {"version": None, "known": False, "ok": True, "problems": []}
