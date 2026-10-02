import subprocess
import sys
from pathlib import Path

import pytest

import doctor

TOOLKIT = Path(__file__).resolve().parents[2] / "guide" / "toolkit"

NPX = """#!/bin/bash
# fake npx: --no-install <tool> --version
tool=$2
case "$tool" in
  antora) [[ -n "$FAKE_ANTORA" ]] || exit 1; echo "@antora/cli: $FAKE_ANTORA"; echo "@antora/site-generator: $FAKE_ANTORA" ;;
  playwright) echo "Version 1.55.0" ;;
  markserv) echo "markserv 1.17.4" ;;
  *) exit 1 ;;
esac
"""

NODE = """#!/bin/bash
if [[ "$1" == "-e" ]]; then printf '%s' "$FAKE_CHROMIUM"; exit 0; fi
echo v26.8.1
"""


def stub(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text(body)
    path.chmod(0o755)


@pytest.fixture
def fake_env(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub(bin_dir, "node", NODE)
    stub(bin_dir, "npx", NPX)
    stub(bin_dir, "uv", "#!/bin/bash\necho 'uv 0.8.12 (36151df0e 2025-08-18)'\n")
    stub(bin_dir, "pandoc", "#!/bin/bash\necho \"pandoc ${FAKE_PANDOC:-3.11}\"\n")
    stub(bin_dir, "uvx", "#!/bin/bash\necho 'mkdocs, version 1.6.1 from /x (Python 3.12)'\n")
    chromium = tmp_path / "chromium"
    chromium.write_text("binary")
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setenv("FAKE_ANTORA", "3.2.1")
    monkeypatch.setenv("FAKE_CHROMIUM", str(chromium))
    return tmp_path


def guide_with(root: Path, requires: str) -> Path:
    tools = root / "guide" / "tools" / "guide"
    tools.mkdir(parents=True)
    (tools / "adapter.yaml").write_text("format: antora\nrequires:\n" + requires)
    return root / "guide"


ANTORA_REQUIRES = """  node: ">=20"
  uv: ">=0.4"
  antora: "~3.2.0"
  playwright-chromium: "^1.48"
"""


@pytest.mark.parametrize("version,constraint,expected", [
    ((26, 8, 1), ">=20", True),
    ((18, 0, 0), ">=20", False),
    ((3, 2, 1), "~3.2.0", True),
    ((3, 3, 0), "~3.2.0", False),
    ((3, 1, 9), "~3.2.0", False),
    ((1, 63, 0), "^1.48", True),
    ((2, 0, 0), "^1.48", False),
    ((0, 0, 1), "*", True),
    ((3, 11, 0), ">=3", True),
])
def test_satisfies(version, constraint, expected):
    assert doctor.satisfies(version, constraint) is expected


def test_bad_constraint():
    with pytest.raises(ValueError):
        doctor.satisfies((1, 0, 0), "==1.0")


def test_parse_version():
    assert doctor.parse_version("v26.8.1") == (26, 8, 1)
    assert doctor.parse_version("pandoc 3.11") == (3, 11, 0)
    assert doctor.parse_version("gh version 2.100.0 (2026-09-03)") == (2, 100, 0)
    assert doctor.parse_version("nothing") is None


def test_all_present(fake_env):
    root = guide_with(fake_env, ANTORA_REQUIRES)
    results = doctor.check(root)
    assert [r.status for r in results] == ["ok"] * 4, [r.line() for r in results]
    assert results[0].line() == "ok   node 26.8.1 (>=20)"
    assert results[2].version == "3.2.1"


def test_missing_local_tool(fake_env, monkeypatch):
    monkeypatch.delenv("FAKE_ANTORA")
    root = guide_with(fake_env, ANTORA_REQUIRES)
    results = {r.tool: r for r in doctor.check(root)}
    assert results["antora"].status == "missing"
    assert results["antora"].line() == "MISSING antora: run npm install in the guide project"


def test_missing_binary(fake_env):
    root = guide_with(fake_env, '  gh: ">=2"\n')
    (r,) = doctor.check(root)
    assert r.status == "missing" and "brew install gh" in r.line()


def test_old_version(fake_env, monkeypatch):
    monkeypatch.setenv("FAKE_PANDOC", "2.19")
    root = guide_with(fake_env, '  pandoc: ">=3"\n')
    (r,) = doctor.check(root)
    assert r.status == "old"
    assert r.line() == "OLD  pandoc 2.19.0 (need >=3): brew install pandoc"


def test_chromium_missing(fake_env, monkeypatch):
    monkeypatch.setenv("FAKE_CHROMIUM", str(fake_env / "no-such-file"))
    root = guide_with(fake_env, '  playwright-chromium: "*"\n')
    (r,) = doctor.check(root)
    assert r.status == "missing" and "npx playwright install chromium" in r.line()


def test_mapping_overrides_command_and_hint(fake_env):
    root = guide_with(fake_env, "  custom:\n    version: '>=1.2'\n    command: pandoc --version\n"
                                "    hint: get it from the vendor\n")
    (r,) = doctor.check(root)
    assert r.status == "ok" and r.version == "3.11.0"
    root2 = guide_with(fake_env / "other", "  thing:\n    command: no-such-cmd\n    hint: get it from the vendor\n")
    (r,) = doctor.check(root2)
    assert r.line() == "MISSING thing: get it from the vendor"


def test_unknown_tool_without_command(fake_env):
    root = guide_with(fake_env, '  frobnicator: ">=1"\n')
    (r,) = doctor.check(root)
    assert r.status == "error" and "unknown tool" in r.message


def test_missing_descriptor(tmp_path):
    (r,) = doctor.check(tmp_path)
    assert r.status == "error"


def test_mkdocs_uses_requirements(fake_env):
    root = guide_with(fake_env, '  mkdocs: ">=1.6"\n')
    (root / "requirements.txt").write_text("mkdocs-material>=9.5,<9.8\n")
    assert doctor.builtin("mkdocs", root).command[:3] == ["uvx", "--with-requirements", "requirements.txt"]
    (r,) = doctor.check(root)
    assert r.status == "ok" and r.version == "1.6.1"


def test_adapter_option_with_empty_root(fake_env, monkeypatch):
    """create runs doctor against the plugin's adapter before the project exists."""
    monkeypatch.delenv("FAKE_ANTORA")
    descriptor = fake_env / "plugin-adapter.yaml"
    descriptor.write_text("format: antora\nrequires:\n" + ANTORA_REQUIRES)
    empty = fake_env / "not-yet-created"
    results = {r.tool: r for r in doctor.check(empty, descriptor)}
    assert results["node"].status == "ok"
    assert results["antora"].line() == "MISSING antora: run npm install in the guide project"


def test_cli_exit_codes(fake_env):
    root = guide_with(fake_env, ANTORA_REQUIRES)
    env = {"PATH": str(fake_env / "bin"), "FAKE_ANTORA": "3.2.0",
           "FAKE_CHROMIUM": str(fake_env / "chromium")}
    proc = subprocess.run([sys.executable, str(TOOLKIT / "doctor.py"), "--root", str(root)],
                          capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    env.pop("FAKE_ANTORA")
    proc = subprocess.run([sys.executable, str(TOOLKIT / "doctor.py"), "--root", str(root)],
                          capture_output=True, text=True, env=env)
    assert proc.returncode == 1
    assert "MISSING antora" in proc.stdout
    proc = subprocess.run([sys.executable, str(TOOLKIT / "doctor.py"), "--root", str(fake_env / "nowhere"),
                           "--adapter", str(root / "tools/guide/adapter.yaml")],
                          capture_output=True, text=True, env=env)
    assert proc.returncode == 1 and "ok   node" in proc.stdout
