---
name: preview
description: Build a guide with its output adapter and serve it locally with live reload, then open it in the browser; shareable or internal view. Works during a create or evolve run and from a linked git worktree. Use for /guide:preview.
argument-hint: "[--internal] [--port N] [--dir PATH]"
allowed-tools: ["Bash", "Read"]
---

# /guide:preview

Shows the rendered guide in a browser within a minute and keeps it current while pages change (FR-030, SC-008).

## Steps

1. The command wrapper runs `guide:preflight` with `preview` (it needs a guide project and a passing `make doctor`); stop when it stops.
2. View: `--internal` selects the internal view (`VIEW=internal`). When `guide.yaml` has `internal.enabled: false`, say there is no internal part and serve the shareable view.
3. Port: `--port N`, otherwise the adapter's `preview_port` from `tools/guide/adapter.yaml` (8000 by default). When the port is taken (`lsof -iTCP:<port> -sTCP:LISTEN`), pick the next free one and say so.
4. Start the server in the background from the guide project root:

   ```bash
   make preview VIEW=<shareable|internal> PORT=<port> OPEN=0
   ```

   Run it with the Bash tool's background mode and remember the shell id. Per adapter this is:
   - antora: `tools/guide/preview-watch.mjs`: rebuilds 300 ms after a change, queues changes that arrive during a build, keeps the last good site when a build fails (and prints the error), and reloads the browser after each successful build
   - mkdocs: the same watcher with `mkdocs build --strict` into a staging directory, so a broken page keeps the last good site
   - gfm: `markserv` with its own reload
5. Wait until the URL answers (poll `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:<port>/` until it returns 200, at most 60 seconds). When it does not come up, show the last lines of the server output and stop it.
6. Open it on macOS with `open http://127.0.0.1:<port>/` (on Linux `xdg-open`). `OPEN=0` keeps the adapter from opening a second browser tab; run by hand, `make preview` opens the browser itself.
7. Report the URL, the view, that edits refresh the page, and how to stop it (ask Claude to stop the preview, or `kill` the background shell). When a build fails while preview runs, show the error; the last good site stays visible.

## Notes

- Preview never writes into the content directories; it builds into `build/`.
- In a linked git worktree (for example `.claude/worktrees/<branch>`), the Antora adapter builds from a generated playbook (`tools/guide/playbook.py`), so preview shows the worktree's branch including uncommitted edits (FR-016a).
- Preview can run while a create or evolve run is in progress; it shows the pages written so far.
