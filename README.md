# WorkspaceForge

Convert a repository into an agent-ready workspace in one command: detect the stack, scaffold a
`.workspace/` directory with progressive context loading and session handoffs, and install a
working Claude Code adapter out of the box.

This is a v0.1 release. Install instructions and usage below; a full README with benchmarks and
comparisons against related tools will follow in a later update.

## Install

```bash
npx workspaceforge-cli init
```

or, for repeat use:

```bash
npm install -g workspaceforge-cli
workspaceforge init
```

## Usage

```bash
# Scan the current repo and write the .workspace/ scaffold plus the Claude Code adapter
workspaceforge init

# Detect stack + existing agent-tooling surface only, no writes
workspaceforge scan --json

# Check workspace health: stack, context budget, handoff count, adapter staleness
workspaceforge status --json

# (Re)install a single adapter's hook wiring
workspaceforge adapter install claude-code

# Leave a handoff note for the next session
workspaceforge handoff new "implemented auth flow, next: wire session refresh"
```

Every subcommand supports `--json` for structured output alongside the human-readable default,
so a script or an agent invoking WorkspaceForge programmatically can parse the result directly.

## What `init` does

- Detects the target repo's stack: language, package manager, and monorepo packages
- Checks for existing agent-config files (`CLAUDE.md`, `AGENTS.md`, `.cursor/rules`,
  `.github/copilot-instructions.md`) and never overwrites them
- Checks for existing memory/context tooling (`.serena/`, a GitNexus-style config,
  `.ai/harness/` from repo-harness) and reports what it finds without touching it
- Writes a `.workspace/` directory: a `workspace.json` manifest, a `context/` folder with a
  budget-targeted root context file plus per-module capability blocks, and an empty `handoff/`
  folder
- Installs a first-class Claude Code adapter: real hook scripts for session start, pre-tool-call,
  and session-end handoff generation, wired into `.workspace/adapters/claude-code/settings.json`

## The `.workspace/` directory

```
.workspace/
  workspace.json              manifest: detected stack, adapters installed, schema version
  context/
    root-context.md           progressive root context, budget-targeted (~12KB)
    modules/
      auth.md                 per-module capability block, loaded on demand
      api.md
  handoff/
    2026-07-13-1421.md         one file per session, timestamped
  adapters/
    claude-code/
      settings.json           hook entries wired into Claude Code's settings schema
      hooks/
        session-start.sh       loads root-context.md + relevant module blocks
        pre-tool-call.sh        lightweight guard, extendable per project
        session-end-handoff.sh writes the next handoff/ file automatically
```

## Adapter status (v0.1)

| Adapter | Status |
|---|---|
| Claude Code | Implemented, works end to end |
| Codex | Registered, not yet implemented |
| Cursor | Registered, not yet implemented |

## Extending WorkspaceForge

WorkspaceForge is built around two plugin interfaces:

- `MemoryBackend` -- detects whether a repo already has a memory/context tool wired in
  (`src/workspaceforge/memory-backends/`)
- `Adapter` -- wires the `.workspace/` scaffold into a specific coding tool
  (`src/workspaceforge/adapters/`)

Adding support for a new tool means implementing one of these interfaces and registering it; no
changes to the CLI or scan code are required.

## Development

```bash
npm install
npm run build
npm test
```

## License

Apache 2.0. See [LICENSE](./LICENSE).
