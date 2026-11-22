"""Redaction and mask rules for captured visuals (specs/008-captured-visuals, research R7).

Standard library only: the capture runner uses this module inside the capture container,
and the host scripts (visuals.py, visualcfg.py) import it from tools/guide/capture/.

Rules are pattern templates. The placeholders `{user}`, `{home}`, and `{host}` stand for
the capturing user's name, home directory, and host name; `resolve()` turns them into
regular expressions with the real values. Only the resolved rules (in the run's scratch
job file) ever hold host values. `describe()` returns rule ids and templates, which is
what sidecars and recipe fingerprints record (FR-017, FR-021).

    rules = effective_rules(recipe_rules, disabled)        # templates, no host values
    resolved = resolve(rules, {"user": ..., "home": ..., "host": ...}, run_subnet="10.89.0.0/24")
    text, counts, masked = apply(text, resolved, masks)
"""
from __future__ import annotations

import ipaddress
import re
from typing import Any

PLACEHOLDERS = ("user", "home", "host")

# Default rules in application order. `expand` allows group references in the
# replacement (default rules only); recipe rules and masks replace with literal text.
DEFAULT_RULES: list[dict[str, Any]] = [
    {"id": "home-path", "template": "{home}(?![\\w.-])", "replacement": "/home/user"},
    {"id": "user-path", "template": "(?<=/home/){user}(?![\\w.-])|(?<=/Users/){user}(?![\\w.-])",
     "replacement": "user"},
    {"id": "user-at", "template": "(?<![\\w.-]){user}@", "replacement": "user@"},
    {"id": "k8s-api", "template": "https://(?:api\\.)?[A-Za-z0-9][A-Za-z0-9.-]*:6443(?!\\d)",
     "replacement": "https://api.cluster.example.com:6443"},
    # host names are case-insensitive (Rolands-MacBook-Pro prints as rolands-macbook-pro)
    {"id": "hostname", "template": "(?i:(?<![\\w.-]){host}(?![\\w-]))", "replacement": "example-host"},
    {"id": "ipv4", "template": "(?<![\\d.])(?:\\d{1,3}\\.){3}\\d{1,3}(?![\\d.]*\\d)",
     "replacement": "192.0.2.1", "kind": "ipv4"},
    {"id": "jwt", "template": "\\beyJ[A-Za-z0-9_-]{4,}\\.[A-Za-z0-9_-]{4,}\\.[A-Za-z0-9_-]{4,}",
     "replacement": "<redacted-jwt>"},
    {"id": "bearer", "template": "(?i)\\b(bearer)\\s+[A-Za-z0-9._~+/=-]{8,}",
     "replacement": "\\1 <redacted>", "expand": True},
    {"id": "api-key", "template": (
        "\\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"
        "|glpat-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|xox[abprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{35}"
        "|sha256~[A-Za-z0-9_-]{20,})"
        # key = value, key: value, "key": "value" (a quote may close the key)
        "|(?i:\\b(api[_-]?key|access[_-]?token|auth[_-]?token|secret[_-]?key|client[_-]?secret|password|token)"
        "([\"']?\\s*[=:]\\s*)[\"']?)[^\\s\"']{8,}"),
     "replacement": "\\1\\2<redacted>", "expand": True},
    {"id": "private-key", "template": "-----BEGIN [A-Z ]*PRIVATE KEY-----[\\s\\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)",
     "replacement": "<redacted-private-key>"},
]

DEFAULT_IDS = [r["id"] for r in DEFAULT_RULES]

# IPv4 addresses that stay: documentation ranges, loopback, the unspecified address.
IPV4_EXEMPT = ["192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "127.0.0.0/8", "0.0.0.0/32"]


def effective_rules(recipe_rules: list[dict] | None = None, disabled: list[str] | None = None) -> list[dict]:
    """Default rules minus the disabled ones, then the recipe rules (FR-022).

    Each rule is {id, template, replacement[, kind, expand]}; recipe rules come as
    {id, pattern, replacement} and are literal replacements.
    """
    off = set(disabled or [])
    rules = [dict(r) for r in DEFAULT_RULES if r["id"] not in off]
    for r in recipe_rules or []:
        rules.append({"id": str(r["id"]), "template": str(r["pattern"]), "replacement": str(r["replacement"])})
    return rules


def describe(rules: list[dict]) -> list[dict]:
    """Ids and pattern templates only (no host values), for sidecars and fingerprints."""
    return [{"id": r["id"], "template": r["template"], "replacement": r["replacement"]} for r in rules]


def _host_alternatives(host: str) -> list[str]:
    names = [host]
    short = host.split(".", 1)[0]
    if short and short != host:
        names.append(short)
    return sorted({n for n in names if n}, key=len, reverse=True)


def _fill(template: str, values: dict[str, str]) -> str | None:
    """Replace the placeholders with escaped values; None when a needed value is empty."""
    out = template
    for key in PLACEHOLDERS:
        token = "{" + key + "}"
        if token not in out:
            continue
        value = (values.get(key) or "").strip()
        if key == "home":
            value = value.rstrip("/")
        if not value or (key == "home" and value in ("", "/")):
            return None
        if key == "host":
            alt = "(?:" + "|".join(re.escape(n) for n in _host_alternatives(value)) + ")"
        else:
            alt = re.escape(value)
        out = out.replace(token, alt)
    return out


def resolve(rules: list[dict], values: dict[str, str], run_subnet: str | None = None) -> list[dict]:
    """Resolve templates into JSON-serializable rules with regular expressions.

    Rules whose placeholders have no value (for example no host name) are kept with
    `pattern: None` so the redaction record still lists them, but they never match.
    """
    resolved = []
    for r in rules:
        pattern = _fill(r["template"], values)
        item = {"id": r["id"], "pattern": pattern, "replacement": r["replacement"],
                "expand": bool(r.get("expand")), "kind": r.get("kind", "regex")}
        if item["kind"] == "ipv4":
            item["exempt"] = IPV4_EXEMPT + ([run_subnet] if run_subnet else [])
        resolved.append(item)
    return resolved


def _ipv4_exempt(text: str, networks: list) -> bool:
    try:
        addr = ipaddress.IPv4Address(text)
    except ValueError:
        return True   # not an address at all (for example 999.1.1.1): leave it
    return any(addr in net for net in networks)


def spans(text: str, rule: dict) -> list[tuple[int, int, str]]:
    """(start, end, replacement) of every replacement one rule makes in text.

    The CLI renderer uses the spans to give a replacement the style of the first
    replaced cell; apply() uses them to build the new text.
    """
    pattern = rule.get("pattern")
    if not pattern:
        return []
    regex = re.compile(pattern)
    kind = rule.get("kind", "regex")
    networks = [ipaddress.ip_network(n, strict=False) for n in rule.get("exempt", [])] if kind == "ipv4" else []
    out = []
    for m in regex.finditer(text):
        if m.end() == m.start():
            continue
        if kind == "ipv4" and _ipv4_exempt(m.group(0), networks):
            continue
        if kind == "mask" or not rule.get("expand"):
            replacement = rule["replacement"]
        else:
            replacement = m.expand(rule["replacement"])   # unmatched groups expand to ""
        out.append((m.start(), m.end(), replacement))
    return out


def substitute(text: str, found: list[tuple[int, int, str]]) -> str:
    parts, last = [], 0
    for start, end, replacement in found:
        parts.append(text[last:start])
        parts.append(replacement)
        last = end
    parts.append(text[last:])
    return "".join(parts)


def mask_rules(masks: list[dict] | None) -> list[dict]:
    """Masks as literal rules (FR-018): every match becomes the fixed replacement."""
    return [{"id": "mask", "pattern": m["pattern"], "replacement": m["replacement"], "kind": "mask"}
            for m in masks or []]


def apply(text: str, rules: list[dict], masks: list[dict] | None = None) -> tuple[str, dict[str, int], int]:
    """Apply resolved rules, then masks. Returns (text, replacements per rule id, masked count)."""
    counts: dict[str, int] = {}
    for rule in rules:
        found = spans(text, rule)
        text = substitute(text, found)
        counts[rule["id"]] = counts.get(rule["id"], 0) + len(found)
    masked = 0
    for rule in mask_rules(masks):
        found = spans(text, rule)
        text = substitute(text, found)
        masked += len(found)
    return text, counts, masked


def apply_segments(segments: list[str], rules: list[dict], masks: list[dict] | None = None
                   ) -> tuple[list[str], dict[str, int], int]:
    """apply() over text split into adjacent segments (the text nodes of one block of a page).

    A rule matches the joined text, so a value split across segments (`<span>/home/</span>
    <b>alice</b>`) is still found; the replacement goes into the segment where the match
    starts, and the matched rest of the following segments is removed.
    """
    segs = list(segments)
    counts: dict[str, int] = {}
    masked = 0
    for rule in list(rules) + mask_rules(masks):
        joined = "".join(segs)
        found = spans(joined, rule)
        if rule.get("kind") == "mask":
            masked += len(found)
        else:
            counts[rule["id"]] = counts.get(rule["id"], 0) + len(found)
        if not found:
            continue
        starts, lengths, pos = [], [len(seg) for seg in segs], 0
        for seg in segs:
            starts.append(pos)
            pos += len(seg)

        def owner(offset: int) -> int:
            """The (non-empty) segment that held the character at offset before this rule."""
            return next(i for i, s0 in enumerate(starts) if s0 <= offset < s0 + lengths[i])

        # Last match first: a replacement changes only text at or after its own start, so
        # the offsets of the earlier matches stay valid.
        for start, end, replacement in reversed(found):
            # spans() never returns empty matches, so both ends fall inside a segment
            first, last = owner(start), owner(end - 1)
            if first == last:
                a = start - starts[first]
                segs[first] = segs[first][:a] + replacement + segs[first][end - starts[first]:]
                continue
            segs[first] = segs[first][: start - starts[first]] + replacement
            for i in range(first + 1, last):
                segs[i] = ""
            segs[last] = segs[last][end - starts[last]:]
    return segs, counts, masked


def merge_counts(total: dict[str, int], more: dict[str, int]) -> dict[str, int]:
    for key, value in more.items():
        total[key] = total.get(key, 0) + value
    return total
