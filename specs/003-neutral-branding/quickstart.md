# Quickstart: validate the neutral theme

Runnable checks that prove the feature end to end. Run from the plugin checkout unless noted. Prerequisites: `uv`, `node` 20+, `npx`, Playwright Chromium, `pandoc`, `pdffonts` (poppler), the same tool chain as `make test-adapters`.

## 1. Unit and contract tests

```bash
make test                                  # includes the new branding, playbook, check, scaffold cases
uv run guide/toolkit/branding.py contract \
  --bundle https://github.com/rhpds/rhdp_showroom_theme/releases/download/v2.0.3/ui-bundle.zip
```

Expected: all tests pass; the contract check prints nothing and exits 0 (it now includes `font-stacks`, `navbar-rule`, `navbar-css`).

## 2. A neutral wordmark guide (User Story 1)

```bash
bash tests/adapters/scaffold.sh antora /tmp/neutral-guide   # existing fixture helper
cd /tmp/neutral-guide
cat >> guide.yaml <<'YAML'
branding:
  wordmark: OpenClaw on OpenShift
  theme: neutral
  footer: none
YAML
make check
```

Expected:

- `build/site/_/img/logo-guide.svg` has no `<text>` and has `<path>` elements; its alt text on every page is "OpenClaw on OpenShift".
- `build/site/_/font/` holds the six `.woff2` files and `OFL.txt`; `build/site/_/css/theme-neutral.css` exists and every page links it.
- `make check` passes; removing `build/site/_/font/OFL.txt` and rerunning only the check step reports `[branding] neutral theme font missing: OFL.txt`.

Browser check (scripted in `tests/adapters/test_antora_neutral.sh`): open `build/site/index.html` in Chromium with no Red Hat fonts installed; `document.fonts.check('16px "Red Hat Text"')` is true after load, the computed `box-shadow` of `.navbar` is `rgb(238, 0, 0) 0px -3px 0px 0px inset`, and `.navbar` is still `3.5rem` high.

## 3. Hat variant (User Story 2)

Replace `wordmark:` with `logo_text: OpenShift AI` and rebuild. Expected: the logo keeps the hat and the MPL-2.0 comment, the product name is outlined, the alt text is "Red Hat OpenShift AI".

## 4. Unchanged guides (User Story 3)

Build a fixture with no block and one with `logo_text` and no `theme`, on `main` and on this branch, and compare:

```bash
diff -r build-main/site build-branch/site      # no output expected, timestamps aside
```

The adapter test automates this against stored golden files.

## 5. PDF (User Story 4)

```bash
make pdf
pdffonts dist/*.pdf | rg -i 'redhat'
```

Expected: Red Hat Text, Display, and Mono appear as embedded fonts; the title page band has the red rule. The printer log shows no blocked font request.

## 6. Validation messages

Set `wordmark: 漢字` and run `uv run tools/guide/guidecfg.py validate`. Expected: `guide.yaml:branding.wordmark: no glyph for "漢" (U+6F22) in Red Hat Display`, exit 1. Set both `wordmark` and `logo_text`: `guide.yaml:branding: set exactly one of logo_text, wordmark, or logo`. Set `theme: dark`: `guide.yaml:branding.theme: must be neutral or stock (got dark)`.

## 7. Create intake (manual)

Run `/guide:create` for a scratch Antora guide, answer "no" to the Red Hat product question, accept the title as wordmark. Expected `guide.yaml` block: `wordmark: <title>`, `theme: neutral`, `footer: none`. Record the run in `tests/manual/003-neutral-branding.md`.
