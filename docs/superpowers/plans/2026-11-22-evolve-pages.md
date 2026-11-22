# Evolve Pages Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/guide:evolve --pages` sets up GitHub Pages for an existing Antora or MkDocs guide, including a guide kept in a subdirectory of a code repository, and Antora guides in a subdirectory build at all.

**Architecture:** `playbook.py` generates a playbook whose local content sources point at the git working tree's top level with a prefixed `start_path` when the guide root is not that top level. The Pages workflow template uploads `{{GUIDE_DIR}}/build/site`. The evolve skill gains a `--pages` mode that reuses create's wrap-up step 2 with the workflow at the git root; the toolkit version goes to 0.5.0 so evolve offers the refresh.

**Tech Stack:** Python 3.11 toolkit (PEP 723, `uv run`), pytest, Antora 3.2, GitHub Actions YAML, Markdown skill files.

**Spec:** `brainstorm/08-pages-deploy.md`, section "Follow-up (2026-11-22): `/guide:evolve --pages` for existing guides" (the earlier sections describe the create side this builds on).

## Global Constraints

- No em dash or en dash characters in any file; tests build them with `chr(0x2014)` and `chr(0x2013)`.
- `uv` instead of pip; podman instead of Docker.
- Pages applies only to `antora` and `mkdocs` guides; never gfm, never embedded.
- Publishing always uses the repository the guide already lives in (`origin`, a GitHub remote); never a new remote.
- Never overwrite an existing workflow file; stop when the repository already has a Pages site.
- `gh api` (enabling Pages) and pushing run only after explicit approval.
- `guide/toolkit/VERSION` becomes `0.5.0`; plugin manifest versions stay unchanged.
- Toolkit code imports nothing from outside `guide/toolkit/`.
- Git commits end with the trailer `Assisted-By: 🤖 Claude Code`.

## Review Focus

1. A guide at the git root without branding: still builds from the committed `site.yml`, nothing generated (existing `test_main_checkout_uses_site_yml`; Task 1 must keep it green).
2. A guide directory that is not a git repository yet: `playbook.path` must not raise; it behaves as today (Task 1 test `test_non_git_guide_uses_site_yml`).
3. A subdirectory guide inside a linked worktree: sources point at the main repository with the worktree branch and the prefixed `start_path` (Task 1 test).
4. `origin` missing or not on GitHub (for example GitLab): `--pages` stops with an explanation and writes nothing (Task 3 skill text test).
5. A guide that does not build (`make site` or the leak check fails): `--pages` stops before writing the workflow, so the repository never gets a workflow that fails on every push (Task 3 skill text test).

---

### Task 1: Antora playbook for a guide in a repository subdirectory

**Files:**
- Modify: `guide/toolkit/playbook.py` (`is_linked_worktree` near line 58, `path` near lines 75 to 150, module docstring)
- Test: `tests/toolkit/test_playbook.py` (new tests after `test_linked_worktree_generates_playbook`, reusing `SITE`, `SITE_INTERNAL`, `git`)

**Interfaces:**
- Produces: `is_linked_worktree(root: Path) -> bool` now decided by git (`--absolute-git-dir` differs from `--git-common-dir`), so it is also true for a subdirectory of a linked worktree, and false outside git. New `_repo_prefix(root: Path) -> str`: the output of `git rev-parse --show-prefix` (for example `"docs/guide/"`), `""` at the top level or outside git. `path()` additionally generates a playbook when the prefix is non-empty, with the reason `guide in a repository subdirectory`.

- [ ] **Step 1: Write the failing tests**

```python
def host_with_guide(tmp_path) -> tuple[Path, Path]:
    host = tmp_path / "host"
    guide = host / "docs" / "guide"
    guide.mkdir(parents=True)
    git("init", "-q", "-b", "main", cwd=host)
    (guide / "site.yml").write_text(yaml.safe_dump(SITE, sort_keys=False))
    (guide / "site-internal.yml").write_text(yaml.safe_dump(SITE_INTERNAL, sort_keys=False))
    (host / "main.go").write_text("package main\n")
    (host / ".gitignore").write_text(".claude/\n")
    git("add", "-A", cwd=host)
    git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "init", cwd=host)
    return host, guide

def test_guide_in_subdirectory_generates_playbook(tmp_path):
    host, guide = host_with_guide(tmp_path)
    out = playbook.path(guide, internal=False)
    assert out == guide / "build" / "playbook.yml"
    assert "guide in a repository subdirectory" in out.read_text().splitlines()[0]
    data = yaml.safe_load(out.read_text())
    (src,) = data["content"]["sources"]
    assert Path(src["url"]).resolve() == host.resolve()
    assert src["start_path"] == "docs/guide/content" and src["branches"] == "HEAD"
    assert Path(data["output"]["dir"]) == (guide / "build" / "site").resolve()
    internal = yaml.safe_load(playbook.path(guide, internal=True).read_text())
    assert [s["start_path"] for s in internal["content"]["sources"]] == ["docs/guide/content", "docs/guide/internal"]

def test_guide_in_subdirectory_of_linked_worktree(tmp_path):
    host, _ = host_with_guide(tmp_path)
    wt = host / ".claude" / "worktrees" / "002-pages"
    git("worktree", "add", "-q", "-b", "002-pages", str(wt), cwd=host)
    guide = wt / "docs" / "guide"
    assert playbook.is_linked_worktree(guide)
    data = yaml.safe_load(playbook.path(guide, internal=False).read_text())
    (src,) = data["content"]["sources"]
    assert Path(src["url"]).resolve() == host.resolve()
    assert src["branches"] == "002-pages" and src["worktrees"] == "002-pages"
    assert src["start_path"] == "docs/guide/content"

def test_non_git_guide_uses_site_yml(tmp_path):
    (tmp_path / "site.yml").write_text(yaml.safe_dump(SITE, sort_keys=False))
    assert not playbook.is_linked_worktree(tmp_path)
    assert playbook.path(tmp_path, internal=False) == tmp_path / "site.yml"
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run --no-project --with pytest --with pyyaml --with 'fonttools[woff]==4.67.0' pytest tests/toolkit/test_playbook.py -q`
Expected: the two subdirectory tests FAIL (`path` returns `site.yml`, `is_linked_worktree` false for the nested guide); `test_non_git_guide_uses_site_yml` may already pass (it pins today's behavior).

- [ ] **Step 3: Implement in `guide/toolkit/playbook.py`**

`is_linked_worktree` and `_repo_prefix` call git with `check=False` semantics (a failing `rev-parse` means "not in git": False and `""`). In `path()`: compute `prefix = _repo_prefix(root)`; generate when `branded or overlaid or linked or prefix`. For each `url: .` source: linked keeps today's url, branches, worktrees; otherwise the url becomes the working tree top level (`git rev-parse --show-toplevel`, or `root` outside git). In both cases, when `prefix` is non-empty, `start_path` becomes `prefix + start_path` (default `start_path` is `""`, giving the prefix without its trailing slash). Add the reason string and extend the docstring with one bullet for the subdirectory case.

- [ ] **Step 4: Run to verify they pass, plus the whole playbook file**

Run: same command as Step 2
Expected: all tests in `test_playbook.py` PASS (including `test_main_checkout_uses_site_yml` and the branded/linked tests).

- [ ] **Step 5: Real Antora build of a subdirectory guide**

Build a scratch host repository with the fixture Antora guide at `docs/guide/` (`bash tests/adapters/scaffold.sh antora <scratch>/g`, move it to `<scratch>/host/docs/guide`, remove its `.git`, `git init` the host, commit; set `CC_GUIDE_NODE_MODULES` to an existing `node_modules` to skip npm), copy this branch's `guide/toolkit/playbook.py` into its `tools/guide/`, then from `docs/guide`: `make site`, once unbranded and once with a `branding: {wordmark: Sub guide, theme: neutral, footer: none}` block committed.
Expected: both exit 0 and `build/site` holds the guide's HTML pages; before this task the same build failed with "Local content source must be a git repository".

- [ ] **Step 6: Commit**

```bash
git add guide/toolkit/playbook.py tests/toolkit/test_playbook.py
git commit -m "fix(toolkit): build Antora guides kept in a repository subdirectory

Assisted-By: 🤖 Claude Code"
```

---

### Task 2: upload path follows the guide directory

**Files:**
- Modify: `guide/templates/guide-pages.yml` (upload step `path`)
- Test: `tests/toolkit/test_workflows.py` (`test_pages_workflow`, plus one new test)

**Interfaces:**
- Produces: the template's upload `path` is `{{GUIDE_DIR}}/build/site`.

- [ ] **Step 1: Write the failing test and adjust the existing assertion**

In `test_pages_workflow` change the path assertion to `assert steps[upload]["with"]["path"] == "./build/site"`. Add:

```python
def test_pages_workflow_for_a_guide_in_a_subdirectory():
    data = render("guide-pages.yml", "docs/guide")
    assert data["defaults"] == {"run": {"working-directory": "docs/guide"}}
    upload = next(s for s in data["jobs"]["build"]["steps"]
                  if s.get("uses", "").startswith("actions/upload-pages-artifact"))
    assert upload["with"]["path"] == "docs/guide/build/site"
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run --no-project --with pytest --with pyyaml pytest tests/toolkit/test_workflows.py -q`
Expected: 2 FAIL (path is still `build/site`).

- [ ] **Step 3: Change the upload `path` to `{{GUIDE_DIR}}/build/site`** and add one header comment line: the upload path is relative to the repository root, unlike the `run` steps.

- [ ] **Step 4: Run to verify they pass**

Run: same as Step 2
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add guide/templates/guide-pages.yml tests/toolkit/test_workflows.py
git commit -m "fix(templates): Pages upload path follows the guide directory

Assisted-By: 🤖 Claude Code"
```

---

### Task 3: `/guide:evolve --pages`, preflight, toolkit 0.5.0

**Files:**
- Modify: `guide/skills/evolve/SKILL.md` (frontmatter `argument-hint`, Arguments table, new section `## 3a. GitHub Pages (`--pages`)` after section 3, toolkit note in section 4 step 1)
- Modify: `guide/commands/evolve.md` (`argument-hint`, the superpowers note)
- Modify: `guide/skills/preflight/SKILL.md` (lines 64 and 78: superpowers and multi_agent not required for `evolve --pages`)
- Modify: `guide/toolkit/VERSION` (`0.5.0`)
- Modify: `README.md` (the Pages sentence: existing guides use `/guide:evolve --pages`)
- Test: `tests/toolkit/test_workflows.py`

**Interfaces:**
- Consumes: Task 1 (subdirectory guides build), Task 2 (`{{GUIDE_DIR}}` drives the upload path), create SKILL.md section 9 step 2 and the `pages` block from the earlier plan.

- [ ] **Step 1: Write the failing test**

```python
GUIDE = Path(__file__).resolve().parents[2] / "guide"

def test_evolve_pages_mode():
    evolve = (GUIDE / "skills" / "evolve" / "SKILL.md").read_text()
    command = (GUIDE / "commands" / "evolve.md").read_text()
    preflight = (GUIDE / "skills" / "preflight" / "SKILL.md").read_text()
    for text in (evolve, command):
        assert "[--pages]" in text.split("argument-hint:")[1].splitlines()[0]
    assert "## 3a. GitHub Pages (`--pages`)" in evolve
    for phrase in ("git rev-parse --show-toplevel", "gh api repos/<owner>/<repo>/pages",
                   "gh repo view --json visibility", "one Pages site per repository",
                   "`{{GUIDE_DIR}}` set to the guide's path inside the repository",
                   "not a GitHub remote", "`make site` and the leak check",
                   "create section 9 step 2", "Toolkit 0.5.0 adds"):
        assert phrase in evolve, phrase
    assert "without `--check` or `--pages`" in preflight
    assert (GUIDE / "toolkit" / "VERSION").read_text().strip() == "0.5.0"
    for text in (evolve, command, preflight):
        assert chr(0x2014) not in text and chr(0x2013) not in text
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --no-project --with pytest --with pyyaml pytest tests/toolkit/test_workflows.py -k evolve_pages -q`
Expected: FAIL on the `argument-hint` assertion.

- [ ] **Step 3: Write section 3a and the other edits**

Section 3a, in this order: (1) refuse gfm and embedded guides (explain that gfm renders on GitHub); (2) when `tools/guide/VERSION` is below 0.5.0, offer the toolkit refresh of section 4 step 1 first, committed on its own; (3) find the git root with `git rev-parse --show-toplevel` and the guide's path inside the repository (`git rev-parse --show-prefix`, without the trailing slash; `.` at the root); (4) refuse when `<git root>/.github/workflows/guide-pages.yml` exists; (5) read owner and repository from `git remote get-url origin`; stop when there is no `origin` or it is not a GitHub remote, and say that GitHub Pages publishes from the repository the guide already lives in; (6) `gh api repos/<owner>/<repo>/pages`: when it returns a site, stop (one Pages site per repository; the guide cannot take over an existing project site); (7) `gh repo view --json visibility`: for a private repository give the create intake warning (public site, paid GitHub plan); ask to proceed; (8) run `make site` and the leak check (`uv run tools/guide/leakcheck.py build/site`) locally and stop on failure; (9) follow create section 9 step 2 with the workflow rendered to `<git root>/.github/workflows/guide-pages.yml` and `{{GUIDE_DIR}}` set to the guide's path inside the repository; (10) report as create section 9 step 6 does for Pages; push only after approval. No drift run, no superpowers, no subagents.
Arguments table row: `--pages` | Set up GitHub Pages for this guide (section 3a); no drift run, no superpowers needed. Section 4 step 1: append "Toolkit 0.5.0 adds the `pages` block in `guide.yaml` and builds Antora guides kept in a repository subdirectory; mention `/guide:evolve --pages` when the guide has no `guide-pages.yml`." Command wrapper and preflight: superpowers and multi_agent are required for `evolve` without `--check` or `--pages`. README: one clause that existing guides get the workflow with `/guide:evolve --pages`.

- [ ] **Step 4: Bump `guide/toolkit/VERSION` to `0.5.0`**

- [ ] **Step 5: Verify**

Run: `make test && make validate && rg -n "$(python3 -c 'print(chr(0x2014) + "|" + chr(0x2013))')" guide README.md brainstorm docs || echo clean`
Expected: all tests pass, validation passes, `clean`.

- [ ] **Step 6: Commit**

```bash
git add guide/skills/evolve/SKILL.md guide/commands/evolve.md guide/skills/preflight/SKILL.md guide/toolkit/VERSION README.md tests/toolkit/test_workflows.py
git commit -m "feat(evolve): --pages sets up GitHub Pages for existing guides

Assisted-By: 🤖 Claude Code"
```
