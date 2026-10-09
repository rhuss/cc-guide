# Session settings and permissions

A guide run is long: a create run on a 20-page guide dispatches dozens of subagents and can take hours. These settings keep it reliable without giving the session more power than it needs (FR-041, FR-042).

## Model and effort

| Setting | Recommendation | Why |
|---|---|---|
| Model of the controlling session | The most capable model available (Opus 5.5 at the time of writing) | The controller adjudicates review findings against the sources, writes rulings, and reviews diagram exports; mistakes there propagate to every page. |
| Subagent model | No override; subagents inherit the session model | The skills dispatch without a `model` parameter. A cheaper implementer model produced more factual errors per page in the SAW run. |
| Effort for create and evolve | `high` | Per-page factual verification needs careful reading of the pinned sources. |
| Effort with `--rigor strict` | `xhigh` | The claim ledger asks for an identifier and a source for every verifiable statement. |
| Effort for preview, export, upstream, validate | default | These commands are mostly deterministic. |

Every command states these recommendations at start. It can see its own model and warns when it is a smaller model; it cannot see the effort level, so it only states the recommendation (research R13).

## Permission allowlist

Pre-approve the tools a run needs in the settings Claude Code reads for the session that runs the guide command (see "Where the allowlist must live" below), so permission prompts do not stall subagents (a prompt for the Excalidraw tools once stalled a diagram task for about three hours). Keep outward actions out of the allowlist: creating repositories, pushing, filing issues, and opening pull requests should still prompt, as a second safety net behind the skills' own approval steps.

```json
{
  "permissions": {
    "allow": [
      "Bash(make:*)",
      "Bash(uv run:*)",
      "Bash(uvx:*)",
      "Bash(node tools/guide/:*)",
      "Bash(npx --no-install antora:*)",
      "Bash(npx --no-install markserv:*)",
      "Bash(npm install)",
      "Bash(git status:*)",
      "Bash(git diff:*)",
      "Bash(git log:*)",
      "Bash(git show:*)",
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(git -C .guide/cache/:*)",
      "Bash(/usr/bin/git status:*)",
      "Bash(/usr/bin/git add:*)",
      "Bash(/usr/bin/git commit:*)",
      "Bash(gh api repos/:*)",
      "Bash(gh pr view:*)",
      "Bash(gh search issues:*)",
      "Bash(rg:*)",
      "Bash(sed -n:*)",
      "Bash(shasum -a 256:*)",
      "mcp__excalidraw"
    ],
    "ask": [
      "Bash(git push:*)",
      "Bash(gh repo create:*)",
      "Bash(gh repo fork:*)",
      "Bash(gh issue create:*)",
      "Bash(gh pr create:*)"
    ]
  }
}
```

The create skill offers to add `mcp__excalidraw` when diagrams are planned.

### Where the allowlist must live

Claude Code reads permissions for a session, and for the subagents it dispatches, from:

- `.claude/settings.local.json` and `.claude/settings.json` of the directory the session runs in (the git toplevel when that directory is inside a repository)
- `~/.claude/settings.json` (user settings, for every session)

The guide project's own `.claude/settings*.json` apply only to sessions started in the guide project. When you run `/guide:create --dir <guide>` from another directory (for example a checkout of the sources, or of cc-guide itself), an allow entry in the guide project is not read, and the permission classifier denied `clear_canvas` and `import_scene` to a drawing subagent in exactly that setup. `scripts/deps.sh --dir <guide> --session-dir <session directory>` reports `excalidraw_allowed` and lists the files that hold the entry in `excalidraw_allowed_in`; the create skill offers to add `mcp__excalidraw` to the session directory's `.claude/settings.local.json`, and to the guide project's for future sessions started there. It merges into an existing file and never drops entries.

## Why not bypass all permissions

Bypassing permissions (`--dangerously-skip-permissions` or the bypass mode) removes the last check in front of the outward actions a guide run can take: creating a remote repository, pushing, filing issues on upstream projects, and running commands against a cluster. The skills ask before each of these, but a permission prompt is an independent safeguard against a skill or subagent that misreads an instruction. An allowlist removes the prompts that slow a run down and keeps the ones that matter.

## Companion plugins and servers

| Component | Needed for | Install |
|---|---|---|
| superpowers 6.3.0 or later | create, evolve (not `evolve --check`) | `claude plugin install superpowers@claude-plugins-official` |
| cc-prose | optional: voice profiles and AI-pattern checks | `claude plugin install prose@cc-rhuss-marketplace` |
| Excalidraw MCP server (`yctimlin/mcp_excalidraw` 1.0.7) | diagrams only | Add the server to the guide project's `.mcp.json` (never commit that file) or your user configuration, start its canvas, and open the canvas URL in a browser before diagram tasks run; set `EXCALIDRAW_EXPORT_DIR` (see below) |

### Excalidraw server file access

The Excalidraw MCP server reads and writes files only under its own working directory (usually the directory the Claude Code session was started in), or under `EXCALIDRAW_EXPORT_DIR` when that is set. Exporting a scene or an image into a guide project elsewhere fails with "Path traversal blocked ... Set EXCALIDRAW_EXPORT_DIR", and the diagrams skill then has to stage every file in an allowed directory and move it. Set `EXCALIDRAW_EXPORT_DIR` in the server's `env` (in `.mcp.json` or your user configuration) to a directory that contains your guide projects, next to `EXPRESS_SERVER_URL`, and restart Claude Code:

```json
"env": {
  "EXPRESS_SERVER_URL": "http://localhost:3000",
  "EXCALIDRAW_EXPORT_DIR": "/Users/<you>/guides"
}
```

### The superpowers dependency declaration

`guide/.claude-plugin/plugin.json` declares `"dependencies": ["superpowers@claude-plugins-official"]` (research R2, verified when the plugin was built). `claude plugin validate` accepts it, and an install without superpowers reports the missing dependency with its install command. Side effect: without superpowers the whole plugin fails to load, so `preview`, `export`, `upstream`, `validate`, and `evolve --check` are unavailable too, although they do not use superpowers. The scheduled drift check is unaffected because it runs `tools/guide/drift.py` in CI without Claude Code. The runtime contract probe (`scripts/superpowers-probe.sh`) still runs for create and evolve, because the declaration does not check versions or the scripts cc-guide calls.
