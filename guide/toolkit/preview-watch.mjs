#!/usr/bin/env node
// Live preview for Antora and MkDocs guide projects (FR-030, research R9a).
//
//   node tools/guide/preview-watch.mjs [--internal] [--port N] [--no-open] [--root DIR]
//
// Builds the shareable (or, with --internal, the internal) view into a staging
// directory and swaps it into the served directory only when the build succeeds, so a
// broken page never replaces the last good site; the error is printed instead.
// chokidar watches the content sources; changes are debounced (300 ms), and changes
// that arrive during a build queue exactly one follow-up build. browser-sync serves the
// site and reloads the browser after every successful build (its client is injected
// into responses served as text/html, which Antora's .html pages are).
// Antora: the playbook comes from tools/guide/playbook.py, so a linked git worktree works too.
// MkDocs: `mkdocs build --strict` into the staging dir (mkdocs serve would stop or show a
// broken page instead of keeping the last good site). The format is read from
// tools/guide/adapter.yaml.
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';

const USAGE = 'usage: preview-watch.mjs [--internal] [--port N] [--no-open] [--root DIR]';

function parseArgs(argv) {
  const opts = { internal: false, port: 8000, open: true, root: '.' };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--internal') opts.internal = true;
    else if (arg === '--no-open') opts.open = false;
    else if (arg === '--port' || arg === '--root') {
      if (i + 1 >= argv.length || argv[i + 1].startsWith('--')) { console.error(`${arg} requires a value`); process.exit(2); }
      const value = argv[++i];
      if (arg === '--port') {
        opts.port = Number(value);
        if (!Number.isInteger(opts.port) || opts.port <= 0) { console.error(`bad port: ${value}`); process.exit(2); }
      } else opts.root = value;
    } else if (arg === '-h' || arg === '--help') { console.log(USAGE); process.exit(0); }
    else { console.error(`unknown argument: ${arg}\n${USAGE}`); process.exit(2); }
  }
  return opts;
}

const opts = parseArgs(process.argv.slice(2));
const root = resolve(opts.root);
const view = opts.internal ? 'internal' : 'shareable';
const require = createRequire(join(root, 'package.json'));
let chokidar; let browserSync;
try {
  chokidar = require('chokidar');
  browserSync = require('browser-sync');
} catch (err) {
  console.error(`[preview] missing Node packages in ${root} (run npm install): ${err.message}`);
  process.exit(1);
}

const adapterFile = join(root, 'tools', 'guide', 'adapter.yaml');
const format = existsSync(adapterFile)
  ? ((readFileSync(adapterFile, 'utf8').match(/^format:\s*["']?(\w+)/m) || [])[1] || 'antora')
  : 'antora';
if (!['antora', 'mkdocs'].includes(format)) {
  console.error(`[preview] the watcher supports the antora and mkdocs formats, not ${format}`);
  process.exit(2);
}

const previewDir = join(root, 'build', 'preview');
const served = join(previewDir, view);
const staging = join(previewDir, `.staging-${view}`);
const log = (msg) => console.log(`[preview] ${msg}`);

// The running build, if any. It runs in its own process group so stopping the preview
// also stops uv, npx, Antora, or MkDocs underneath it.
let activeChild = null;

function run(command, env = {}) {
  return new Promise((resolveRun) => {
    const child = spawn('bash', ['-c', command], { cwd: root, env: { ...process.env, ...env }, detached: true });
    activeChild = child;
    let out = '';
    child.stdout.on('data', (d) => { out += d; });
    child.stderr.on('data', (d) => { out += d; });
    child.on('close', (code) => { activeChild = null; resolveRun({ code, out }); });
    child.on('error', (err) => { activeChild = null; resolveRun({ code: 1, out: String(err) }); });
  });
}

function stopBuild() {
  if (!activeChild) return;
  try { process.kill(-activeChild.pid, 'SIGTERM'); } catch { /* already gone */ }
}

// One build into the staging dir; swapped in only on success.
async function buildOnce() {
  const started = Date.now();
  log(`building the ${view} view...`);
  rmSync(staging, { recursive: true, force: true });
  const command = format === 'mkdocs'
    ? 'uvx --quiet --with-requirements requirements.txt mkdocs build --strict '
      + `-f ${opts.internal ? 'mkdocs-internal.yml' : 'mkdocs.yml'} -d "$STAGING"`
    : 'set -o pipefail; '
      + `playbook=$(uv run --quiet tools/guide/playbook.py path ${opts.internal ? '--internal' : ''}) || exit 1; `
      + 'attrs=$(uv run --quiet tools/guide/attrs.py export --format antora) || exit 1; '
      + 'eval "npx --no-install antora --log-failure-level=warn $attrs --to-dir \\"$STAGING\\" \\"$playbook\\""';
  const { code, out } = await run(command, { STAGING: staging });
  const seconds = ((Date.now() - started) / 1000).toFixed(1);
  if (code !== 0 || !existsSync(join(staging, 'index.html'))) {
    console.error(`[preview] build FAILED after ${seconds}s; keeping the last good site. Error:`);
    console.error(out.trim().split('\n').slice(-25).join('\n'));
    rmSync(staging, { recursive: true, force: true });
    return false;
  }
  const old = join(previewDir, `.old-${view}`);
  rmSync(old, { recursive: true, force: true });
  if (existsSync(served)) renameSync(served, old);
  renameSync(staging, served);
  rmSync(old, { recursive: true, force: true });
  log(`build ok in ${seconds}s`);
  return true;
}

let building = false;
let pending = false;
let timer = null;
let bs = null;

async function trigger() {
  if (building) { pending = true; return; }
  building = true;
  try {
    do {
      pending = false;
      if (await buildOnce() && bs) bs.reload();
    } while (pending);
  } finally {
    building = false;
  }
}

function schedule(event, path) {
  log(`${event}: ${path.startsWith(root) ? path.slice(root.length + 1) : path}`);
  clearTimeout(timer);
  timer = setTimeout(trigger, 300);
}

async function main() {
  mkdirSync(previewDir, { recursive: true });
  building = true;
  const ok = await buildOnce();
  building = false;
  if (!ok && !existsSync(served)) {
    mkdirSync(served, { recursive: true });
    writeFileSync(join(served, 'index.html'), '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Preview</title></head>'
      + '<body><h1>The first build failed</h1><p>See the terminal for the error. The page reloads after the next successful build.</p></body></html>');
  }

  const sources = format === 'mkdocs'
    ? ['docs', 'mkdocs.yml', 'mkdocs-internal.yml', 'requirements.txt', 'tools/guide/mkdocs_macros.py']
    : ['content', 'site.yml', 'site-internal.yml'].concat(opts.internal ? ['internal'] : []);
  const watched = sources.concat(['baseline.yaml', 'guide.yaml'])
    .map((p) => join(root, p))
    .filter((p) => existsSync(p));
  const watcher = chokidar.watch(watched, {
    ignoreInitial: true,
    ignored: (p) => /(^|[/\\])(node_modules|build|\.git|\.guide)([/\\]|$)/.test(p.slice(root.length)),
    awaitWriteFinish: { stabilityThreshold: 100, pollInterval: 50 },
  });
  watcher.on('all', (event, path) => schedule(event, path));
  if (pending) trigger();

  bs = browserSync.create('guide-preview');
  bs.init({
    server: { baseDir: served },
    port: opts.port,
    open: opts.open ? 'local' : false,
    notify: false,
    ui: false,
    ghostMode: false,
    logLevel: 'silent',
    files: false,
  }, () => {
    const url = bs.getOption('urls').get('local');
    log(`serving the ${view} view at ${url} (Ctrl-C to stop)`);
  });

  const stop = () => {
    log('stopping');
    stopBuild();
    watcher.close().finally(() => { bs.exit(); process.exit(0); });
  };
  process.on('SIGINT', stop);
  process.on('SIGTERM', stop);
}

main().catch((err) => {
  console.error(`[preview] ${err.stack || err}`);
  process.exit(1);
});
