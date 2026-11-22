"""Web visual capture with Playwright (specs/008-captured-visuals, research R6).

Runs inside the capture container (runner.py web). One call captures one visual in one
color scheme variant:

1. A Chromium context with a fixed viewport, device scale 2, locale en-US, time zone UTC,
   reduced motion, the variant's color scheme, a fixed clock start, and a style that
   disables animations, transitions, and the caret (FR-014).
2. The recipe steps: goto, click, fill, press, wait, hide, highlight, crop, script
   (FR-005). A failing step writes a redacted debug image to /work/debug/ and the
   step number and selector to the result (FR-013).
3. Redaction and masks over the page text (text nodes, input values, title, alt,
   aria-label, aria-valuetext, aria-description, placeholder; open shadow roots and
   same-origin iframes included; text split across inline elements matched as one)
   before anything is read or drawn, and once more right before the screenshot
   (FR-018, FR-021).
4. The sidecar text: the ARIA snapshot of the crop element (or body), taken before the
   overlay exists; the highlight records (label, selector, element text).
5. The overlay: one SVG layer that dims everything except the highlighted boxes,
   outlines each box, and puts a numbered badge next to it, placed from the live
   element positions (FR-019, FR-020). place_badge() picks the first candidate position
   (above right, above left, below right, below left, right, left; always outside the
   box) whose badge stays inside the captured area and covers no visible text, no other
   highlight, and no earlier badge; otherwise the least covering one.
6. The screenshot, clipped to the crop element plus a 16 px margin, or the viewport.
"""
from __future__ import annotations

import datetime as _dt
import importlib.util
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import redact  # noqa: E402

VISUALS = Path("/visuals")
MARGIN = 16
BADGE_RADIUS = 12     # callout badge circle (CSS pixels); its white stroke adds 1
BADGE_GAP = 2         # space between the outline and the badge
OUTLINE_PAD = 4       # the outline's distance from the element box (the pad in OVERLAY_JS)
CLOCK = _dt.datetime(2026, 1, 1, 12, 0, 0, tzinfo=_dt.timezone.utc)
ROLE_RE = re.compile(r"^role=([a-z]+)(?:\[name=(.+)\])?$")
STILL_CSS = ("*,*::before,*::after{animation:none!important;transition:none!important;"
             "caret-color:transparent!important;scroll-behavior:auto!important}")
INIT_SCRIPT = """
(() => {
  const css = %s;
  const add = () => {
    if (document.querySelector('style[data-ccg-still]')) return;
    const s = document.createElement('style');
    s.setAttribute('data-ccg-still', '');
    s.textContent = css;
    (document.head || document.documentElement).appendChild(s);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', add); else add();
})();
""" % json.dumps(STILL_CSS)

COLLECT_JS = """
() => {
  // Every text the page shows, including open shadow roots and same-origin iframes.
  // Text nodes carry the id of their nearest block-level ancestor, so a value split
  // across inline elements (<span>/home/</span><b>alice</b>) is matched as one text.
  const ATTRS = ['title', 'alt', 'aria-label', 'aria-valuetext', 'aria-description', 'placeholder'];
  const SKIP = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE']);
  const items = [];
  const blocks = new Map();
  const blockId = (node) => {
    let el = node.parentElement;
    while (el) {
      if (blocks.has(el)) return blocks.get(el);
      const view = el.ownerDocument.defaultView;
      const display = view ? view.getComputedStyle(el).display : 'block';
      if (!display.startsWith('inline') && display !== 'contents') {
        blocks.set(el, blocks.size);
        return blocks.get(el);
      }
      const root = el.getRootNode();
      el = el.parentElement || (root && root.host) || null;
    }
    return -1;
  };
  const visit = (root) => {
    const doc = root.ownerDocument || root;
    const walker = doc.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = walker.nextNode())) {
      const p = n.parentElement;
      if (p && SKIP.has(p.tagName)) continue;
      if (n.nodeValue && n.nodeValue.trim()) items.push({node: n, kind: 'text', value: n.nodeValue, group: blockId(n)});
    }
    for (const el of root.querySelectorAll('input, textarea')) {
      if (el.value) items.push({node: el, kind: 'value', value: el.value, group: null});
    }
    for (const attr of ATTRS) {
      for (const el of root.querySelectorAll('[' + attr + ']')) {
        const v = el.getAttribute(attr);
        if (v) items.push({node: el, kind: 'attr', attr: attr, value: v, group: null});
      }
    }
    for (const el of root.querySelectorAll('*')) {
      if (el.shadowRoot) visit(el.shadowRoot);
      if (el.tagName === 'IFRAME' || el.tagName === 'FRAME') {
        let inner = null;
        try { inner = el.contentDocument; } catch (e) { inner = null; }   // cross-origin
        if (inner && inner.documentElement) visit(inner.documentElement);
      }
    }
  };
  visit(document.documentElement);
  if (document.title) items.push({node: null, kind: 'title', value: document.title, group: null});
  window.__ccgItems = items;
  return items.map(i => ({value: i.value, group: i.group}));
}
"""

APPLY_JS = """
(changes) => {
  for (const [index, value] of changes) {
    const item = window.__ccgItems[index];
    if (item.kind === 'text') item.node.nodeValue = value;
    else if (item.kind === 'value') item.node.value = value;
    else if (item.kind === 'attr') item.node.setAttribute(item.attr, value);
    else if (item.kind === 'title') document.title = value;
  }
  delete window.__ccgItems;
}
"""

BOX_JS = """
(el) => {
  const r = el.getBoundingClientRect();
  return {x: r.left + window.scrollX, y: r.top + window.scrollY, width: r.width, height: r.height};
}
"""

TEXT_BOXES_JS = """
() => {
  // Page boxes of every visible text line (Range.getClientRects of the text nodes, open
  // shadow roots included) and of form fields that show a value; badges avoid them.
  const out = [];
  const add = (r) => { if (r.width > 0 && r.height > 0) out.push({x: r.left + window.scrollX, y: r.top + window.scrollY, width: r.width, height: r.height}); };
  const shown = (el) => {
    const st = el ? getComputedStyle(el) : null;
    return !st || (st.visibility === 'visible' && parseFloat(st.opacity || '1') > 0);
  };
  const visit = (root) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const range = document.createRange();
    let n;
    while ((n = walker.nextNode())) {
      if (!n.nodeValue || !n.nodeValue.trim() || !shown(n.parentElement)) continue;
      range.selectNodeContents(n);
      for (const r of range.getClientRects()) add(r);
    }
    for (const el of root.querySelectorAll('input, textarea, select')) {
      if (shown(el)) add(el.getBoundingClientRect());
    }
    for (const el of root.querySelectorAll('*')) if (el.shadowRoot) visit(el.shadowRoot);
  };
  visit(document.documentElement);
  return out;
}
"""

OVERLAY_JS = """
({boxes, area, labels, badges}) => {
  const NS = 'http://www.w3.org/2000/svg';
  const doc = document.documentElement;
  const W = Math.max(doc.scrollWidth, document.body ? document.body.scrollWidth : 0, window.innerWidth);
  const H = Math.max(doc.scrollHeight, document.body ? document.body.scrollHeight : 0, window.innerHeight);
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('aria-hidden', 'true');
  svg.setAttribute('width', W); svg.setAttribute('height', H);
  svg.style.cssText = 'position:absolute;left:0;top:0;pointer-events:none;z-index:2147483647;overflow:visible';
  const make = (tag, attrs) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; };
  const pad = 4;
  if (boxes.length) {
    const mask = make('mask', {id: 'ccg-mask'});
    mask.appendChild(make('rect', {x: 0, y: 0, width: W, height: H, fill: 'white'}));
    for (const b of boxes) mask.appendChild(make('rect', {x: b.x - pad, y: b.y - pad, width: b.width + 2 * pad, height: b.height + 2 * pad, rx: 4, fill: 'black'}));
    const defs = make('defs', {}); defs.appendChild(mask); svg.appendChild(defs);
    svg.appendChild(make('rect', {x: 0, y: 0, width: W, height: H, fill: 'rgba(0,0,0,0.45)', mask: 'url(#ccg-mask)'}));
  }
  const r = %d;
  boxes.forEach((b, i) => {
    svg.appendChild(make('rect', {x: b.x - pad, y: b.y - pad, width: b.width + 2 * pad, height: b.height + 2 * pad, rx: 4, fill: 'none', stroke: '#e00000', 'stroke-width': 3}));
    const [cx, cy] = badges[i];   // placed by place_badge() in Python
    svg.appendChild(make('circle', {cx: cx, cy: cy, r: r, fill: '#e00000', stroke: 'white', 'stroke-width': 2}));
    const t = make('text', {x: cx, y: cy, fill: 'white', 'font-family': 'DejaVu Sans, sans-serif', 'font-size': 13, 'font-weight': 700, 'text-anchor': 'middle', 'dominant-baseline': 'central'});
    t.textContent = labels[i];
    svg.appendChild(t);
  });
  document.body.appendChild(svg);
}
""" % BADGE_RADIUS


# --- callout badge placement (FR-019) -----------------------------------------


def _intersection(a: dict, b: dict) -> float:
    """Area shared by two {x, y, width, height} boxes."""
    w = min(a["x"] + a["width"], b["x"] + b["width"]) - max(a["x"], b["x"])
    h = min(a["y"] + a["height"], b["y"] + b["height"]) - max(a["y"], b["y"])
    return w * h if w > 0 and h > 0 else 0.0


def _contains(outer: dict, inner: dict) -> bool:
    return (inner["x"] >= outer["x"] and inner["y"] >= outer["y"]
            and inner["x"] + inner["width"] <= outer["x"] + outer["width"]
            and inner["y"] + inner["height"] <= outer["y"] + outer["height"])


def _grow(box: dict, by: float) -> dict:
    return {"x": box["x"] - by, "y": box["y"] - by, "width": box["width"] + 2 * by, "height": box["height"] + 2 * by}


def badge_rect(cx: float, cy: float, r: float = BADGE_RADIUS) -> dict:
    """The square a badge covers, its stroke included."""
    return {"x": cx - r - 1, "y": cy - r - 1, "width": 2 * r + 2, "height": 2 * r + 2}


def badge_candidates(box: dict, r: float = BADGE_RADIUS) -> list[tuple[float, float]]:
    """Badge centers in order of preference, all outside the outlined box:
    above right, above left, below right, below left, right, left."""
    out = OUTLINE_PAD + r + BADGE_GAP + 1
    right, left = box["x"] + box["width"] + out, box["x"] - out
    above, below = box["y"] - out, box["y"] + box["height"] + out
    middle = box["y"] + box["height"] / 2
    return [(right, above), (left, above), (right, below), (left, below), (right, middle), (left, middle)]


def place_badge(box: dict, area: dict, obstacles: list[dict], r: float = BADGE_RADIUS) -> tuple[float, float, float]:
    """(cx, cy, covered area) of the badge of one highlighted box.

    The first candidate whose badge stays inside the captured area and covers none of the
    obstacles (visible text, other highlights, earlier badges) wins. Without one, every
    candidate is moved into the area and the one that covers the least wins, preferring
    positions that stay off the outlined box. Obstacles whose center lies inside the
    outlined box (the element's own text) do not count.
    """
    own = _grow(box, OUTLINE_PAD + 1.5)       # the outline and half its stroke

    def centered_in_own(o: dict) -> bool:
        cx, cy = o["x"] + o["width"] / 2, o["y"] + o["height"] / 2
        return own["x"] <= cx <= own["x"] + own["width"] and own["y"] <= cy <= own["y"] + own["height"]

    others = [o for o in obstacles if not centered_in_own(o)]

    def covered(cx: float, cy: float) -> float:
        rect = badge_rect(cx, cy, r)
        return sum(_intersection(rect, o) for o in others)

    candidates = badge_candidates(box, r)
    for cx, cy in candidates:
        if _contains(area, badge_rect(cx, cy, r)) and covered(cx, cy) == 0:
            return cx, cy, 0.0
    best = None
    for i, (cx, cy) in enumerate(candidates):
        cx = min(max(cx, area["x"] + r + 1), area["x"] + area["width"] - r - 1)
        cy = min(max(cy, area["y"] + r + 1), area["y"] + area["height"] - r - 1)
        key = (_intersection(badge_rect(cx, cy, r), own) > 0, covered(cx, cy), i)
        if best is None or key < best[0]:
            best = (key, (cx, cy))
    (cx, cy) = best[1]
    return cx, cy, covered(cx, cy)


def place_badges(boxes: list[dict], area: dict, text_boxes: list[dict],
                 r: float = BADGE_RADIUS) -> list[tuple[float, float, float]]:
    """Badges of every highlight in order; each avoids the text, the other highlights,
    and the badges placed before it."""
    placed: list[tuple[float, float, float]] = []
    for i, box in enumerate(boxes):
        obstacles = [t for t in text_boxes if _intersection(t, area) > 0]
        obstacles += [_grow(b, OUTLINE_PAD + 1.5) for j, b in enumerate(boxes) if j != i]
        obstacles += [badge_rect(cx, cy, r) for cx, cy, _ in placed]
        placed.append(place_badge(box, area, obstacles, r))
    return placed


class StepError(Exception):
    def __init__(self, step: int, kind: str, selector: str | None, message: str):
        super().__init__(message)
        self.step, self.kind, self.selector = step, kind, selector


def locate(page, selector: str):
    """CSS, text=<text>, or role=<role>[name=<name>] (FR-005)."""
    if selector.startswith("text="):
        return page.get_by_text(selector[len("text="):])
    m = ROLE_RE.match(selector)
    if m:
        if m.group(2) is not None:
            return page.get_by_role(m.group(1), name=m.group(2).strip("\"'"), exact=True)
        return page.get_by_role(m.group(1))
    return page.locator(selector)


def redaction_changes(items: list[dict], rules: list[dict], masks: list[dict]
                      ) -> tuple[list[list], dict[str, int], int]:
    """The [index, new value] changes for the collected page items, with the counts.

    Consecutive text items of the same block form one text (redact.apply_segments), so a
    match across inline elements is found; values and attributes stand alone.
    """
    counts: dict[str, int] = {}
    masked = 0
    changes: list[list] = []
    i = 0
    while i < len(items):
        group = items[i].get("group")
        j = i + 1
        if group is not None:
            while j < len(items) and items[j].get("group") == group:
                j += 1
        values = [str(item.get("value") or "") for item in items[i:j]]
        new, c, m = redact.apply_segments(values, rules, masks)
        redact.merge_counts(counts, c)
        masked += m
        changes += [[i + k, nv] for k, (old, nv) in enumerate(zip(values, new)) if nv != old]
        i = j
    return changes, counts, masked


def redact_page(page, rules: list[dict], masks: list[dict]) -> tuple[dict[str, int], int]:
    """Redact and mask the page's text in place; returns (counts per rule, masked count)."""
    changes, counts, masked = redaction_changes(page.evaluate(COLLECT_JS), rules, masks)
    page.evaluate(APPLY_JS, changes)
    for rule in rules:
        counts.setdefault(rule["id"], 0)
    return counts, masked


def run_script(page, rel: str, base_url: str) -> None:
    path = VISUALS / rel
    spec = importlib.util.spec_from_file_location(f"ccg_script_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.run(page, base_url)


def mark(page, locator, name: str):
    """Tag the matched element and return a locator for the tag.

    Highlights and the crop are resolved by their step; redaction may later change the
    text a `text=` selector matched, so they are found again by this mark, not the selector.
    """
    locator.evaluate("(el, m) => el.setAttribute('data-ccg-mark', m)", name)
    return page.locator(f'[data-ccg-mark="{name}"]')


def _box(locator) -> dict:
    return locator.evaluate(BOX_JS)


def _first_line(text: str) -> str:
    return (text or "").strip().splitlines()[0] if (text or "").strip() else ""


def capture(job: dict, name: str, variant: str, work: Path) -> dict:
    """Capture one web visual in one variant; writes the PNG and the result JSON."""
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    spec = job["visuals"][name]
    stem = f"{name}-dark" if variant == "dark" else name
    out = Path(work) / "out"
    debug = Path(work) / "debug"
    out.mkdir(parents=True, exist_ok=True)
    debug.mkdir(parents=True, exist_ok=True)
    rules, masks = spec["rules"], spec.get("masks") or []
    base_url = (spec.get("base_url") or "").rstrip("/")
    timeout_ms = float(spec.get("timeout", 15)) * 1000
    result: dict = {"text": "", "highlights": [], "redaction": {}, "masks": 0, "scripts": [], "error": None}

    def finish() -> dict:
        (out / f"{stem}.result.json").write_text(json.dumps(result, sort_keys=True))
        return result

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--font-render-hinting=none", "--disable-lcd-text", "--hide-scrollbars"])
        options = {"viewport": spec["viewport"], "device_scale_factor": 2, "locale": "en-US",
                   "timezone_id": "UTC", "reduced_motion": "reduce"}
        if variant in ("light", "dark"):
            options["color_scheme"] = variant
        context = browser.new_context(**options)
        context.add_init_script(INIT_SCRIPT)
        page = context.new_page()
        page.clock.install(time=CLOCK)
        page.set_default_timeout(timeout_ms)
        page.set_default_navigation_timeout(max(timeout_ms, 60000))
        crop = None
        highlights: list[tuple[str, str, object]] = []
        try:
            for number, step in enumerate(spec["steps"], start=1):
                (kind, arg), = step.items()
                selector = None
                try:
                    if kind == "goto":
                        page.goto(base_url + arg, wait_until="load")
                    elif kind == "click":
                        selector = arg
                        locate(page, arg).first.click()
                    elif kind == "fill":
                        selector = arg["selector"]
                        locate(page, selector).first.fill(arg["text"])
                    elif kind == "press":
                        page.keyboard.press(arg)
                    elif kind == "wait":
                        selector = arg
                        locate(page, arg).first.wait_for(state="visible")
                    elif kind == "hide":
                        selector = arg
                        locate(page, arg).evaluate_all(
                            "els => els.forEach(e => e.style.setProperty('visibility', 'hidden', 'important'))")
                    elif kind == "highlight":
                        selector = arg["selector"]
                        loc = locate(page, selector).first
                        loc.wait_for(state="visible")
                        highlights.append((str(arg["label"]), selector, mark(page, loc, f"h{len(highlights)}")))
                    elif kind == "crop":
                        selector = arg
                        loc = locate(page, arg).first
                        loc.wait_for(state="visible")
                        crop = mark(page, loc, "crop")
                    elif kind == "script":
                        run_script(page, arg, base_url)
                        result["scripts"].append(arg)
                except Exception as err:  # noqa: BLE001 (a script step may raise anything)
                    raise StepError(number, kind, selector if selector is not None else arg
                                    if isinstance(arg, str) else None, _first_line(str(err))) from None

            # All scrolling first, then redaction, then every measurement: scrolling can load
            # or re-render content, and moving to one element must not shift another's box.
            for _label, _selector, loc in highlights:
                loc.scroll_into_view_if_needed()
            if crop is not None:
                crop.scroll_into_view_if_needed()
            counts, masked = redact_page(page, rules, masks)
            target = crop if crop is not None else page.locator("body")
            result["text"] = target.aria_snapshot()
            records = [{"label": label, "selector": selector, "text": " ".join(loc.inner_text().split())}
                       for label, selector, loc in highlights]
            boxes = [_box(loc) for _label, _selector, loc in highlights]
            result["highlights"] = records
            if crop is not None:
                c = _box(crop)
                area = {"x": max(c["x"] - MARGIN, 0), "y": max(c["y"] - MARGIN, 0),
                        "width": c["width"] + 2 * MARGIN, "height": c["height"] + 2 * MARGIN}
            else:
                scroll = page.evaluate("() => ({x: window.scrollX, y: window.scrollY})")
                area = {"x": scroll["x"], "y": scroll["y"], "width": spec["viewport"]["width"],
                        "height": spec["viewport"]["height"]}
            if boxes:
                badges = place_badges(boxes, area, page.evaluate(TEXT_BOXES_JS))
                # scratch only (out/<stem>.result.json); the sidecar never carries positions
                result["badges"] = [{"label": r["label"], "x": round(cx, 1), "y": round(cy, 1),
                                     "covers": round(cover, 1)} for r, (cx, cy, cover) in zip(records, badges)]
                page.evaluate(OVERLAY_JS, {"boxes": boxes, "area": area, "labels": [r["label"] for r in records],
                                           "badges": [[cx, cy] for cx, cy, _ in badges]})
            # Second pass right before the screenshot: timers and re-renders keep running
            # while the boxes are measured, and new text must not reach the image unredacted.
            more, more_masked = redact_page(page, rules, masks)
            result["redaction"], result["masks"] = redact.merge_counts(counts, more), masked + more_masked
            page.screenshot(path=str(out / f"{stem}.png"), full_page=True, clip=area, animations="disabled",
                            caret="hide", scale="device")
        except StepError as err:
            try:
                redact_page(page, rules, masks)
                page.screenshot(path=str(debug / f"{stem}-step{err.step}.png"), animations="disabled", caret="hide")
            except PlaywrightError:
                pass
            result["error"] = f"step {err.step} ({err.kind}"
            result["error"] += f" {err.selector})" if err.selector else ")"
            result["error"] += f": {err}"
            result["step"], result["selector"] = err.step, err.selector
        except PlaywrightError as err:
            result["error"] = f"capture failed: {_first_line(str(err))}"
        finally:
            browser.close()
    return finish()
