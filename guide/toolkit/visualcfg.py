#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Capture recipe (visuals.yaml), fingerprints, and sidecars for captured visuals.

specs/008-captured-visuals: shared by visuals.py (capture, drift), check.py (the
`visuals` rule family), and drift.py (affected visuals). Nothing here starts a
container or calls podman (FR-024).

    recipe = load_recipe(root)          # None when the guide has no visuals.yaml
    problems = validate(root)           # ["visuals.yaml: <path>: <message>", ...]
    fingerprint(recipe, name, root)     # 16 hex over everything that shapes a visual (R11)
    capture_env_version()               # 12 hex over tools/guide/capture/ (R3)
    load_sidecar(path), dump_sidecar(path, data)

Steps and seed steps are numbered from 1, like the run's own messages ("step 2",
"seed step 1"): `visuals.x.step 1`, `environments.e.seed step 1.run`. Other lists
use zero-based indexes (`visuals.x.masks[0]`), like guidecfg.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

TOOLKIT_DIR = Path(__file__).resolve().parent
CAPTURE_DIR = TOOLKIT_DIR / "capture"
if str(CAPTURE_DIR) not in sys.path:
    sys.path.insert(0, str(CAPTURE_DIR))
import redact  # noqa: E402  (tools/guide/capture/redact.py, inside the toolkit)

RECIPE = "visuals.yaml"
SIDECAR_DIR = "visuals"
SIDECAR_SUFFIX = ".visual.yaml"
ENV_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,30}$")
VISUAL_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,62}$")
RULE_ID_RE = re.compile(r"^[a-z][a-z0-9-]*$")
ROLE_RE = re.compile(r"^role=([a-z]+)(?:\[name=(.+)\])?$")
RESERVED_SOURCES = ("self", "visual")
DEFAULTS: dict[str, Any] = {
    "width": 100, "prompt": "$ ", "viewport": {"width": 1280, "height": 800},
    "timeout": 15, "tolerance": 16, "threshold": 0.5,
}
DEFAULT_VISUAL_DIRS = {"antora": "content/modules/ROOT/images/visuals"}
FALLBACK_VISUAL_DIR = "docs/assets/visuals"

TOP_KEYS = {"schema", "defaults", "redaction", "environments", "visuals"}
ENV_KEYS = {"kind", "image", "source", "env", "command", "seed"}
WEB_ENV_KEYS = ENV_KEYS | {"port", "ready", "ready_timeout"}
SEED_KEYS = {"run", "in", "files"}
VISUAL_KEYS = {"kind", "env", "masks", "disable_redaction"}
WEB_VISUAL_KEYS = VISUAL_KEYS | {"steps", "viewport", "variants", "threshold"}
CLI_VISUAL_KEYS = VISUAL_KEYS | {"command", "exit", "width", "prompt", "env_vars"}
SELECTOR_STEPS = ("click", "wait", "crop", "hide")
STEP_KINDS = ("goto", "click", "fill", "press", "wait", "highlight", "crop", "hide", "script")
SIDECAR_KEYS = ("schema", "name", "variant", "kind", "image", "environment", "fingerprint", "capture_env",
                "captured_at", "redaction", "masks", "scripts", "variants", "highlights", "style", "placeholder", "text")
ENVIRONMENT_KEYS = ("name", "image", "digest", "platform", "source", "source_commit")


class RecipeError(Exception):
    """visuals.yaml cannot be read at all (syntax error, duplicate key)."""


# --- YAML loading -------------------------------------------------------------


class _UniqueKeyLoader(yaml.SafeLoader):
    """A safe loader that rejects duplicate mapping keys (a visual declared twice)."""


def _construct_mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    seen: dict[Any, int] = {}
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate key {key!r} (first on line {seen[key] + 1})", key_node.start_mark)
        seen[key] = key_node.start_mark.line
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def _read_recipe(path: Path) -> Any:
    try:
        return yaml.load(path.read_text(), Loader=_UniqueKeyLoader)   # noqa: S506 (safe loader subclass)
    except yaml.YAMLError as err:
        raise RecipeError(f"{RECIPE}: invalid YAML: {err}".replace("\n", " ")) from None


# --- model --------------------------------------------------------------------


@dataclass
class SeedStep:
    run: str
    in_: str = "tool"
    files: list[str] = field(default_factory=list)


@dataclass
class Environment:
    name: str
    kind: str
    image: str
    source: str | None = None
    port: int | None = None
    ready: str = "/"
    ready_timeout: float = 120
    env: dict[str, str] = field(default_factory=dict)
    command: list[str] | None = None
    seed: list[SeedStep] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    @property
    def url(self) -> str | None:
        return f"http://{self.name}:{self.port}" if self.kind == "web" and self.port else None


@dataclass
class Visual:
    name: str
    kind: str
    env: str
    steps: list[dict] = field(default_factory=list)
    viewport: dict | None = None
    variants: list[str] = field(default_factory=list)
    command: str | None = None
    exit: int = 0
    width: int | None = None
    prompt: str | None = None
    env_vars: dict[str, str] = field(default_factory=dict)
    masks: list[dict] = field(default_factory=list)
    disable_redaction: list[str] = field(default_factory=list)
    threshold: float | None = None
    raw: dict = field(default_factory=dict)

    def outputs(self) -> list[tuple[str, str]]:
        """(variant, output name) pairs: default, light (<name>), dark (<name>-dark)."""
        if not self.variants:
            return [("default", self.name)]
        out = []
        if "light" in self.variants:
            out.append(("light", self.name))
        if "dark" in self.variants:
            out.append(("dark", f"{self.name}-dark"))
        return out

    @property
    def extension(self) -> str:
        return "svg" if self.kind == "cli" else "png"

    @property
    def scripts(self) -> list[str]:
        return [str(s["script"]) for s in self.steps if isinstance(s, dict) and "script" in s]


@dataclass
class Recipe:
    root: Path
    defaults: dict[str, Any]
    redaction_rules: list[dict]
    environments: dict[str, Environment]
    visuals: dict[str, Visual]

    def environment(self, visual: Visual) -> Environment | None:
        return self.environments.get(visual.env)

    def rules(self, visual: Visual) -> list[dict]:
        """Effective redaction rules (templates only) of a visual."""
        return redact.effective_rules(self.redaction_rules, visual.disable_redaction)

    def resolved(self, visual: Visual) -> dict[str, Any]:
        """The defaults that apply to a visual, with its own overrides."""
        d = self.defaults
        if visual.kind == "cli":
            return {"width": visual.width or d["width"],
                    "prompt": visual.prompt if visual.prompt is not None else d["prompt"]}
        return {"viewport": visual.viewport or d["viewport"], "timeout": d["timeout"],
                "tolerance": d["tolerance"],
                "threshold": visual.threshold if visual.threshold is not None else d["threshold"]}

    def resolve_ref(self, name: str) -> tuple[str, str] | None:
        """visual:<name> -> (visual name, variant); `<x>-dark` maps to <x> when it declares dark."""
        if name.endswith("-dark"):
            base = name[: -len("-dark")]
            v = self.visuals.get(base)
            if v is not None and "dark" in v.variants:
                return base, "dark"
        v = self.visuals.get(name)
        if v is None:
            return None
        return name, (v.outputs()[0][0] if v.outputs() else "default")

    def visuals_for_source(self, source_id: str) -> list[str]:
        envs = {e.name for e in self.environments.values() if e.source == source_id}
        return sorted(v.name for v in self.visuals.values() if v.env in envs)


# --- loading ------------------------------------------------------------------


def recipe_path(root: Path) -> Path:
    return Path(root) / RECIPE


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _str_map(value: Any) -> dict[str, str]:
    return {str(k): str(v) for k, v in _as_dict(value).items()}


def _build(root: Path, data: dict) -> Recipe:
    defaults = dict(DEFAULTS)
    for key, value in _as_dict(data.get("defaults")).items():
        if key in defaults and value is not None:
            defaults[key] = value
    rules = [r for r in _as_list(_as_dict(data.get("redaction")).get("rules"))
             if isinstance(r, dict) and {"id", "pattern", "replacement"} <= set(r)]
    envs: dict[str, Environment] = {}
    for name, raw in _as_dict(data.get("environments")).items():
        raw = _as_dict(raw)
        seed = []
        for s in _as_list(raw.get("seed")):
            s = _as_dict(s)
            seed.append(SeedStep(str(s.get("run", "")), str(s.get("in", "tool")),
                                 [str(f) for f in _as_list(s.get("files"))]))
        command = raw.get("command")
        envs[str(name)] = Environment(
            name=str(name), kind=str(raw.get("kind", "")), image=str(raw.get("image", "")),
            source=raw.get("source"), port=raw.get("port") if isinstance(raw.get("port"), int) else None,
            ready=str(raw.get("ready", "/")),
            ready_timeout=raw.get("ready_timeout", 120) if isinstance(raw.get("ready_timeout"), (int, float)) else 120,
            env=_str_map(raw.get("env")),
            command=[str(c) for c in command] if isinstance(command, list) else None,
            seed=seed, raw=raw)
    visuals: dict[str, Visual] = {}
    for name, raw in _as_dict(data.get("visuals")).items():
        raw = _as_dict(raw)
        width = raw.get("width")
        threshold = raw.get("threshold")
        visuals[str(name)] = Visual(
            name=str(name), kind=str(raw.get("kind", "")), env=str(raw.get("env", "")),
            steps=[s for s in _as_list(raw.get("steps")) if isinstance(s, dict)],
            viewport=raw.get("viewport") if isinstance(raw.get("viewport"), dict) else None,
            variants=[str(v) for v in _as_list(raw.get("variants"))],
            command=str(raw["command"]) if raw.get("command") is not None else None,
            exit=raw.get("exit", 0) if isinstance(raw.get("exit", 0), int) else 0,
            width=width if isinstance(width, int) else None,
            prompt=str(raw["prompt"]) if raw.get("prompt") is not None else None,
            env_vars=_str_map(raw.get("env_vars")),
            masks=[m for m in _as_list(raw.get("masks")) if isinstance(m, dict)],
            disable_redaction=[str(r) for r in _as_list(raw.get("disable_redaction"))],
            threshold=threshold if isinstance(threshold, (int, float)) and not isinstance(threshold, bool) else None,
            raw=raw)
    return Recipe(Path(root), defaults, rules, envs, visuals)


def load_recipe(root: Path) -> Recipe | None:
    """The guide's recipe, or None without visuals.yaml. RecipeError on unreadable YAML.

    Loading is lenient (values of the wrong type fall back to defaults); validate()
    reports every problem.
    """
    path = recipe_path(root)
    if not path.is_file():
        return None
    data = _read_recipe(path)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise RecipeError(f"{RECIPE}: must be a mapping")
    return _build(Path(root), data)


# --- validation ---------------------------------------------------------------


def baseline_sources(root: Path) -> dict[str, str]:
    """Source id -> pinned commit from baseline.yaml (lenient; {} when missing)."""
    path = Path(root) / "baseline.yaml"
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError:
        return {}
    out = {}
    for s in _as_list(_as_dict(data).get("sources")):
        if isinstance(s, dict) and s.get("id"):
            out[str(s["id"])] = str(s.get("commit") or "")
    return out


class _Problems:
    def __init__(self) -> None:
        self.items: list[str] = []

    def add(self, path: str, message: str) -> None:
        self.items.append(f"{RECIPE}: {path}: {message}")

    def keys(self, value: dict, path: str, allowed: set[str]) -> None:
        for k in value:
            if k not in allowed:
                self.add(f"{path}.{k}", "unknown key")


def _image_ok(image: str) -> str | None:
    """None when the reference names a tag or digest, else the problem."""
    if "@sha256:" in image:
        return None
    last = image.rsplit("/", 1)[-1]
    if ":" not in last:
        return f"image {image!r} needs a tag or digest (FR-003)"
    if last.rsplit(":", 1)[1] in ("", "latest"):
        return f"image {image!r} must not use the latest tag (FR-003)"
    return None


def _selector_ok(sel: Any) -> str | None:
    if not isinstance(sel, str) or not sel.strip():
        return "selector must be a non-empty string"
    if sel.startswith("role=") and not ROLE_RE.match(sel):
        return f"selector {sel!r} must be role=<role> or role=<role>[name=<name>]"
    if sel.startswith("text=") and len(sel) == len("text="):
        return "text= selector needs a text"
    return None


def _visual_file(root: Path, rel: Any, path: str, p: _Problems, what: str) -> None:
    if not isinstance(rel, str) or not rel:
        p.add(path, f"{what} must be a path under visuals/")
        return
    candidate = Path(rel)
    if candidate.is_absolute() or ".." in candidate.parts:
        p.add(path, f"{what} {rel!r} must be a relative path inside visuals/")
        return
    if not (Path(root) / SIDECAR_DIR / candidate).is_file():
        p.add(path, f"{what} visuals/{rel} does not exist")


def _check_regex(pattern: Any, path: str, p: _Problems) -> None:
    if not isinstance(pattern, str) or not pattern:
        p.add(path, "pattern must be a non-empty regular expression")
        return
    try:
        re.compile(pattern)
    except re.error as err:
        p.add(path, f"pattern is not a valid regular expression: {err}")


def _check_masks(value: Any, path: str, p: _Problems) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        p.add(path, "must be a list of {pattern, replacement}")
        return
    for i, m in enumerate(value):
        mp = f"{path}[{i}]"
        if not isinstance(m, dict):
            p.add(mp, "must be a mapping with pattern and replacement")
            continue
        p.keys(m, mp, {"pattern", "replacement"})
        _check_regex(m.get("pattern"), f"{mp}.pattern", p)
        if not isinstance(m.get("replacement"), str):
            p.add(f"{mp}.replacement", "required string")


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_viewport(value: Any, path: str, p: _Problems) -> None:
    if not isinstance(value, dict) or set(value) != {"width", "height"} or not all(
            isinstance(value[k], int) and not isinstance(value[k], bool) and value[k] > 0 for k in value):
        p.add(path, "must be {width: <pixels>, height: <pixels>}")


def _check_defaults(value: Any, p: _Problems) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        p.add("defaults", "must be a mapping")
        return
    p.keys(value, "defaults", set(DEFAULTS))
    if "width" in value and not (isinstance(value["width"], int) and 20 <= value["width"] <= 300):
        p.add("defaults.width", "must be an integer from 20 to 300")
    if "prompt" in value and not isinstance(value["prompt"], str):
        p.add("defaults.prompt", "must be a string")
    if "viewport" in value:
        _check_viewport(value["viewport"], "defaults.viewport", p)
    if "timeout" in value and not (_number(value["timeout"]) and value["timeout"] > 0):
        p.add("defaults.timeout", "must be a positive number of seconds")
    if "tolerance" in value and not (isinstance(value["tolerance"], int) and 0 <= value["tolerance"] <= 255):
        p.add("defaults.tolerance", "must be an integer from 0 to 255")
    if "threshold" in value and not (_number(value["threshold"]) and 0 <= value["threshold"] <= 100):
        p.add("defaults.threshold", "must be a percentage from 0 to 100")


def _check_redaction(value: Any, p: _Problems) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        p.add("redaction", "must be a mapping")
        return
    p.keys(value, "redaction", {"rules"})
    rules = value.get("rules")
    if rules is None:
        return
    if not isinstance(rules, list):
        p.add("redaction.rules", "must be a list of {id, pattern, replacement}")
        return
    seen: set[str] = set()
    for i, r in enumerate(rules):
        rp = f"redaction.rules[{i}]"
        if not isinstance(r, dict):
            p.add(rp, "must be a mapping with id, pattern, and replacement")
            continue
        p.keys(r, rp, {"id", "pattern", "replacement"})
        rid = r.get("id")
        if not isinstance(rid, str) or not RULE_ID_RE.match(rid):
            p.add(f"{rp}.id", f"must be a lowercase id (got {rid!r})")
        elif rid in redact.DEFAULT_IDS:
            p.add(f"{rp}.id", f"{rid!r} is a default rule id; choose another id")
        elif rid in seen:
            p.add(f"{rp}.id", f"duplicate rule id {rid!r}")
        else:
            seen.add(rid)
        _check_regex(r.get("pattern"), f"{rp}.pattern", p)
        if not isinstance(r.get("replacement"), str):
            p.add(f"{rp}.replacement", "required string")


def _check_environment(root: Path, name: Any, env: Any, sources: dict[str, str], p: _Problems) -> None:
    path = f"environments.{name}"
    if not isinstance(name, str) or not ENV_NAME_RE.match(name):
        p.add(path, "environment names must be host names: lower case letters, digits, and -, "
                    "starting with a letter, at most 31 characters")
    if not isinstance(env, dict):
        p.add(path, "must be a mapping")
        return
    kind = env.get("kind")
    if kind == "kind-cluster":
        p.add(f"{path}.kind", "kind-cluster environments are not supported yet")
        return
    if kind not in ("web", "cli"):
        p.add(f"{path}.kind", f"must be web or cli (got {kind!r})")
        return
    p.keys(env, path, WEB_ENV_KEYS if kind == "web" else ENV_KEYS)
    image = env.get("image")
    if not isinstance(image, str) or not image:
        p.add(f"{path}.image", "required image reference with a tag or digest")
    else:
        problem = _image_ok(image)
        if problem:
            p.add(f"{path}.image", problem)
    source = env.get("source")
    if source is not None:
        if source in RESERVED_SOURCES:
            p.add(f"{path}.source", f"{source!r} is a reserved source id")
        elif not isinstance(source, str) or source not in sources:
            p.add(f"{path}.source", f"baseline.yaml defines no source {source!r}")
    if kind == "web":
        port = env.get("port")
        if not (isinstance(port, int) and not isinstance(port, bool) and 0 < port < 65536):
            p.add(f"{path}.port", "required container port of the web UI (1 to 65535)")
        ready = env.get("ready", "/")
        if not isinstance(ready, str) or not ready.startswith("/"):
            p.add(f"{path}.ready", "must be a path starting with /")
        timeout = env.get("ready_timeout", 120)
        if not (_number(timeout) and timeout > 0):
            p.add(f"{path}.ready_timeout", "must be a positive number of seconds")
    if "env" in env and not (isinstance(env["env"], dict) and all(
            isinstance(k, str) and isinstance(v, (str, int, float)) for k, v in env["env"].items())):
        p.add(f"{path}.env", "must map variable names to strings")
    if "command" in env and not (isinstance(env["command"], list) and env["command"]
                                 and all(isinstance(c, str) for c in env["command"])):
        p.add(f"{path}.command", "must be a non-empty list of strings")
    seed = env.get("seed")
    if seed is None:
        return
    if not isinstance(seed, list):
        p.add(f"{path}.seed", "must be a list of seed steps")
        return
    for i, step in enumerate(seed):
        sp = f"{path}.seed step {i + 1}"
        if not isinstance(step, dict):
            p.add(sp, "must be a mapping with run (and optionally in, files)")
            continue
        p.keys(step, sp, SEED_KEYS)
        if not isinstance(step.get("run"), str) or not step.get("run").strip():
            p.add(f"{sp}.run", "required shell command")
        if step.get("in", "tool") not in ("tool", "capture"):
            p.add(f"{sp}.in", f"must be tool or capture (got {step.get('in')!r})")
        files = step.get("files")
        if files is None:
            continue
        if not isinstance(files, list):
            p.add(f"{sp}.files", "must be a list of paths under visuals/")
            continue
        for j, f in enumerate(files):
            _visual_file(root, f, f"{sp}.files[{j}]", p, "seed file")


def _check_steps(root: Path, steps: Any, path: str, p: _Problems) -> None:
    if not isinstance(steps, list) or not steps:
        p.add(f"{path}.steps", "web visuals need a non-empty list of steps")
        return
    crops = 0
    labels: set[str] = set()
    for i, step in enumerate(steps):
        sp = f"{path}.step {i + 1}"
        if not isinstance(step, dict) or len(step) != 1:
            p.add(sp, f"a step is a mapping with exactly one of {', '.join(STEP_KINDS)}")
            continue
        (kind, arg), = step.items()
        if kind not in STEP_KINDS:
            p.add(sp, f"unknown step {kind!r} (one of {', '.join(STEP_KINDS)})")
            continue
        if kind == "goto":
            if not isinstance(arg, str) or not arg.startswith("/"):
                p.add(sp, "goto needs a path starting with / (relative to the environment's URL)")
        elif kind in SELECTOR_STEPS:
            problem = _selector_ok(arg)
            if problem:
                p.add(sp, problem)
            if kind == "crop":
                crops += 1
                if crops == 2:
                    p.add(sp, "at most one crop per visual")
        elif kind == "press":
            if not isinstance(arg, str) or not arg:
                p.add(sp, "press needs a key name (for example Enter)")
        elif kind == "fill":
            if not isinstance(arg, dict) or set(arg) != {"selector", "text"} or not isinstance(arg.get("text"), str):
                p.add(sp, "fill needs {selector, text}")
            else:
                problem = _selector_ok(arg["selector"])
                if problem:
                    p.add(sp, problem)
        elif kind == "highlight":
            if not isinstance(arg, dict) or set(arg) != {"selector", "label"}:
                p.add(sp, "highlight needs {selector, label}")
                continue
            problem = _selector_ok(arg["selector"])
            if problem:
                p.add(sp, problem)
            label = arg["label"]
            if not isinstance(label, (str, int)) or isinstance(label, bool) or str(label) == "":
                p.add(sp, "highlight label must be a short string such as \"1\"")
            elif str(label) in labels:
                p.add(sp, f"duplicate highlight label {str(label)!r}")
            else:
                labels.add(str(label))
        elif kind == "script":
            _visual_file(root, arg, sp, p, "script")


def _check_visual(root: Path, name: Any, vis: Any, envs: dict, p: _Problems) -> None:
    path = f"visuals.{name}"
    if not isinstance(name, str) or not VISUAL_NAME_RE.match(name):
        p.add(path, "visual names must be lower case letters, digits, and -, starting with a letter, "
                    "at most 63 characters")
    if not isinstance(vis, dict):
        p.add(path, "must be a mapping")
        return
    kind = vis.get("kind")
    if kind not in ("web", "cli"):
        p.add(f"{path}.kind", f"must be web or cli (got {kind!r})")
        return
    p.keys(vis, path, WEB_VISUAL_KEYS if kind == "web" else CLI_VISUAL_KEYS)
    env_name = vis.get("env")
    env = envs.get(env_name) if isinstance(env_name, str) else None
    if env is None:
        p.add(f"{path}.env", f"no environment {env_name!r} declared")
    else:
        env_kind = env.get("kind") if isinstance(env, dict) else None
        if kind == "web" and env_kind != "web":
            p.add(f"{path}.env", f"a web visual needs a web environment ({env_name!r} is {env_kind!r})")
        if kind == "cli" and env_kind not in ("web", "cli"):
            p.add(f"{path}.env", f"a cli visual needs a cli or web environment ({env_name!r} is {env_kind!r})")
    _check_masks(vis.get("masks"), f"{path}.masks", p)
    disabled = vis.get("disable_redaction")
    if disabled is not None:
        if not isinstance(disabled, list):
            p.add(f"{path}.disable_redaction", "must be a list of default rule ids")
        else:
            for r in disabled:
                if r not in redact.DEFAULT_IDS:
                    p.add(f"{path}.disable_redaction", f"{r!r} is not a default rule id "
                                                       f"({', '.join(redact.DEFAULT_IDS)})")
    if kind == "web":
        _check_steps(root, vis.get("steps"), path, p)
        if "viewport" in vis:
            _check_viewport(vis["viewport"], f"{path}.viewport", p)
        variants = vis.get("variants")
        if variants is not None and (not isinstance(variants, list) or not variants
                                     or not all(isinstance(v, str) for v in variants)
                                     or not set(variants) <= {"light", "dark"} or len(set(variants)) != len(variants)):
            p.add(f"{path}.variants", "must be a non-empty list of light and dark without repeats")
        if "threshold" in vis and not (_number(vis["threshold"]) and 0 <= vis["threshold"] <= 100):
            p.add(f"{path}.threshold", "must be a percentage from 0 to 100")
        return
    if not isinstance(vis.get("command"), str) or not vis.get("command").strip():
        p.add(f"{path}.command", "required shell command")
    if "exit" in vis and not (isinstance(vis["exit"], int) and not isinstance(vis["exit"], bool)
                              and 0 <= vis["exit"] <= 255):
        p.add(f"{path}.exit", "must be an exit status from 0 to 255")
    if "width" in vis and not (isinstance(vis["width"], int) and 20 <= vis["width"] <= 300):
        p.add(f"{path}.width", "must be an integer from 20 to 300")
    if "prompt" in vis and not isinstance(vis["prompt"], str):
        p.add(f"{path}.prompt", "must be a string")
    if "env_vars" in vis and not (isinstance(vis["env_vars"], dict) and all(
            isinstance(k, str) and isinstance(v, (str, int, float)) for k, v in vis["env_vars"].items())):
        p.add(f"{path}.env_vars", "must map variable names to strings")


def validate(root: Path) -> list[str]:
    """Every problem of visuals.yaml as `visuals.yaml: <path>: <message>` (FR-007).

    [] when the recipe is clean or missing (callers report "no visuals declared").
    """
    root = Path(root)
    path = recipe_path(root)
    if not path.is_file():
        return []
    try:
        data = _read_recipe(path)
    except RecipeError as err:
        return [str(err)]
    p = _Problems()
    if data is None:
        data = {}
    if not isinstance(data, dict):
        return [f"{RECIPE}: (root): must be a mapping"]
    p.keys(data, "(root)", TOP_KEYS)
    if data.get("schema") != 1:
        p.add("schema", f"must be 1 (got {data.get('schema')!r})")
    _check_defaults(data.get("defaults"), p)
    _check_redaction(data.get("redaction"), p)
    envs = data.get("environments")
    if envs is None:
        envs = {}
    if not isinstance(envs, dict):
        p.add("environments", "must be a mapping of environment name to environment")
        envs = {}
    sources = baseline_sources(root)
    for name, env in envs.items():
        _check_environment(root, name, env, sources, p)
    visuals = data.get("visuals")
    if visuals is None:
        visuals = {}
    if not isinstance(visuals, dict):
        p.add("visuals", "must be a mapping of visual name to visual")
        visuals = {}
    for name, vis in visuals.items():
        _check_visual(root, name, vis, envs, p)
    for name, vis in visuals.items():
        variants = vis.get("variants") if isinstance(vis, dict) else None
        if isinstance(variants, list) and "dark" in variants and f"{name}-dark" in visuals:
            p.add(f"visuals.{name}-dark", f"the name collides with the dark variant of visual {name!r}")
    return p.items


# --- identity: capture environment version and fingerprints -------------------


def _capture_files(capture_dir: Path) -> list[Path]:
    files = []
    for path in sorted(capture_dir.rglob("*")):
        rel = path.relative_to(capture_dir)
        if not path.is_file() or "__pycache__" in rel.parts or path.suffix == ".pyc":
            continue
        if any(part.startswith(".") and part != ".containerignore" for part in rel.parts):
            continue
        files.append(path)
    return files


def capture_env_version(toolkit_dir: Path | None = None) -> str:
    """12 hex of SHA-256 over the capture build context (research R3)."""
    capture_dir = Path(toolkit_dir or TOOLKIT_DIR) / "capture"
    digest = hashlib.sha256()
    for path in _capture_files(capture_dir):
        rel = path.relative_to(capture_dir).as_posix()
        digest.update(rel.encode() + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).hexdigest().encode() + b"\n")
    return digest.hexdigest()[:12]


def _file_hash(root: Path, rel: str) -> str:
    path = Path(root) / SIDECAR_DIR / rel
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return "missing"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def fingerprint(recipe: Recipe, visual_name: str, guide_root: Path | None = None,
                capture_env: str | None = None) -> str:
    """16 hex of SHA-256 over everything that shapes a visual (research R11, FR-017)."""
    root = Path(guide_root or recipe.root)
    visual = recipe.visuals[visual_name]
    env = recipe.environment(visual)
    env_raw = dict(env.raw) if env else {}
    seed = []
    for step in (env.seed if env else []):
        seed.append({"run": step.run, "in": step.in_, "files": {f: _file_hash(root, f) for f in step.files}})
    env_raw.pop("seed", None)
    doc = {
        "visual": visual.raw,
        "environment": env_raw,
        "seed": seed,
        "scripts": {s: _file_hash(root, s) for s in visual.scripts},
        "rules": redact.describe(recipe.rules(visual)),
        "masks": [{"pattern": m.get("pattern"), "replacement": m.get("replacement")} for m in visual.masks],
        "defaults": recipe.resolved(visual),
        "capture_env": capture_env or capture_env_version(),
    }
    return hashlib.sha256(_canonical(doc).encode()).hexdigest()[:16]


def env_url_var(name: str) -> str:
    """GUIDE_ENV_<NAME>_URL with the name upper-cased and - replaced by _ (FR-002)."""
    return "GUIDE_ENV_" + name.upper().replace("-", "_") + "_URL"


# --- paths --------------------------------------------------------------------


def visual_dir(guide_root: Path) -> str:
    """The adapter's visual directory, relative to the guide root (FR-015)."""
    path = Path(guide_root) / "tools" / "guide" / "adapter.yaml"
    data: dict = {}
    if path.is_file():
        try:
            data = _as_dict(yaml.safe_load(path.read_text()))
        except yaml.YAMLError:
            data = {}
    if isinstance(data.get("visual_dir"), str) and data["visual_dir"]:
        return data["visual_dir"].strip("/")
    return DEFAULT_VISUAL_DIRS.get(str(data.get("format", "")), FALLBACK_VISUAL_DIR)


def sidecar_path(guide_root: Path, output_name: str) -> Path:
    return Path(guide_root) / SIDECAR_DIR / f"{output_name}{SIDECAR_SUFFIX}"


def image_rel(guide_root: Path, output_name: str, extension: str) -> str:
    return f"{visual_dir(guide_root)}/{output_name}.{extension}"


# --- sidecars -----------------------------------------------------------------


class _SidecarDumper(yaml.SafeDumper):
    pass


def _str_representer(dumper: yaml.SafeDumper, value: str) -> yaml.ScalarNode:
    if "\n" in value:
        return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", value)


_SidecarDumper.add_representer(str, _str_representer)


def order_sidecar(data: dict) -> dict:
    """Keys in the order of contracts/sidecar.md; unknown keys keep their order at the end."""
    out = {k: data[k] for k in SIDECAR_KEYS if k in data}
    if isinstance(out.get("environment"), dict):
        env = out["environment"]
        out["environment"] = {k: env[k] for k in ENVIRONMENT_KEYS if k in env} | {
            k: v for k, v in env.items() if k not in ENVIRONMENT_KEYS}
    out.update({k: v for k, v in data.items() if k not in out})
    return out


def dump_sidecar_text(data: dict) -> str:
    return yaml.dump(order_sidecar(data), Dumper=_SidecarDumper, sort_keys=False, allow_unicode=True,
                     width=4096, default_flow_style=False)


def dump_sidecar(path: Path, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(dump_sidecar_text(data))
    tmp.replace(path)


def load_sidecar(path: Path) -> dict | None:
    """The sidecar as a mapping, None when missing; RecipeError when unreadable."""
    path = Path(path)
    if not path.is_file():
        return None
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as err:
        raise RecipeError(f"{path.name}: invalid YAML: {err}".replace("\n", " ")) from None
    if not isinstance(data, dict):
        raise RecipeError(f"{path.name}: must be a mapping")
    return data


def load_sidecar_safe(path: Path) -> dict | None:
    """load_sidecar, but None for an unreadable sidecar too."""
    try:
        return load_sidecar(path)
    except RecipeError:
        return None


def placeholder_sidecar(recipe: Recipe, visual_name: str, variant: str, output_name: str,
                        guide_root: Path | None = None) -> dict:
    """A placeholder visual (FR-031a): recipe entry and sidecar, no image yet."""
    root = Path(guide_root or recipe.root)
    visual = recipe.visuals[visual_name]
    return {
        "schema": 1, "name": visual_name, "variant": variant, "kind": visual.kind,
        "image": image_rel(root, output_name, visual.extension),
        "fingerprint": fingerprint(recipe, visual_name, root), "placeholder": True, "text": "",
    }
