# cc-guide

A Claude Code plugin for writing source-verified, persona-split guides from transcripts, source code, and other inputs, and for evolving them as the sources change.

The plugin is in the specification phase. The design lives in:

- [`brainstorm/01-cc-guide-plugin.md`](brainstorm/01-cc-guide-plugin.md): problem, approaches, decision, and the lessons learned from the first guide built this way.
- [`specs/001-cc-guide-plugin/spec.md`](specs/001-cc-guide-plugin/spec.md): the feature specification (on branch `001-cc-guide-plugin` until it is merged).

Planned commands: `create`, `evolve`, `preview`, `upstream`, and `validate`. The plugin builds on the [superpowers](https://github.com/obra/superpowers) plugin and uses an Excalidraw MCP server for diagrams.

## License

MIT, see [LICENSE](LICENSE).
