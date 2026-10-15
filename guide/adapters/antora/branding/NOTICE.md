# Notice: files derived from the RHDP showroom theme

`logo-text.svg.tmpl` in this directory is derived from `img/logo-demo-platform.svg` of the RHDP showroom UI theme, release v2.0.3:

- Upstream repository: https://github.com/rhpds/rhdp_showroom_theme
- Release bundle: https://github.com/rhpds/rhdp_showroom_theme/releases/download/v2.0.3/ui-bundle.zip
- License: Mozilla Public License 2.0 (MPL-2.0)

The Red Hat wordmark paths, the hat, the divider, and the text attributes are unchanged. The changes are the placeholders the branding renderer fills in (`{{VIEWBOX_WIDTH}}`, `{{TEXT}}`, `{{TEXT_LENGTH}}`) and the `textLength` and `lengthAdjust` attributes on the `<text>` element. Every logo rendered from the template (`img/logo-guide.svg` in a guide's build output) keeps the notice below as an XML comment.

The template is covered by the MPL-2.0, not by the license of this plugin. The full license text is available at https://mozilla.org/MPL/2.0/.

## Exhibit A, Source Code Form License Notice

```text
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
```

## Red Hat fonts

The `fonts/` directory holds the variable web fonts of the Red Hat font family, release 5.0.0, and their license:

- Upstream repository: https://github.com/RedHatOfficial/RedHatFont
- License: SIL Open Font License, Version 1.1 (`fonts/OFL.txt`)
- Files: `RedHatDisplay-VF.woff2`, `RedHatDisplay-Italic-VF.woff2`, `RedHatText-VF.woff2`, `RedHatText-Italic-VF.woff2`, `RedHatMono-VF.woff2`, `RedHatMono-Italic-VF.woff2`, unchanged; their checksums are in `fonts/fonts.yaml`

The fonts are covered by the OFL, not by the license of this plugin. A guide with `theme: neutral` publishes them under `_/font/` in its built site, always together with `OFL.txt`. Logos with outlined text (`wordmark`, and `logo_text` with `theme: neutral`) are a rendering of Red Hat Display glyphs into SVG paths; they are documents made with the fonts, not modified versions of the fonts.

`fonts/update-fonts.py` downloads a release and rewrites `fonts/fonts.yaml`; it stays in the plugin and is not copied into guide projects.

## Trademark

The Red Hat logo is a trademark of Red Hat, Inc. The `logo_text` setting renders it and is meant for guides about Red Hat products; guides about other products use their own `logo` (see `guide/docs/branding.md`).
