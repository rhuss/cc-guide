#!/usr/bin/env node
// SC-004 measurement for a branded Antora guide (specs/002-antora-branding): in Chromium at
// a 1280 x 800 window, the header logo must end left of the site title next to it, and the
// text of the rendered logo-guide.svg must lie inside the SVG's viewBox (not clipped), with
// whatever font Chromium resolves from the logo's font-family list.
//
//   node tests/adapters/measure_logo.mjs <guide root> [<built site dir>]
//
// Playwright comes from the guide project's node_modules. Prints PASS/FAIL lines and exits
// 1 on a failure, 2 on a usage error.
import { createRequire } from 'node:module';
import { existsSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const [rootArg, siteArg] = process.argv.slice(2);
if (!rootArg) {
  console.error('usage: measure_logo.mjs <guide root> [<built site dir>]');
  process.exit(2);
}
const root = resolve(rootArg);
const site = resolve(siteArg || join(root, 'build', 'site'));
const page = join(site, 'guide', 'index.html');
const logo = join(site, '_', 'img', 'logo-guide.svg');
for (const file of [page, logo]) {
  if (!existsSync(file)) {
    console.error(`missing ${file} (build the site first)`);
    process.exit(2);
  }
}

const require = createRequire(join(root, 'package.json'));
const { chromium } = require('playwright');
let failures = 0;
const result = (ok, message) => {
  console.log(`${ok ? 'PASS' : 'FAIL'} ${message}`);
  if (!ok) failures += 1;
};

const browser = await chromium.launch();
try {
  const tab = await browser.newPage({ viewport: { width: 1280, height: 800 } });

  await tab.goto(pathToFileURL(page).href, { waitUntil: 'load' });
  const header = await tab.evaluate(() => {
    const img = document.querySelector('.navbar-logo-img');
    const title = document.querySelector('.site-title');
    if (!img || !title) return null;
    const a = img.getBoundingClientRect();
    const b = title.getBoundingClientRect();
    return { logoLeft: a.left, logoRight: a.right, logoWidth: a.width, titleLeft: b.left, loaded: img.complete && img.naturalWidth > 0 };
  });
  if (!header) {
    result(false, 'header has a .navbar-logo-img and a .site-title');
  } else {
    result(header.loaded, 'the header logo image loads');
    result(header.logoRight <= header.titleLeft,
      `header logo (${header.logoLeft.toFixed(0)} to ${header.logoRight.toFixed(0)} px) ends before the site title (${header.titleLeft.toFixed(0)} px)`);
  }

  await tab.goto(pathToFileURL(logo).href, { waitUntil: 'load' });
  const box = await tab.evaluate(() => {
    const svg = document.documentElement;
    const text = svg.querySelector('text');
    if (!text) return null;
    const [, , width, height] = svg.getAttribute('viewBox').split(/\s+/).map(Number);
    const b = text.getBBox();
    const m = text.transform.baseVal.consolidate()?.matrix || new DOMMatrix();
    const corners = [[b.x, b.y], [b.x + b.width, b.y], [b.x, b.y + b.height], [b.x + b.width, b.y + b.height]]
      .map(([x, y]) => [m.a * x + m.c * y + m.e, m.b * x + m.d * y + m.f]);
    const xs = corners.map((c) => c[0]);
    const ys = corners.map((c) => c[1]);
    return { width, height, left: Math.min(...xs), right: Math.max(...xs), top: Math.min(...ys), bottom: Math.max(...ys),
      content: text.textContent };
  });
  if (!box) {
    result(false, 'logo-guide.svg has a <text> element');
  } else {
    const inside = box.left >= -0.5 && box.top >= -0.5 && box.right <= box.width + 0.5 && box.bottom <= box.height + 0.5;
    result(inside, `logo text "${box.content}" (${box.left.toFixed(1)} to ${box.right.toFixed(1)}) lies inside the viewBox `
      + `(0 to ${box.width})`);
  }
} finally {
  await browser.close();
}
process.exit(failures ? 1 : 0);
