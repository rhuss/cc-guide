---
name: preflight
description: Shared preflight for every /guide command. Resolves the guide project, detects the active harness and the companion capabilities (superpowers, cc-prose, Excalidraw MCP, parallel subagents) from in-session exposure, checks the adapter tool chain, and states the recommended session settings. Invoked by the guide command wrappers (and self-invoked by the skills on harnesses with no command layer) before the command's own skill; stops before any file is written when a requirement fails.
argument-hint: "<command> [--dir PATH] [--check] [--format antora|mkdocs|gfm]"
allowed-tools: ["Bash", "Read"]
---

# Guide preflight

Run this before any other step of a `/guide:*` command. It writes no files. When a check fails, stop the command with the message given here; never continue with a degraded flow (SC-009, FR-003, FR-004). Preflight runs on every supported harness (Claude Code, Codex, OpenCode); the only harness-specific step is the Claude-only settings/permission wiring in step 2 (FR-010, FR-018).

## Paths

- `PLUGIN`: the plugin root, two directories above this skill's base directory (`<base>/../..`). Scripts live in `$PLUGIN/scripts/`, the toolkit in `$PLUGIN/toolkit/`, adapters in `$PLUGIN/adapters/`.
- `GUIDE`: the guide project. Use `--dir PATH` when given, otherwise the current directory. Resolve it to an absolute path. Never `cd` into `.guide/cache/`.
- `SESSION`: the directory this session was started in (the primary working directory in your environment information), resolved to an absolute path. On Claude Code the session's permissions are read from its `.claude/settings*.json` (at its git toplevel inside a repository) and from `~/.claude/settings.json`, not from the guide project's settings when the two differ. Other harnesses manage permissions differently and read no `.claude/settings*.json`.

## Steps

### 1. Guide project

- For every command except `create` and `evolve --adopt`: `$GUIDE/guide.yaml` must exist. If it does not, stop:
  > No guide project at `<GUIDE>` (guide.yaml not found). Run `/guide:create` to start one, or pass `--dir` with the guide project path.

  When the directory already holds a guide that cc-guide did not create (a `baseline.yaml`, an Antora `antora.yml`, a `mkdocs.yml`, or a `docs/` directory), add: "To bring an existing guide under cc-guide, run `/guide:evolve --adopt`."
- For `evolve --adopt`: `guide.yaml` may be missing; the adoption step writes it.
- For `create`: the target rules are checked by the create skill (FR-005b); preflight only notes whether `guide.yaml` already exists (an existing guide project means create resumes, see the create skill).

### 2. Harness and companion capabilities (FR-007, FR-010, FR-017)

Decide every dependency from **in-session capability exposure**: look at your own available skills and tools, not at any plugin registry or settings file (FR-007). Determine:

- **harness**: `claude` when you are Claude Code (the Claude skills and the subagent `Agent`/`Task` tool are exposed); `codex` when you run under Codex; `opencode` when you run under OpenCode. Use your environment and your exposed tool set.
- **superpowers**: `true` when the superpowers skills (for example `brainstorming`, `writing-plans`, `subagent-driven-development`, `requesting-code-review`) are among your available skills.
- **superpowers_version**: best-effort. The version superpowers reports if your harness exposes it; otherwise omit it (it is only used for an advisory warning).
- **multi_agent**: `true` when your harness exposes parallel subagent dispatch, the capability per-page writing and review depend on (the `Agent`/`Task` tool on Claude Code; the multi-agent spawn/wait tools on Codex when its multi-agent features are enabled).
- **prose**: `true` when the `prose:humanizer` skill is available.
- **excalidraw**: `true` when `mcp__excalidraw__*` tools are available.

Pass what you observed to `deps.sh`, which assembles the record and computes the Claude-only Excalidraw settings wiring:

```bash
bash "$PLUGIN/scripts/deps.sh" --harness <harness> \
  --superpowers <true|false> [--superpowers-version <version>] \
  --multi-agent <true|false> --prose <true|false> --excalidraw <true|false> \
  --dir "$GUIDE" --session-dir "$SESSION"
```

It prints JSON `{"harness", "superpowers", "superpowers_version", "multi_agent", "prose", "excalidraw", "excalidraw_allowed", "excalidraw_allowed_in"}`. `excalidraw_allowed`/`excalidraw_allowed_in` are meaningful only when `harness == "claude"`; on other harnesses they are `false`/`[]`.

**superpowers** is required for `create` and for `evolve` without `--check`. When `superpowers` is false for those, stop and write nothing (FR-011), naming the active harness:
> `/guide:<command>` needs the superpowers plugin for this harness, and it is not available in this session. Install it for `<harness>` (Claude Code: `claude plugin install superpowers@claude-plugins-official`; Codex or OpenCode: install superpowers through that harness's plugin mechanism), restart the session, and run the command again. Nothing was written.

When `superpowers` is true, check the version advisory (FR-016); never block on it:

```bash
bash "$PLUGIN/scripts/superpowers-probe.sh" <superpowers_version>
```

| Exit | Meaning | Action |
|---|---|---|
| 0 | Version at or above the known-good threshold, or no version reported | Continue. |
| 3 | Version below the known-good threshold in `$PLUGIN/compat.yaml` | Warn once with the `problems[]` line, then continue. |

**multi_agent** is required for `create` and for `evolve` without `--check` (per-page writing and review are dispatched to parallel subagents, FR-017). When `multi_agent` is false for those, stop and write nothing:
> `/guide:<command>` needs your harness's parallel subagent dispatch, and it is not available in this session. On Codex, enable its multi-agent features (see the superpowers Codex notes) and restart; on Claude Code the subagent tool is always available. There is no single-agent fallback. Nothing was written.

**cc-prose** is optional (FR-003a, FR-008). When `prose` is false, show exactly one line and continue:
> Note: cc-prose is not available in this session, so pages use cc-guide's built-in style rules. On Claude Code, installing it (`claude plugin install prose@cc-rhuss-marketplace`) adds voice profiles and AI-pattern checks.

Record `prose: present|absent`; the create and evolve skills pass it to the page-task templates.

**Excalidraw MCP** is needed only when a run plans diagram tasks (FR-003, FR-009). Record whether `mcp__excalidraw__*` tools are available in this session (your own tool list).
- When `harness == "claude"`: also record `excalidraw_allowed` and `excalidraw_allowed_in` from deps.sh. The entry covers this session only when `excalidraw_allowed_in` lists a settings file of the session directory (at its git toplevel inside a repository) or `~/.claude/settings.json`; when the session runs in another directory, an entry only in the guide project's files covers just the sessions started there. The create and evolve skills act on it once diagrams are planned.
- When `harness != "claude"`: there is no settings/permission wiring to do; report Excalidraw presence from exposure only (`excalidraw_allowed` is `false` and unused). When Excalidraw is absent, diagram tasks use the placeholder path (FR-009).

Preflight never stops for Excalidraw and writes no settings.

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

> Recommended session: the most capable model available for this controlling session, subagents inherit it (no model override), effort `high` for create and evolve, `xhigh` with `--rigor strict`. See `$PLUGIN/docs/settings.md` for the Claude Code permission allowlist.

You can see your own model name in your system prompt; you cannot see the effort level. When your model is a Sonnet or Haiku class model, add one warning line and continue:

> Warning: this session runs `<model>`. Source verification and reviews are more reliable with the most capable model; consider switching the model before continuing.

### 5. Result

Report a compact block and hand it to the calling skill:

```text
preflight: guide=<GUIDE> project=<exists|new> harness=<claude|codex|opencode> superpowers=<ok|unknown-version|not-needed> superpowers_version=<version|none> multi_agent=<yes|no> prose=<present|absent> excalidraw=<available|missing> excalidraw_allowed=<true|false|n/a> excalidraw_allowed_in=<paths|none> doctor=<ok|skipped|failed>
```

`excalidraw_allowed` is `n/a` on non-Claude harnesses.

## Rules

- Never write, create, or modify a file during preflight.
- Never install anything without the author's approval; show the install command instead.
- Run every command from the guide project root or with `-C`/`--root`; never `cd` into `.guide/cache/`.
