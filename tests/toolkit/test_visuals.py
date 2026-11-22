"""visuals.py orchestration with a fake podman (FR-008 to FR-013, SC-006)."""
from __future__ import annotations

import fcntl
import shutil
import json
import os
import socket
import subprocess
from pathlib import Path

import pytest

import visuals
import visualcfg

REPO = Path(__file__).resolve().parents[2]
RUN_ID = "20260101-000000-abcd"
VALUES = {"user": "alice", "home": "/home/alice", "host": "box.corp.example"}

RECIPE = """\
schema: 1
environments:
  web1:
    kind: web
    image: docker.io/library/nginx:1.27-alpine
    port: 80
    ready: /health
    ready_timeout: 5
    seed:
      - run: cp /visuals/seed/index.html /usr/share/nginx/html/
        files: [seed/index.html]
      - run: echo second
  tools:
    kind: cli
    image: docker.io/library/alpine:3.20
visuals:
  table:
    kind: web
    env: web1
    steps:
      - goto: /
      - crop: "role=table"
  colors:
    kind: cli
    env: tools
    command: printf '\\033[1;32mok\\033[0m'
    env_vars: {TARGET: "${GUIDE_ENV_WEB1_URL}"}
"""


def cp(rc: int = 0, out: str = "", err: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], rc, out, err)


class FakePodman:
    """Records calls and simulates containers, networks, and the capture runner."""

    def __init__(self, missing: bool = False, info_rc: int = 0):
        self.calls: list[list[str]] = []
        self.pty_calls: list[list[str]] = []
        self.missing = missing
        self.info_rc = info_rc
        self.containers: dict[str, list[str]] = {}
        self.networks: set[str] = set()
        self.work: Path | None = None
        self.ps: list[dict] = []
        self.nets: list[dict] = []
        self.hooks: list = []      # (predicate, callable(args) -> CompletedProcess)
        self.pty_result: tuple[int, bytes] = (0, b"\x1b[1;32mok\x1b[0m\r\n")

    def on(self, predicate, result):
        self.hooks.insert(0, (predicate, result))

    def run(self, args, timeout=None, input=None):
        args = list(args)
        if self.missing:
            raise FileNotFoundError("podman")
        self.calls.append(args)
        for predicate, result in self.hooks:
            if predicate(args):
                return result(args) if callable(result) else result
        cmd = args[0]
        if cmd == "info":
            return cp(self.info_rc, "arm64\n", "" if self.info_rc == 0 else "cannot connect")
        if cmd == "ps":
            return cp(0, json.dumps(self.ps))
        if args[:2] == ["network", "ls"]:
            return cp(0, json.dumps(self.nets))
        if args[:2] == ["network", "create"]:
            self.networks.add(args[-1])
            return cp(0, args[-1])
        if args[:2] == ["network", "inspect"]:
            return cp(0, json.dumps([{"name": args[-1], "subnets": [{"subnet": "10.89.1.0/24"}]}]))
        if args[:2] == ["network", "rm"]:
            self.networks.discard(args[-1])
            return cp(0)
        if args[:2] == ["image", "exists"]:
            return cp(0)
        if args[:2] == ["image", "inspect"]:
            return cp(0, 'sha256:aaa|["x@sha256:aaa","x@sha256:index"]\n')
        if cmd == "run":
            name = args[args.index("--name") + 1]
            self.containers[name] = args
            for i, a in enumerate(args):
                if a == "-v" and args[i + 1].endswith(":/work"):
                    self.work = Path(args[i + 1][: -len(":/work")])
            return cp(0, "id\n")
        if cmd == "rm":
            self.containers.pop(args[-1], None)
            return cp(0)
        if cmd == "logs":
            return cp(0, "log line 1\nlog line 2\n")
        if cmd == "exec":
            return self.exec(args)
        return cp(0)

    def exec(self, args):
        if "runner.py" in " ".join(args):
            return self.runner(args)
        return cp(0)

    def runner(self, args):
        if "ready" in args:
            return cp(0, "status 200\n")
        if "cli" in args:
            name = args[args.index("--visual") + 1]
            out = self.work / "out"
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{name}.svg").write_text("<svg/>")
            (out / f"{name}.result.json").write_text(json.dumps(
                {"text": "$ printf ok\nok", "style": "0123456789abcdef", "redaction": {"home-path": 1}, "masks": 0}))
            return cp(0)
        if "web" in args:
            name = args[args.index("--visual") + 1]
            variant = args[args.index("--variant") + 1] if "--variant" in args else "default"
            stem = f"{name}-dark" if variant == "dark" else name
            out = self.work / "out"
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{stem}.png").write_bytes(b"\x89PNG fake")
            (out / f"{stem}.result.json").write_text(json.dumps(
                {"text": "- table", "highlights": [], "redaction": {}, "masks": 0, "scripts": [], "error": None}))
            return cp(0)
        if "diff" in args:
            return cp(0, json.dumps({"diff": 0.0}))
        return cp(0)

    def run_pty(self, args, columns=100, rows=200, timeout=300):
        self.pty_calls.append(list(args))
        return self.pty_result

    def created(self, kind: str) -> list[list[str]]:
        if kind == "container":
            return [c for c in self.calls if c[0] == "run"]
        return [c for c in self.calls if c[:2] == ["network", "create"]]


def guide(root: Path, recipe: str = RECIPE) -> Path:
    (root / "visuals" / "seed").mkdir(parents=True, exist_ok=True)
    (root / "visuals" / "seed" / "index.html").write_text("<table><tr><th>accuracy</th></tr></table>\n")
    (root / "visuals.yaml").write_text(recipe)
    return root


def capture(root: Path, fake: FakePodman, names=(), lines=None) -> int:
    out = lines if lines is not None else []
    return visuals.cmd_capture(root, list(names), podman=fake, out=out.append, run_id=RUN_ID, values=VALUES)


def run_dir(root: Path) -> Path:
    return root / ".guide" / "visuals" / RUN_ID


# --- prerequisites -----------------------------------------------------------


def test_no_recipe_no_podman_calls(tmp_guide):
    fake = FakePodman()
    lines: list[str] = []
    assert capture(tmp_guide, fake, lines=lines) == 0
    assert lines == ["no visuals declared"]
    assert fake.calls == []


def test_missing_podman_exit_2(tmp_guide):
    guide(tmp_guide)
    lines: list[str] = []
    assert capture(tmp_guide, FakePodman(missing=True), lines=lines) == 2
    assert "podman not found" in lines[-1] and "podman.io" in lines[-1]


def test_podman_info_failure_exit_2(tmp_guide):
    guide(tmp_guide)
    lines: list[str] = []
    assert capture(tmp_guide, FakePodman(info_rc=125), lines=lines) == 2
    assert "podman cannot run containers" in lines[-1]


def test_invalid_recipe_exit_2(tmp_guide):
    guide(tmp_guide, RECIPE.replace("alpine:3.20", "alpine"))
    fake = FakePodman()
    lines: list[str] = []
    assert capture(tmp_guide, fake, lines=lines) == 2
    assert "tag or digest" in lines[-1]
    assert fake.calls == []


def test_unknown_name_exit_2(tmp_guide):
    guide(tmp_guide)
    lines: list[str] = []
    assert capture(tmp_guide, FakePodman(), names=["nope"], lines=lines) == 2
    assert "no visual 'nope'" in lines[-1]


def test_lock_held_exit_2(tmp_guide):
    guide(tmp_guide)
    scratch = tmp_guide / ".guide" / "visuals"
    scratch.mkdir(parents=True)
    with open(scratch / ".lock", "w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lines: list[str] = []
        fake = FakePodman()
        assert capture(tmp_guide, fake, lines=lines) == 2
        assert lines[-1] == "error: capture already running"
        assert not fake.created("container")


# --- lifecycle ----------------------------------------------------------------


def test_labels_and_no_published_ports(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()
    capture(tmp_guide, fake)
    creates = fake.created("container") + fake.created("network")
    assert len(fake.created("container")) == 3      # capture, web1, tools
    for call in creates:
        labels = [call[i + 1] for i, a in enumerate(call) if a == "--label"]
        keys = {lab.split("=", 1)[0] for lab in labels}
        assert keys == {"io.cc-guide.capture", "io.cc-guide.run", "io.cc-guide.guide", "io.cc-guide.pid",
                        "io.cc-guide.host"}
        assert f"io.cc-guide.run={RUN_ID}" in labels
        assert f"io.cc-guide.pid={os.getpid()}" in labels
        assert not any(lab.endswith(socket.gethostname()) for lab in labels)
    for call in fake.calls:
        assert "-p" not in call and "--publish" not in call and not any(a.startswith("--publish") for a in call)


def test_tool_containers(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()
    capture(tmp_guide, fake)
    web = fake.containers.get(f"ccg-{RUN_ID}-web1") or next(c for c in fake.created("container")
                                                             if f"ccg-{RUN_ID}-web1" in c)
    tools = next(c for c in fake.created("container") if f"ccg-{RUN_ID}-tools" in c)
    cap = next(c for c in fake.created("container") if f"ccg-{RUN_ID}-capture" in c)
    for call, alias in ((web, "web1"), (tools, "tools")):
        assert call[call.index("--network-alias") + 1] == alias
        assert call[call.index("--hostname") + 1] == alias
        assert call[call.index("--network") + 1] == f"ccg-{RUN_ID}"
        assert "GUIDE_ENV_WEB1_URL=http://web1:80" in call
        assert f"{tmp_guide.resolve() / 'visuals'}:/visuals:ro" in call
    for call in (web, tools, cap):
        assert call[call.index("--security-opt") + 1] == "label=disable"
    assert "GUIDE_ENV_WEB1_URL=http://web1:80" in cap
    assert cap[cap.index("--hostname") + 1] == "capture"
    assert tools[tools.index("--entrypoint") + 1] == "sleep"
    assert tools[-2:] == ["docker.io/library/alpine:3.20", "infinity"]
    assert "--entrypoint" not in web


def test_cli_environment_with_command_keeps_entrypoint(tmp_guide):
    guide(tmp_guide, RECIPE.replace("    image: docker.io/library/alpine:3.20\n",
                                    "    image: docker.io/library/alpine:3.20\n    command: [\"sleep\", \"600\"]\n"))
    fake = FakePodman()
    capture(tmp_guide, fake)
    tools = next(c for c in fake.created("container") if f"ccg-{RUN_ID}-tools" in c)
    assert "--entrypoint" not in tools and tools[-3:] == ["docker.io/library/alpine:3.20", "sleep", "600"]


def test_teardown_removes_everything(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()
    capture(tmp_guide, fake)
    assert fake.containers == {}
    assert fake.networks == set()
    assert not (run_dir(tmp_guide) / "job.json").exists()
    assert not (run_dir(tmp_guide) / "raw").exists()


def test_seed_failure_names_step_and_tears_down(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()
    fake.on(lambda a: a[0] == "exec" and "echo second" in a, cp(3, "", "boom"))
    lines: list[str] = []
    assert capture(tmp_guide, fake, lines=lines) == 1
    table = next(line for line in lines if " table" in line)
    assert table.startswith("failed") and "seed step 2 of environment web1" in table and "echo second" in table
    assert fake.containers == {} and fake.networks == set()


def test_readiness_timeout_includes_log_tail(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()
    fake.on(lambda a: a[0] == "exec" and "ready" in a, cp(1, "status 503\n"))
    lines: list[str] = []
    assert capture(tmp_guide, fake, lines=lines) == 1
    text = "\n".join(lines)
    assert "environment web1 not ready" in text and "status 503" in text and "log line 2" in text
    ready = next(c for c in fake.calls if c[0] == "exec" and "ready" in c)
    assert "http://web1:80/health" in ready and ready[1] == f"ccg-{RUN_ID}-capture"
    assert fake.containers == {}


def test_image_pull_failure(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()
    fake.on(lambda a: a[:2] == ["image", "exists"] and "nginx" in a[-1], cp(1))
    fake.on(lambda a: a[0] == "pull", cp(125, "", "manifest unknown"))
    lines: list[str] = []
    assert capture(tmp_guide, fake, lines=lines) == 1
    table = next(line for line in lines if " table" in line)
    assert "docker.io/library/nginx:1.27-alpine" in table and "could not be pulled" in table
    assert not any(c for c in fake.created("container") if f"ccg-{RUN_ID}-web1" in c)


def test_interrupt_still_tears_down(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()

    def interrupt(_args):
        raise KeyboardInterrupt
    fake.on(lambda a: a[0] == "exec" and "cp /visuals" in " ".join(a), interrupt)
    lines: list[str] = []
    assert capture(tmp_guide, fake, lines=lines) == 1
    assert "interrupted" in lines[-1]
    assert fake.containers == {} and fake.networks == set()
    assert not (run_dir(tmp_guide) / "job.json").exists()


def test_sweep_only_dead_pids_on_this_host(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()
    host = visuals._short_hash(socket.gethostname())
    dead = 999999
    while visuals.pid_alive(dead):
        dead += 1
    fake.ps = [
        {"Id": "dead1", "Labels": {"io.cc-guide.host": host, "io.cc-guide.pid": str(dead)}},
        {"Id": "alive1", "Labels": {"io.cc-guide.host": host, "io.cc-guide.pid": str(os.getpid())}},
        {"Id": "other1", "Labels": {"io.cc-guide.host": "elsewhere", "io.cc-guide.pid": str(dead)}},
    ]
    fake.nets = [
        {"name": "ccg-dead", "labels": {"io.cc-guide.host": host, "io.cc-guide.pid": str(dead)}},
        {"name": "ccg-alive", "labels": {"io.cc-guide.host": host, "io.cc-guide.pid": str(os.getpid())}},
    ]
    capture(tmp_guide, fake)
    removed = [c[-1] for c in fake.calls if c[0] == "rm"]
    assert "dead1" in removed and "alive1" not in removed and "other1" not in removed
    removed_nets = [c[-1] for c in fake.calls if c[:2] == ["network", "rm"]]
    assert "ccg-dead" in removed_nets and "ccg-alive" not in removed_nets


def test_capture_image_built_when_missing(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()
    fake.on(lambda a: a[:2] == ["image", "exists"] and a[-1].startswith("localhost/cc-guide-capture:"), cp(1))
    capture(tmp_guide, fake)
    build = next(c for c in fake.calls if c[0] == "build")
    assert build[2] == f"localhost/cc-guide-capture:{visualcfg.capture_env_version()}"
    assert build[-1].endswith("capture")


def test_job_file_written_then_removed(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()
    seen = {}

    def snapshot(args):
        job = fake.work / "job.json"
        if "job" not in seen and job.exists():
            seen["job"] = json.loads(job.read_text())
        fake.containers.pop(args[-1], None)
        return cp(0)
    fake.on(lambda a: a[0] == "rm", snapshot)     # teardown runs before the scratch cleanup
    capture(tmp_guide, fake)
    job = seen["job"]
    assert job["urls"] == {"GUIDE_ENV_WEB1_URL": "http://web1:80"}
    rules = job["visuals"]["colors"]["rules"]
    assert any("alice" in (r["pattern"] or "") for r in rules)       # host values only in the job file
    ipv4 = next(r for r in rules if r["id"] == "ipv4")
    assert "10.89.1.0/24" in ipv4["exempt"]
    assert not (run_dir(tmp_guide) / "job.json").exists()


# --- validate -----------------------------------------------------------------


def test_validate_exit_codes(tmp_guide, capsys):
    assert visuals.main(["--root", str(tmp_guide), "validate"]) == 0
    assert "no visuals declared" in capsys.readouterr().out
    guide(tmp_guide)
    assert visuals.main(["--root", str(tmp_guide), "validate"]) == 0
    guide(tmp_guide, RECIPE.replace("port: 80", "port: eighty"))
    assert visuals.main(["--root", str(tmp_guide), "validate"]) == 1
    assert "visuals.yaml: environments.web1.port:" in capsys.readouterr().out


def test_version(capsys):
    assert visuals.main(["version"]) == 0
    assert capsys.readouterr().out.strip() == visualcfg.capture_env_version()


# --- CLI capture path (T016) --------------------------------------------------


def test_cli_capture_writes_svg_and_sidecar(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()
    lines: list[str] = []
    assert capture(tmp_guide, fake, names=["colors"], lines=lines) == 0
    assert lines == ["captured  colors  docs/assets/visuals/colors.svg"]
    assert (tmp_guide / "docs" / "assets" / "visuals" / "colors.svg").read_text() == "<svg/>"
    side = visualcfg.load_sidecar(tmp_guide / "visuals" / "colors.visual.yaml")
    recipe = visualcfg.load_recipe(tmp_guide)
    assert side["name"] == "colors" and side["variant"] == "default" and side["kind"] == "cli"
    assert side["image"] == "docs/assets/visuals/colors.svg"
    assert side["environment"] == {"name": "tools", "image": "docker.io/library/alpine:3.20",
                                   "digest": "sha256:index", "platform": "linux/arm64"}
    assert side["fingerprint"] == visualcfg.fingerprint(recipe, "colors", tmp_guide)
    assert side["capture_env"] == visualcfg.capture_env_version()
    assert side["redaction"]["rules"] == ["home-path", "user-path", "user-at", "k8s-api", "hostname", "ipv4",
                                          "jwt", "bearer", "api-key", "private-key"]
    assert side["redaction"]["replacements"]["home-path"] == 1 and side["redaction"]["disabled"] == []
    assert side["style"] == "0123456789abcdef" and side["text"] == "$ printf ok\nok"
    assert list(side)[:6] == ["schema", "name", "variant", "kind", "image", "environment"]


def test_cli_pty_call(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()
    capture(tmp_guide, fake, names=["colors"])
    (call,) = fake.pty_calls
    assert call[:2] == ["exec", "-t"]
    assert "COLUMNS=100" in call and "LINES=200" in call and "TERM=xterm-256color" in call
    assert "TARGET=http://web1:80" in call                    # ${GUIDE_ENV_WEB1_URL} expanded
    assert call[-4:] == [f"ccg-{RUN_ID}-tools", "sh", "-c", "printf '\\033[1;32mok\\033[0m'"]
    render = next(c for c in fake.calls if c[0] == "exec" and "cli" in c)
    assert render[1] == f"ccg-{RUN_ID}-capture" and render[-2:] == ["--visual", "colors"]


def test_job_has_host_values_sidecar_does_not(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()
    seen = {}

    def runner(args):
        seen["job"] = (fake.work / "job.json").read_text()
        return fake.runner(args)
    fake.on(lambda a: a[0] == "exec" and "runner.py" in " ".join(a) and "cli" in a, runner)
    capture(tmp_guide, fake, names=["colors"])
    assert "alice" in seen["job"] and "box" in seen["job"]
    side = (tmp_guide / "visuals" / "colors.visual.yaml").read_text()
    for value in ("alice", "/home/alice", "box.corp.example"):
        assert value not in side


def test_exit_mismatch_keeps_committed_files(tmp_guide):
    guide(tmp_guide)
    svg = tmp_guide / "docs" / "assets" / "visuals" / "colors.svg"
    svg.parent.mkdir(parents=True)
    svg.write_text("<svg>committed</svg>")
    side = tmp_guide / "visuals" / "colors.visual.yaml"
    side.write_text("schema: 1\nname: colors\n")
    fake = FakePodman()
    fake.pty_result = (2, b"line1\r\nfailed at /home/alice/x\r\n")
    lines: list[str] = []
    assert capture(tmp_guide, fake, lines=lines) == 1
    colors = next(line for line in lines if " colors" in line)
    assert colors.startswith("failed") and "exited 2, expected 0" in colors and "printf" in colors
    assert "failed at /home/user/x" in colors and "alice" not in colors
    assert svg.read_text() == "<svg>committed</svg>"
    assert side.read_text() == "schema: 1\nname: colors\n"
    assert not any(c for c in fake.calls if c[0] == "exec" and "cli" in c)


def test_expected_nonzero_exit(tmp_guide):
    guide(tmp_guide, RECIPE.replace("    env_vars:", "    exit: 3\n    env_vars:"))
    fake = FakePodman()
    fake.pty_result = (3, b"warning\r\n")
    assert capture(tmp_guide, fake, names=["colors"]) == 0


def test_render_failure_fails_visual(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()
    fake.on(lambda a: a[0] == "exec" and "runner.py" in " ".join(a) and "cli" in a, cp(1, "", "font missing"))
    lines: list[str] = []
    assert capture(tmp_guide, fake, names=["colors"], lines=lines) == 1
    assert lines[-1].startswith("failed") and "rendering failed: font missing" in lines[-1]
    assert not (tmp_guide / "visuals" / "colors.visual.yaml").exists()


def test_summary_and_report(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()
    lines: list[str] = []
    capture(tmp_guide, fake, names=["colors"], lines=lines)
    assert (run_dir(tmp_guide) / "report.md").read_text() == "\n".join(lines) + "\n"


def test_unexpected_error_in_one_visual_keeps_others(tmp_guide):
    """A broken result file fails only that visual (checkpoint review finding 5)."""
    guide(tmp_guide)
    fake = FakePodman()

    def broken(args):
        out = fake.work / "out"
        out.mkdir(parents=True, exist_ok=True)
        (out / "colors.result.json").write_text("{truncated")
        return cp(0)
    fake.on(lambda a: a[0] == "exec" and "runner.py" in " ".join(a) and "cli" in a, broken)
    lines: list[str] = []
    assert capture(tmp_guide, fake, lines=lines) == 1
    colors = next(line for line in lines if " colors" in line)
    assert colors.startswith("failed") and "unexpected error" in colors
    assert any(" table" in line for line in lines)
    assert fake.containers == {}


def test_readiness_check_timeout_is_an_environment_failure(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()

    def hang(_args):
        raise subprocess.TimeoutExpired("podman", 65)
    fake.on(lambda a: a[0] == "exec" and "ready" in a, hang)
    lines: list[str] = []
    assert capture(tmp_guide, fake, lines=lines) == 1
    assert "environment web1 not ready" in next(line for line in lines if " table" in line)


def test_cli_sidecar_has_no_variants_key(tmp_guide):
    guide(tmp_guide)
    capture(tmp_guide, FakePodman(), names=["colors"])
    assert "variants" not in visualcfg.load_sidecar(tmp_guide / "visuals" / "colors.visual.yaml")


# --- web capture path (T022) --------------------------------------------------


def web_recipe(variants: str | None = None) -> str:
    extra = f"    variants: {variants}\n" if variants else ""
    return RECIPE.replace("    env: web1\n    steps:", f"    env: web1\n{extra}    steps:")


def web_result(fake: FakePodman, text: str = "- table", highlights=None, dark_text: str | None = None):
    def runner(args):
        name = args[args.index("--visual") + 1]
        variant = args[args.index("--variant") + 1]
        stem = f"{name}-dark" if variant == "dark" else name
        out = fake.work / "out"
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{stem}.png").write_bytes(f"PNG {variant}".encode())
        body = dark_text if (variant == "dark" and dark_text is not None) else text
        (out / f"{stem}.result.json").write_text(json.dumps(
            {"text": body, "highlights": highlights or [], "redaction": {"ipv4": 2}, "masks": 1,
             "scripts": [], "error": None}))
        return cp(0)
    fake.on(lambda a: a[0] == "exec" and "runner.py" in " ".join(a) and "web" in a, runner)


VIS = Path("docs") / "assets" / "visuals"


def test_web_default_variant(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()
    hl = [{"label": "1", "selector": "role=columnheader[name=accuracy]", "text": "accuracy"}]
    web_result(fake, text='- table:\n  - columnheader "accuracy"', highlights=hl)
    lines: list[str] = []
    assert capture(tmp_guide, fake, names=["table"], lines=lines) == 0
    assert lines == ["captured  table  docs/assets/visuals/table.png"]
    call = next(c for c in fake.calls if c[0] == "exec" and "web" in c)
    assert call[-2:] == ["--variant", "default"]
    side = visualcfg.load_sidecar(tmp_guide / "visuals" / "table.visual.yaml")
    assert side["variant"] == "default" and side["kind"] == "web" and "variants" not in side
    assert side["highlights"] == hl and side["text"] == '- table:\n  - columnheader "accuracy"'
    assert side["masks"] == 1 and side["redaction"]["replacements"]["ipv4"] == 2
    assert side["style"] is None
    assert (tmp_guide / VIS / "table.png").read_bytes() == b"PNG default"


def test_dark_variant_skipped_when_equal(tmp_guide):
    guide(tmp_guide, web_recipe("[light, dark]"))
    stale = tmp_guide / VIS / "table-dark.png"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"old dark")
    fake = FakePodman()
    web_result(fake)
    lines: list[str] = []
    assert capture(tmp_guide, fake, names=["table"], lines=lines) == 0
    assert lines[0].startswith("captured  table  ")
    assert lines[1].startswith("skipped   table (dark)")
    side = visualcfg.load_sidecar(tmp_guide / "visuals" / "table.visual.yaml")
    assert side["variant"] == "light" and side["variants"] == {"dark": "skipped"}
    assert not stale.exists() and not (tmp_guide / "visuals" / "table-dark.visual.yaml").exists()
    diff = next(c for c in fake.calls if c[0] == "exec" and "diff" in c)
    assert diff[-4:] == ["/work/out/table.png", "/work/out/table-dark.png", "--tolerance", "16"]


def test_dark_variant_written_when_different(tmp_guide):
    guide(tmp_guide, web_recipe("[light, dark]"))
    fake = FakePodman()
    web_result(fake)
    fake.on(lambda a: a[0] == "exec" and "diff" in a, cp(0, '{"diff": 12.5}'))
    assert capture(tmp_guide, fake, names=["table"]) == 0
    light = visualcfg.load_sidecar(tmp_guide / "visuals" / "table.visual.yaml")
    dark = visualcfg.load_sidecar(tmp_guide / "visuals" / "table-dark.visual.yaml")
    assert light["variants"] == {"dark": "captured"}
    assert dark["variant"] == "dark" and "variants" not in dark
    assert dark["image"] == "docs/assets/visuals/table-dark.png"
    assert (tmp_guide / VIS / "table-dark.png").read_bytes() == b"PNG dark"


def test_dark_text_difference_counts(tmp_guide):
    guide(tmp_guide, web_recipe("[light, dark]"))
    fake = FakePodman()
    web_result(fake, dark_text="- table dark")
    capture(tmp_guide, fake, names=["table"])
    assert (tmp_guide / "visuals" / "table-dark.visual.yaml").exists()
    assert not any(c for c in fake.calls if c[0] == "exec" and "diff" in c)


def test_dark_only(tmp_guide):
    guide(tmp_guide, web_recipe("[dark]"))
    fake = FakePodman()
    web_result(fake)
    lines: list[str] = []
    assert capture(tmp_guide, fake, names=["table"], lines=lines) == 0
    assert lines == ["captured  table (dark)  docs/assets/visuals/table-dark.png"]
    assert not (tmp_guide / VIS / "table.png").exists()
    assert not (tmp_guide / "visuals" / "table.visual.yaml").exists()
    assert visualcfg.load_sidecar(tmp_guide / "visuals" / "table-dark.visual.yaml")["variant"] == "dark"


def test_failed_step_keeps_committed_files(tmp_guide):
    guide(tmp_guide, web_recipe("[light, dark]"))
    png = tmp_guide / VIS / "table.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(b"committed")
    side = tmp_guide / "visuals" / "table.visual.yaml"
    side.write_text("schema: 1\nname: table\n")
    fake = FakePodman()

    def failing(args):
        variant = args[args.index("--variant") + 1]
        stem = "table-dark" if variant == "dark" else "table"
        out = fake.work / "out"
        out.mkdir(parents=True, exist_ok=True)
        if variant == "dark":
            (out / f"{stem}.result.json").write_text(json.dumps(
                {"error": "step 2 (wait role=table): Timeout 15000ms exceeded.", "step": 2, "selector": "role=table"}))
            return cp(1)
        (out / f"{stem}.png").write_bytes(b"fresh")
        (out / f"{stem}.result.json").write_text(json.dumps({"text": "x", "highlights": [], "error": None}))
        return cp(0)
    fake.on(lambda a: a[0] == "exec" and "runner.py" in " ".join(a) and "web" in a, failing)
    lines: list[str] = []
    assert capture(tmp_guide, fake, names=["table"], lines=lines) == 1
    assert lines == [f"failed    table (dark)  step 2 (wait role=table): Timeout 15000ms exceeded. "
                     f"(debug image in .guide/visuals/{RUN_ID}/debug/)"]
    assert png.read_bytes() == b"committed"
    assert side.read_text() == "schema: 1\nname: table\n"
    assert sorted(p.name for p in png.parent.iterdir()) == ["table.png"]


# --- visual drift (T032) --------------------------------------------------------


def drift(root: Path, fake: FakePodman, names=(), fmt: str = "markdown", lines=None) -> int:
    out = lines if lines is not None else []
    return visuals.cmd_drift(root, list(names), fmt, podman=fake, out=out.append, run_id=RUN_ID, values=VALUES)


def committed(root: Path, fake_factory=FakePodman, recipe: str = RECIPE, **web_kw) -> None:
    """Capture once with the fake so the committed visuals and sidecars exist."""
    guide(root, recipe)
    fake = fake_factory()
    web_result(fake, **web_kw)
    assert capture(root, fake) == 0
    shutil.rmtree(root / ".guide")


def snapshot(root: Path) -> dict:
    files = {}
    for base in (root / "docs", root / "visuals"):
        for f in sorted(base.rglob("*")):
            if f.is_file():
                files[f.relative_to(root).as_posix()] = f.read_bytes()
    return files


def report(root: Path) -> dict:
    return json.loads((run_dir(root) / "report.json").read_text())


def by_name(rep: dict) -> dict:
    return {(v["name"], v["variant"]): v for v in rep["visuals"]}


def test_drift_unchanged(tmp_guide):
    committed(tmp_guide)
    before = snapshot(tmp_guide)
    fake = FakePodman()
    web_result(fake)
    lines: list[str] = []
    assert drift(tmp_guide, fake, lines=lines) == 0
    rep = report(tmp_guide)
    assert rep["has_drift"] is False
    assert {k: v["status"] for k, v in by_name(rep).items()} == {("table", "default"): "unchanged",
                                                                 ("colors", "default"): "unchanged"}
    assert "No visual drift." in lines[-1]
    assert snapshot(tmp_guide) == before
    diff = next(c for c in fake.calls if c[0] == "exec" and "diff" in c)
    assert diff[-4:] == ["/work/committed/table.png", "/work/out/table.png", "--tolerance", "16"]
    assert (run_dir(tmp_guide) / "committed" / "table.png").read_bytes() == b"PNG default"


def test_drift_text_change(tmp_guide):
    committed(tmp_guide, text='- table:\n  - columnheader "loss"')
    before = snapshot(tmp_guide)
    fake = FakePodman()
    web_result(fake, text='- table:\n  - columnheader "val-loss"')
    lines: list[str] = []
    assert drift(tmp_guide, fake, lines=lines) == 10
    table = by_name(report(tmp_guide))[("table", "default")]
    assert table["status"] == "drifted"
    assert table["text_diff"] == ['-  - columnheader "loss"', '+  - columnheader "val-loss"']
    assert table["image_before"]["digest"] == "sha256:index" and table["image_after"]["platform"] == "linux/arm64"
    md = lines[-1]
    assert "## `table`" in md and '+  - columnheader "val-loss"' in md and "Status: **drifted**" in md
    assert snapshot(tmp_guide) == before


def test_drift_cli_style_change(tmp_guide):
    committed(tmp_guide)
    fake = FakePodman()
    web_result(fake)

    def restyled(args):
        fake.runner(args)
        path = fake.work / "out" / "colors.result.json"
        data = json.loads(path.read_text())
        data["style"] = "ffffffffffffffff"
        path.write_text(json.dumps(data))
        return cp(0)
    fake.on(lambda a: a[0] == "exec" and "runner.py" in " ".join(a) and "cli" in a, restyled)
    assert drift(tmp_guide, fake) == 10
    colors = by_name(report(tmp_guide))[("colors", "default")]
    assert colors["status"] == "drifted" and colors["style_changed"] is True
    assert colors["image_diff"] is None and colors["text_diff"] == []


@pytest.mark.parametrize("value,expected", [(0.4, 0), (0.6, 10)])
def test_drift_image_threshold(tmp_guide, value, expected):
    committed(tmp_guide)
    fake = FakePodman()
    web_result(fake)
    fake.on(lambda a: a[0] == "exec" and "diff" in a, cp(0, json.dumps({"diff": value})))
    assert drift(tmp_guide, fake, names=["table"]) == expected
    assert by_name(report(tmp_guide))[("table", "default")]["image_diff"] == value


def test_drift_per_visual_threshold(tmp_guide):
    committed(tmp_guide, recipe=RECIPE.replace("    env: web1\n", "    env: web1\n    threshold: 2\n"))
    fake = FakePodman()
    web_result(fake)
    fake.on(lambda a: a[0] == "exec" and "diff" in a, cp(0, json.dumps({"diff": 1.5})))
    assert drift(tmp_guide, fake, names=["table"]) == 0


def test_drift_platform_mismatch_reports_but_does_not_count(tmp_guide):
    committed(tmp_guide)
    side = tmp_guide / "visuals" / "table.visual.yaml"
    data = visualcfg.load_sidecar(side)
    data["environment"]["platform"] = "linux/amd64"
    visualcfg.dump_sidecar(side, data)
    fake = FakePodman()
    web_result(fake)
    fake.on(lambda a: a[0] == "exec" and "diff" in a, cp(0, json.dumps({"diff": 7.0})))
    assert drift(tmp_guide, fake, names=["table"]) == 0
    table = by_name(report(tmp_guide))[("table", "default")]
    assert table["platform_mismatch"] is True and table["image_diff"] == 7.0 and table["status"] == "unchanged"


def test_drift_recapture_failed(tmp_guide):
    committed(tmp_guide)
    fake = FakePodman()

    def failing(args):
        out = fake.work / "out"
        out.mkdir(parents=True, exist_ok=True)
        (out / "table.result.json").write_text(json.dumps(
            {"error": "step 2 (crop role=table): Timeout", "step": 2, "selector": "role=table"}))
        return cp(1)
    fake.on(lambda a: a[0] == "exec" and "runner.py" in " ".join(a) and "web" in a, failing)
    assert drift(tmp_guide, fake, names=["table"]) == 10
    table = by_name(report(tmp_guide))[("table", "default")]
    assert table["status"] == "recapture-failed" and table["step"] == 2 and table["selector"] == "role=table"
    assert table["image_before"]["digest"] == "sha256:index"          # checkpoint 2 finding 3


def test_drift_cli_recapture_failed_names_command(tmp_guide):
    committed(tmp_guide)
    fake = FakePodman()
    fake.pty_result = (1, b"boom\r\n")
    assert drift(tmp_guide, fake, names=["colors"]) == 10
    colors = by_name(report(tmp_guide))[("colors", "default")]
    assert colors["status"] == "recapture-failed" and "printf" in colors["selector"]
    assert colors["image_before"]["image"] == "docker.io/library/alpine:3.20"


def test_drift_environment_failed_exit_2(tmp_guide):
    committed(tmp_guide)
    fake = FakePodman()
    fake.on(lambda a: a[0] == "exec" and "ready" in a, cp(1, "status 503\n"))
    lines: list[str] = []
    assert drift(tmp_guide, fake, names=["table"], lines=lines) == 2
    table = by_name(report(tmp_guide))[("table", "default")]
    assert table["status"] == "environment-failed" and "not ready" in table["detail"]


def test_drift_pages_list(tmp_guide):
    committed(tmp_guide)
    (tmp_guide / "tools" / "guide").mkdir(parents=True)
    (tmp_guide / "tools" / "guide" / "adapter.yaml").write_text(
        "format: gfm\ncontent_root: docs\ninternal_root: internal\npage_glob: '**/*.md'\ncomment: html\n")
    (tmp_guide / "docs" / "user").mkdir(parents=True)
    (tmp_guide / "docs" / "user" / "runs.md").write_text("# Runs\n\n<!-- Sources:\nvisual:table\n-->\n\nText.\n")
    (tmp_guide / "docs" / "other.md").write_text("# Other\n\n<!-- Sources:\nmini:README.md\n-->\n\nText.\n")
    fake = FakePodman()
    web_result(fake, text="changed")
    drift(tmp_guide, fake, names=["table"], fmt="json")
    assert by_name(report(tmp_guide))[("table", "default")]["pages"] == ["docs/user/runs.md"]


def test_drift_dark_skipped_but_now_different(tmp_guide):
    committed(tmp_guide, recipe=web_recipe("[light, dark]"))
    assert visualcfg.load_sidecar(tmp_guide / "visuals" / "table.visual.yaml")["variants"] == {"dark": "skipped"}
    fake = FakePodman()
    web_result(fake, dark_text="- table in dark")
    assert drift(tmp_guide, fake, names=["table"]) == 10
    dark = by_name(report(tmp_guide))[("table", "dark")]
    assert dark["status"] == "drifted" and "dark theme" in dark["detail"]
    assert by_name(report(tmp_guide))[("table", "light")]["status"] == "unchanged"


def test_drift_json_and_markdown_shapes(tmp_guide):
    committed(tmp_guide)
    fake = FakePodman()
    web_result(fake)
    lines: list[str] = []
    assert drift(tmp_guide, fake, fmt="json", lines=lines) == 0
    rep = json.loads(lines[-1])
    assert set(rep) == {"run_id", "platform", "has_drift", "visuals"}
    assert set(rep["visuals"][0]) == {"name", "variant", "status", "image_diff", "platform_mismatch", "text_diff",
                                      "style_changed", "pages", "image_before", "image_after", "step", "selector",
                                      "detail"}
    assert (run_dir(tmp_guide) / "report.md").read_text().startswith("# Visual drift report")


def test_drift_without_recipe(tmp_guide):
    fake = FakePodman()
    lines: list[str] = []
    assert drift(tmp_guide, fake, lines=lines) == 0
    assert lines == ["no visuals declared"] and fake.calls == []


def test_drift_missing_podman_exit_2(tmp_guide):
    guide(tmp_guide)
    assert drift(tmp_guide, FakePodman(missing=True)) == 2


# --- init, placeholder, version (T036) -------------------------------------------


def toolkit_guide(root: Path) -> Path:
    (root / "tools" / "guide").mkdir(parents=True)
    (root / "tools" / "guide" / "adapter.yaml").write_text("format: gfm\nvisual_dir: docs/assets/visuals\n")
    return root


def test_init_creates_recipe_and_sidecar_dir(tmp_guide):
    toolkit_guide(tmp_guide)
    lines: list[str] = []
    template = REPO / "guide" / "templates" / "visuals.yaml"
    assert visuals.cmd_init(tmp_guide, out=lines.append, template=template) == 0
    assert lines == ["created visuals.yaml, visuals/.gitkeep"]
    assert (tmp_guide / "visuals.yaml").read_text() == template.read_text()
    assert (tmp_guide / "visuals" / ".gitkeep").is_file()
    assert visualcfg.validate(tmp_guide) == []
    lines.clear()
    assert visuals.cmd_init(tmp_guide, out=lines.append, template=template) == 0
    assert lines == ["visuals already set up; nothing to do"]


def test_init_without_template_asks_for_a_toolkit_refresh(tmp_guide):
    toolkit_guide(tmp_guide)
    lines: list[str] = []
    assert visuals.cmd_init(tmp_guide, out=lines.append, template=tmp_guide / "missing.yaml") == 1
    assert "refresh the toolkit" in lines[0]


def test_init_keeps_an_existing_recipe(tmp_guide):
    toolkit_guide(tmp_guide)
    (tmp_guide / "visuals.yaml").write_text("schema: 1\n# mine\n")
    visuals.cmd_init(tmp_guide, out=lambda _l: None)
    assert (tmp_guide / "visuals.yaml").read_text() == "schema: 1\n# mine\n"


def test_init_needs_a_guide_project(tmp_guide):
    lines: list[str] = []
    assert visuals.cmd_init(tmp_guide, out=lines.append) == 1
    assert "adapter.yaml" in lines[0]


def test_placeholder(tmp_guide):
    guide(tmp_guide, web_recipe("[light, dark]"))
    lines: list[str] = []
    assert visuals.cmd_placeholder(tmp_guide, ["table", "colors"], out=lines.append) == 0
    side = visualcfg.load_sidecar(tmp_guide / "visuals" / "table.visual.yaml")
    assert side["placeholder"] is True and side["variant"] == "light" and side["text"] == ""
    assert side["image"] == "docs/assets/visuals/table.png"
    assert visualcfg.load_sidecar(tmp_guide / "visuals" / "table-dark.visual.yaml")["placeholder"] is True
    assert visualcfg.load_sidecar(tmp_guide / "visuals" / "colors.visual.yaml")["image"].endswith("colors.svg")
    assert not (tmp_guide / "docs").exists()


def test_placeholder_keeps_captured_and_rejects_unknown(tmp_guide):
    guide(tmp_guide)
    side = tmp_guide / "visuals" / "colors.visual.yaml"
    side.write_text("schema: 1\nname: colors\nredaction: {}\n")
    lines: list[str] = []
    assert visuals.cmd_placeholder(tmp_guide, ["colors"], out=lines.append) == 0
    assert side.read_text() == "schema: 1\nname: colors\nredaction: {}\n" and lines[0].startswith("kept")
    assert visuals.cmd_placeholder(tmp_guide, ["nope"], out=lines.append) == 1
    assert "no visual 'nope'" in lines[-1]


def test_placeholder_cli(tmp_guide, capsys):
    guide(tmp_guide)
    assert visuals.main(["--root", str(tmp_guide), "placeholder", "colors"]) == 0
    assert "placeholder colors" in capsys.readouterr().out


# --- review fixes: failure handling, cleanup, redaction of diagnostics ----------


def test_run_network_is_internal(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()
    web_result(fake)
    assert capture(tmp_guide, fake) == 0
    create = fake.created("network")[0]
    assert "--internal" in create and create[-1] == f"ccg-{RUN_ID}"


def test_container_that_fails_to_start_is_still_removed(tmp_guide):
    # podman can create a container and then fail to start it: teardown must remove it
    guide(tmp_guide)
    fake = FakePodman()
    name = f"ccg-{RUN_ID}-web1"
    fake.on(lambda a: a[0] == "run" and name in a, cp(125, "", "OCI runtime error"))
    assert capture(tmp_guide, fake) == 1
    assert ["rm", "-f", "-t", "0", name] in fake.calls


def test_network_recorded_before_create_fails(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()
    fake.on(lambda a: a[:2] == ["network", "create"], cp(125, "", "boom"))
    lines: list[str] = []
    assert capture(tmp_guide, fake, lines=lines) == 1
    assert ["network", "rm", "-f", f"ccg-{RUN_ID}"] in fake.calls
    assert all("failed" in line for line in lines)


def test_podman_timeout_fails_the_environment_not_the_run(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()

    def hang(args):
        raise subprocess.TimeoutExpired(args, 1)
    fake.on(lambda a: a[0] == "exec" and "echo second" in a, hang)
    lines: list[str] = []
    assert capture(tmp_guide, fake, lines=lines) == 1
    table = next(line for line in lines if "table" in line)
    assert "seed step 2" in table and "timed out" in table
    assert not fake.containers and not fake.networks


def test_timeouts_are_passed_to_podman(tmp_guide):
    guide(tmp_guide)
    seen: list[tuple[str, float | None]] = []
    fake = FakePodman()
    original = fake.run

    def run(args, timeout=None, input=None):
        seen.append((args[0], timeout))
        return original(args, timeout=timeout, input=input)
    fake.run = run
    web_result(fake)
    assert capture(tmp_guide, fake) == 0
    assert seen and all(t is not None for _, t in seen)


def test_failure_details_are_redacted(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()
    fake.on(lambda a: a[0] == "exec" and "echo second" in a,
            cp(1, "token at /home/alice/.config on box.corp.example", "Authorization: Bearer abcdefghijklmnop"))
    lines: list[str] = []
    assert capture(tmp_guide, fake, lines=lines) == 1
    text = "\n".join(lines) + (run_dir(tmp_guide) / "report.md").read_text()
    assert "/home/alice" not in text and "box.corp.example" not in text and "abcdefghijklmnop" not in text
    assert "/home/user/.config" in text and "example-host" in text


def test_drift_json_stdout_is_json_when_the_image_is_built(tmp_guide):
    committed(tmp_guide)
    fake = FakePodman()
    web_result(fake)
    fake.on(lambda a: a[:2] == ["image", "exists"] and a[2].startswith(visuals.IMAGE_REPO), cp(1))
    lines: list[str] = []
    assert drift(tmp_guide, fake, fmt="json", lines=lines) == 0
    assert len(lines) == 1 and json.loads(lines[0])["has_drift"] is False
    assert any(c[0] == "build" for c in fake.calls)


def test_drift_json_without_recipe(tmp_guide):
    lines: list[str] = []
    assert drift(tmp_guide, FakePodman(), fmt="json", lines=lines) == 0
    assert json.loads(lines[0]) == {"run_id": None, "platform": "", "has_drift": False, "visuals": []}


def test_drift_failed_image_comparison_is_not_unchanged(tmp_guide):
    committed(tmp_guide)
    fake = FakePodman()
    web_result(fake)
    fake.on(lambda a: a[0] == "exec" and "diff" in a, cp(1, "", "Pillow error"))
    assert drift(tmp_guide, fake, names=["table"]) == 10
    table = by_name(report(tmp_guide))[("table", "default")]
    assert table["status"] == "recapture-failed" and "image comparison failed" in table["detail"]


def test_drift_missing_committed_image_drifts(tmp_guide):
    committed(tmp_guide)
    (tmp_guide / VIS / "table.png").unlink()
    fake = FakePodman()
    web_result(fake)
    assert drift(tmp_guide, fake, names=["table"]) == 10
    table = by_name(report(tmp_guide))[("table", "default")]
    assert table["status"] == "drifted" and table["image_diff"] == 100.0


def test_drift_placeholder_sidecar_drifts(tmp_guide):
    guide(tmp_guide)
    assert visuals.cmd_placeholder(tmp_guide, ["table"], out=lambda _l: None) == 0
    fake = FakePodman()
    web_result(fake)
    assert drift(tmp_guide, fake, names=["table"]) == 10
    table = by_name(report(tmp_guide))[("table", "default")]
    assert table["status"] == "drifted" and table["detail"] == "placeholder, never captured"


def test_sweep_removes_host_values_of_dead_runs_and_prunes(tmp_guide):
    guide(tmp_guide)
    scratch = tmp_guide / ".guide" / "visuals"
    for i in range(visuals.KEEP_RUNS + 2):
        d = scratch / f"20250101-0000{i:02d}-0000"
        (d / "raw").mkdir(parents=True)
        (d / "raw" / "colors.bin").write_bytes(b"/home/alice")
        (d / "job.json").write_text('{"user": "alice"}')
        (d / "report.md").write_text("ok")
    fake = FakePodman()
    web_result(fake)
    assert capture(tmp_guide, fake) == 0
    old = sorted(d for d in scratch.iterdir() if d.is_dir() and d.name != RUN_ID)
    assert len(old) == visuals.KEEP_RUNS - 1
    assert all(not (d / "job.json").exists() and not (d / "raw").exists() for d in old)
    assert all((d / "report.md").exists() for d in old)


def test_job_file_and_raw_output_are_private(tmp_guide):
    """FR-021: the only unredacted files are owner-only scratch inputs, gone after the run."""
    guide(tmp_guide)
    fake = FakePodman()
    web_result(fake)
    modes, raw_modes = [], []
    original = fake.runner

    def runner(args):
        if "--job" in args:   # cli and web read the job file; ready runs before it exists
            modes.append((fake.work / "job.json").stat().st_mode & 0o777)
        if "cli" in args:
            name = args[args.index("--visual") + 1]
            raw_modes.append((fake.work / "raw" / f"{name}.bin").stat().st_mode & 0o777)
            raw_modes.append((fake.work / "raw").stat().st_mode & 0o777)
        return original(args)
    fake.runner = runner
    assert capture(tmp_guide, fake) == 0
    assert modes and set(modes) == {0o600}
    assert raw_modes and set(raw_modes) == {0o600, 0o700}
    assert not (run_dir(tmp_guide) / "job.json").exists() and not (run_dir(tmp_guide) / "raw").exists()


def test_needed_environments_are_transitive(tmp_guide):
    recipe = RECIPE.replace("      - run: echo second\n",
                            "      - run: echo ${GUIDE_ENV_WEB2_URL}\n").replace(
        "  tools:\n", "  web2:\n    kind: web\n    image: docker.io/library/nginx:1.27-alpine\n    port: 80\n"
                      "  tools:\n")
    guide(tmp_guide, recipe)
    run = visuals.Run(tmp_guide, FakePodman(), run_id=RUN_ID, values=VALUES)
    run.recipe = visualcfg.load_recipe(tmp_guide)
    names = [e.name for e in run.needed_environments([run.recipe.visuals["colors"]])]
    assert names == ["tools", "web1", "web2"]


def test_teardown_ignores_a_second_interrupt(tmp_guide):
    guide(tmp_guide)
    fake = FakePodman()
    web_result(fake)
    removed: list[str] = []
    original = fake.run

    def run(args, timeout=None, input=None):
        if args[0] == "exec" and "--visual" in args and "table" in args:
            raise KeyboardInterrupt("first")
        if args[0] == "rm":
            os.kill(os.getpid(), __import__("signal").SIGINT)   # a second Ctrl-C during cleanup
            removed.append(args[-1])
        return original(args, timeout=timeout, input=input)
    fake.run = run
    lines: list[str] = []
    assert capture(tmp_guide, fake, lines=lines) == 1
    assert len(removed) == 3 and not fake.networks
    assert lines[-1] == "interrupted: every container and the network of the run were removed"


def test_place_refuses_a_symlink(tmp_guide, tmp_path):
    guide(tmp_guide)
    secret = tmp_path / "secret.txt"
    secret.write_text("host file")
    fake = FakePodman()

    def linked(args):
        fake.runner(args)
        out = fake.work / "out" / "colors.svg"
        out.unlink()
        out.symlink_to(secret)
        return cp(0)
    fake.on(lambda a: a[0] == "exec" and "runner.py" in " ".join(a) and "cli" in a, linked)
    lines: list[str] = []
    assert capture(tmp_guide, fake, names=["colors"], lines=lines) == 1
    assert not (tmp_guide / VIS / "colors.svg").exists()
    assert "not a regular file" in lines[-1]


def test_run_pty_gives_a_terminal_of_the_width(tmp_path):
    status, raw = visuals.Podman(binary="/bin/sh").run_pty(["-c", "test -t 1 && echo tty; stty size"], columns=37)
    assert status == 0
    assert raw.replace(b"\r", b"").split(b"\n")[:2] == [b"tty", b"200 37"]


def test_run_pty_timeout(tmp_path):
    import time as _time
    start = _time.monotonic()
    status, raw = visuals.Podman(binary="/bin/sh").run_pty(["-c", "sleep 5"], timeout=0.5)
    assert _time.monotonic() - start < 4
    assert b"[cc-guide: command timed out]" in raw and status != 0


def test_containerfile_pins_every_python_package():
    """FR-009: every package uv installs is pinned, the transitive ones included."""
    import re

    text = (REPO / "guide" / "toolkit" / "capture" / "Containerfile").read_text()
    install = text.split("uv pip install", 1)[1].split("\n\n", 1)[0]
    packages = [t.strip('"') for t in install.split() if t != "\\" and not t.startswith("-")]
    assert packages, "no packages found in the uv pip install line"
    unpinned = [p for p in packages if not re.fullmatch(r"[A-Za-z0-9_.\-\[\]]+==[0-9][0-9A-Za-z.]*", p)]
    assert unpinned == []
    names = {re.sub(r"\[.*\]", "", p.split("==")[0]).lower() for p in packages}
    # the dependencies that decide rendering and font compression
    assert {"wcwidth", "zopfli", "brotli", "greenlet", "pyee", "typing-extensions"} <= names
