# Contract: UI bundle contract file

`guide/adapters/antora/branding/contract.yaml` (vendored as `tools/guide/branding/contract.yaml`):

```yaml
# Parts of the pinned RHDP showroom UI bundle that the branding overlay relies on.
bundle: https://github.com/rhpds/rhdp_showroom_theme/releases/download/v2.0.3/ui-bundle.zip
rules:
  - id: logo-lookup
    file: partials/header-content.hbs
    matches:
      - 'img/logo-\{\{or site\.keys\.navbarLogo'
      - 'navbar-logo-alt \(or site\.keys\.navbarLogo'
      - 'class="navbar-logo-img"'
  - id: alt-helper
    file: helpers/navbar-logo-alt.js
    exists: true
  - id: footer-partial
    file: partials/footer-content.hbs
    contains: ['<footer class="footer">', 'demo.redhat.com', 'class="poweredBy"']
  - id: layout-includes
    file: layouts/default.hbs
    contains: ['{{> head ', '{{> header}}', '{{> footer}}']
  - id: layout-404-includes
    file: layouts/404.hbs
    contains: ['{{> head ', '{{> header}}', '{{> footer}}']
  - id: header-include
    file: partials/header.hbs
    contains: ['{{> header-content}}']
  - id: footer-include
    file: partials/footer.hbs
    contains: ['{{> footer-content}}']
  - id: head-order
    file: partials/head.hbs
    matches: ['head-styles\}\}[\s\S]*head-meta\}\}[\s\S]*head-icons\}\}']
  - id: head-styles-site-css
    file: partials/head-styles.hbs
    contains: ['/css/site.css']
  - id: head-meta-stock
    file: partials/head-meta.hbs
    equals: '<link rel="icon" href="{{uiRootPath}}/img/favicon.ico" type="image/x-icon">'
  - id: head-icons-stock
    file: partials/head-icons.hbs
    equals: '<link rel="icon" href="{{{uiRootPath}}}/img/favicon.ico" type="image/x-icon">'
  - id: site-css
    file: css/site.css
    contains: ['.navbar-logo-img{height:2rem;width:auto}', '--navbar-background:var(--color-jet-70)', '--color-jet-70:#151515']
  - id: stock-logo
    file: img/logo-demo-platform.svg
    contains: ['viewBox="0 0 1080 178.739"', 'translate(308 149)', 'font-size="82"', '<tspan x="0" y="0">Demo Platform</tspan>']
accent_color: "#06c"
accent_hover_color: "#004d99"
accent_selectors:            # color: <accent> in branding.css; each must appear with #06c in css/site.css
  - {selector: '.doc a', property: color}
  - {selector: '.toc .toc-menu a:hover', property: color}
  - {selector: '.toc .toc-menu a.is-active', property: border-left-color}
  - {selector: ':focus-visible', property: outline-color}
  - {selector: '.skip-link', property: color}
  - {selector: '#search-input:focus', property: border-color}
accent_hover_selectors:      # hover shade; each must appear with #004d99 in css/site.css
  - {selector: '.doc a:hover', property: color}
accent_restore_selectors:    # restated after the hover rules; each must appear with its value in css/site.css
  - {selector: '.doc a.unresolved', property: color, value: '#e00'}
  - {selector: '.toc .toc-menu a.is-active', property: color, value: '#151515'}
```

`equals` compares after stripping leading and trailing whitespace from both sides: the stock `partials/head-icons.hbs` is indented by four spaces.

Every rule requires its file to exist; `exists: true` marks a rule that checks only that. Any other rule key, and `exists` with a value other than `true`, makes the checker stop with an error.

The checker treats each `accent_selectors` and `accent_hover_selectors` entry as an additional rule (`accent:<selector>`), and each `accent_restore_selectors` entry as one more (`restore:<selector>`): `css/site.css` must contain a rule for the selector whose declarations include the stock color (or the entry's `value`). The restore entries cover rules that follow an accent or hover rule in `css/site.css` with the same specificity and would otherwise be overridden by `branding.css` (an unresolved link stays red on hover, a hovered active table-of-contents entry keeps its dark text). The values above are the ones of the pinned v2.0.3 bundle.

Failure output: `contract: <rule id>: <file>: <missing file | missing "<string>" | no match for /<regex>/ | content differs from the recorded stock content>`; exit 1.
