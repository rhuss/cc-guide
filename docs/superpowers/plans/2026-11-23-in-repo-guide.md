# In-Repo Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/guide:create` sets up an Antora or MkDocs guide in a subdirectory of an existing repository (an in-repo guide), with confidential data kept out of committed files.

**Architecture:** `guidecfg.py` treats a guide inside a git repository but not at its top level like an embedded guide for confidential data (it reads `confidential.local.yaml` and accepts `local:` inputs) without requiring it. `scaffold-project.sh --in-repo` scaffolds without `internal/` and git-ignores the local file. The create skill gains the in-repo target case, intake, setup, and workflow rules.

**Tech Stack:** Python 3.11 toolkit (`uv run`), bash, pytest, Markdown skill files.

**Spec:** `brainstorm/11-in-repo-guide.md`

## Global Constraints

- No em dash or en dash characters in any file; tests build them with `chr(0x2014)` and `chr(0x2013)`.
- Formats for an in-repo guide: `antora` and `mkdocs` only (gfm uses embedded mode).
- No internal part, no `self` source, no pull request check, no README change, no docs consolidation (those are #10).
- Confidential terms, patterns, and real input locations of an in-repo guide go to `confidential.local.yaml`, never into committed files; the toolkit allows this but does not require it (guides already moved into a repository keep validating).
- A guide at the top level of its own repository keeps ignoring a stray `confidential.local.yaml` (existing test `test_local_confidential_file_ignored_by_separate_guides`).
- Workflows go to the repository root with `{{GUIDE_DIR}}` = the guide's path and `{{BRANCH}}` = the default branch; enabling Pages and pushing only after approval.
- Git commits end with `Assisted-By: 🤖 Claude Code`.

## Review Focus

1. A guide directory not inside any git repository (a fresh scaffold before `git init`): not an in-repo guide; behaves as a separate guide (Task 1 test `test_in_repo_guide_detection`).
2. An existing gfm guide moved into `docs/guide/` of a repository with confidential inputs registered by real location: keeps validating (Task 1 test `test_in_repo_guide_does_not_require_local_inputs`).
3. `--in-repo` combined with `--embedded`, or with `--format gfm`: refused before anything is written (Task 2 test).
4. `--in-repo` on a non-empty directory that is not a guide project: refused, nothing merged (Task 2 test).
5. create run at a repository root with `--format antora`: offers the in-repo guide instead of refusing (Task 3 skill text test).

---

### Task 1: confidential data of in-repo guides

**Files:**
- Modify: `guide/toolkit/guidecfg.py` (new helper next to `host_toplevel` near line 333; `load_guide` near line 659; `load_inputs` near lines 909 to 949; `LOCAL_FILE` comment at line 69)
- Test: `tests/toolkit/test_guidecfg.py` (section "confidential.local.yaml", around lines 725 to 885)

**Interfaces:**
- Produces: `in_repo_guide(root: Path) -> bool`: True when `host_toplevel(root)` is not None and differs from `root` (both resolved); embedded guides are in-repo guides by this definition too. `load_guide` merges local terms and patterns when the guide has an `embedded` block or `in_repo_guide(root)`. `load_inputs` accepts `local:` locations under the same condition. The rule "a confidential input must be `local:`" stays embedded-only.

- [ ] **Step 1: Write the failing tests and update the two tests that pin the old rule**

```python
def in_repo(tmp_path: Path) -> Path:
    """A standalone guide (no embedded block) in docs/guide of a host repository."""
    host = tmp_path / "host"
    root = host / "docs" / "guide"
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(host)], check=True)
    return make_gfm_guide(root)

def test_in_repo_guide_detection(tmp_path, render_fixture_guide):
    root = in_repo(tmp_path)
    assert guidecfg.in_repo_guide(root)
    assert not guidecfg.in_repo_guide(root.parent.parent)        # the repository root itself
    assert not guidecfg.in_repo_guide(render_fixture_guide)       # not inside any git repository

def test_in_repo_guide_reads_local_confidential(tmp_path):
    root = in_repo(tmp_path)
    write_local(root, {"confidential_terms": ["ACME Corp"]})
    assert guidecfg.load_guide(root).confidential_terms == ["ACME Corp"]

def test_in_repo_guide_accepts_local_inputs(tmp_path):
    root = in_repo(tmp_path)
    notes = tmp_path / "n.txt"; notes.write_text("n\n")
    write_local(root, {"inputs": {"call-1": str(notes)}})
    (root / "inputs.yaml").write_text(yaml.safe_dump({"inputs": [
        {"id": "call-1", "kind": "notes", "location": "local:call-1", "confidential": True}]}))
    assert guidecfg.load_inputs(root).get("call-1").path(root) == notes

def test_in_repo_guide_does_not_require_local_inputs(tmp_path):
    root = in_repo(tmp_path)
    (root / "inputs.yaml").write_text(yaml.safe_dump({"inputs": [
        {"id": "call-1", "kind": "notes", "location": str(tmp_path / "acme.txt"), "confidential": True}]}))
    guidecfg.load_inputs(root)
```

`test_local_input_only_in_embedded_guides` becomes `test_local_input_only_in_embedded_or_in_repo_guides`: after popping `embedded` the guide still sits in the host repository and loads; then copy the guide to a directory outside any repository (`shutil.copytree(embedded, tmp_path / "outside")`) and assert `"local:"` in `config_error(guidecfg.load_inputs, outside)`. In `test_confidential_input_of_embedded_guide_must_be_local` the last two lines stay valid (after popping `embedded` the in-repo guide is not required to use `local:`); only its comment changes to "an in-repo guide may keep confidential locations".

- [ ] **Step 2: Run to verify they fail**

Run: `uv run --no-project --with pytest --with pyyaml pytest tests/toolkit/test_guidecfg.py -k "in_repo or local" -q`
Expected: the new tests FAIL (`AttributeError: ... in_repo_guide`, local terms not merged, `local:` rejected); the renamed test fails on the in-repo load.

- [ ] **Step 3: Implement `in_repo_guide(root: Path) -> bool` and widen the two conditions in `guide/toolkit/guidecfg.py`**

In `load_inputs`, `local:` is allowed when `embedded or in_repo_guide(root)`; keep the error text but say "only in embedded guides and guides inside a repository". Update the `LOCAL_FILE` comment and the module docstring line 14.

- [ ] **Step 4: Run to verify they pass**

Run: `uv run --no-project --with pytest --with pyyaml pytest tests/toolkit/test_guidecfg.py -q`
Expected: all PASS, including `test_local_confidential_file_ignored_by_separate_guides`.

- [ ] **Step 5: Commit**

```bash
git add guide/toolkit/guidecfg.py tests/toolkit/test_guidecfg.py
git commit -m "feat(toolkit): confidential.local.yaml for guides inside a repository

Assisted-By: 🤖 Claude Code"
```

---

### Task 2: `scaffold-project.sh --in-repo`

**Files:**
- Modify: `guide/scripts/scaffold-project.sh` (usage, option parsing, the embedded branch near lines 40 to 85)
- Test: `tests/toolkit/test_scaffold_project.py`

**Interfaces:**
- Produces: `scaffold-project.sh --format antora|mkdocs --title TITLE --in-repo DIR`: copies the adapter scaffold without `internal/` (no overlay), refuses a non-empty DIR that is not a guide project (as `--embedded`), appends `confidential.local.yaml` to DIR/.gitignore once, exits 2 with a message for `--format gfm` ("use --embedded") or together with `--embedded`.

- [ ] **Step 1: Write the failing tests**

```python
def test_in_repo_scaffold(tmp_path):
    guide = tmp_path / "host" / "docs" / "guide"
    proc = run(REPO / "guide/scripts/scaffold-project.sh", "--format", "antora", "--title", "T", "--in-repo", guide)
    assert proc.returncode == 0, proc.stderr
    assert not (guide / "content" / "modules" / "internal").exists() and not (guide / "internal").exists()
    assert (guide / "site.yml").is_file() and (guide / "tools" / "guide" / "adapter.yaml").is_file()
    assert (guide / ".gitignore").read_text().splitlines().count("confidential.local.yaml") == 1
    assert run(REPO / "guide/scripts/scaffold-project.sh", "--format", "antora", "--title", "T", "--in-repo",
               guide).returncode == 0
    assert (guide / ".gitignore").read_text().splitlines().count("confidential.local.yaml") == 1

@pytest.mark.parametrize("args", [["--format", "gfm", "--in-repo"],
                                  ["--format", "antora", "--in-repo", "--embedded"]])
def test_in_repo_scaffold_refusals(tmp_path, args):
    proc = run(REPO / "guide/scripts/scaffold-project.sh", *args, "--title", "T", tmp_path / "g")
    assert proc.returncode == 2 and not (tmp_path / "g").exists()

def test_in_repo_scaffold_refuses_unrelated_directory(tmp_path):
    target = tmp_path / "guide"; target.mkdir(); (target / "notes.txt").write_text("mine\n")
    proc = run(REPO / "guide/scripts/scaffold-project.sh", "--format", "mkdocs", "--title", "T", "--in-repo", target)
    assert proc.returncode == 2 and "not a guide project" in proc.stderr
```

Check which `internal` paths the Antora and MkDocs scaffolds contain (`find guide/adapters/{antora,mkdocs}/scaffold -path '*internal*'`) and make the first assertion name exactly those.

- [ ] **Step 2: Run to verify they fail**

Run: `uv run --no-project --with pytest --with pyyaml pytest tests/toolkit/test_scaffold_project.py -k in_repo -q`
Expected: FAIL (usage error, exit 2 for the first test).

- [ ] **Step 3: Implement the flag** reusing the embedded branch's refusal and `.gitignore` logic; skip every scaffold path under an `internal` directory (top-level `internal/` and an Antora `modules/internal/` if present); `site-internal.yml` and `mkdocs-internal.yml` stay (their builds skip while `internal.enabled` is false). Update the header comment and `usage`.

- [ ] **Step 4: Run to verify they pass**

Run: `uv run --no-project --with pytest --with pyyaml pytest tests/toolkit/test_scaffold_project.py -q`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add guide/scripts/scaffold-project.sh tests/toolkit/test_scaffold_project.py
git commit -m "feat(scaffold): --in-repo for Antora and MkDocs guides inside a repository

Assisted-By: 🤖 Claude Code"
```

---

### Task 3: create skill and README

**Files:**
- Modify: `guide/skills/create/SKILL.md` (section 3 target cases and the `--embedded --format` rule; a new "In-repo guide" subsection after "Embedded setup"; section 11 Workflows)
- Modify: `README.md` (one sentence next to the Pages paragraph)
- Test: `tests/toolkit/test_workflows.py`

**Interfaces:**
- Consumes: `in_repo_guide` semantics (Task 1), `--in-repo` (Task 2), evolve section 3a steps 2 to 6 (`/guide:evolve --pages` checks).

- [ ] **Step 1: Write the failing test**

```python
def test_create_skill_offers_in_repo_guides():
    text = SKILL.read_text()
    for phrase in ("add an Antora or MkDocs guide in a subdirectory (README untouched)",
                   "default `docs/guide`", "--in-repo", "In-repo guide",
                   "`--format antora` or `--format mkdocs` at a repository root selects the in-repo guide",
                   "confidential.local.yaml", "no internal part",
                   "evolve section 3a steps 2 to 6", "`{{BRANCH}}` set to the default branch"):
        assert phrase in text, phrase
    assert "is inside the repository `<toplevel>` but not its root. Embedded guides live" not in text
    assert chr(0x2014) not in text and chr(0x2013) not in text
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --no-project --with pytest --with pyyaml pytest tests/toolkit/test_workflows.py -k in_repo -q`
Expected: FAIL on the first phrase.

- [ ] **Step 3: Edit `guide/skills/create/SKILL.md`**

Section 3: the repository-root case asks "Embed a gfm guide here (the README becomes the guide's front page), or add an Antora or MkDocs guide in a subdirectory (README untouched)?" (embedded recommended only when the author wants the README as front page); the in-repo answer asks for the subdirectory (default `docs/guide`). `--format antora` or `--format mkdocs` at a repository root selects the in-repo guide. The subdirectory-of-a-repository case: when the target is empty or does not exist, offer the in-repo guide there (GUIDE is the target); otherwise stop as for a non-empty directory. The `--embedded --format antora|mkdocs` rule now offers the in-repo guide or gfm embedding.
New subsection "In-repo guide" (after "Embedded setup"): preconditions as in "Embedded preconditions"; intake as section 4 without question 13's remote part (ask only about pushes; the repository's `origin` is used), without question 8 (no internal part: "code repositories are often public; confidential terms and patterns go to `confidential.local.yaml`"), format antora or mkdocs; setup as section 5 without `git init` and without step 10, scaffold with `--in-repo`, confidential terms, patterns, and real locations of confidential inputs (`local:<id>`) in `confidential.local.yaml` (from `$PLUGIN/templates/confidential.local.yaml`); workflows as below.
Section 11: for an in-repo guide, workflows go to `<git root>/.github/workflows/` with `{{GUIDE_DIR}}` set to the guide's path inside the repository and `{{BRANCH}}` set to the default branch; GitHub Pages first runs evolve section 3a steps 2 to 6 and stops on their refusals.

- [ ] **Step 4: Update `README.md`** next to the Pages sentence: create can also add an Antora or MkDocs guide to a subdirectory of an existing repository.

- [ ] **Step 5: Verify**

Run: `make test && make validate && rg -n "$(python3 -c 'print(chr(0x2014) + "|" + chr(0x2013))')" guide README.md brainstorm docs || echo clean`
Expected: all pass, validation passes, `clean`.

- [ ] **Step 6: Commit**

```bash
git add guide/skills/create/SKILL.md README.md tests/toolkit/test_workflows.py
git commit -m "feat(create): Antora and MkDocs guides inside an existing repository

Assisted-By: 🤖 Claude Code"
```
