# Quickstart: validate nested guide discovery

Prerequisites: `uv`, this checkout. Run from the repository root.

```bash
T=$(mktemp -d)
G=guide/templates/guide.yaml   # any valid guide.yaml

# 1. cc-review layout: standalone guide two levels down (US1)
mkdir -p "$T/a/docs/guide" && cp "$G" "$T/a/docs/guide/"
uv run guide/toolkit/guidecfg.py discover --dir "$T/a"; echo "exit=$?"
# expect: .../a/docs/guide, exit=0

# 2. Shallower wins (US2)
mkdir -p "$T/a/guide" && cp "$G" "$T/a/guide/"
uv run guide/toolkit/guidecfg.py discover --dir "$T/a"; echo "exit=$?"
# expect: .../a/guide, exit=0

# 3. Tie at the same depth exits 3 (US2)
mkdir -p "$T/b/docs/guide" "$T/b/site/guide"
cp "$G" "$T/b/docs/guide/"; cp "$G" "$T/b/site/guide/"
uv run guide/toolkit/guidecfg.py discover --dir "$T/b"; echo "exit=$?"
# expect: both paths sorted on stdout, message on stderr, exit=3

# 4. Pruned locations only (US4)
mkdir -p "$T/c/node_modules/x" "$T/c/.guide/cache/x" "$T/c/build"
cp "$G" "$T/c/node_modules/x/"; cp "$G" "$T/c/.guide/cache/x/"; cp "$G" "$T/c/build/"
uv run guide/toolkit/guidecfg.py discover --dir "$T/c"; echo "exit=$?"
# expect: exit=4

# 5. Depth 4 is not found (US4)
mkdir -p "$T/d/a/b/c/guide" && cp "$G" "$T/d/a/b/c/guide/"
uv run guide/toolkit/guidecfg.py discover --dir "$T/d"; echo "exit=$?"
# expect: exit=4

rm -rf "$T"
```

Full suite: `make test` (discovery tests in `tests/toolkit/test_guidecfg.py`, section `discover`).

Preflight check (US1 AS2): `get embedded.front_page` needs a fully valid configuration (the template above has placeholders and fails `get`). Copy the test fixture guide instead: `cp -R tests/fixtures/sample-guide "$T/e/docs/guide"` (after `mkdir -p "$T/e/docs"`), resolve it with `discover --dir "$T/e"`, then `uv run guide/toolkit/guidecfg.py get embedded.front_page --root "$T/e/docs/guide"` prints an empty line, so preflight reports `embedded=no`.
