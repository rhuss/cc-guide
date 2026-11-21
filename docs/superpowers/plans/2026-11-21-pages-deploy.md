# GitHub Pages Deploy Option Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/guide:create` can install a GitHub Actions workflow that builds, leak-checks, and publishes the shareable view of a separate Antora or MkDocs guide on GitHub Pages.

**Architecture:** A new workflow template `guide/templates/guide-pages.yml` sits next to the drift and pull request check templates and is rendered by the create skill at wrap-up. `guidecfg.py` learns a `pages` block (`enabled`, `url`) so the opt-in is recorded and validated. The create skill gains one intake question and one wrap-up step.

**Tech Stack:** Python 3.11 toolkit (PEP 723, `uv run`), pytest, GitHub Actions YAML, Markdown skill files.

**Spec:** `brainstorm/08-pages-deploy.md`

## Global Constraints

- No em dash or en dash characters in any file; tests build them with `chr(0x2014)` and `chr(0x2013)`.
- `uv` instead of pip; podman instead of Docker in any container instruction.
- The internal view (`build/site-internal`, `site-internal.yml`, `mkdocs-internal.yml`) is never published.
- Pages applies only to a separate guide with format `antora` or `mkdocs`; never gfm, never embedded.
- Never overwrite an existing workflow file.
- Enabling Pages (`gh api -X POST repos/<owner>/<repo>/pages -f build_type=workflow`) and pushing are outward actions: shown in full, run only after explicit approval.
- The workflow uses no secrets and fetches no sources.
- Git commits end with the trailer `Assisted-By: 🤖 Claude Code`.
- Toolkit code in `guide/toolkit/` imports nothing from outside its directory. `guide/toolkit/VERSION` stays at 0.4.0 (recent toolkit features did not bump it).

## Review Focus

1. A shareable build that contains a confidential term: the leak check must fail the job before anything is uploaded (Task 2 pins step order and the absence of `continue-on-error`).
2. A `pages` block on a gfm or embedded guide: validation rejects it with a key-specific message (Task 1).
3. `pages.url` given as `http://...`, without a trailing slash, or as a non-string: rejected, so `site.url` never gets a malformed value (Task 1).
4. An author who declines enabling Pages, or has no remote yet: the workflow still lands, and the run summary carries the enable command and says deploys fail until Pages is on (Task 3 skill text test).
5. A private remote: the intake warns that the site is public and needs a paid plan (Task 3 skill text test).

---

### Task 1: `pages` block in guide.yaml

**Files:**
- Modify: `guide/toolkit/guidecfg.py` (`Guide` dataclass near line 136, `GUIDE_KEYS` near line 525, `load_guide` near line 615 to 645, `GET_KEYS` near line 1041, module docstring list of `get` keys near line 24)
- Modify: `guide/templates/guide.yaml` (commented `pages` example after the `drift` block)
- Test: `tests/toolkit/test_guidecfg.py` (new tests after the publish tests, reusing `make_gfm_guide`, `vendor_adapter`, `config_error`, `edit`)

**Interfaces:**
- Produces: `Pages` dataclass `Pages(enabled: bool = False, url: str = "")`; `Guide.pages: Pages | None = None` (None when the block is absent); `PAGES_KEYS = {"enabled", "url"}`; `get` keys `pages.enabled` (`"true"`/`"false"`, `"false"` without a block) and `pages.url` (`""` without a block).

- [ ] **Step 1: Write the failing tests**

```python
def set_pages(root: Path, **values) -> None:
    edit(root / "guide.yaml", lambda d: d.update(pages=values))

def antora_guide(tmp_guide):
    root = make_gfm_guide(tmp_guide)
    vendor_adapter(root, "antora")
    edit(root / "guide.yaml", lambda d: d.update(format="antora"))
    return root

def test_pages_block_loads(tmp_guide):
    root = antora_guide(tmp_guide)
    set_pages(root, enabled=True, url="https://rhuss.github.io/my-guide/")
    g = guidecfg.load_guide(root)
    assert g.pages == guidecfg.Pages(enabled=True, url="https://rhuss.github.io/my-guide/")

def test_guide_without_pages_block(tmp_guide):
    assert guidecfg.load_guide(antora_guide(tmp_guide)).pages is None

@pytest.mark.parametrize("values, key", [
    ({"enabled": "yes"}, "pages.enabled"),
    ({"enabled": True, "url": "http://x.github.io/r/"}, "pages.url"),
    ({"enabled": True, "url": "https://x.github.io/r"}, "pages.url"),
    ({"enabled": True, "url": 42}, "pages.url"),
    ({"enabled": True, "branch": "gh-pages"}, "pages.branch"),
])
def test_pages_block_rejects_bad_values(tmp_guide, values, key):
    root = antora_guide(tmp_guide)
    set_pages(root, **values)
    assert key in config_error(guidecfg.load_guide, root)

def test_pages_rejected_for_gfm(tmp_guide):
    root = make_gfm_guide(tmp_guide)
    set_pages(root, enabled=True)
    msg = config_error(guidecfg.load_guide, root)
    assert "pages" in msg and "antora or mkdocs" in msg

def test_pages_enabled_without_url_is_valid(tmp_guide):   # no remote yet
    root = antora_guide(tmp_guide)
    set_pages(root, enabled=True)
    assert guidecfg.load_guide(root).pages == guidecfg.Pages(enabled=True, url="")

def test_get_pages_keys(tmp_guide):
    root = antora_guide(tmp_guide)
    assert guidecfg.GET_KEYS["pages.enabled"](guidecfg.load_guide(root)) == "false"
    set_pages(root, enabled=True, url="https://o.github.io/r/")
    g = guidecfg.load_guide(root)
    assert guidecfg.GET_KEYS["pages.enabled"](g) == "true"
    assert guidecfg.GET_KEYS["pages.url"](g) == "https://o.github.io/r/"
```

An embedded guide is always gfm, so the gfm rejection covers it; no separate embedded test.

- [ ] **Step 2: Run to verify they fail**

Run: `uv run --with pytest --with pyyaml pytest tests/toolkit/test_guidecfg.py -k pages -v` (or `make test` filtered the same way)
Expected: FAIL (`AttributeError: module 'guidecfg' has no attribute 'Pages'` / unknown key `pages`)

- [ ] **Step 3: Implement `_load_pages(c: _Checker, value: Any, fmt: Any) -> Pages | None` in `guide/toolkit/guidecfg.py`**

Follow `_load_publish`: `c.mapping(value, "pages", PAGES_KEYS)`, `c.boolean` for `enabled` (default False). `url` defaults to `""`; a non-empty value must be a string starting with `https://` and ending with `/`, else `c.add("pages.url", ...)`. When `fmt` is not `antora` or `mkdocs`, `c.add("pages", f"GitHub Pages needs the antora or mkdocs format (got {fmt!r})")`. Call it from `load_guide` only when `"pages" in data`, add `"pages"` to `GUIDE_KEYS`, pass `pages=` to `Guide(...)`, add the two `GET_KEYS` entries and list them in the docstring.

- [ ] **Step 4: Add the commented example to `guide/templates/guide.yaml`**

```yaml
# GitHub Pages (antora and mkdocs only; .github/workflows/guide-pages.yml). /guide:create
# writes this block when the author opts in. The site is public even for a private repository.
# pages:
#   enabled: true
#   url: https://<owner>.github.io/<repo>/
```

- [ ] **Step 5: Run the full toolkit suite**

Run: `make test`
Expected: all pass, including the new `pages` tests and the existing `test_guidecfg.py` template checks.

- [ ] **Step 6: Commit**

```bash
git add guide/toolkit/guidecfg.py guide/templates/guide.yaml tests/toolkit/test_guidecfg.py
git commit -m "feat(toolkit): pages block in guide.yaml

Assisted-By: 🤖 Claude Code"
```

---

### Task 2: `guide-pages.yml` workflow template

**Files:**
- Create: `guide/templates/guide-pages.yml`
- Test: `tests/toolkit/test_workflows.py` (reuses its `render(name, guide_dir)` helper)

**Interfaces:**
- Produces: template with the single placeholder `{{GUIDE_DIR}}` (always rendered to `.`); jobs `build` and `deploy`.

- [ ] **Step 1: Write the failing tests**

```python
def test_pages_workflow():
    data = render("guide-pages.yml", ".")
    text = (TEMPLATES / "guide-pages.yml").read_text()
    assert data["on"]["push"]["branches"] == ["main"] and "workflow_dispatch" in data["on"]
    assert data["permissions"] == {"contents": "read", "pages": "write", "id-token": "write"}
    assert data["concurrency"] == {"group": "pages", "cancel-in-progress": False}
    assert data["defaults"] == {"run": {"working-directory": "."}}
    steps = data["jobs"]["build"]["steps"]
    checkout = next(s for s in steps if s.get("uses", "").startswith("actions/checkout"))
    assert checkout["with"] == {"fetch-depth": 0, "persist-credentials": False}
    runs = [s.get("run", "") for s in steps]
    site = next(i for i, r in enumerate(runs) if r.strip() == "make site")
    leak = next(i for i, r in enumerate(runs) if "leakcheck.py build/site" in r)
    upload = next(i for i, s in enumerate(steps) if s.get("uses", "").startswith("actions/upload-pages-artifact"))
    assert site < leak < upload
    assert steps[upload]["with"]["path"] == "build/site"
    assert not any(s.get("continue-on-error") for s in steps)
    deploy = data["jobs"]["deploy"]
    assert deploy["needs"] == "build" and deploy["environment"]["name"] == "github-pages"
    assert any(s.get("uses", "").startswith("actions/deploy-pages") for s in deploy["steps"])
    assert "secrets." not in text and "site-internal" not in text and "fetch-baseline" not in text
    assert chr(0x2014) not in text and chr(0x2013) not in text
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --with pytest --with pyyaml pytest tests/toolkit/test_workflows.py -k pages -v`
Expected: FAIL with `FileNotFoundError` for `guide-pages.yml`

- [ ] **Step 3: Write `guide/templates/guide-pages.yml`**

Header comment in the style of `guide-drift.yml`: what installs it, that it publishes only the shareable view, that the site is public even for a private repository, that Pages must be set to "GitHub Actions" (the `gh api` command), and that it needs no secrets because `make site` builds from committed pages and `baseline.yaml`. Build job steps in order: `actions/checkout@v4` (with the two keys above), `actions/setup-node@v4` (`node-version: "22"`), `astral-sh/setup-uv@v6`, `make site` (env `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD: "1"`; the Antora Makefile's `node_modules` target runs `npm install`, MkDocs runs through `uvx`), `uv run --quiet tools/guide/leakcheck.py build/site`, `actions/configure-pages@v5`, `actions/upload-pages-artifact@v3` with `path: build/site`. The `{{GUIDE_DIR}}` default affects `run` steps only; `path` is relative to the workspace, which equals `.` here. Deploy job: `needs: build`, `environment: {name: github-pages, url: ${{ steps.deployment.outputs.page_url }}}`, one step `actions/deploy-pages@v4` with `id: deployment`.

- [ ] **Step 4: Run to verify it passes**

Run: `make test`
Expected: all pass.

- [ ] **Step 5: Smoke-build check (local, no network deploy)**

Run, in a throwaway Antora guide created by `bash guide/scripts/scaffold-project.sh --format antora --title "Pages smoke" "$SCRATCH/pages-smoke"` after `git init` and one commit: `make site && uv run --quiet tools/guide/leakcheck.py build/site`
Expected: exit 0 and `build/site/index.html` exists. This confirms the two commands the workflow runs work without `fetch-baseline`. If `make site` needs anything from `.guide/cache/`, stop and report; the workflow design assumes it does not.

- [ ] **Step 6: Commit**

```bash
git add guide/templates/guide-pages.yml tests/toolkit/test_workflows.py
git commit -m "feat(templates): GitHub Pages workflow for Antora and MkDocs guides

Assisted-By: 🤖 Claude Code"
```

---

### Task 3: create skill and README

**Files:**
- Modify: `guide/skills/create/SKILL.md` (section 4 intake list after question 13; embedded intake list; section 9 wrap-up; section 11 Workflows)
- Modify: `README.md` (line 110 area, the sentence about the opt-in drift check)
- Test: `tests/toolkit/test_workflows.py` (skill text test)

**Interfaces:**
- Consumes: `guide/templates/guide-pages.yml` (Task 2); `pages.enabled`, `pages.url` (Task 1).

- [ ] **Step 1: Write the failing test**

```python
SKILL = Path(__file__).resolve().parents[2] / "guide" / "skills" / "create" / "SKILL.md"

def test_create_skill_offers_pages():
    text = SKILL.read_text()
    assert "Publish the shareable view on GitHub Pages? (default no)" in text
    assert "public on the web" in text and "paid GitHub plan" in text
    assert "guide-pages.yml" in text and "pages.enabled: true" in text
    assert "gh api -X POST repos/<owner>/<repo>/pages -f build_type=workflow" in text
    assert "deploys fail until Pages is switched on" in text
    assert "`site.url` in `site.yml`" in text and "`site_url` in `mkdocs.yml`" in text
    assert chr(0x2014) not in text and chr(0x2013) not in text
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --with pytest --with pyyaml pytest tests/toolkit/test_workflows.py -k create_skill -v`
Expected: FAIL on the first assertion.

- [ ] **Step 3: Edit `guide/skills/create/SKILL.md`**

- Section 4, new question 14 (separate guide, format `antora` or `mkdocs` only): "Publish the shareable view on GitHub Pages? (default no)". When the remote is or will be private, say first that the site is public on the web regardless of repository visibility and that Pages from a private repository needs a paid GitHub plan. The internal view is never published.
- Embedded intake: add "**GitHub Pages**: not offered (gfm renders on GitHub)."
- Section 9, new step between 1 and 2, "**GitHub Pages** (when opted in)": render the template as in section 11; set `site.url` in `site.yml` (Antora; not in `site-internal.yml`) or `site_url` in `mkdocs.yml` to `https://<owner>.github.io/<repo>/` when the remote is known; write `pages: {enabled: true, url: ...}` to `guide.yaml` (`url` omitted without a remote) and run `uv run tools/guide/guidecfg.py validate`; commit `ci: publish the guide with GitHub Pages`; with a GitHub remote, show `gh api -X POST repos/<owner>/<repo>/pages -f build_type=workflow` and run it only after approval. The report (step 5) names the URL, and when Pages was not switched on, the enable command and that deploys fail until Pages is switched on.
- Section 11: new bullet for `guide-pages.yml` at `.github/workflows/guide-pages.yml`, rendered with `{{GUIDE_DIR}}` = `.`, installed at wrap-up so pushes during page tasks never deploy. Extend "Before writing either file" to "any of these files".

- [ ] **Step 4: Update `README.md`**

Next to the drift check sentence, one sentence: the opt-in Pages workflow (`.github/workflows/guide-pages.yml`) publishes the shareable view of Antora and MkDocs guides at `https://<owner>.github.io/<repo>/`.

- [ ] **Step 5: Verify**

Run: `make test && make validate && rg -n "$(printf '—|–')" guide/skills/create/SKILL.md README.md guide/templates/guide-pages.yml brainstorm/08-pages-deploy.md || echo clean`
Expected: tests pass, plugin validation passes, `clean`.

- [ ] **Step 6: Commit**

```bash
git add guide/skills/create/SKILL.md README.md tests/toolkit/test_workflows.py
git commit -m "feat(create): offer GitHub Pages deployment for Antora and MkDocs guides

Assisted-By: 🤖 Claude Code"
```
