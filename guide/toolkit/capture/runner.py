"""Capture container entry point (specs/008-captured-visuals, contracts/toolkit-cli.md).

Runs inside the capture container only; tools/guide/visuals.py calls it with
`podman exec <capture> python3 /opt/ccg/runner.py <command>`.

    ready --url URL --timeout S             poll until HTTP status < 400 (FR-002a)
    web --job /work/job.json --visual NAME [--variant light|dark|default]
    cli --job /work/job.json --visual NAME  render /work/raw/NAME.bin to /work/out/NAME.svg
    diff A.png B.png --tolerance N          print {"diff": <percent of differing pixels>}

`ready` needs only the standard library; `diff` needs Pillow; `web` needs Playwright;
`cli` needs pyte and fontTools. Imports happen per command so the host tests can run
`ready` and `diff` without the capture image.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

WORK = Path("/work")


def ready(url: str, timeout: float, interval: float = 0.5) -> tuple[bool, str]:
    """Poll url until it answers below 400; (ok, last status or error)."""
    deadline = time.monotonic() + timeout
    last = "no answer"
    while True:
        try:
            with urllib.request.urlopen(url, timeout=max(1.0, min(5.0, timeout))) as resp:  # noqa: S310
                status = resp.status
        except urllib.error.HTTPError as err:
            status = err.code
        except (urllib.error.URLError, OSError, ValueError) as err:
            status = None
            last = f"connection error: {getattr(err, 'reason', err)}"
        if status is not None:
            if status < 400:
                return True, f"status {status}"
            last = f"status {status}"
        if time.monotonic() >= deadline:
            return False, last
        time.sleep(interval)


def image_diff(a: Path, b: Path, tolerance: int) -> float:
    """Percent of pixels where any channel differs by more than tolerance (R8)."""
    from PIL import Image, ImageChops

    with Image.open(a) as ia, Image.open(b) as ib:
        if ia.size != ib.size:
            return 100.0
        ra, rb = ia.convert("RGBA"), ib.convert("RGBA")
        delta = ImageChops.difference(ra, rb)
        total = ra.size[0] * ra.size[1]
        if total == 0:
            return 0.0
        # Per pixel: the largest channel difference, then count those above the tolerance.
        channels = delta.split()
        biggest = channels[0]
        for ch in channels[1:]:
            biggest = ImageChops.lighter(biggest, ch)
        hist = biggest.histogram()
        differing = sum(hist[tolerance + 1:])
        return round(100.0 * differing / total, 4)


def load_job(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def cmd_ready(args: argparse.Namespace) -> int:
    ok, detail = ready(args.url, args.timeout)
    print(detail)
    return 0 if ok else 1


def cmd_diff(args: argparse.Namespace) -> int:
    print(json.dumps({"diff": image_diff(Path(args.a), Path(args.b), args.tolerance)}))
    return 0


def cmd_cli(args: argparse.Namespace) -> int:
    import render_cli

    job = load_job(args.job)
    spec = job["visuals"][args.visual]
    work = Path(args.job).parent
    raw = (work / "raw" / f"{args.visual}.bin").read_bytes()
    out = work / "out"
    out.mkdir(parents=True, exist_ok=True)
    result_path = out / f"{args.visual}.result.json"
    try:
        result = render_cli.render(raw, command=spec["command"], prompt=spec["prompt"], width=spec["width"],
                                   rules=spec["rules"], masks=spec["masks"])
    except render_cli.RenderError as err:
        result_path.write_text(json.dumps({"error": str(err)}))
        print(str(err), file=sys.stderr)
        return 1
    (out / f"{args.visual}.svg").write_bytes(result.pop("svg"))
    result_path.write_text(json.dumps(result, sort_keys=True))
    return 0


def cmd_web(args: argparse.Namespace) -> int:
    import web

    job = load_job(args.job)
    work = Path(args.job).parent
    result = web.capture(job, args.visual, args.variant, work)
    return 0 if not result.get("error") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="cc-guide capture runner (inside the capture container)")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("ready")
    p.add_argument("--url", required=True)
    p.add_argument("--timeout", type=float, default=120)
    p.set_defaults(func=cmd_ready)
    p = sub.add_parser("diff")
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--tolerance", type=int, default=16)
    p.set_defaults(func=cmd_diff)
    p = sub.add_parser("cli")
    p.add_argument("--job", type=Path, default=WORK / "job.json")
    p.add_argument("--visual", required=True)
    p.set_defaults(func=cmd_cli)
    p = sub.add_parser("web")
    p.add_argument("--job", type=Path, default=WORK / "job.json")
    p.add_argument("--visual", required=True)
    p.add_argument("--variant", choices=("light", "dark", "default"), default="default")
    p.set_defaults(func=cmd_web)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
