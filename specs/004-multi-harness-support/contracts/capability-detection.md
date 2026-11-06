# Contract: Capability detection

Defines the detection record `deps.sh` emits and how skills consume it. Replaces reads of `~/.claude/plugins/installed_plugins.json` (FR-005, FR-007).

## `deps.sh` output (JSON)

```json
{
  "harness": "claude | codex | opencode",
  "superpowers": true,
  "superpowers_version": "7.0.0 | null",
  "multi_agent": true,
  "prose": false,
  "excalidraw": false,
  "excalidraw_allowed": false,
  "excalidraw_allowed_in": []
}
```

- `superpowers`, `prose`, `excalidraw`, `multi_agent`: derived from in-session capability exposure, NOT from a registry or settings file.
  - `superpowers`: superpowers skills exposed in the session.
  - `prose`: `prose:humanizer` skill exposed.
  - `excalidraw`: `mcp__excalidraw__*` tools available.
  - `multi_agent`: the harness's subagent/parallel-dispatch tools available.
- `superpowers_version`: best-effort; `null` when the harness exposes no version. Used only for the advisory compatibility warning (FR-016), never to block.
- `excalidraw_allowed` / `excalidraw_allowed_in`: computed and meaningful ONLY when `harness == "claude"` (FR-010). On other harnesses they are `false` / `[]` and unused.

## Preflight contract

- `superpowers == false` and command is create/evolve: STOP with a harness-appropriate install message; write nothing (FR-011).
- `multi_agent == false` and command is create/evolve: STOP with the parallel-subagent prerequisite message (FR-017).
- `superpowers_version` below the recorded threshold or null-but-present-mismatch: WARN once, continue (FR-016).
- `harness == "claude"`: run the existing settings/permission wiring for Excalidraw as today.
- `harness != "claude"`: skip settings wiring; report `excalidraw` presence from exposure only.
- `prose == false`: downstream pages use `style-rules.md` (FR-008). `excalidraw == false`: diagram tasks use the placeholder path (FR-009).

## Version-contract source

`guide/compat.yaml` keeps a single recorded minimum/known-good version threshold, consumed only for the advisory warning. `installPath` is removed from the probe output and from all callers.

## Backward compatibility

On Claude Code the record carries the same fields the current `deps.sh` emits (`superpowers`, `prose`, `excalidraw`, `excalidraw_allowed`, `excalidraw_allowed_in`), so existing Claude behavior is unchanged (FR-012). New fields (`harness`, `superpowers_version`, `multi_agent`) are additive.
