# cc-guide

A plugin for Claude Code (primary), Codex, and OpenCode that writes guides you can trust and keeps them current, from one plugin directory.

You point it at the material you have: source repositories, walkthrough transcripts, tickets, links, and notes. It interviews you about audience and personas, plans the guide with you, and then writes it page by page. A fresh reviewer checks every page against the sources, pinned to exact commits, before the next page starts. When the sources move on, the plugin shows which pages cite changed files and updates only those.

The method comes from building the [Secure Agent Workspace](https://github.com/validatedpatterns-sandbox/secure-agent-workspace) guide, where per-page reviews found a factual error in nearly every page. The lessons are in [`guide/docs/learnings.md`](guide/docs/learnings.md).

## Commands

| Command | What it does |
|---|---|
| `/guide:create` | Interview, scaffold, pin sources, plan, write and review every page, final review, run summary |
| `/guide:evolve` | Drift report against the baseline, targeted page updates with the same reviews, new baseline written last; `--check` reports drift only, `--adopt` brings in an existing guide |
| `/guide:preview` | Build and serve the guide locally with live reload; shareable or internal view |
| `/guide:export` | One PDF of the whole guide with a title page, linked table of contents, and page numbers |
| `/guide:upstream` | Re-verify collected source problems on the current default branch, draft reports, file only what you approve |
| `/guide:validate` | Run the guide's check commands against a cluster: read-only by default, full recipes only on a disposable cluster |

## Output formats

| Format | Pages | Site | PDF |
|---|---|---|---|
| `antora` | AsciiDoc | Antora with the RHDP showroom UI | Antora html-single export, printed with Playwright |
| `mkdocs` | Markdown | MkDocs Material | print-site page, printed with Playwright |
| `gfm` | Markdown rendered on GitHub | no build needed (Pandoc HTML for checks and the tarball) | Pandoc assembly, printed with Playwright |

All three share one contract: the same `make` targets (`doctor`, `fetch-baseline`, `site`, `site-internal`, `check`, `preview`, `pdf`, `dist`, `drift`), baseline values injected at build time instead of typed versions, an optional internal part that never reaches the shareable build, and content checks that fail the build. Details are in [`guide/docs/adapters.md`](guide/docs/adapters.md).

A `gfm` guide can also live inside the repository it documents (embedded mode): the guide sits in one subdirectory, the repository's README becomes the guide's source-verified front page, development material moves to a developer README, and `/guide:evolve` keeps the README current as the code changes. Run `/guide:create` at the root of an existing repository, or pass `--embedded`. See [`guide/docs/embedded.md`](guide/docs/embedded.md).

## Install

cc-guide runs on Claude Code (primary), Codex, and OpenCode from one plugin directory. Each harness reads only its own entry point and resolves the same shared skills, so the command set and behavior are the same across harnesses except for the documented degradations below.

### Claude Code

```bash
# from a checkout of this repository
make install
```

### Codex

Register this checkout as a local plugin and install it through Codex's own plugin mechanism. Codex reads `guide/.codex-plugin/plugin.json` and discovers the guide skills directly; there is no command layer, and the skills run `guide:preflight` themselves. create and evolve need Codex's multi-agent features enabled (`multi_agent = true` in `~/.codex/config.toml`), because per-page writing and review are dispatched to parallel subagents; preflight stops with a prerequisite message when that capability is not available.

### OpenCode

Install the command shims into a project with the bundled installer:

```bash
bash guide/opencode/install.sh --project-dir <project>
```

It copies the six guide commands into `<project>/.opencode/plugins/guide/command/`; each one chains `guide:preflight` and the matching guide skill, so OpenCode runs the same shared logic as the other harnesses with no behavior fork. OpenCode is delivered best-effort on the shared adapter (install, command discovery, and launch); the multi-agent prerequisite and the degradations below apply the same way as on Codex.

### Requirements (every harness)

- [superpowers](https://github.com/obra/superpowers) installed for the active harness (required for create and evolve; detected by capability exposure in the session). On Claude Code: `claude plugin install superpowers@claude-plugins-official`. cc-guide was validated against superpowers 7.0.0; an older version runs with an advisory warning, never a block.
- `uv`, `git`, Node 20 or later, and Playwright Chromium (`npx playwright install chromium`). Pandoc 3 for the `gfm` format. `gh` (authenticated) for change requests and upstream reports. `jq` or `python3` for the capability-detection scripts (`scripts/deps.sh`, `scripts/superpowers-probe.sh`): jq is preferred, python3 is the fallback, and at least one must be on `PATH`.

### Known degradations on non-Claude harnesses

Two optional capabilities are Claude Code only for now and fall back automatically; the authoring and verification flow is otherwise equivalent to Claude Code:

- Prose polish: without [cc-prose](https://github.com/rhuss/cc-prose) (voice profiles and the AI-pattern gate), pages are written with cc-guide's built-in style rules. cc-prose is Claude Code only today, so this is the default on Codex until its separate multi-harness port lands.
- Diagrams: without the Excalidraw MCP server (`yctimlin/mcp_excalidraw`), diagram tasks fall back to placeholder images that name the missing diagrams, and the run continues.

Recommended session settings and the Claude Code permission allowlist are in [`guide/docs/settings.md`](guide/docs/settings.md).

## Quick start

```text
/guide:create --dir ~/guides/minisvc --format antora \
  --source minisvc=https://github.com/example/minisvc@v1.2.3 \
  --input ~/transcripts/walkthrough.txt \
  "An admin and user guide for minisvc"
```

The command asks about personas, sections, rigor, an internal part, and whether to create a private remote repository. It then shows the guide plan for approval before any page is written. Afterwards:

```text
/guide:preview            # look at it in the browser
/guide:export             # one PDF for reviewers
/guide:evolve --check     # has anything moved since the baseline?
/guide:evolve             # update the affected pages
/guide:upstream           # report the problems found in the sources
```

## Rigor profiles

| Profile | Reviews | Use it for |
|---|---|---|
| `fast` | final whole-guide review only | drafts and small guides; about half the review dispatches |
| `standard` (default) | a review after every page, plus the final review | most guides |
| `strict` | standard, plus a claim ledger with an identifier and a source for every verifiable statement | guides that must survive an audit |

## How a guide project looks

```text
guide.yaml            format, personas, sections and voices, internal part, confidential terms
baseline.yaml         every source pinned to a commit, plus documented change requests
inputs.yaml           references and checksums of transcripts and notes (never their content)
findings/upstream.yaml  problems found in the sources and their filing status
runs/<run-id>.md      rulings, review statistics, and findings of each run
tools/guide/          the vendored toolkit (checks, drift, leak check, PDF printer)
<adapter content>     pages, partials, images, diagram sources
```

The toolkit lives in the guide project so the scheduled drift check (`.github/workflows/guide-drift.yml`, opt-in) runs in CI without Claude Code.

## Development

```bash
make validate        # claude plugin validate on the marketplace and the plugin
make test            # toolkit tests (pytest through uv)
make test-adapters   # per-format smoke tests (antora, mkdocs, gfm) plus the additive per-harness checks (Claude Code, Codex, OpenCode)
make eval            # how to run the behavioral evals (agent-eval-harness)
```

The design is in [`specs/001-cc-guide-plugin/`](specs/001-cc-guide-plugin/). Manual end-to-end runs are recorded in [`tests/manual/`](tests/manual/).

## License

MIT, see [LICENSE](LICENSE).
