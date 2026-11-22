"""capture/web.py redaction of page items (FR-018, FR-021), without a browser."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "guide" / "toolkit" / "capture"))
import redact  # noqa: E402
import web  # noqa: E402

VALUES = {"user": "alice", "home": "/home/alice", "host": "build-box"}
RULES = redact.resolve(redact.effective_rules(), VALUES)


def test_text_split_across_inline_elements_is_redacted():
    # <p>see <span>/home/</span><b>alice</b>/notes on build-box</p>, then a separate cell
    items = [{"value": "see ", "group": 0}, {"value": "/home/", "group": 0}, {"value": "alice", "group": 0},
             {"value": "/notes on build-box", "group": 0}, {"value": "alice", "group": 1}]
    changes, counts, _ = web.redaction_changes(items, RULES, [])
    new = [it["value"] for it in items]
    for index, value in changes:
        new[index] = value
    assert "".join(new[:4]) == "see /home/user/notes on example-host"
    assert new[4] == "alice"     # another block: no match across block boundaries
    assert counts["home-path"] == 1 and counts["hostname"] == 1


def test_attributes_and_values_stand_alone():
    items = [{"value": "/home/", "group": None}, {"value": "alice", "group": None},
             {"value": "token=abcdefghijkl", "group": None}]
    changes, counts, _ = web.redaction_changes(items, RULES, [])
    assert changes == [[2, "token=<redacted>"]]
    assert counts["api-key"] == 1


def test_masks_apply_to_page_items():
    items = [{"value": "run at 2026-", "group": 3}, {"value": "11-22", "group": 3}]
    changes, _, masked = web.redaction_changes(items, RULES, [{"pattern": r"\d{4}-\d{2}-\d{2}",
                                                               "replacement": "2026-01-01"}])
    assert masked == 1
    assert changes == [[0, "run at 2026-01-01"], [1, ""]]


def test_collector_walks_shadow_roots_and_frames():
    js = web.COLLECT_JS
    assert "shadowRoot" in js and "contentDocument" in js
    for attr in ("aria-label", "aria-valuetext", "aria-description", "title", "alt", "placeholder"):
        assert f"'{attr}'" in js
