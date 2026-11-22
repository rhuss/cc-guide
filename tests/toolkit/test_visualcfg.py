"""Recipe schema, fingerprint, capture environment version, sidecars (visualcfg.py)."""
import shutil
from pathlib import Path

import pytest
import yaml

import visualcfg

REPO = Path(__file__).resolve().parents[2]
TOOLKIT = REPO / "guide" / "toolkit"

BASE = """\
schema: 1
environments:
  web1:
    kind: web
    image: docker.io/library/nginx:1.27-alpine
    port: 80
    seed:
      - run: cp /visuals/seed/index.html /usr/share/nginx/html/
        files: [seed/index.html]
  tools:
    kind: cli
    image: docker.io/library/alpine:3.20
visuals:
  table:
    kind: web
    env: web1
    steps:
      - goto: /
      - wait: "role=table"
      - highlight: {selector: "role=columnheader[name=accuracy]", label: "1"}
      - crop: "role=table"
  colors:
    kind: cli
    env: tools
    command: printf hello
"""


def make_guide(root: Path, recipe: str = BASE, baseline: str | None = None) -> Path:
    (root / "visuals" / "seed").mkdir(parents=True, exist_ok=True)
    (root / "visuals" / "seed" / "index.html").write_text("<table></table>\n")
    (root / "visuals.yaml").write_text(recipe)
    if baseline is not None:
        (root / "baseline.yaml").write_text(baseline)
    return root


def problems(root: Path, recipe: str, **kw) -> list[str]:
    make_guide(root, recipe, **kw)
    return visualcfg.validate(root)


def test_clean_recipe(tmp_guide):
    assert problems(tmp_guide, BASE) == []
    r = visualcfg.load_recipe(tmp_guide)
    assert set(r.visuals) == {"table", "colors"}
    assert r.environments["web1"].url == "http://web1:80"


def test_no_recipe(tmp_guide):
    assert visualcfg.load_recipe(tmp_guide) is None
    assert visualcfg.validate(tmp_guide) == []


def test_defaults_resolution(tmp_guide):
    make_guide(tmp_guide, BASE.replace("schema: 1\n", "schema: 1\ndefaults:\n  width: 80\n  threshold: 1.5\n"))
    r = visualcfg.load_recipe(tmp_guide)
    assert r.resolved(r.visuals["colors"]) == {"width": 80, "prompt": "$ "}
    assert r.resolved(r.visuals["table"]) == {"viewport": {"width": 1280, "height": 800}, "timeout": 15,
                                              "tolerance": 16, "threshold": 1.5}


def replace(old: str, new: str) -> str:
    assert old in BASE, old
    return BASE.replace(old, new)


INVALID = [
    ("bad env name", replace("  web1:\n", "  Web_1:\n").replace("env: web1", "env: Web_1"),
     "environments.Web_1", "host names"),
    ("bad visual name", replace("  table:\n", "  Table:\n"), "visuals.Table", "visual names"),
    ("kind", replace("kind: cli\n    image", "kind: vm\n    image"), "environments.tools.kind", "web or cli"),
    ("kind-cluster", replace("kind: cli\n    image", "kind: kind-cluster\n    image"), "environments.tools.kind",
     "kind-cluster environments are not supported yet"),
    ("no tag", replace("alpine:3.20", "alpine"), "environments.tools.image", "tag or digest"),
    ("latest", replace("alpine:3.20", "alpine:latest"), "environments.tools.image", "latest"),
    ("unknown source", replace("    port: 80\n", "    port: 80\n    source: nope\n"), "environments.web1.source",
     "baseline.yaml defines no source 'nope'"),
    ("self source", replace("    port: 80\n", "    port: 80\n    source: self\n"), "environments.web1.source",
     "reserved"),
    ("visual source", replace("    port: 80\n", "    port: 80\n    source: visual\n"), "environments.web1.source",
     "reserved"),
    ("no port", replace("    port: 80\n", ""), "environments.web1.port", "required"),
    ("ready path", replace("    port: 80\n", "    port: 80\n    ready: health\n"), "environments.web1.ready",
     "starting with /"),
    ("web visual on cli env", replace("    env: web1\n", "    env: tools\n"), "visuals.table.env",
     "web visual needs a web environment"),
    ("two crops", replace('      - crop: "role=table"\n', '      - crop: "role=table"\n      - crop: "#x"\n'),
     "visuals.table.step 5", "at most one crop"),
    ("duplicate labels", replace('      - crop: "role=table"\n',
                                 '      - highlight: {selector: "#a", label: "1"}\n      - crop: "role=table"\n'),
     "visuals.table.step 4", "duplicate highlight label"),
    ("width", replace("    command: printf hello\n", "    command: printf hello\n    width: 10\n"),
     "visuals.colors.width", "20 to 300"),
    ("seed in", replace("        files: [seed/index.html]\n", "        files: [seed/index.html]\n        in: host\n"),
     "environments.web1.seed step 1.in", "tool or capture"),
    ("seed file", replace("files: [seed/index.html]", "files: [seed/missing.html]"),
     "environments.web1.seed step 1.files[0]", "does not exist"),
    ("script file", replace("      - goto: /\n", "      - goto: /\n      - script: scripts/x.py\n"),
     "visuals.table.step 2", "does not exist"),
    ("dark collision", replace("    env: web1\n", "    env: web1\n    variants: [light, dark]\n")
     + "  table-dark:\n    kind: cli\n    env: tools\n    command: true\n",
     "visuals.table-dark", "collides with the dark variant"),
    ("unknown key", replace("    command: printf hello\n", "    command: printf hello\n    colour: red\n"),
     "visuals.colors.colour", "unknown key"),
    ("unknown step", replace("      - goto: /\n", "      - goto: /\n      - scroll: '#a'\n"),
     "visuals.table.step 2", "unknown step"),
    ("role selector", replace('wait: "role=table"', 'wait: "role=Table[name"'), "visuals.table.step 2",
     "role=<role>"),
    ("rule collision", BASE + "redaction:\n  rules:\n    - {id: hostname, pattern: x, replacement: y}\n",
     "redaction.rules[0].id", "default rule id"),
    ("disable unknown", replace("    command: printf hello\n",
                                "    command: printf hello\n    disable_redaction: [nope]\n"),
     "visuals.colors.disable_redaction", "not a default rule id"),
    ("schema", replace("schema: 1", "schema: 2"), "schema", "must be 1"),
    ("missing env", replace("    env: tools\n", "    env: other\n"), "visuals.colors.env", "no environment"),
    ("cli command", replace("    command: printf hello\n", ""), "visuals.colors.command", "required"),
    ("bad mask", replace("    command: printf hello\n", "    command: printf hello\n    masks:\n"
                                                          "      - {pattern: '(', replacement: x}\n"),
     "visuals.colors.masks[0].pattern", "regular expression"),
]


@pytest.mark.parametrize("label,recipe,path,message", INVALID, ids=[i[0] for i in INVALID])
def test_validation_rule(tmp_guide, label, recipe, path, message):
    found = problems(tmp_guide, recipe, baseline="captured: 2026-01-01\nsources:\n  - {id: tool, repo: x, commit: y}\n")
    matching = [p for p in found if p.startswith(f"visuals.yaml: {path}: ") and message in p]
    assert matching, found


def test_known_source_accepted(tmp_guide):
    recipe = replace("    port: 80\n", "    port: 80\n    source: tool\n")
    assert problems(tmp_guide, recipe, baseline="sources:\n  - {id: tool, repo: x, commit: abc}\n") == []
    r = visualcfg.load_recipe(tmp_guide)
    assert r.visuals_for_source("tool") == ["table"]


@pytest.mark.parametrize("dup", ["visual", "environment"])
def test_duplicate_names_rejected(tmp_guide, dup):
    if dup == "visual":
        recipe = BASE + "  colors:\n    kind: cli\n    env: tools\n    command: true\n"
    else:
        recipe = BASE.replace("visuals:\n", "  tools:\n    kind: cli\n    image: alpine:3.20\nvisuals:\n")
    found = problems(tmp_guide, recipe)
    assert len(found) == 1 and "duplicate key" in found[0]
    with pytest.raises(visualcfg.RecipeError):
        visualcfg.load_recipe(tmp_guide)


def test_template_skeleton_validates(tmp_guide):
    shutil.copy(REPO / "guide" / "templates" / "visuals.yaml", tmp_guide / "visuals.yaml")
    assert visualcfg.validate(tmp_guide) == []
    r = visualcfg.load_recipe(tmp_guide)
    assert r.visuals == {} and r.environments == {}


def test_contract_example_validates(tmp_guide):
    """The full example of contracts/visuals-yaml.md is a clean recipe."""
    contract = (REPO / "specs" / "008-captured-visuals" / "contracts" / "visuals-yaml.md").read_text()
    example = contract.split("```yaml\n", 1)[1].split("```", 1)[0]
    (tmp_guide / "visuals" / "seed").mkdir(parents=True)
    (tmp_guide / "visuals" / "seed" / "runs.py").write_text("print('seed')\n")
    (tmp_guide / "visuals.yaml").write_text(example)
    (tmp_guide / "baseline.yaml").write_text("sources:\n  - {id: mlflow, repo: x, commit: abc}\n")
    assert visualcfg.validate(tmp_guide) == []


def copy_toolkit_capture(dest: Path) -> Path:
    shutil.copytree(TOOLKIT / "capture", dest / "capture",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return dest


def test_capture_env_version(tmp_path):
    kit = copy_toolkit_capture(tmp_path / "kit")
    v1 = visualcfg.capture_env_version(kit)
    assert len(v1) == 12 and int(v1, 16) >= 0
    (kit / "capture" / "__pycache__").mkdir()
    (kit / "capture" / "__pycache__" / "x.pyc").write_bytes(b"\0\1")
    (kit / "capture" / ".DS_Store").write_bytes(b"junk")
    assert visualcfg.capture_env_version(kit) == v1
    (kit / "capture" / "redact.py").write_text((kit / "capture" / "redact.py").read_text() + "\n# changed\n")
    assert visualcfg.capture_env_version(kit) != v1


def test_capture_env_version_matches_repo():
    assert visualcfg.capture_env_version() == visualcfg.capture_env_version(TOOLKIT)


def fp(root: Path, name: str = "table", env: str = "abc") -> str:
    return visualcfg.fingerprint(visualcfg.load_recipe(root), name, root, capture_env=env)


def test_fingerprint_stable_across_key_order(tmp_guide):
    make_guide(tmp_guide)
    a = fp(tmp_guide)
    reordered = BASE.replace("    kind: web\n    image: docker.io/library/nginx:1.27-alpine\n    port: 80\n",
                             "    port: 80\n    image: docker.io/library/nginx:1.27-alpine\n    kind: web\n")
    assert reordered != BASE
    make_guide(tmp_guide, reordered)
    assert fp(tmp_guide) == a and len(a) == 16


@pytest.mark.parametrize("change", ["seed", "image", "mask", "capture_env", "defaults", "redaction"])
def test_fingerprint_changes(tmp_guide, change):
    make_guide(tmp_guide)
    before = fp(tmp_guide)
    env = "abc"
    if change == "seed":
        (tmp_guide / "visuals" / "seed" / "index.html").write_text("<table><tr></tr></table>\n")
    elif change == "image":
        make_guide(tmp_guide, BASE.replace("nginx:1.27-alpine", "nginx:1.28-alpine"))
    elif change == "mask":
        make_guide(tmp_guide, BASE.replace('      - crop: "role=table"\n', '      - crop: "role=table"\n'
                                           '    masks:\n      - {pattern: "x", replacement: "y"}\n'))
    elif change == "capture_env":
        env = "def"
    elif change == "defaults":
        make_guide(tmp_guide, BASE.replace("schema: 1\n", "schema: 1\ndefaults:\n  threshold: 2\n"))
    elif change == "redaction":
        make_guide(tmp_guide, BASE + "redaction:\n  rules:\n    - {id: tenant, pattern: a, replacement: b}\n")
    assert fp(tmp_guide, env=env) != before


def test_cli_fingerprint_ignores_web_defaults(tmp_guide):
    make_guide(tmp_guide)
    before = fp(tmp_guide, "colors")
    make_guide(tmp_guide, BASE.replace("schema: 1\n", "schema: 1\ndefaults:\n  threshold: 2\n"))
    assert fp(tmp_guide, "colors") == before


def test_env_url_var():
    assert visualcfg.env_url_var("my-env") == "GUIDE_ENV_MY_ENV_URL"


def test_outputs_and_refs(tmp_guide):
    make_guide(tmp_guide, BASE.replace("    env: web1\n", "    env: web1\n    variants: [light, dark]\n"))
    r = visualcfg.load_recipe(tmp_guide)
    assert r.visuals["table"].outputs() == [("light", "table"), ("dark", "table-dark")]
    assert r.visuals["colors"].outputs() == [("default", "colors")]
    assert r.resolve_ref("table-dark") == ("table", "dark")
    assert r.resolve_ref("table") == ("table", "light")
    assert r.resolve_ref("nope") is None


def test_visual_dir(tmp_guide):
    assert visualcfg.visual_dir(tmp_guide) == "docs/assets/visuals"
    tools = tmp_guide / "tools" / "guide"
    tools.mkdir(parents=True)
    shutil.copy(REPO / "guide" / "adapters" / "antora" / "adapter.yaml", tools / "adapter.yaml")
    assert visualcfg.visual_dir(tmp_guide) == "content/modules/ROOT/images/visuals"


SIDECAR = {
    "text": "line one\nline two\n", "name": "table", "schema": 1, "variant": "default", "kind": "web",
    "image": "docs/assets/visuals/table.png",
    "environment": {"platform": "linux/arm64", "name": "web1", "image": "nginx:1.27-alpine", "digest": "sha256:ab"},
    "fingerprint": "0123456789abcdef", "capture_env": "abcdefabcdef", "captured_at": "2026-11-22T10:15:00Z",
    "redaction": {"rules": ["home-path"], "disabled": [], "replacements": {"home-path": 0}},
    "masks": 0, "scripts": [], "variants": {}, "highlights": [{"label": "1", "selector": "#a", "text": "acc"}],
    "style": None,
}


def test_sidecar_round_trip_and_order(tmp_path):
    path = tmp_path / "visuals" / "table.visual.yaml"
    visualcfg.dump_sidecar(path, SIDECAR)
    text = path.read_text()
    keys = [line.split(":", 1)[0] for line in text.splitlines() if line and not line.startswith((" ", "-"))]
    assert keys == ["schema", "name", "variant", "kind", "image", "environment", "fingerprint", "capture_env",
                    "captured_at", "redaction", "masks", "scripts", "variants", "highlights", "style", "text"]
    assert "text: |" in text
    env_keys = [line.strip().split(":", 1)[0] for line in text.split("environment:\n", 1)[1].split("fingerprint")[0]
                .splitlines()]
    assert env_keys == ["name", "image", "digest", "platform"]
    assert visualcfg.load_sidecar(path) == SIDECAR
    assert visualcfg.load_sidecar(tmp_path / "missing.visual.yaml") is None


def test_placeholder_sidecar(tmp_guide):
    make_guide(tmp_guide)
    r = visualcfg.load_recipe(tmp_guide)
    data = visualcfg.placeholder_sidecar(r, "colors", "default", "colors")
    assert list(visualcfg.order_sidecar(data)) == ["schema", "name", "variant", "kind", "image", "fingerprint",
                                                   "placeholder", "text"]
    assert data["placeholder"] is True and data["text"] == "" and data["image"] == "docs/assets/visuals/colors.svg"
    path = visualcfg.sidecar_path(tmp_guide, "colors")
    visualcfg.dump_sidecar(path, data)
    assert yaml.safe_load(path.read_text())["placeholder"] is True


@pytest.mark.parametrize("value", ["5", "[{x: 1}]", "dark"])
def test_bad_variants_reported_not_raised(tmp_guide, value):
    recipe = replace("    env: web1\n", f"    env: web1\n    variants: {value}\n")
    if value == "dark":
        recipe += "  table-dark:\n    kind: cli\n    env: tools\n    command: true\n"
    found = problems(tmp_guide, recipe)
    assert any("visuals.table.variants" in p for p in found), found
    assert not any("collides" in p for p in found)
