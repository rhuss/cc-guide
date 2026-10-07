"""guide/scripts/scaffold-project.sh: full scaffold and the --toolkit-only refresh evolve uses."""
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def run(*args, cwd=None):
    return subprocess.run(["bash", *map(str, args)], capture_output=True, text=True, cwd=cwd)


def plugin_copy(tmp_path: Path) -> Path:
    """A copy of the plugin directory, so the test can change the toolkit."""
    dest = tmp_path / "plugin"
    shutil.copytree(REPO / "guide", dest, ignore=shutil.ignore_patterns("__pycache__", "node_modules"))
    return dest


def test_full_scaffold_keeps_existing_files(tmp_path):
    plugin = plugin_copy(tmp_path)
    guide = tmp_path / "g"
    guide.mkdir()
    (guide / "Makefile").write_text("# mine\n")
    proc = run(plugin / "scripts/scaffold-project.sh", "--format", "gfm", "--title", "My Guide", guide)
    assert proc.returncode == 0, proc.stderr
    assert (guide / "Makefile").read_text() == "# mine\n"
    assert "kept existing Makefile" in proc.stdout
    tools = guide / "tools" / "guide"
    assert (tools / "adapter.yaml").read_text().startswith(
        (plugin / "adapters/gfm/adapter.yaml").read_text()[:20])
    assert (tools / "templates" / "run-summary.md").is_file()
    assert (tools / "readonly.yaml").is_file()
    assert "{{TITLE}}" not in (guide / "docs" / "README.md").read_text()


def test_toolkit_only_refresh(tmp_path):
    plugin = plugin_copy(tmp_path)
    guide = tmp_path / "g"
    assert run(plugin / "scripts/scaffold-project.sh", "--format", "antora", "--title", "T", guide).returncode == 0
    page = guide / "content" / "modules" / "ROOT" / "pages" / "index.adoc"
    page.write_text("= Edited by the author\n")
    stale = guide / "tools" / "guide" / "removed-module.py"
    stale.write_text("# no longer in the toolkit\n")

    (plugin / "toolkit" / "VERSION").write_text("9.9.9\n")
    (plugin / "toolkit" / "new_module.py").write_text("# new\n")
    proc = run(plugin / "scripts/scaffold-project.sh", "--format", "antora", "--toolkit-only", guide)
    assert proc.returncode == 0, proc.stderr
    assert "toolkit 9.9.9 installed" in proc.stdout
    tools = guide / "tools" / "guide"
    assert (tools / "VERSION").read_text().strip() == "9.9.9"
    assert (tools / "new_module.py").is_file()
    assert not stale.exists()                      # rsync --delete removed it
    assert (tools / "adapter.yaml").is_file()      # re-added after the rsync
    assert page.read_text() == "= Edited by the author\n"  # content untouched


def test_antora_scaffold_vendors_branding_assets(tmp_path):
    plugin = plugin_copy(tmp_path)
    guide = tmp_path / "g"
    assert run(plugin / "scripts/scaffold-project.sh", "--format", "antora", "--title", "T", guide).returncode == 0
    branding = guide / "tools" / "guide" / "branding"
    assert (branding / "contract.yaml").read_text() == (plugin / "adapters/antora/branding/contract.yaml").read_text()
    assert (branding / "logo-text.svg.tmpl").read_text() == \
        (plugin / "adapters/antora/branding/logo-text.svg.tmpl").read_text()
    assert (branding / "NOTICE.md").is_file()


def test_toolkit_only_refresh_restores_branding_assets(tmp_path):
    plugin = plugin_copy(tmp_path)
    guide = tmp_path / "g"
    assert run(plugin / "scripts/scaffold-project.sh", "--format", "antora", "--title", "T", guide).returncode == 0
    branding = guide / "tools" / "guide" / "branding"
    shutil.rmtree(branding)
    contract = plugin / "adapters" / "antora" / "branding" / "contract.yaml"
    contract.write_text(contract.read_text() + "# changed in the plugin\n")
    proc = run(plugin / "scripts/scaffold-project.sh", "--format", "antora", "--toolkit-only", guide)
    assert proc.returncode == 0, proc.stderr
    assert (branding / "logo-text.svg.tmpl").is_file()
    assert (branding / "contract.yaml").read_text().endswith("# changed in the plugin\n")


def test_gfm_scaffold_has_no_branding_assets(tmp_path):
    plugin = plugin_copy(tmp_path)
    guide = tmp_path / "g"
    assert run(plugin / "scripts/scaffold-project.sh", "--format", "gfm", "--title", "T", guide).returncode == 0
    assert (guide / "tools" / "guide" / "adapter.yaml").is_file()
    assert not (guide / "tools" / "guide" / "branding").exists()


def test_unknown_format(tmp_path):
    proc = run(REPO / "guide/scripts/scaffold-project.sh", "--format", "hugo", "--title", "T", tmp_path / "g")
    assert proc.returncode == 2 and "unknown format" in proc.stderr
