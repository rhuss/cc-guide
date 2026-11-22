"""capture/web.py callout badge placement (FR-019), without a browser."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "guide" / "toolkit" / "capture"))
import web  # noqa: E402


def box(x, y, width, height):
    return {"x": x, "y": y, "width": width, "height": height}


def covers_nothing(cx, cy, obstacles):
    rect = web.badge_rect(cx, cy)
    return all(web._intersection(rect, o) == 0 for o in obstacles)


# The smoke test table: three header cells in a row at the top of a crop with a 16 px margin.
AREA = box(0, 0, 363, 161)
RUN, ACCURACY, LOSS = box(17, 16, 147, 32), box(164, 16, 108, 32), box(272, 16, 75, 32)
HEADER_TEXT = [box(31, 24, 30, 17), box(178, 24, 79, 17), box(286, 24, 37, 17)]
ROW_TEXT = [box(31, 56, 67, 17), box(178, 56, 45, 17), box(286, 56, 45, 17),
            box(31, 88, 76, 17), box(178, 88, 45, 17), box(286, 88, 45, 17)]


def test_first_free_candidate_above_right():
    cx, cy, cover = web.place_badge(box(100, 100, 50, 20), box(0, 0, 400, 400), [])
    assert cover == 0
    assert (cx, cy) == web.badge_candidates(box(100, 100, 50, 20))[0]
    assert cx > 150 and cy < 100      # outside the box, above and to the right


def test_candidates_stay_outside_the_outlined_box():
    b = box(100, 100, 50, 20)
    outline = web._grow(b, web.OUTLINE_PAD + 1.5)
    for cx, cy in web.badge_candidates(b):
        assert web._intersection(web.badge_rect(cx, cy), outline) == 0


def test_badge_never_covers_the_neighbor_header():
    """The accuracy header sits at the top of the crop: above is outside the area, right
    covers the loss header; the badge goes to the first position that covers no text."""
    texts = HEADER_TEXT + ROW_TEXT
    cx, cy, cover = web.place_badge(ACCURACY, AREA, texts)
    assert cover == 0
    assert covers_nothing(cx, cy, texts)
    assert web._contains(AREA, web.badge_rect(cx, cy))
    right = web.badge_candidates(ACCURACY)[4]
    assert not covers_nothing(*right, HEADER_TEXT)          # the old placement hid "lo" of loss


def test_own_text_is_not_an_obstacle():
    b = box(100, 100, 50, 20)
    own = box(102, 102, 46, 16)
    cx, cy, cover = web.place_badge(b, box(0, 0, 400, 400), [own])
    assert cover == 0 and (cx, cy) == web.badge_candidates(b)[0]


def test_order_of_preference():
    b = box(100, 100, 50, 20)
    area = box(0, 0, 400, 400)
    order = web.badge_candidates(b)
    blocked = []
    for expected in order:
        cx, cy, cover = web.place_badge(b, area, blocked)
        assert (cx, cy) == expected and cover == 0
        blocked.append(web.badge_rect(*expected))


def test_fallback_least_covering_inside_the_area():
    b = box(100, 100, 50, 20)
    area = box(0, 0, 400, 400)
    candidates = web.badge_candidates(b)
    obstacles = [web.badge_rect(cx, cy) for i, (cx, cy) in enumerate(candidates) if i != 3]
    cx3, cy3 = candidates[3]
    obstacles.append(box(cx3 - 13, cy3 - 13, 4, 4))     # below left: only a corner is covered
    cx, cy, cover = web.place_badge(b, area, obstacles)
    assert (cx, cy) == (cx3, cy3) and cover == 16
    assert web._contains(area, web.badge_rect(cx, cy))


def test_fallback_moves_into_the_area():
    b = box(10, 10, 380, 30)             # nearly as large as the area: no candidate fits
    area = box(0, 0, 400, 60)
    cx, cy, _ = web.place_badge(b, area, [])
    assert web._contains(area, web.badge_rect(cx, cy))


def test_fallback_prefers_positions_off_the_box():
    b = box(100, 10, 50, 20)             # at the top edge: above is outside the area
    area = box(0, 0, 400, 80)
    candidates = web.badge_candidates(b)
    # the in-area candidates (below and beside) are taken; moved into the area, the above
    # candidates stay beside the box and win over positions on top of it
    blocked = [web.badge_rect(cx, cy) for cx, cy in candidates[2:]]
    cx, cy, _ = web.place_badge(b, area, blocked)
    assert web._contains(area, web.badge_rect(cx, cy))
    assert web._intersection(web.badge_rect(cx, cy), web._grow(b, web.OUTLINE_PAD + 1.5)) == 0


def test_badges_avoid_each_other_and_other_highlights():
    a, b = box(100, 100, 50, 20), box(160, 100, 50, 20)
    placed = web.place_badges([a, b], box(0, 0, 400, 400), [])
    (ax, ay, _), (bx, by, _) = placed
    assert web._intersection(web.badge_rect(ax, ay), web.badge_rect(bx, by)) == 0
    assert web._intersection(web.badge_rect(ax, ay), web._grow(b, web.OUTLINE_PAD + 1.5)) == 0
    assert web._intersection(web.badge_rect(bx, by), web._grow(a, web.OUTLINE_PAD + 1.5)) == 0


def test_text_outside_the_area_is_ignored():
    texts = [box(1000, 1000, 50, 20)]
    placed = web.place_badges([box(100, 100, 50, 20)], box(0, 0, 400, 400), texts)
    assert placed[0][2] == 0
