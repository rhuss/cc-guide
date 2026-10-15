#!/usr/bin/env node
// Browser probe for the neutral theme (specs/003-neutral-branding): open a built page in
// Chromium at 1280 x 800 with every Google Fonts request blocked (and counted), wait until
// the fonts settle, and print one JSON object with the Red Hat faces that loaded (with
// Google blocked, only vendored files can supply them), the number of Google Fonts
// requests the page made, the computed font family of the body, and the computed box
// shadow and height of the navigation bar. The caller asserts on it.
//
//   node tests/adapters/measure_neutral.mjs <guide root> [<built site dir>]
//
// Playwright comes from the guide project's node_modules. Exits 2 on a usage error and 1
// when the page does not load.
import { createRequire } from 'node:module';
import { existsSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const [rootArg, siteArg] = process.argv.slice(2);
if (!rootArg) {
  console.error('usage: measure_neutral.mjs <guide root> [<built site dir>]');
  process.exit(2);
}
const root = resolve(rootArg);
const site = resolve(siteArg || join(root, 'build', 'site'));
const page = join(site, 'guide', 'index.html');
if (!existsSync(page)) {
  console.error(`missing ${page} (build the site first)`);
  process.exit(2);
}

const require = createRequire(join(root, 'package.json'));
const { chromium } = require('playwright');
const browser = await chromium.launch();
try {
  const tab = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  let googleRequests = 0;
  await tab.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, (route) => {
    googleRequests += 1;
    return route.abort();
  });
  const response = await tab.goto(pathToFileURL(page).href, { waitUntil: 'load' });
  if (!response) {
    console.error(`could not load ${page}`);
    process.exit(1);
  }
  const result = await tab.evaluate(async () => {
    await document.fonts.ready;
    // document.fonts.check() is also true when no @font-face matches (a system font), so
    // count the faces that actually loaded from the stylesheet instead.
    const loaded = [...document.fonts]
      .filter((face) => face.status === 'loaded')
      .map((face) => `${face.family.replace(/"/g, '')} ${face.style}`);
    const navbar = document.querySelector('.navbar');
    const nav = navbar ? getComputedStyle(navbar) : null;
    return {
      loaded: [...new Set(loaded)].sort(),
      bodyFont: getComputedStyle(document.body).fontFamily,
      navbarShadow: nav ? nav.boxShadow : null,
      navbarHeight: navbar ? navbar.getBoundingClientRect().height : null,
    };
  });
  console.log(JSON.stringify({ ...result, googleRequests }));
} finally {
  await browser.close();
}
