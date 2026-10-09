---
name: preflight
description: Shared preflight for every /guide command. Resolves the guide project, checks the companion plugins (superpowers, cc-prose, Excalidraw MCP) and the adapter tool chain, and states the recommended session settings. Invoked by the guide command wrappers before their own skill; stops before any file is written when a requirement fails.
argument-hint: "<command> [--dir PATH] [--check] [--format antora|mkdocs|gfm]"
allowed-tools: ["Bash", "Read"]
---

# Guide preflight

Run this before any other step of a `/guide:*` command. It writes no files. When a check fails, stop the command with the message given here; never continue with a degraded flow (SC-009, FR-003, FR-004).

## Paths

- `PLUGIN`: the plugin root, two directories above this skill's base directory (`<base>/../..`). Scripts live in `$PLUGIN/scripts/`, the toolkit in `$PLUGIN/toolkit/`, adapters in `$PLUGIN/adapters/`.
- `GUIDE`: the guide project. Use `--dir PATH` when given, otherwise the current directory. Resolve it to an absolute path. Never `cd` into `.guide/cache/`.
- `SESSION`: the directory this Claude Code session was started in (the primary working directory in your environment information), resolved to an absolute path. Claude Code reads the session's permissions from its `.claude/settings*.json` (at its git toplevel inside a repository) and from `~/.claude/settings.json`, not from the guide project's settings when the two differ.

## Steps

### 1. Guide project

- For every command except `create` and `evolve --adopt`: `$GUIDE/guide.yaml` must exist. If it does not, stop:
  > No guide project at `<GUIDE>` (guide.yaml not found). Run `/guide:create` to start one, or pass `--dir` with the guide project path.

  When the directory already holds a guide that cc-guide did not create (a `baseline.yaml`, an Antora `antora.yml`, a `mkdocs.yml`, or a `docs/` directory), add: "To bring an existing guide under cc-guide, run `/guide:evolve --adopt`."
- For `evolve --adopt`: `guide.yaml` may be missing; the adoption step writes it.
- For `create`: the target rules are checked by the create skill (FR-005b); preflight only notes whether `guide.yaml` already exists (an existing guide project means create resumes, see the create skill).

### 2. Companion plugins

Run:

```bash
bash "$PLUGIN/scripts/deps.sh" --dir "$GUIDE" --session-dir "$SESSION"
```

It prints JSON `{"superpowers": bool, "prose": bool, "excalidraw_allowed": bool, "excalidraw_allowed_in": [paths]}`. `excalidraw_allowed` is true when an `mcp__excalidraw` allow entry is in the guide project's settings, in the session directory's settings, or in `~/.claude/settings.json`; `excalidraw_allowed_in` lists the files that hold it.

**superpowers** is required for `create` and for `evolve` without `--check`. For those, run the contract probe:

```bash
bash "$PLUGIN/scripts/superpowers-probe.sh"
```

| Exit | Meaning | Action |
|---|---|---|
| 0 | Installed, contract intact, known-good version | Continue. |
| 3 | Contract intact, version not in `$PLUGIN/compat.yaml` | Warn once: "superpowers `<version>` is not a known-good version (known: ...); the contract probe passed, continuing." Continue. |
| 4 | Not installed, or a skill or script is missing or changed | Stop. Name every entry of `problems[]` from the JSON. |

Stop message when superpowers is missing:
> `/guide:<command>` needs the superpowers plugin (6.3.0 or later). Install it with `claude plugin install superpowers@claude-plugins-official`, restart Claude Code, and run the command again. Nothing was written.

Stop message when the probe fails on a changed contract:
> superpowers `<version>` changed in a way cc-guide does not support: `<problems>`. Known-good versions: `<compat.yaml known_good>`. Install a known-good version or update cc-guide. Nothing was written.

**cc-prose** is optional (FR-003a). When `prose` is false, show exactly one line and continue:
> Note: cc-prose is not installed, so pages use cc-guide's built-in style rules. Installing it (`claude plugin install prose@cc-rhuss-marketplace`) adds voice profiles and AI-pattern checks.

Record `prose: present|absent`; the create and evolve skills pass it to the page-task templates.

**Excalidraw MCP** is needed only when a run plans diagram tasks. Record whether `mcp__excalidraw__*` tools are available in this session (look at your own tool list), and `excalidraw_allowed` and `excalidraw_allowed_in` from deps.sh. The entry covers this session only when `excalidraw_allowed_in` lists a settings file of the session directory (at its git toplevel inside a repository) or `~/.claude/settings.json`; when the session runs in another directory, an entry only in the guide project's files covers just the sessions started there. The create and evolve skills act on it once diagrams are planned (FR-003); preflight does not stop for it and writes no settings.

### 3. Adapter tool chain

- When `$GUIDE/tools/guide/adapter.yaml` exists, run `make -C "$GUIDE" doctor`.
- For `create` before the scaffold exists, run doctor against the plugin's adapter descriptor once the format is known:

  ```bash
  uv run "$PLUGIN/toolkit/doctor.py" --root "$GUIDE" --adapter "$PLUGIN/adapters/<format>/adapter.yaml"
  ```

  Tools that are installed per project by `npm install` (antora, markserv, Playwright) are expected to be missing at this point; the create skill installs them after scaffolding and runs `make doctor` again. Stop only for tools the author must install system-wide (node, uv, git, pandoc for gfm), with the hint doctor prints.
- A non-zero `make doctor` in an existing guide project stops `preview`, `export`, and `validate` with doctor's hints. `create` and `evolve` stop too, except `evolve --check`, which needs only `uv` and `git`, and `evolve --adopt` before the toolkit is installed (doctor runs after adoption installs it).

### 4. Session recommendations (FR-041, FR-042)

Print once:

> Recommended session: the most capable model available (for example Opus 5.5) for this controlling session, subagents inherit it (no model override), effort `high` for create and evolve, `xhigh` with `--rigor strict`. See `$PLUGIN/docs/settings.md` for the permission allowlist.

You can see your own model name in your system prompt; you cannot see the effort level. When your model is a Sonnet or Haiku class model, add one warning line and continue:

> Warning: this session runs `<model>`. Source verification and reviews are more reliable with the most capable model; consider `/model` before continuing.

### 5. Result

Report a compact block and hand it to the calling skill:

```text
preflight: guide=<GUIDE> project=<exists|new> superpowers=<ok|unknown-version|not-needed> prose=<present|absent> excalidraw=<available|missing> excalidraw_allowed=<true|false> excalidraw_allowed_in=<paths|none> doctor=<ok|skipped|failed>
```

## Rules

- Never write, create, or modify a file during preflight.
- Never install anything without the author's approval; show the install command instead.
- Run every command from the guide project root or with `-C`/`--root`; never `cd` into `.guide/cache/`.
