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


FONT_FILES = ["fonts.yaml", "OFL.txt", "RedHatDisplay-VF.woff2", "RedHatDisplay-Italic-VF.woff2",
              "RedHatText-VF.woff2", "RedHatText-Italic-VF.woff2", "RedHatMono-VF.woff2",
              "RedHatMono-Italic-VF.woff2"]


def assert_fonts_vendored(plugin: Path, guide: Path) -> None:
    fonts = guide / "tools" / "guide" / "branding" / "fonts"
    for name in FONT_FILES:
        assert (fonts / name).read_bytes() == (plugin / "adapters/antora/branding/fonts" / name).read_bytes(), name
    assert not (fonts / "update-fonts.py").exists()     # maintainer tool, never vendored


def test_antora_scaffold_vendors_fonts_without_maintainer_script(tmp_path):
    plugin = plugin_copy(tmp_path)
    guide = tmp_path / "g"
    assert run(plugin / "scripts/scaffold-project.sh", "--format", "antora", "--title", "T", guide).returncode == 0
    assert_fonts_vendored(plugin, guide)
    shutil.rmtree(guide / "tools" / "guide" / "branding" / "fonts")
    proc = run(plugin / "scripts/scaffold-project.sh", "--format", "antora", "--toolkit-only", guide)
    assert proc.returncode == 0, proc.stderr
    assert_fonts_vendored(plugin, guide)


def test_gfm_scaffold_has_no_branding_assets(tmp_path):
    plugin = plugin_copy(tmp_path)
    guide = tmp_path / "g"
    assert run(plugin / "scripts/scaffold-project.sh", "--format", "gfm", "--title", "T", guide).returncode == 0
    assert (guide / "tools" / "guide" / "adapter.yaml").is_file()
    assert not (guide / "tools" / "guide" / "branding").exists()


def test_unknown_format(tmp_path):
    proc = run(REPO / "guide/scripts/scaffold-project.sh", "--format", "hugo", "--title", "T", tmp_path / "g")
    assert proc.returncode == 2 and "unknown format" in proc.stderr


# --- embedded mode (specs/005-embedded-guide, T015) ----------------------------------


def test_embedded_scaffold(tmp_path):
    plugin = plugin_copy(tmp_path)
    host = tmp_path / "host"
    host.mkdir()
    (host / "README.md").write_text("# Host\n")
    guide = host / "guide"
    proc = run(plugin / "scripts/scaffold-project.sh", "--format", "gfm", "--title", "Host", "--embedded", guide)
    assert proc.returncode == 0, proc.stderr
    assert not (guide / "internal").exists()
    assert (guide / "docs" / "README.md").read_text() == \
        (plugin / "adapters/gfm/embedded/docs/README.md").read_text()
    assert "../../README.md" in (guide / "docs" / "README.md").read_text()
    assert "kept existing" not in proc.stdout
    ignore = (guide / ".gitignore").read_text().splitlines()
    assert "confidential.local.yaml" in ignore
    assert (guide / "docs" / "SUMMARY.md").is_file()
    assert (guide / "tools" / "guide" / "adapter.yaml").is_file()
    assert (host / "README.md").read_text() == "# Host\n"
    # a second run is idempotent (resume): nothing duplicated in .gitignore
    assert run(plugin / "scripts/scaffold-project.sh", "--format", "gfm", "--title", "Host", "--embedded",
               guide).returncode == 0
    (guide / "guide.yaml").write_text("schema: 1\n")
    assert run(plugin / "scripts/scaffold-project.sh", "--format", "gfm", "--title", "Host", "--embedded",
               guide).returncode == 0
    assert (guide / ".gitignore").read_text().splitlines().count("confidential.local.yaml") == 1


def test_embedded_scaffold_refuses_other_formats(tmp_path):
    proc = run(REPO / "guide/scripts/scaffold-project.sh", "--format", "mkdocs", "--title", "T", "--embedded",
               tmp_path / "g")
    assert proc.returncode == 2 and "gfm" in proc.stderr
    assert not (tmp_path / "g").exists()


def test_embedded_scaffold_refuses_unrelated_directory(tmp_path):
    target = tmp_path / "guide"
    target.mkdir()
    (target / "notes.txt").write_text("mine\n")
    proc = run(REPO / "guide/scripts/scaffold-project.sh", "--format", "gfm", "--title", "T", "--embedded", target)
    assert proc.returncode == 2 and "not a guide project" in proc.stderr
    assert sorted(p.name for p in target.iterdir()) == ["notes.txt"]


def test_standalone_scaffold_unchanged_by_embedded_overlay(tmp_path):
    plugin = plugin_copy(tmp_path)
    guide = tmp_path / "g"
    assert run(plugin / "scripts/scaffold-project.sh", "--format", "gfm", "--title", "T", guide).returncode == 0
    files = sorted(p.relative_to(guide).as_posix() for p in guide.rglob("*")
                   if p.is_file() and "tools" not in p.relative_to(guide).parts)
    scaffold = plugin / "adapters" / "gfm" / "scaffold"
    expected = sorted(p.relative_to(scaffold).as_posix() for p in scaffold.rglob("*") if p.is_file())
    assert files == expected
    assert (guide / "docs" / "README.md").read_text() == \
        (scaffold / "docs" / "README.md").read_text().replace("{{TITLE}}", "T")
    assert "confidential.local.yaml" not in (guide / ".gitignore").read_text()
