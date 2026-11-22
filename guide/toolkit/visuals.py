#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Captured visuals: capture, visual drift, and recipe tools (specs/008-captured-visuals).

Usage (from the guide project root, or with --root DIR):

    uv run tools/guide/visuals.py validate              schema check, no podman (FR-007)
    uv run tools/guide/visuals.py capture [NAME...]     capture all or the named visuals
    uv run tools/guide/visuals.py drift [NAME...] [--format markdown|json]
    uv run tools/guide/visuals.py init                  add visuals.yaml and visuals/ to a guide
    uv run tools/guide/visuals.py placeholder NAME...   placeholder sidecars (FR-031a)
    uv run tools/guide/visuals.py version               capture environment version

A run (capture or drift) takes a lock in .guide/visuals/, removes leftovers of dead
runs, builds or reuses the capture image (localhost/cc-guide-capture:<version>),
creates a network of its own, starts the capture container and every needed tool
container on it (no published ports, FR-011), waits for readiness, runs the seed
steps, replays the visuals, and removes every container and the network it created,
also on failure or interrupt (FR-008). Every podman call goes through the Podman
class, so tests inject a fake.

Exit codes. capture: 0 all captured or skipped, 1 any visual or environment failed,
2 recipe or configuration error, podman missing, or a run in progress.
drift: 0 no drift, 10 drift, 2 environment failure or the errors above.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import errno
import fcntl
import getpass
import hashlib
import json
import os
import pty
import re
import secrets
import select
import shutil
import signal
import socket
import struct
import subprocess
import sys
import termios
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import visualcfg  # noqa: E402
import redact  # noqa: E402  (tools/guide/capture/redact.py, on sys.path through visualcfg)

LABEL = "io.cc-guide.capture"
IMAGE_REPO = "localhost/cc-guide-capture"
SCRATCH = Path(".guide") / "visuals"
RUNNER = "/opt/ccg/runner.py"
INSTALL_HINT = "install podman: podman.io/docs/installation"
CLI_TIMEOUT = 300
LOG_TAIL = 40
KEEP_RUNS = 10           # run directories kept in .guide/visuals/ (older ones are pruned)
# Timeouts (seconds) of podman calls, so an unattended run never hangs (FR-008).
T_SHORT, T_EXEC, T_SEED, T_PULL, T_BUILD = 60, 300, 600, 900, 1800
URL_VAR_RE = re.compile(r"\$\{(GUIDE_ENV_[A-Z0-9_]+_URL)\}")
ANSI_RE = re.compile(r"\x1b(?:\[[0-9;?]*[ -/]*[@-~]|\][^\x07]*\x07|[@-Z\\-_])")

EXIT_OK, EXIT_FAILED, EXIT_CONFIG, EXIT_DRIFT = 0, 1, 2, 10


class ConfigError(Exception):
    """Recipe or configuration problem, missing podman, or a run in progress (exit 2)."""


class EnvironmentFailed(Exception):
    """An environment could not be pulled, became ready, or seeded."""


# --- podman -------------------------------------------------------------------


class Podman:
    """The only place that runs podman (plan design note 2)."""

    def __init__(self, binary: str = "podman"):
        self.binary = binary

    def run(self, args: list[str], timeout: float | None = None,
            input: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([self.binary, *args], capture_output=True, text=True, check=False,
                              timeout=timeout, input=input)

    def run_pty(self, args: list[str], columns: int = 100, rows: int = 200,
                timeout: float = CLI_TIMEOUT) -> tuple[int, bytes]:
        """Run under a host pseudo-terminal (research R4); returns (exit status, raw bytes)."""
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, columns, 0, 0))
        proc = subprocess.Popen([self.binary, *args], stdin=slave, stdout=slave, stderr=slave,
                                close_fds=True, start_new_session=True)
        os.close(slave)
        chunks: list[bytes] = []
        deadline = time.monotonic() + timeout
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    proc.kill()
                    chunks.append(b"\r\n[cc-guide: command timed out]\r\n")
                    break
                ready, _, _ = select.select([master], [], [], min(remaining, 1.0))
                if not ready:
                    if proc.poll() is not None:
                        # drain what is left, then stop
                        try:
                            data = os.read(master, 65536)
                        except OSError:
                            break
                        if not data:
                            break
                        chunks.append(data)
                    continue
                try:
                    data = os.read(master, 65536)
                except OSError as err:
                    if err.errno == errno.EIO:
                        break
                    raise
                if not data:
                    break
                chunks.append(data)
        finally:
            os.close(master)
        status = proc.wait()
        return status, b"".join(chunks)


# --- results ------------------------------------------------------------------


@dataclass
class Outcome:
    name: str
    variant: str
    status: str            # captured | failed | skipped
    detail: str = ""
    step: int | None = None
    selector: str | None = None

    def line(self) -> str:
        label = self.name if self.variant in ("default", "light") else f"{self.name} ({self.variant})"
        return f"{self.status:<9} {label}  {self.detail}".rstrip()


@dataclass
class EnvState:
    env: visualcfg.Environment
    container: str
    error: str | None = None
    digest: str = ""


@dataclass
class DriftResult:
    """One visual and variant in the visual drift report (data-model.md)."""
    name: str
    variant: str
    status: str            # unchanged | drifted | recapture-failed | environment-failed
    image_diff: float | None = None
    platform_mismatch: bool = False
    text_diff: list[str] = field(default_factory=list)
    style_changed: bool = False
    pages: list[str] = field(default_factory=list)
    image_before: dict = field(default_factory=dict)
    image_after: dict = field(default_factory=dict)
    step: int | None = None
    selector: str | None = None
    detail: str = ""

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


# --- helpers ------------------------------------------------------------------


def _short_hash(text: str, n: int = 12) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:n]   # noqa: S324 (identifier, not security)


def new_run_id() -> str:
    return _dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)


def host_values() -> dict[str, str]:
    """The capturing user's values the default rules resolve to (job file only)."""
    try:
        user = getpass.getuser()
    except Exception:  # noqa: BLE001
        user = os.environ.get("USER", "")
    return {"user": user, "home": str(Path.home()), "host": socket.gethostname()}


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass                    # alive, owned by another user
    return True


def tail(text: str, lines: int = 10) -> str:
    return "\n".join((text or "").rstrip().splitlines()[-lines:])


def expand_url_vars(value: str, urls: dict[str, str]) -> str:
    """${GUIDE_ENV_<NAME>_URL} only; nothing else is expanded (contracts/visuals-yaml.md)."""
    return URL_VAR_RE.sub(lambda m: urls.get(m.group(1), m.group(0)), value)


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- the run ------------------------------------------------------------------


class Run:
    """One capture or drift run of a guide project."""

    def __init__(self, root: Path, podman: Podman | None = None,
                 run_id: str | None = None, values: dict[str, str] | None = None,
                 toolkit_dir: Path | None = None, log: Callable[[str], None] | None = None):
        self.root = Path(root).resolve()
        self.podman = podman or Podman()
        # progress goes to stderr so stdout holds only the summary or report (drift --format json)
        self.log = log or (lambda line: print(line, file=sys.stderr))
        self.run_id = run_id or new_run_id()
        self.values = values if values is not None else host_values()
        self.toolkit_dir = Path(toolkit_dir or visualcfg.TOOLKIT_DIR)
        self.scratch = self.root / SCRATCH
        self.dir = self.scratch / self.run_id
        self.network = f"ccg-{self.run_id}"
        self.capture = f"ccg-{self.run_id}-capture"
        self.containers: list[str] = []
        self.network_created = False
        self.subnet: str | None = None
        self.platform = ""
        self.capture_env = visualcfg.capture_env_version(self.toolkit_dir)
        self.image = f"{IMAGE_REPO}:{self.capture_env}"
        self.envs: dict[str, EnvState] = {}
        self.recipe: visualcfg.Recipe | None = None
        self._lock = None
        self.leftovers: list[str] = []

    # labels and names

    def labels(self) -> list[str]:
        pairs = {LABEL: "1", "io.cc-guide.run": self.run_id, "io.cc-guide.guide": _short_hash(str(self.root)),
                 "io.cc-guide.pid": str(os.getpid()), "io.cc-guide.host": _short_hash(socket.gethostname())}
        out: list[str] = []
        for key, value in pairs.items():
            out += ["--label", f"{key}={value}"]
        return out

    def container_name(self, env: str) -> str:
        return f"ccg-{self.run_id}-{env}"

    def pod(self, args: list[str], timeout: float = T_SHORT) -> subprocess.CompletedProcess:
        """A podman call with a timeout; a timeout comes back as exit status 124."""
        try:
            return self.podman.run(args, timeout=timeout)
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess([args[0]], 124, "", f"podman {args[0]} timed out after {int(timeout)}s")

    # prerequisites, lock, sweep

    def check_podman(self) -> None:
        try:
            proc = self.podman.run(["info", "--format", "{{.Host.Arch}}"], timeout=120)
        except FileNotFoundError:
            raise ConfigError(f"podman not found: {INSTALL_HINT}") from None
        except subprocess.TimeoutExpired:
            raise ConfigError("podman info timed out: is the podman machine running?") from None
        if proc.returncode != 0:
            raise ConfigError("podman cannot run containers (podman info failed; on macOS start the machine "
                              f"with podman machine start): {tail(proc.stderr, 3)}")
        arch = (proc.stdout or "").strip() or "unknown"
        self.platform = f"linux/{arch}"

    def acquire_lock(self) -> None:
        self.scratch.mkdir(parents=True, exist_ok=True)
        handle = open(self.scratch / ".lock", "w")  # noqa: SIM115 (held for the run)
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            raise ConfigError("capture already running") from None
        self._lock = handle

    def release_lock(self) -> None:
        if self._lock is not None:
            fcntl.flock(self._lock, fcntl.LOCK_UN)
            self._lock.close()
            self._lock = None

    def sweep(self) -> None:
        """Remove labeled resources of dead runs on this host (FR-008)."""
        host = _short_hash(socket.gethostname())

        def stale(labels: dict) -> bool:
            if (labels or {}).get("io.cc-guide.host") != host:
                return False
            try:
                return not pid_alive(int((labels or {}).get("io.cc-guide.pid", "0")))
            except ValueError:
                return False

        proc = self.pod(["ps", "-a", "--filter", f"label={LABEL}=1", "--format", "json"])
        for item in _json_list(proc):
            if stale(item.get("Labels") or {}):
                self.pod(["rm", "-f", "-t", "0", item.get("Id") or (item.get("Names") or [""])[0]])
        proc = self.pod(["network", "ls", "--filter", f"label={LABEL}=1", "--format", "json"])
        for item in _json_list(proc):
            if stale(item.get("labels") or item.get("Labels") or {}):
                self.pod(["network", "rm", "-f", item.get("name") or item.get("Name")])
        self.sweep_scratch()

    def sweep_scratch(self) -> None:
        """Under the lock: drop the host values and raw output of earlier runs, prune old runs.

        A run killed before its cleanup (SIGKILL, a crash) leaves job.json (resolved host
        values) and raw/ (unredacted CLI output) behind; no other run is active now.
        """
        runs = sorted((d for d in self.scratch.iterdir() if d.is_dir() and d != self.dir),
                      key=lambda d: d.name) if self.scratch.is_dir() else []
        for d in runs:
            shutil.rmtree(d / "raw", ignore_errors=True)
            (d / "job.json").unlink(missing_ok=True)
        for d in runs[: max(len(runs) - (KEEP_RUNS - 1), 0)]:
            shutil.rmtree(d, ignore_errors=True)

    # image, network, containers

    def ensure_image(self) -> None:
        if self.pod(["image", "exists", self.image]).returncode == 0:
            return
        self.log(f"building the capture environment {self.image} (the first build takes a few minutes)")
        proc = self.pod(["build", "-t", self.image, str(self.toolkit_dir / "capture")], timeout=T_BUILD)
        if proc.returncode != 0:
            raise EnvironmentFailed(f"building the capture environment failed: {tail(proc.stderr or proc.stdout)}")

    def create_network(self) -> None:
        # recorded before the call: teardown removes it even when the call is interrupted
        self.network_created = True
        # --internal: no route out of the run network, so tools and pages cannot reach the
        # internet or services on the author's network (FR-010); images are pulled on the host
        proc = self.pod(["network", "create", "--internal", *self.labels(), self.network])
        if proc.returncode != 0:
            raise EnvironmentFailed(f"podman network create failed: {tail(proc.stderr, 3)}")
        info = _json_list(self.pod(["network", "inspect", self.network]))
        subnets = (info[0].get("subnets") if info else None) or []
        if subnets and isinstance(subnets[0], dict):
            self.subnet = subnets[0].get("subnet")

    def url_vars(self) -> dict[str, str]:
        urls = {}
        for env in (self.recipe.environments.values() if self.recipe else []):
            if env.url:
                urls[visualcfg.env_url_var(env.name)] = env.url
        return urls

    def _env_args(self, mapping: dict[str, str]) -> list[str]:
        out: list[str] = []
        for key, value in mapping.items():
            out += ["-e", f"{key}={value}"]
        return out

    def start_capture(self) -> None:
        (self.root / visualcfg.SIDECAR_DIR).mkdir(parents=True, exist_ok=True)
        args = ["run", "-d", "--name", self.capture, "--network", self.network, "--hostname", "capture",
                "--network-alias", "capture", "--security-opt", "label=disable",
                "-v", f"{self.root / visualcfg.SIDECAR_DIR}:/visuals:ro", "-v", f"{self.dir}:/work",
                *self.labels(), *self._env_args(self.url_vars()), self.image]
        # recorded before the call: podman may create the container and still fail to start it
        self.containers.append(self.capture)
        proc = self.pod(args)
        if proc.returncode != 0:
            raise EnvironmentFailed(f"starting the capture container failed: {tail(proc.stderr, 3)}")

    def start_environment(self, env: visualcfg.Environment) -> EnvState:
        state = EnvState(env, self.container_name(env.name))
        self.envs[env.name] = state
        try:
            if self.pod(["image", "exists", env.image]).returncode != 0:
                pulled = self.pod(["pull", "-q", env.image], timeout=T_PULL)
                if pulled.returncode != 0:
                    raise EnvironmentFailed(f"image {env.image} could not be pulled: {tail(pulled.stderr, 3)}")
            state.digest = self.image_digest(env.image)
            args = ["run", "-d", "--name", state.container, "--network", self.network,
                    "--network-alias", env.name, "--hostname", env.name, "--security-opt", "label=disable",
                    "-v", f"{self.root / visualcfg.SIDECAR_DIR}:/visuals:ro", *self.labels(),
                    *self._env_args({**env.env, **self.url_vars()})]
            if env.kind == "cli" and not env.command:
                args += ["--entrypoint", "sleep", env.image, "infinity"]
            else:
                args += [env.image, *(env.command or [])]
            self.containers.append(state.container)   # before the call, as in start_capture
            proc = self.pod(args)
            if proc.returncode != 0:
                raise EnvironmentFailed(f"starting environment {env.name} ({env.image}) failed: "
                                        f"{tail(proc.stderr, 3)}")
        except EnvironmentFailed as err:
            state.error = str(err)
        return state

    def image_digest(self, image: str) -> str:
        """Index (manifest list) digest when available, else the image digest (FR-017)."""
        proc = self.pod(["image", "inspect", "--format", "{{.Digest}}|{{json .RepoDigests}}", image])
        if proc.returncode != 0 or "|" not in (proc.stdout or ""):
            return ""
        digest, repo = proc.stdout.strip().split("|", 1)
        try:
            repo_digests = json.loads(repo) or []
        except json.JSONDecodeError:
            repo_digests = []
        others = [d.split("@", 1)[1] for d in repo_digests if "@" in d and d.split("@", 1)[1] != digest]
        return others[0] if others else digest

    def wait_ready(self, state: EnvState) -> None:
        env = state.env
        if state.error or env.kind != "web":
            return
        url = f"http://{env.name}:{env.port}{env.ready}"
        try:
            proc = self.podman.run(["exec", self.capture, "python3", RUNNER, "ready", "--url", url,
                                    "--timeout", str(env.ready_timeout)], timeout=env.ready_timeout + 60)
        except subprocess.TimeoutExpired:
            proc = subprocess.CompletedProcess([], 1, "readiness check did not return", "")
        if proc.returncode != 0:
            logs = self.pod(["logs", "--tail", str(LOG_TAIL), state.container])
            state.error = (f"environment {env.name} not ready after {env.ready_timeout}s at {env.ready} "
                           f"({(proc.stdout or proc.stderr).strip() or 'no answer'}); container log:\n"
                           f"{tail((logs.stdout or '') + (logs.stderr or ''), LOG_TAIL)}")

    def seed(self, state: EnvState) -> None:
        if state.error:
            return
        for i, step in enumerate(state.env.seed, start=1):
            target = self.capture if step.in_ == "capture" else state.container
            proc = self.pod(["exec", target, "sh", "-c", step.run], timeout=T_SEED)
            if proc.returncode != 0:
                state.error = (f"seed step {i} of environment {state.env.name} failed (exit {proc.returncode}): "
                               f"{step.run}\n{tail((proc.stdout or '') + (proc.stderr or ''))}")
                return

    def teardown(self) -> list[str]:
        """Remove every container and the network of the run; the names that could not be removed."""
        left: list[str] = []
        for name in reversed(self.containers):
            if self.pod(["rm", "-f", "-t", "0", name]).returncode != 0:
                left.append(name)
        self.containers = []
        if self.network_created:
            if self.pod(["network", "rm", "-f", self.network]).returncode != 0:
                left.append(self.network)
            self.network_created = False
        self.leftovers = left
        return left

    def cleanup_scratch(self) -> None:
        shutil.rmtree(self.dir / "raw", ignore_errors=True)
        (self.dir / "job.json").unlink(missing_ok=True)

    # environments a selection needs

    def needed_environments(self, visuals: list[visualcfg.Visual]) -> list[visualcfg.Environment]:
        """Environments of the visuals plus web environments their commands refer to."""
        names: list[str] = []
        recipe = self.recipe
        for v in visuals:
            if v.env not in names:
                names.append(v.env)
        texts = []
        for v in visuals:
            texts += [v.command or "", *v.env_vars.values()]
        scanned: set[str] = set()
        while True:
            # to a fixed point: an environment added for a reference can refer to another one
            for name in names:
                env = recipe.environments.get(name)
                if env and name not in scanned:
                    scanned.add(name)
                    texts += [s.run for s in env.seed] + list(env.env.values())
            joined = "\n".join(texts)
            added = [env.name for env in recipe.environments.values()
                     if env.url and env.name not in names and f"${{{visualcfg.env_url_var(env.name)}}}" in joined]
            if not added:
                break
            names += added
        return [recipe.environments[n] for n in names if n in recipe.environments]

    # job file

    def job(self, visuals: list[visualcfg.Visual]) -> dict:
        urls = self.url_vars()
        spec: dict[str, Any] = {}
        for v in visuals:
            env = self.recipe.environments.get(v.env)
            rules = redact.resolve(self.recipe.rules(v), self.values, run_subnet=self.subnet)
            item: dict[str, Any] = {"kind": v.kind, "env": v.env, "rules": rules, "masks": v.masks,
                                    **self.recipe.resolved(v)}
            if v.kind == "cli":
                item["command"] = v.command
            else:
                item["base_url"] = env.url if env else None
                item["steps"] = v.steps
            spec[v.name] = item
        return {"run_id": self.run_id, "urls": urls, "visuals": spec}

    def write_job(self, visuals: list[visualcfg.Visual]) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        # the job file holds the resolved host values: readable by the owner only
        path = self.dir / "job.json"
        path.unlink(missing_ok=True)      # O_CREAT keeps the mode of an existing file
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(json.dumps(self.job(visuals), indent=1, sort_keys=True))

    # the run itself

    def execute(self, visuals: list[visualcfg.Visual], per_visual: Callable[[visualcfg.Visual], list],
                on_failure: Callable[[visualcfg.Visual, str, bool], list] | None = None) -> list:
        """Bring the environments up, run per_visual for each visual, always tear down.

        on_failure(visual, message, environment_failed) builds the entries of a visual that
        could not run (default: failed capture outcomes).
        """
        fail = on_failure or self._failure_outcome
        outcomes: list = []
        previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}

        def interrupted(signum, _frame):
            raise KeyboardInterrupt(f"signal {signum}")

        for sig in previous:
            signal.signal(sig, interrupted)
        try:
            for d in ("out", "debug"):
                (self.dir / d).mkdir(parents=True, exist_ok=True)
            # raw/ (unredacted CLI output) and job.json (host values) are owner-only (FR-021)
            (self.dir / "raw").mkdir(mode=0o700, exist_ok=True)
            (self.dir / "raw").chmod(0o700)
            try:
                self.ensure_image()
                self.create_network()
                self.start_capture()
            except EnvironmentFailed as err:
                return [o for v in visuals for o in fail(v, str(err), True)]
            for env in self.needed_environments(visuals):
                try:
                    self.start_environment(env)
                except (OSError, subprocess.SubprocessError) as err:
                    self.envs.setdefault(env.name, EnvState(env, self.container_name(env.name))).error = \
                        f"starting environment {env.name} failed: {err}"
            for state in self.envs.values():
                self.wait_ready(state)
            for state in self.envs.values():
                self.seed(state)
            self.write_job(visuals)
            for v in visuals:
                state = self.envs.get(v.env)
                if state is None or state.error:
                    outcomes += fail(v, state.error if state else f"no environment {v.env}", True)
                    continue
                try:
                    outcomes += per_visual(v)
                except (OSError, ValueError, KeyError, subprocess.SubprocessError) as err:
                    # FR-012: one visual's unexpected failure never stops the others
                    outcomes += fail(v, f"unexpected error: {type(err).__name__}: {self.safe(str(err), v)}", False)
            return outcomes
        finally:
            # a second Ctrl-C or a SIGTERM after SIGINT must not cut the cleanup short (FR-008)
            for sig in previous:
                signal.signal(sig, signal.SIG_IGN)
            try:
                self.teardown()
                self.cleanup_scratch()
            finally:
                for sig, handler in previous.items():
                    signal.signal(sig, handler)

    def _failure_outcome(self, v: visualcfg.Visual, error: str, _environment: bool) -> list[Outcome]:
        """A failed capture outcome; a capture fails the same way whatever failed (FR-012)."""
        variant = v.outputs()[0][0] if v.outputs() else "default"
        # container logs and seed output may carry host values or credentials
        return [Outcome(v.name, variant, "failed", self.safe(error, v))]

    # per visual: capture paths

    def capture_visual(self, v: visualcfg.Visual) -> list[Outcome]:
        if v.kind == "cli":
            return [self.capture_cli(v)]
        return self.capture_web(v)

    def env_record(self, v: visualcfg.Visual) -> dict:
        """Provenance of the environment a visual was captured from (FR-017)."""
        env = self.recipe.environments[v.env]
        state = self.envs.get(v.env)
        record = {"name": env.name, "image": env.image, "digest": state.digest if state else "",
                  "platform": self.platform}
        if env.source:
            record["source"] = env.source
            record["source_commit"] = visualcfg.baseline_sources(self.root).get(env.source, "")
        return record

    def sidecar(self, v: visualcfg.Visual, variant: str, output_name: str, result: dict,
                variants: dict | None = None) -> dict:
        rules = self.recipe.rules(v)
        replacements = {r["id"]: 0 for r in rules}
        replacements.update({k: int(n) for k, n in (result.get("redaction") or {}).items() if k in replacements})
        return {
            "schema": 1, "name": v.name, "variant": variant, "kind": v.kind,
            "image": visualcfg.image_rel(self.root, output_name, v.extension),
            "environment": self.env_record(v),
            "fingerprint": visualcfg.fingerprint(self.recipe, v.name, self.root, capture_env=self.capture_env),
            "capture_env": self.capture_env, "captured_at": _now(),
            "redaction": {"rules": [r["id"] for r in rules], "disabled": list(v.disable_redaction),
                          "replacements": replacements},
            "masks": int(result.get("masks") or 0),
            "scripts": list(result.get("scripts") or []),
            **({"variants": variants} if variants is not None else {}),
            "highlights": list(result.get("highlights") or []),
            "style": result.get("style"),
            "text": result.get("text") or "",
        }

    def place(self, v: visualcfg.Visual, output_name: str, sidecar: dict) -> None:
        """Move the fresh image into the visual directory and write the sidecar (capture only)."""
        src = self.dir / "out" / f"{output_name}.{v.extension}"
        if src.is_symlink() or not src.is_file():
            raise ValueError(f"{src.name} from the capture container is not a regular file")
        dest = self.root / visualcfg.visual_dir(self.root) / f"{output_name}.{v.extension}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        src.unlink()
        visualcfg.dump_sidecar(visualcfg.sidecar_path(self.root, output_name), sidecar)

    def safe(self, text: str, v: visualcfg.Visual) -> str:
        """Console text with escapes stripped and host values redacted."""
        rules = redact.resolve(self.recipe.rules(v), self.values, run_subnet=self.subnet)
        return redact.apply(ANSI_RE.sub("", text).replace("\r", ""), rules, v.masks)[0]

    def run_cli(self, v: visualcfg.Visual) -> tuple[int, bytes]:
        """Run a CLI visual's command under a host pty in its environment's container (R4)."""
        state = self.envs[v.env]
        width = self.recipe.resolved(v)["width"]
        urls = self.url_vars()
        env_args = ["-e", f"COLUMNS={width}", "-e", "LINES=200", "-e", "TERM=xterm-256color"]
        for key, value in v.env_vars.items():
            env_args += ["-e", f"{key}={expand_url_vars(value, urls)}"]
        status, raw = self.podman.run_pty(["exec", "-t", *env_args, state.container, "sh", "-c", v.command],
                                          columns=width)
        # unredacted output: owner-only, deleted at teardown and swept after a crash (FR-021)
        raw_dir = self.dir / "raw"
        raw_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        raw_dir.chmod(0o700)
        path = raw_dir / f"{v.name}.bin"
        path.unlink(missing_ok=True)      # O_CREAT keeps the mode of an existing file
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
        return status, raw

    def render_cli(self, v: visualcfg.Visual) -> tuple[dict | None, str]:
        """runner.py cli in the capture container; (result, error)."""
        proc = self.pod(["exec", self.capture, "python3", RUNNER, "cli", "--job", "/work/job.json",
                         "--visual", v.name], timeout=T_EXEC)
        result_path = self.dir / "out" / f"{v.name}.result.json"
        result = json.loads(result_path.read_text()) if result_path.is_file() else None
        if proc.returncode != 0 or result is None or result.get("error"):
            reason = (result or {}).get("error") or tail((proc.stderr or "") + (proc.stdout or ""), 5)
            return None, self.safe(f"rendering failed: {reason}", v)
        return result, ""

    def capture_cli(self, v: visualcfg.Visual) -> Outcome:
        status, raw = self.run_cli(v)
        if status != v.exit:
            output = tail(self.safe(raw.decode("utf-8", "replace"), v), 10)
            return Outcome(v.name, "default", "failed",
                           f"command `{self.safe(v.command, v)}` exited {status}, expected {v.exit}:\n{output}",
                           selector=v.command)
        result, error = self.render_cli(v)
        if result is None:
            return Outcome(v.name, "default", "failed", error)
        self.place(v, v.name, self.sidecar(v, "default", v.name, result))
        return Outcome(v.name, "default", "captured", visualcfg.image_rel(self.root, v.name, "svg"))

    def run_web(self, v: visualcfg.Visual, variant: str) -> tuple[dict | None, Outcome | None]:
        """runner.py web for one variant; (result, None) or (None, failed outcome)."""
        stem = f"{v.name}-dark" if variant == "dark" else v.name
        timeout = (len(v.steps) + 4) * float(self.recipe.resolved(v)["timeout"]) + 180
        try:
            proc = self.podman.run(["exec", self.capture, "python3", RUNNER, "web", "--job", "/work/job.json",
                                    "--visual", v.name, "--variant", variant], timeout=timeout)
        except subprocess.TimeoutExpired:
            return None, Outcome(v.name, variant, "failed", f"capture did not finish within {int(timeout)}s")
        result_path = self.dir / "out" / f"{stem}.result.json"
        result = json.loads(result_path.read_text()) if result_path.is_file() else None
        if result is None or result.get("error") or proc.returncode != 0:
            if result and result.get("error"):
                detail = f"{result['error']} (debug image in {SCRATCH}/{self.run_id}/debug/)" \
                    if result.get("step") else result["error"]
            else:
                detail = f"web capture failed: {tail((proc.stderr or '') + (proc.stdout or ''), 5)}"
            return None, Outcome(v.name, variant, "failed", self.safe(detail, v),
                                 step=(result or {}).get("step"), selector=(result or {}).get("selector"))
        return result, None

    def image_diff(self, a: str, b: str, tolerance: int) -> float | None:
        """runner.py diff on two files under the run directory (paths relative to it)."""
        proc = self.pod(["exec", self.capture, "python3", RUNNER, "diff", f"/work/{a}", f"/work/{b}",
                         "--tolerance", str(tolerance)], timeout=T_EXEC)
        try:
            return float(json.loads(proc.stdout or "{}")["diff"])
        except (ValueError, KeyError, TypeError):
            return None

    def dark_equals_light(self, v: visualcfg.Visual, light: dict, dark: dict) -> bool:
        """FR-037: the tool ignored the color scheme (same text, image difference below threshold)."""
        if light.get("text") != dark.get("text") or light.get("highlights") != dark.get("highlights"):
            return False
        resolved = self.recipe.resolved(v)
        diff = self.image_diff(f"out/{v.name}.png", f"out/{v.name}-dark.png", resolved["tolerance"])
        return diff is not None and diff <= float(resolved["threshold"])

    def capture_web(self, v: visualcfg.Visual) -> list[Outcome]:
        results: dict[str, dict] = {}
        failures: list[Outcome] = []
        for variant, _stem in v.outputs():
            result, failure = self.run_web(v, variant)
            if failure is not None:
                failures.append(failure)
            else:
                results[variant] = result
        if failures:
            # FR-012: a failed visual leaves its committed files untouched, all variants alike
            return failures
        outcomes = []
        if "light" in results and "dark" in results:
            same = self.dark_equals_light(v, results["light"], results["dark"])
            self.place(v, v.name, self.sidecar(v, "light", v.name, results["light"],
                                               variants={"dark": "skipped" if same else "captured"}))
            outcomes.append(Outcome(v.name, "light", "captured", visualcfg.image_rel(self.root, v.name, "png")))
            if same:
                for stale in (self.root / visualcfg.visual_dir(self.root) / f"{v.name}-dark.png",
                              visualcfg.sidecar_path(self.root, f"{v.name}-dark")):
                    stale.unlink(missing_ok=True)
                outcomes.append(Outcome(v.name, "dark", "skipped", "same as light: the tool ignores the color scheme"))
            else:
                self.place(v, f"{v.name}-dark", self.sidecar(v, "dark", f"{v.name}-dark", results["dark"]))
                outcomes.append(Outcome(v.name, "dark", "captured",
                                        visualcfg.image_rel(self.root, f"{v.name}-dark", "png")))
            return outcomes
        for variant, stem in v.outputs():
            self.place(v, stem, self.sidecar(v, variant, stem, results[variant]))
            outcomes.append(Outcome(v.name, variant, "captured", visualcfg.image_rel(self.root, stem, "png")))
        return outcomes


# --- visual drift (FR-027 to FR-030) -------------------------------------------


def comparable_lines(sidecar: dict | None) -> list[str]:
    """The lines drift compares: the text content and the highlights, never provenance."""
    if not sidecar:
        return []
    lines = str(sidecar.get("text") or "").splitlines()
    for h in sidecar.get("highlights") or []:
        lines.append(f"highlight {h.get('label')}: {h.get('selector')} = {h.get('text')}")
    return lines


def text_diff(before: dict | None, after: dict | None) -> list[str]:
    a, b = comparable_lines(before), comparable_lines(after)
    if a == b:
        return []
    return [line for line in difflib.unified_diff(a, b, lineterm="", n=0)
            if not line.startswith(("---", "+++", "@@"))]


def guide_text(root: Path, page: Path) -> str:
    """The page text check.py reads: only the guide region of a marked front page."""
    import guidecfg
    import region

    text = page.read_text(errors="replace")
    front = guidecfg.embedded_front_page(root)
    if front is not None and page.resolve() == front.resolve():
        try:
            parsed = region.parse(text)
        except region.RegionError:
            return text
        if parsed.marked:
            return parsed.content
    return text


def citing_pages(root: Path) -> dict[str, list[str]]:
    """visual:<name> citations in page source blocks: name (and <name>-dark) -> pages."""
    import guidecfg
    import sources

    try:
        adapter = guidecfg.load_adapter(root, required=False)
    except guidecfg.ConfigError:
        adapter = None
    if adapter is None:
        return {}
    style = "line" if adapter.comment == "line" else "html"
    found: dict[str, list[str]] = {}
    for page in guidecfg.pages(root, adapter, "all"):
        block = sources.find_block(guide_text(root, page), style)
        for ref in (block.refs if block else []):
            if ref.kind == "visual":
                # relpath: an embedded guide's front page prints as ../README.md
                rel = Path(os.path.relpath(page.resolve(), Path(root).resolve())).as_posix()
                found.setdefault(ref.visual, [])
                if rel not in found[ref.visual]:
                    found[ref.visual].append(rel)
    return found


class DriftRun(Run):
    """Recapture into the run directory and compare with the committed visuals; never place."""

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.pages: dict[str, list[str]] = {}

    def pages_of(self, v: visualcfg.Visual, stem: str) -> list[str]:
        return sorted(set(self.pages.get(v.name, []) + self.pages.get(stem, [])))

    def before(self, sidecar: dict | None) -> dict:
        env = (sidecar or {}).get("environment") or {}
        return {k: env.get(k, "") for k in ("image", "digest", "platform")}

    def after(self, v: visualcfg.Visual) -> dict:
        env = self.env_record(v)
        return {k: env.get(k, "") for k in ("image", "digest", "platform")}

    def failure(self, v: visualcfg.Visual, error: str, environment: bool) -> list[DriftResult]:
        status = "environment-failed" if environment else "recapture-failed"
        return [DriftResult(v.name, variant, status, pages=self.pages_of(v, stem), detail=self.safe(error, v),
                            image_before=self.before(visualcfg.load_sidecar_safe(visualcfg.sidecar_path(self.root, stem))))
                for variant, stem in v.outputs()]

    def committed_diff(self, v: visualcfg.Visual, stem: str) -> float | None:
        """Copy the committed PNG next to the fresh one and diff them in the capture container."""
        committed = self.root / visualcfg.visual_dir(self.root) / f"{stem}.png"
        if not committed.is_file():
            return 100.0
        (self.dir / "committed").mkdir(parents=True, exist_ok=True)
        shutil.copy(committed, self.dir / "committed" / f"{stem}.png")
        return self.image_diff(f"committed/{stem}.png", f"out/{stem}.png", self.recipe.resolved(v)["tolerance"])

    def compare(self, v: visualcfg.Visual, variant: str, stem: str, fresh: dict) -> DriftResult:
        side = visualcfg.load_sidecar_safe(visualcfg.sidecar_path(self.root, stem))
        result = DriftResult(v.name, variant, "unchanged", pages=self.pages_of(v, stem),
                             image_before=self.before(side), image_after=self.after(v))
        if side is None or side.get("placeholder"):
            result.status = "drifted"
            result.detail = "no committed capture" if side is None else "placeholder, never captured"
            result.text_diff = text_diff(None, fresh)
            return result
        result.text_diff = text_diff(side, fresh)
        if v.kind == "cli":
            result.style_changed = side.get("style") != fresh.get("style")
            drifted = bool(result.text_diff) or result.style_changed
        else:
            result.platform_mismatch = bool(side.get("environment", {}).get("platform")) and \
                side["environment"]["platform"] != self.platform
            result.image_diff = self.committed_diff(v, stem)
            if result.image_diff is None:
                # a failed comparison must not pass as "unchanged" (FR-027)
                result.status = "recapture-failed"
                result.detail = "image comparison failed: the committed and the fresh image could not be compared"
                return result
            over = result.image_diff > float(self.recipe.resolved(v)["threshold"])
            drifted = bool(result.text_diff) or (over and not result.platform_mismatch)
            if over and result.platform_mismatch:
                result.detail = (f"image difference reported only: captured on {side['environment']['platform']}, "
                                 f"compared on {self.platform}")
        result.status = "drifted" if drifted else "unchanged"
        return result

    def drift_visual(self, v: visualcfg.Visual) -> list[DriftResult]:
        if v.kind == "cli":
            status, raw = self.run_cli(v)
            if status != v.exit:
                return [DriftResult(v.name, "default", "recapture-failed", pages=self.pages_of(v, v.name),
                                    selector=self.safe(v.command, v), image_after=self.after(v),
                                    image_before=self.before(visualcfg.load_sidecar_safe(
                                        visualcfg.sidecar_path(self.root, v.name))),
                                    detail=f"command exited {status}, expected {v.exit}")]
            fresh, error = self.render_cli(v)
            if fresh is None:
                return self.failure(v, error, False)
            return [self.compare(v, "default", v.name, fresh)]
        fresh: dict[str, dict] = {}
        results: list[DriftResult] = []
        for variant, stem in v.outputs():
            result, failure = self.run_web(v, variant)
            if failure is not None:
                results.append(DriftResult(v.name, variant, "recapture-failed", pages=self.pages_of(v, stem),
                                           step=failure.step, selector=failure.selector, detail=failure.detail,
                                           image_after=self.after(v), image_before=self.before(
                                               visualcfg.load_sidecar_safe(visualcfg.sidecar_path(self.root, stem)))))
            else:
                fresh[variant] = result
        light = visualcfg.load_sidecar_safe(visualcfg.sidecar_path(self.root, v.name))
        dark_skipped = bool(light) and (light.get("variants") or {}).get("dark") == "skipped"
        for variant, stem in v.outputs():
            if variant not in fresh:
                continue
            if variant == "dark" and dark_skipped:
                result = DriftResult(v.name, "dark", "unchanged", pages=self.pages_of(v, stem),
                                     image_before=self.before(light), image_after=self.after(v))
                if "light" in fresh and not self.dark_equals_light(v, fresh["light"], fresh["dark"]):
                    result.status = "drifted"
                    result.detail = "the dark variant was skipped, but the tool now renders a different dark theme"
                results.append(result)
                continue
            results.append(self.compare(v, variant, stem, fresh[variant]))
        return results


def drift_markdown(results: list[DriftResult], run: Run) -> str:
    changed = [r for r in results if r.status != "unchanged"]
    out = ["# Visual drift report", ""]
    if not changed:
        out += [f"Run `{run.run_id}` on {run.platform}. No visual drift.", ""]
    else:
        names = sorted({r.name for r in changed if r.status in ("drifted", "recapture-failed")})
        verdict = (f"Visual drift found: recapture with `make visuals VISUALS=\"{' '.join(names)}\"` "
                   "or run `/guide:evolve`." if names else "Environments failed; nothing was compared.")
        out += [f"Run `{run.run_id}` on {run.platform}. {verdict}", ""]
    for r in changed:
        label = r.name if r.variant in ("default", "light") else f"{r.name} ({r.variant})"
        out += [f"## `{label}`", ""]
        diff = "n/a" if r.image_diff is None else f"{r.image_diff:g}%"
        out.append(f"Status: **{r.status}**. Image difference: {diff}.")
        if r.style_changed:
            out.append("The colors or text styles changed.")
        if r.platform_mismatch:
            out.append("Captured on another platform than this run; the image difference alone is not drift.")
        if r.step:
            out.append(f"Failed at step {r.step}" + (f" (`{r.selector}`)." if r.selector else "."))
        elif r.selector:
            out.append(f"Command: `{r.selector}`.")
        if r.detail:
            out.append(r.detail)
        out.append("Pages: " + (", ".join(f"`{p}`" for p in r.pages) if r.pages else "none cite it") + ".")
        b, a = r.image_before, r.image_after
        if b or a:
            out.append(f"Environment before: `{b.get('image', '')}` `{b.get('digest', '')}` {b.get('platform', '')}; "
                       f"after: `{a.get('image', '')}` `{a.get('digest', '')}` {a.get('platform', '')}.")
        if r.text_diff:
            out += ["", "Changed sidecar lines:", "", "```diff", *r.text_diff, "```"]
        out.append("")
    unchanged = [r for r in results if r.status == "unchanged"]
    if unchanged:
        out += ["## Unchanged", "", ", ".join(f"`{r.name}`" + ("" if r.variant in ("default", "light")
                                                            else f" ({r.variant})") for r in unchanged), ""]
    return "\n".join(out)


def drift_exit(results: list[DriftResult]) -> int:
    if any(r.status == "environment-failed" for r in results):
        return EXIT_CONFIG
    if any(r.status in ("drifted", "recapture-failed") for r in results):
        return EXIT_DRIFT
    return EXIT_OK


def _json_list(proc: subprocess.CompletedProcess) -> list[dict]:
    if proc.returncode != 0:
        return []
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return []
    return [d for d in data if isinstance(d, dict)] if isinstance(data, list) else []


# --- commands -----------------------------------------------------------------


def _interrupted(run: Run) -> str:
    if run.leftovers:
        return ("interrupted: could not remove " + ", ".join(run.leftovers)
                + " (remove them with podman rm -f and podman network rm)")
    return "interrupted: every container and the network of the run were removed"


def _load(root: Path, out: Callable[[str], None]) -> visualcfg.Recipe | None:
    """The recipe, or None after printing "no visuals declared". ConfigError on problems."""
    try:
        recipe = visualcfg.load_recipe(root)
    except visualcfg.RecipeError as err:
        raise ConfigError(str(err)) from None
    if recipe is None:
        out("no visuals declared")
        return None
    problems = visualcfg.validate(root)
    if problems:
        raise ConfigError("\n".join(problems))
    return recipe


def select_visuals(recipe: visualcfg.Recipe, names: list[str]) -> list[visualcfg.Visual]:
    if not names:
        return list(recipe.visuals.values())
    chosen: list[visualcfg.Visual] = []
    for name in names:
        ref = recipe.resolve_ref(name)
        if ref is None:
            raise ConfigError(f"no visual {name!r} in visuals.yaml")
        v = recipe.visuals[ref[0]]
        if v not in chosen:
            chosen.append(v)
    return chosen


def cmd_validate(root: Path, out: Callable[[str], None] = print) -> int:
    try:
        recipe = visualcfg.load_recipe(root)
    except visualcfg.RecipeError as err:
        out(str(err))
        return EXIT_FAILED
    if recipe is None:
        out("no visuals declared")
        return EXIT_OK
    problems = visualcfg.validate(root)
    for p in problems:
        out(p)
    if problems:
        return EXIT_FAILED
    out(f"visuals.yaml: {len(recipe.visuals)} visuals, {len(recipe.environments)} environments, no problems")
    return EXIT_OK


def cmd_capture(root: Path, names: list[str], podman: Podman | None = None,
                out: Callable[[str], None] = print, **run_kw) -> int:
    try:
        recipe = _load(root, out)
        if recipe is None:
            return EXIT_OK
        visuals = select_visuals(recipe, names)
        run = Run(root, podman, **run_kw)
        run.recipe = recipe
        run.check_podman()
        run.acquire_lock()
    except ConfigError as err:
        out(f"error: {err}")
        return EXIT_CONFIG
    try:
        run.sweep()
        outcomes = run.execute(visuals, run.capture_visual)
    except KeyboardInterrupt:
        out(_interrupted(run))
        return EXIT_FAILED
    finally:
        run.release_lock()
    for o in outcomes:
        out(o.line())
    report = "\n".join(o.line() for o in outcomes) + "\n"
    run.dir.mkdir(parents=True, exist_ok=True)
    (run.dir / "report.md").write_text(report)
    return EXIT_FAILED if any(o.status == "failed" for o in outcomes) else EXIT_OK


def cmd_drift(root: Path, names: list[str], fmt: str = "markdown", podman: Podman | None = None,
              out: Callable[[str], None] = print, **run_kw) -> int:
    """Recapture into .guide/visuals/<run-id>/ and compare; committed files stay untouched (FR-030)."""
    # with --format json, stdout carries the JSON document only; messages go to stderr
    note = out if fmt != "json" else (lambda line: print(line, file=sys.stderr))
    try:
        recipe = _load(root, note)
        if recipe is None:
            if fmt == "json":
                out(json.dumps({"run_id": None, "platform": "", "has_drift": False, "visuals": []}, indent=2))
            return EXIT_OK
        visuals = select_visuals(recipe, names)
        run = DriftRun(root, podman, **run_kw)
        run.recipe = recipe
        run.check_podman()
        run.acquire_lock()
    except ConfigError as err:
        note(f"error: {err}")
        return EXIT_CONFIG
    try:
        run.pages = citing_pages(run.root)
        run.sweep()
        results = run.execute(visuals, run.drift_visual, on_failure=run.failure)
    except KeyboardInterrupt:
        out(_interrupted(run))
        return EXIT_CONFIG
    finally:
        run.release_lock()
    report = {"run_id": run.run_id, "platform": run.platform,
              "has_drift": any(r.status in ("drifted", "recapture-failed") for r in results),
              "visuals": [r.to_dict() for r in results]}
    markdown = drift_markdown(results, run)
    run.dir.mkdir(parents=True, exist_ok=True)
    (run.dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (run.dir / "report.md").write_text(markdown + "\n")
    out(json.dumps(report, indent=2) if fmt == "json" else markdown)
    return drift_exit(results)


def cmd_init(root: Path, out: Callable[[str], None] = print, template: Path | None = None) -> int:
    """Add visuals to an existing guide (FR-034): visuals.yaml from the template and visuals/."""
    root = Path(root)
    if not (root / "tools" / "guide" / "adapter.yaml").is_file():
        out("error: no tools/guide/adapter.yaml: run this in a guide project with an installed toolkit")
        return EXIT_FAILED
    created = []
    recipe = visualcfg.recipe_path(root)
    if not recipe.exists():
        # tools/guide/templates/visuals.yaml, copied by the scaffold script
        template = Path(template or visualcfg.TOOLKIT_DIR / "templates" / "visuals.yaml")
        if not template.is_file():
            out(f"error: {template} is missing; refresh the toolkit first")
            return EXIT_FAILED
        shutil.copy(template, recipe)
        created.append("visuals.yaml")
    keep = root / visualcfg.SIDECAR_DIR / ".gitkeep"
    if not keep.exists():
        keep.parent.mkdir(parents=True, exist_ok=True)
        keep.write_text("")
        created.append(f"{visualcfg.SIDECAR_DIR}/.gitkeep")
    out(("created " + ", ".join(created)) if created else "visuals already set up; nothing to do")
    return EXIT_OK


def cmd_placeholder(root: Path, names: list[str], out: Callable[[str], None] = print) -> int:
    """Placeholder sidecars for declared visuals that are not captured yet (FR-031a)."""
    root = Path(root)
    try:
        recipe = _load(root, out)
    except ConfigError as err:
        out(f"error: {err}")
        return EXIT_FAILED
    if recipe is None:
        return EXIT_FAILED
    try:
        chosen = select_visuals(recipe, names)
    except ConfigError as err:
        out(f"error: {err}")
        return EXIT_FAILED
    for v in chosen:
        for variant, stem in v.outputs():
            path = visualcfg.sidecar_path(root, stem)
            existing = visualcfg.load_sidecar_safe(path)
            if existing is not None and not existing.get("placeholder"):
                out(f"kept      {stem}  already captured")
                continue
            visualcfg.dump_sidecar(path, visualcfg.placeholder_sidecar(recipe, v.name, variant, stem, root))
            out(f"placeholder {stem}  {visualcfg.SIDECAR_DIR}/{path.name}")
    return EXIT_OK


def cmd_version(out: Callable[[str], None] = print) -> int:
    out(visualcfg.capture_env_version())
    return EXIT_OK


def main(argv: list[str] | None = None, podman: Podman | None = None) -> int:
    parser = argparse.ArgumentParser(description="Captured visuals for a cc-guide guide project")
    parser.add_argument("--root", type=Path, default=Path("."))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    p = sub.add_parser("capture")
    p.add_argument("names", nargs="*")
    p = sub.add_parser("drift")
    p.add_argument("names", nargs="*")
    p.add_argument("--format", choices=("markdown", "json"), default="markdown")
    sub.add_parser("init")
    p = sub.add_parser("placeholder")
    p.add_argument("names", nargs="+")
    sub.add_parser("version")
    args = parser.parse_args(argv)
    if args.command == "validate":
        return cmd_validate(args.root)
    if args.command == "capture":
        return cmd_capture(args.root, args.names, podman)
    if args.command == "drift":
        return cmd_drift(args.root, args.names, args.format, podman)
    if args.command == "init":
        return cmd_init(args.root)
    if args.command == "placeholder":
        return cmd_placeholder(args.root, args.names)
    return cmd_version()


if __name__ == "__main__":
    sys.exit(main())
