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

The Red Hat logo is a trademark of Red Hat, Inc. The `logo_text` setting renders it and is meant for guides about Red Hat products; guides about other products use their own `logo` (see `guide/docs/branding.md`).
