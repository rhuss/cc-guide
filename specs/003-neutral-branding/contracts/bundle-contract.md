# Contract: UI bundle rules added for the neutral theme

`guide/adapters/antora/branding/contract.yaml` replaces the spec 002 rule `head-styles-site-css` with `head-styles-stock`, which pins the whole stock `partials/head-styles.hbs` (its three Google Fonts links and the `css/site.css` link) with `equals`, because the neutral theme drops the Google Fonts links (research R11). It also gains these rules, checked by `uv run tools/guide/branding.py contract --bundle <bundle>` and by the adapter tests against the pinned v2.0.3 bundle. The rule format is spec 002's (`specs/002-antora-branding/contracts/bundle-contract.md`).

```yaml
  # The vendored @font-face rules use the family names the bundle's font stacks
  # already name, so the stacks resolve to the vendored fonts without overrides.
  - id: font-stacks
    file: css/site.css
    contains: ['Red Hat Text,RedHatText', 'Red Hat Display,RedHatDisplay', 'Red Hat Mono,RedHatMono']
  # The neutral theme's red rule is an inset box shadow on the fixed navigation bar.
  - id: navbar-rule
    file: partials/header-content.hbs
    contains: ['<nav class="navbar">']
  - id: navbar-css
    file: css/site.css
    contains: ['.navbar{background:#151515', 'position:fixed']
```

All strings were taken from the unpacked v2.0.3 bundle. A newer bundle that renames a family or replaces the navbar fails the check with the rule id before any guide switches to it.
