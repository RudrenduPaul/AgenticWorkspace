# WorkspaceForge

Convert a repository into an agent-ready workspace in one command: detect the stack, scaffold a
`.workspace/` directory with progressive context loading and session handoffs, and install a
working Claude Code adapter out of the box.

```bash
npx workspaceforge-cli init
```

This is a v0.1 release. Zero installs, zero GitHub stars, first release. 97/97 tests pass. It
does what's described below and nothing more. The section right below is an honest comparison
against the other tools already working in this space, so you can decide if WorkspaceForge is
actually worth trying before you run it.

## How this compares to repo-harness and harnesskit

Repo-local context and session-handoff tracking for coding agents is not a new idea. Before
building this, we checked what's already shipping. Two npm packages cover overlapping ground,
and their current state (checked 2026-07-13) matters more than any of our own claims about them:

| | **WorkspaceForge** v0.1.0 | **repo-harness** v0.9.2 | **harnesskit** v0.1.1 |
|---|---|---|---|
| npm activity | First release, 0 versions published to the real registry yet | 37 published versions, created 2026-05-28, last published 2026-07-09 (4 days before this was written) | 2 published versions, last published 2026-03-20 (about 4 months stale) |
| GitHub | 0 stars (new repo) | 390 stars, 24 forks, pushed today | GitHub repo now returns 404, cannot inspect source |
| Claude Code adapter | Implemented end to end: real hook scripts + `settings.json` wiring, installed by `init` in the same run that creates the workspace | Implemented: `~/.claude/settings.json` hook adapter | Unverified, could not inspect source or README (npm page blocked our fetch, GitHub repo gone) |
| Codex adapter | Registered in the adapter interface, `install()` throws "not yet implemented" -- honest stub, not a silent no-op | Implemented: `~/.codex/hooks.json` adapter | Unverified |
| Cursor adapter | Registered, same honest-stub pattern as Codex | Mentioned in architecture docs; we could not confirm it's fully implemented the way the Claude/Codex adapters are | Unverified |
| Progressive context loading | Budget-targeted root context file (~12KB) plus per-module capability blocks, loaded on demand | Budget-targeted root context (~12KB) via `.ai/context/context-map.json`, backed by a CodeGraph structural index we do not build | Unverified |
| Session handoff files | Timestamped file per session under `handoff/` | `.ai/harness/handoff/resume.md` plus `tasks/current.md` | Unverified |
| CLI JSON output | Every subcommand (`scan`, `status`, `adapter install`, `handoff`) supports `--json` | Has JSON output on at least `--dry-run --json` and `--state --json` | Unverified |
| Detects other tools without touching them | Yes: checks for `.serena/`, a GitNexus-style config, and repo-harness's own `.ai/harness/` directory, reports what it finds, never reads or writes any of them | Not checked -- outside scope of what we reviewed | Unverified |
| Plugin/extension model | Two documented TypeScript interfaces (`MemoryBackend`, `Adapter`); adding a tool means implementing one and registering it, no CLI changes needed | Not verified from the README alone; would need to read source to confirm | Unverified |
| Hosted multi-repo dashboard | Does not exist. Not planned as part of this OSS CLI. | Does not exist, self-hosted file-backed workflow only | Unverified |
| Documentation languages | English only | English (primary), plus Simplified Chinese, Japanese, French, Spanish | Unverified |

What we could verify came from `npm view`, the GitHub API, and repo-harness's own README (fetched
directly). We did not install and run repo-harness against a real repo ourselves, so anything
marked "implemented" for it is a README claim we read, not a claim we reproduced firsthand.
Everything marked "unverified" for harnesskit stayed that way because its GitHub repository no
longer resolves and its npm page blocked automated fetches; we are not going to guess at what a
tool does from a description string.

The honest read: repo-harness is more mature than WorkspaceForge on almost every dimension in
this table right now. It already has a working Claude Code adapter, a working Codex adapter, and
five languages of documentation. It has been iterating fast (37 versions in about six weeks). If
you already use it and it works for you, there's no reason to switch.

What we actually built differently: a plugin architecture with two small, documented interfaces
(`MemoryBackend` for detecting other tools, `Adapter` for wiring into a specific coding agent)
instead of one project doing everything itself, and an explicit compatibility check that detects
repo-harness's own `.ai/harness/` directory and reports it rather than silently duplicating or
conflicting with it. Beyond that, right now, this is a new, unproven CLI going up against a more
established one. We're not going to dress that up.

One more thing worth naming: Claude Code itself now ships a first-party `MEMORY.md`-based memory
system and team memory stores, plus a `post-session` lifecycle hook that can snapshot
uncommitted work. It doesn't scan a repo's stack or install a Claude-Code-specific adapter the way
WorkspaceForge does, but the gap between "what the platform does natively" and "what a tool like
this adds" is narrower than it was when this category started, and it's worth watching before
assuming any of this tooling stays necessary.

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

97/97 tests pass as of this release.

## License

Apache 2.0. See [LICENSE](./LICENSE).
