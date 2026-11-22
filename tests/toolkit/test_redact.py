"""Redaction and mask rules (capture/redact.py, FR-018, FR-021, FR-022)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "guide" / "toolkit" / "capture"))
import redact  # noqa: E402

VALUES = {"user": "alice", "home": "/home/alice", "host": "build-box.corp.example"}
SUBNET = "10.89.7.0/24"


def run(text, disabled=None, recipe=None, masks=None, values=VALUES, subnet=SUBNET):
    rules = redact.resolve(redact.effective_rules(recipe, disabled), values, run_subnet=subnet)
    return redact.apply(text, rules, masks)


@pytest.mark.parametrize("rule,sample,expected", [
    ("home-path", "report at /home/alice/report.md", "report at /home/user/report.md"),
    ("user-path", "see /Users/alice/notes", "see /Users/user/notes"),
    ("user-at", "ssh alice@server", "ssh user@server"),
    ("hostname", "running on build-box.corp.example now", "running on example-host now"),
    ("hostname", "short name build-box here", "short name example-host here"),
    ("ipv4", "connect 172.16.4.20:5000", "connect 192.0.2.1:5000"),
    ("bearer", "Authorization: Bearer abcdefghijklmnop123", "Authorization: Bearer <redacted>"),
    ("api-key", "key sk-ABCDEFGHIJKLMNOPQRSTUVWX1234", "key <redacted>"),
    ("api-key", "token ghp_" + "a" * 36, "token <redacted>"),
    ("api-key", "API_KEY=supersecretvalue", "API_KEY=<redacted>"),
    ("jwt", "jwt eyJhbGciOi.eyJzdWIiOiIx.c2lnbmF0dXJl end", "jwt <redacted-jwt> end"),
    ("k8s-api", "server: https://api.prod.acme.net:6443", "server: https://api.cluster.example.com:6443"),
    ("k8s-api", "server: https://cluster7.internal:6443/x", "server: https://api.cluster.example.com:6443/x"),
])
def test_default_rule_replaces(rule, sample, expected):
    text, counts, masked = run(sample)
    assert text == expected
    assert counts[rule] >= 1
    assert masked == 0


@pytest.mark.parametrize("address", ["127.0.0.1", "0.0.0.0", "192.0.2.10", "198.51.100.7", "203.0.113.200", "10.89.7.15"])
def test_ipv4_exemptions(address):
    text, counts, _ = run(f"listening on {address}:8080")
    assert text == f"listening on {address}:8080"
    assert counts["ipv4"] == 0


def test_run_subnet_only_when_given():
    text, counts, _ = run("peer 10.89.7.15", subnet=None)
    assert text == "peer 192.0.2.1" and counts["ipv4"] == 1


def test_version_numbers_are_not_addresses():
    text, counts, _ = run("version 1.2.3.4.5 and 2.19.0")
    assert text == "version 1.2.3.4.5 and 2.19.0"
    assert counts["ipv4"] == 0


def test_disabled_rule_not_applied():
    text, counts, _ = run("ssh alice@server", disabled=["user-at"])
    assert text == "ssh alice@server"
    assert "user-at" not in counts


def test_recipe_rule_literal_replacement():
    text, counts, _ = run("tenant acme-42 and acme-7", recipe=[{"id": "tenant", "pattern": "acme-[0-9]+",
                                                               "replacement": "example-\\1"}])
    assert text == "tenant example-\\1 and example-\\1"
    assert counts["tenant"] == 2


def test_masks_fixed_value():
    masks = [{"pattern": r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", "replacement": "2026-01-01 12:00:00"},
             {"pattern": r"run-[0-9a-f]{8}", "replacement": "run-00000000"}]
    text, _, masked = run("at 2025-03-04 05:06:07 run-deadbeef and 2024-01-02 03:04:05", masks=masks)
    assert text == "at 2026-01-01 12:00:00 run-00000000 and 2026-01-01 12:00:00"
    assert masked == 3


def test_counts_per_rule():
    _, counts, _ = run("/home/alice/a /home/alice/b alice@x 172.16.0.1")
    assert counts["home-path"] == 2
    assert counts["user-at"] == 1
    assert counts["ipv4"] == 1
    assert counts["hostname"] == 0


def test_describe_has_no_host_values():
    rules = redact.effective_rules([{"id": "tenant", "pattern": "acme-[0-9]+", "replacement": "x"}], ["jwt"])
    described = redact.describe(rules)
    blob = json.dumps(described)
    for value in ("alice", "/home/alice", "build-box"):
        assert value not in blob
    ids = [d["id"] for d in described]
    assert "jwt" not in ids and ids[-1] == "tenant"
    assert all(set(d) == {"id", "template", "replacement"} for d in described)


def test_missing_values_never_match():
    text, counts, _ = run("/home/alice and build-box", values={"user": "", "home": "", "host": ""})
    assert text == "/home/alice and build-box"
    assert counts["home-path"] == 0 and counts["hostname"] == 0


def test_resolved_rules_are_json():
    rules = redact.resolve(redact.effective_rules(), VALUES, run_subnet=SUBNET)
    assert json.loads(json.dumps(rules)) == rules
    assert set(redact.DEFAULT_IDS) == {"home-path", "user-path", "user-at", "hostname", "ipv4", "bearer",
                                       "api-key", "jwt", "k8s-api", "private-key"}


def test_macos_home_path():
    values = {"user": "bob", "home": "/Users/bob", "host": "laptop"}
    text, counts, _ = run("open /Users/bob/project and /Users/bobby/x", values=values)
    assert text == "open /home/user/project and /Users/bobby/x"
    assert counts["home-path"] == 1


@pytest.mark.parametrize("sample,expected", [
    ('{"password": "hunter2hunter2"}', '{"password": <redacted>"}'),
    ("'api_key': 'abcdefghijkl'", "'api_key': <redacted>'"),
    ("token=abcdefghijkl", "token=<redacted>"),
    ("oc token sha256~" + "a" * 43, "oc token <redacted>"),
])
def test_quoted_keys_and_more_token_shapes(sample, expected):
    assert run(sample)[0] == expected


def test_hostname_is_case_insensitive():
    assert run("on BUILD-BOX.corp.example and Build-Box")[0] == "on example-host and example-host"


def test_private_key_block():
    text, counts, _ = run("a\n-----BEGIN OPENSSH PRIVATE KEY-----\nAAAA\n-----END OPENSSH PRIVATE KEY-----\nb")
    assert text == "a\n<redacted-private-key>\nb" and counts["private-key"] == 1


def test_segments_match_across_boundaries():
    rules = redact.resolve(redact.effective_rules(), VALUES, run_subnet=SUBNET)
    segs, counts, _ = redact.apply_segments(["see /ho", "me/ali", "ce/x on ", "build-box", " ok"], rules)
    assert "".join(segs) == "see /home/user/x on example-host ok"
    assert segs == ["see /home/user", "", "/x on ", "example-host", " ok"]
    assert counts["home-path"] == 1 and counts["hostname"] == 1


def test_segments_equal_apply_for_one_segment():
    rules = redact.resolve(redact.effective_rules(), VALUES, run_subnet=SUBNET)
    text = "a /home/alice b alice@x c 172.16.0.9 /home/alice"
    masks = [{"pattern": "c", "replacement": "C"}]
    segs, counts, masked = redact.apply_segments([text], rules, masks)
    assert (segs[0], counts, masked) == redact.apply(text, rules, masks)


def test_segments_several_matches_in_one_segment_after_a_split_match():
    rules = redact.resolve(redact.effective_rules(), VALUES, run_subnet=SUBNET)
    segs, counts, _ = redact.apply_segments(["/home/al", "ice and /home/alice and /home/alice"], rules)
    assert "".join(segs) == "/home/user and /home/user and /home/user"
    assert counts["home-path"] == 3
