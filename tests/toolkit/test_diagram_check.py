import copy
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

import diagram_check

TOOLKIT = Path(__file__).resolve().parents[2] / "guide" / "toolkit"
SCENES = Path(__file__).resolve().parents[1] / "fixtures" / "diagrams"


def kinds(findings):
    return sorted(f.kind for f in findings)


def run_cli(*args):
    return subprocess.run([sys.executable, str(TOOLKIT / "diagram_check.py"), *map(str, args)],
                          capture_output=True, text=True)


def test_straight_arrow_crossing_unbound_text():
    findings = diagram_check.check(diagram_check.load_scene(SCENES / "straight-text.excalidraw"))
    assert kinds(findings) == ["arrow-crosses-text"]
    assert set(findings[0].element_ids) == {"arr", "note"}


def test_curved_arrow_crossing_box_is_reported():
    scene = diagram_check.load_scene(SCENES / "curved-box.excalidraw")
    findings = diagram_check.check(scene)
    assert kinds(findings) == ["arrow-crosses-box"]
    assert set(findings[0].element_ids) == {"curve", "c"}


def test_straight_chord_of_the_curve_would_not_cross():
    raw = json.loads((SCENES / "curved-box.excalidraw").read_text())
    arrow = next(e for e in raw["elements"] if e["id"] == "curve")
    arrow["points"] = [[0, 0], [400, 0]]
    arrow["roundness"] = None
    arrow["height"] = 0
    assert diagram_check.check(diagram_check.scene_from_dict(raw)) == []


def test_catmull_rom_passes_through_points():
    scene = diagram_check.load_scene(SCENES / "curved-box.excalidraw")
    samples = diagram_check.sample_arrow(scene.elements["curve"])
    for px, py in [(50, 64), (240, 160), (450, 64)]:
        assert min(math.dist((px, py), s) for s in samples) < 0.5
    # roughly one sample every 4 px along the path
    assert len(samples) > 100
    assert max(math.dist(a, b) for a, b in zip(samples, samples[1:])) <= 4.5


def test_polyline_sampling_step():
    scene = diagram_check.load_scene(SCENES / "straight-text.excalidraw")
    samples = diagram_check.sample_arrow(scene.elements["arr"], step_px=4)
    assert samples[0] == (104, 30) and samples[-1] == (396, 30)
    assert max(math.dist(a, b) for a, b in zip(samples, samples[1:])) <= 4.0001


def test_arrow_ends_inside_bound_boxes_not_reported():
    # The arrow starts and ends inside its bound boxes, crosses their labels there,
    # and carries its own label at the midpoint: all fine.
    assert diagram_check.check(diagram_check.load_scene(SCENES / "clean.excalidraw")) == []


def test_bound_via_box_bound_elements_only():
    raw = json.loads((SCENES / "clean.excalidraw").read_text())
    arrow = next(e for e in raw["elements"] if e["id"] == "arr")
    arrow["startBinding"] = None
    findings = diagram_check.check(diagram_check.scene_from_dict(raw))
    # box "a" still lists the arrow in boundElements: crossing it is fine,
    # but the arrow end itself is not bound.
    assert kinds(findings) == ["unbound-arrow-end"]


def test_label_and_box_crossing_frame_border():
    findings = diagram_check.check(diagram_check.load_scene(SCENES / "frame-border.excalidraw"))
    crossing = {fid for f in findings if f.kind == "crosses-frame-border" for fid in f.element_ids}
    assert kinds(findings) == ["crosses-frame-border"] * 3
    assert {"straddle", "flabel", "g-title"} <= crossing
    assert not {"inside", "g-child", "far"} & crossing


def test_duplicate_bound_text_and_unbound_ends():
    findings = diagram_check.check(diagram_check.load_scene(SCENES / "dup-unbound.excalidraw"))
    assert kinds(findings) == ["duplicate-bound-text", "unbound-arrow-end", "unbound-arrow-end"]
    dup = next(f for f in findings if f.kind == "duplicate-bound-text")
    assert set(dup.element_ids) == {"a", "t1", "t2"}  # the deleted t3 does not count
    unbound = {f.element_ids[0] for f in findings if f.kind == "unbound-arrow-end"}
    assert unbound == {"loose", "ghost"}


def test_rotated_box_uses_rotated_bounds():
    raw = json.loads((SCENES / "straight-text.excalidraw").read_text())
    raw["elements"] = [e for e in raw["elements"] if e["id"] != "note"]
    # a tall thin box above the arrow; rotated by 90 degrees it lies across the arrow
    raw["elements"].append({"id": "bar", "type": "rectangle", "x": 245, "y": -80, "width": 10, "height": 80,
                            "angle": 0, "isDeleted": False, "groupIds": [], "boundElements": None})
    assert diagram_check.check(diagram_check.scene_from_dict(copy.deepcopy(raw))) == []
    raw["elements"][-1]["angle"] = math.pi / 2
    raw["elements"][-1]["y"] = -10
    findings = diagram_check.check(diagram_check.scene_from_dict(raw))
    assert kinds(findings) == ["arrow-crosses-box"]


def test_deleted_elements_are_ignored():
    raw = json.loads((SCENES / "straight-text.excalidraw").read_text())
    next(e for e in raw["elements"] if e["id"] == "note")["isDeleted"] = True
    assert diagram_check.check(diagram_check.scene_from_dict(raw)) == []


def test_cli_clean_scene_exits_zero():
    proc = run_cli("check", SCENES / "clean.excalidraw")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(proc.stdout.strip().splitlines()[-1])["count"] == 0


def test_cli_findings_exit_one_with_text_and_json():
    proc = run_cli("check", SCENES / "curved-box.excalidraw")
    assert proc.returncode == 1
    lines = proc.stdout.strip().splitlines()
    assert any(line.startswith("arrow-crosses-box") for line in lines)
    report = json.loads(lines[-1])
    assert report["count"] == 1
    assert report["findings"][0]["kind"] == "arrow-crosses-box"
    proc = run_cli("check", "--json", SCENES / "curved-box.excalidraw")
    assert json.loads(proc.stdout)["count"] == 1


def test_cli_missing_scene_exits_two(tmp_path):
    assert run_cli("check", tmp_path / "nope.excalidraw").returncode == 2


@pytest.fixture
def exported_png(tmp_path):
    """A synthetic 4x export of the curved-box scene with a unique color per pixel column/row."""
    from PIL import Image

    scene = diagram_check.load_scene(SCENES / "curved-box.excalidraw")
    x0, y0, x1, y1 = scene.bounds
    scale, padding = 4, 10
    width = round((x1 - x0 + 2 * padding) * scale)
    height = round((y1 - y0 + 2 * padding) * scale)
    img = Image.new("RGB", (width, height))
    img.putdata([(x % 256, y % 256, (x // 256 + y // 256) % 256) for y in range(height) for x in range(width)])
    path = tmp_path / "export.png"
    img.save(path)
    return path, scene, scale, padding


def test_crops_tiles_native_resolution_and_one_per_finding(exported_png, tmp_path):
    from PIL import Image

    png, scene, scale, padding = exported_png
    findings = diagram_check.check(scene)
    out = tmp_path / "crops"
    paths = diagram_check.crops(png, scene, out, findings)
    full = Image.open(png)
    tiles = [p for p in paths if p.name.startswith("tile-")]
    finding_crops = [p for p in paths if p.name.startswith("finding-")]
    assert len(finding_crops) == len(findings) == 1
    assert full.width > 1600  # forces more than one tile column
    assert len(tiles) == math.ceil(full.width / 1600) * math.ceil(full.height / 1200)
    covered = 0
    for tile in tiles:
        img = Image.open(tile)
        assert img.width <= 1600 and img.height <= 1200
        covered += img.width * img.height
    assert covered == full.width * full.height
    # native resolution: the second column tile starts at x=1600 of the export
    second = Image.open(out / "tile-r0-c1.png")
    assert second.getpixel((0, 0)) == full.getpixel((1600, 0))
    assert second.getpixel((5, 7)) == full.getpixel((1605, 7))


def test_scene_to_pixel_mapping(exported_png):
    png, scene, scale, padding = exported_png
    from PIL import Image

    size = Image.open(png).size
    x0, y0, _, _ = scene.bounds
    box = scene.elements["c"].bbox
    px = diagram_check.to_pixels(box, scene, size, padding)
    assert px[0] == pytest.approx((box[0] - x0 + padding) * scale, abs=1)
    assert px[1] == pytest.approx((box[1] - y0 + padding) * scale, abs=1)
    assert px[2] == pytest.approx((box[2] - x0 + padding) * scale, abs=1)


def test_cli_crops(exported_png, tmp_path):
    png, _, _, _ = exported_png
    out = tmp_path / "cli-crops"
    proc = run_cli("crops", png, "--scene", SCENES / "curved-box.excalidraw", "--out", out)
    assert proc.returncode == 0, proc.stderr
    assert any(p.name.startswith("finding-01-") for p in out.iterdir())


# --- claims gate (FR-044) -----------------------------------------------------------

CLEAN_CLAIMS = [
    {"id": "a", "kind": "label", "elements": ["a"], "text": "box a", "sources": ["mini:README.md:3"]},
    {"id": "b", "kind": "label", "elements": ["b"], "text": "box b", "sources": ["mini:config/defaults.yaml:2-4,6"]},
    {"id": "flow", "kind": "connects", "elements": ["arr"], "text": "a calls b",
     "sources": ["url:https://example.com/minisvc"]},
    {"id": "legend", "kind": "legend", "elements": ["legend"]},
]


def clean_scene():
    return diagram_check.load_scene(SCENES / "clean.excalidraw")


def test_claims_cover_clean_scene():
    assert diagram_check.check_claims(clean_scene(), copy.deepcopy(CLEAN_CLAIMS)) == []


def test_claims_report_uncovered_label_and_arrow():
    claims = [c for c in copy.deepcopy(CLEAN_CLAIMS) if c["id"] not in ("b", "flow")]
    findings = diagram_check.check_claims(clean_scene(), claims)
    assert kinds(findings) == ["claim-missing-arrow", "claim-missing-label", "claim-missing-label"]
    labels = {f.element_ids[0] for f in findings if f.kind == "claim-missing-label"}
    assert labels == {"b-label", "arr-label"}


def test_label_claim_does_not_cover_an_arrow():
    claims = copy.deepcopy(CLEAN_CLAIMS)
    claims[2]["kind"] = "label"
    assert kinds(diagram_check.check_claims(clean_scene(), claims)) == ["claim-missing-arrow"]


@pytest.mark.parametrize("sources", [[], ["the README"], ["mini:README.md:three"], ["mini:README.md:3", "nowhere"]])
def test_claims_need_well_formed_sources(sources):
    claims = copy.deepcopy(CLEAN_CLAIMS)
    claims[0]["sources"] = sources
    findings = diagram_check.check_claims(clean_scene(), claims)
    assert kinds(findings) == ["claim-no-source"]


def test_live_source_and_legend_without_source():
    claims = copy.deepcopy(CLEAN_CLAIMS)
    claims[0]["sources"] = ["live:cntbh oc get sandbox -o yaml (2026-10-10)"]
    assert diagram_check.check_claims(clean_scene(), claims) == []


def test_claims_report_unknown_element_and_kind():
    claims = copy.deepcopy(CLEAN_CLAIMS) + [
        {"id": "ghost", "kind": "label", "elements": ["nope"], "sources": ["mini:README.md"]},
        {"id": "odd", "kind": "runs-in", "elements": ["a"], "sources": ["mini:README.md"]},
    ]
    assert kinds(diagram_check.check_claims(clean_scene(), claims)) == ["claim-no-source", "claim-unknown-element"]


def test_every_frame_needs_a_contains_claim():
    scene = diagram_check.load_scene(SCENES / "frame-border.excalidraw")
    labels = [{"id": "t", "kind": "label", "elements": ["flabel", "g-title"], "sources": ["mini:README.md:1"]}]
    findings = diagram_check.check_claims(scene, labels)
    assert kinds(findings) == ["claim-missing-frame", "claim-missing-frame"]
    assert {f.element_ids[0] for f in findings} == {"f1", "g-frame"}
    contains = labels + [{"id": "c", "kind": "contains", "elements": ["f1", "g-frame"], "sources": ["mini:README.md:1"]}]
    assert diagram_check.check_claims(scene, contains) == []


def test_cli_claims(tmp_path):
    import yaml

    good = tmp_path / "claims.yaml"
    good.write_text(yaml.safe_dump({"diagram": "clean", "claims": CLEAN_CLAIMS}))
    proc = run_cli("claims", SCENES / "clean.excalidraw", "--claims", good)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(proc.stdout.splitlines()[-1])["count"] == 0

    bad = tmp_path / "bad.yaml"
    bad.write_text(yaml.safe_dump({"claims": CLEAN_CLAIMS[:1]}))
    proc = run_cli("claims", SCENES / "clean.excalidraw", "--claims", bad)
    assert proc.returncode == 1
    assert "claim-missing-arrow" in proc.stdout

    broken = tmp_path / "broken.yaml"
    broken.write_text("claims: [unclosed")
    assert run_cli("claims", SCENES / "clean.excalidraw", "--claims", broken).returncode == 2
    assert run_cli("claims", SCENES / "clean.excalidraw", "--claims", tmp_path / "missing.yaml").returncode == 2
