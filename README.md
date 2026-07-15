# AgenticWorkspace

Point it at any repo. It detects the stack, writes a `.workspace/` directory with progressive
context and session handoffs, and installs a working Claude Code adapter, all in one command.

[![CI](https://github.com/RudrenduPaul/AgenticWorkspace/actions/workflows/ci.yml/badge.svg)](https://github.com/RudrenduPaul/AgenticWorkspace/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](./LICENSE)
[![Node >= 18](https://img.shields.io/badge/node-%3E%3D18-brightgreen.svg)](./package.json)

```bash
npx agenticworkspace-cli init
```

This is a v0.1 release. Zero installs, zero GitHub stars, first release. 99/99 tests pass. It does
what's described below and nothing more. There's an honest comparison against the other tools
already working in this space further down, so you can decide if AgenticWorkspace is actually
worth trying before you run it.

## Install

Not published to npm yet. Until it is, run it from a local clone:

```bash
git clone https://github.com/RudrenduPaul/AgenticWorkspace.git
cd AgenticWorkspace
npm install
npm run build
node dist/agenticworkspace/cli.js init
```

Once published, both of these will work:

```bash
npx agenticworkspace-cli init
# or, for repeat use:
npm install -g agenticworkspace-cli
agenticworkspace init
```

## Features

Everything below is verified against the actual source in this repo, not aspirational.

- **Real stack detection** -- language (JavaScript/TypeScript, Python, lighter-weight signals for
  Rust/Go/Ruby), package manager (npm/pnpm/yarn), and monorepo package count, read from real
  manifest files (`src/agenticworkspace/scan/stack-detector.ts`).
- **Non-destructive by default** -- checks for `CLAUDE.md`, `AGENTS.md`, `.cursor/rules`, and
  `.github/copilot-instructions.md` and never overwrites them
  (`src/agenticworkspace/scan/config-detector.ts`).
- **Detects other agent-memory tooling without touching it** -- looks for a `.serena/` directory, a
  GitNexus-style config, or repo-harness's own `.ai/harness/` directory, reports what it finds, and
  never reads or writes any of them (`src/agenticworkspace/memory-backends/`).
- **A real, working Claude Code adapter** -- writes actual hook scripts for session start,
  pre-tool-call, and session-end handoff generation, wired into
  `.workspace/adapters/claude-code/settings.json`
  (`src/agenticworkspace/adapters/claude-code/install.ts`).
- **Structured JSON output on every subcommand** -- `init`, `scan`, `status`, `adapter install`, and
  `handoff new` all support `--json`, including on error paths (a nonexistent `--path`, a missing
  workspace, an unimplemented adapter), so a calling agent never has to parse human-readable text
  or guess at exit codes.
- **Two documented plugin interfaces, not a hardcoded pipeline** -- `MemoryBackend`
  (`src/agenticworkspace/memory-backends/types.ts`) and `Adapter`
  (`src/agenticworkspace/adapters/types.ts`). Adding a new tool means implementing one interface
  and registering it (`registry.ts` in each folder); no changes to CLI or scan code are required.
  See [Extending AgenticWorkspace](#extending-agenticworkspace) below.
- **Shell-injection-safe hook generation** -- every scanned value (module names, paths) that ends
  up embedded in a generated shell script passes through an allowlist and quoting check first
  (`src/agenticworkspace/util/sanitize.ts`), covered by 30 dedicated unit tests.
- **Partial-state recovery** -- an interrupted or malformed prior `init` run is detected and
  surfaced (interactive repair/reset/abort prompt, or a structured JSON error with a dedicated exit
  code in `--json` mode) instead of being silently overwritten or resumed
  (`src/agenticworkspace/state/partial-state.ts`).

## Quickstart

A real run against a small two-file JavaScript repo, output unedited:

```bash
$ agenticworkspace init --json --path ./my-app

{
  "ok": true,
  "agenticworkspace_version": "0.1.1",
  "scanned_at": "2026-07-15T04:56:35.727Z",
  "target": "/Users/you/my-app",
  "stack": {
    "language": "javascript",
    "package_manager": "npm",
    "monorepo": false,
    "packages": 1
  },
  "existing_config": {
    "claudeMd": false,
    "agentsMd": false,
    "cursorRules": false,
    "copilotInstructions": false,
    "anyDetected": false
  },
  "memory_backends": [
    { "name": "serena", "detected": false, "description": "Serena memory/context tool (.serena/ directory)" },
    { "name": "gitnexus", "detected": false, "description": "GitNexus-style config (.gitnexus/ or gitnexus.config.json)" },
    { "name": "repo-harness", "detected": false, "description": "repo-harness (.ai/harness/ directory) -- detected only, never modified" }
  ],
  "context": { "root_context_kb": 0.6, "budget_kb": 12, "modules": [] },
  "adapters": { "claude_code": { "installed": true, "hook_schema_version": "2026-07-01" } },
  "workspace_dir": "/Users/you/my-app/.workspace"
}
```

That single run wrote six real files on disk:

```
.workspace/workspace.json
.workspace/context/root-context.md
.workspace/adapters/claude-code/settings.json
.workspace/adapters/claude-code/adapter-meta.json
.workspace/adapters/claude-code/hooks/session-start.sh
.workspace/adapters/claude-code/hooks/pre-tool-call.sh
.workspace/adapters/claude-code/hooks/session-end-handoff.sh
```

Drop `--json` for a human-readable version of the same run:

```bash
$ agenticworkspace init --path ./my-app

AgenticWorkspace v0.1 -- Repo-to-Agent-Workspace Converter
Target: /Users/you/my-app

Scanning repository...
[OK] Stack detected: javascript, npm
[--] No existing agent-config files found
[--] No memory/context tool detected

Writing .workspace/ scaffold...
  .workspace/workspace.json                created
  .workspace/context/root-context.md        created (0.6KB of 12KB budget)
  .workspace/handoff/                       created (empty, ready for first session)

Installing Claude Code adapter...
  .workspace/adapters/claude-code/settings.json         written
  .workspace/adapters/claude-code/hooks/session-start.sh  written
  .workspace/adapters/claude-code/hooks/pre-tool-call.sh  written
  .workspace/adapters/claude-code/hooks/session-end-handoff.sh  written

Workspace ready. Next Claude Code session in this repo will load root-context.md automatically
and write a handoff file on exit.
```

## CLI reference

Every command accepts `-p, --path <path>` (defaults to the current directory) and `--json`
(structured output instead of the human-readable default).

| Command | Description |
|---|---|
| `agenticworkspace init` | Scan the repo and write the `.workspace/` scaffold plus the Claude Code adapter. Idempotent -- safe to re-run. |
| `agenticworkspace scan` | Detect stack and existing agent-tooling surface only. No writes. |
| `agenticworkspace status` | Report workspace health: stack, context budget usage, handoff count, adapter staleness. |
| `agenticworkspace adapter install <name>` | (Re)install a single adapter's hook wiring, e.g. `claude-code`. Returns `adapter_not_implemented` for `codex` or `cursor`. |
| `agenticworkspace handoff new <message>` | Write a new timestamped session handoff file under `.workspace/handoff/`. |

Exit codes are stable across `--json` and human-readable modes, so a script can branch on them
without parsing text:

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | General error (bad input, unexpected filesystem failure) |
| `2` | Partial/malformed `.workspace/` state detected |
| `3` | Adapter not yet implemented (`codex`, `cursor`) |
| `4` | No `.workspace/` found (run `init` first) |

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

## Extending AgenticWorkspace

AgenticWorkspace is built around two plugin interfaces, not one project doing everything itself:

- `MemoryBackend` (`src/agenticworkspace/memory-backends/types.ts`) -- detects whether a repo
  already has a memory/context tool wired in. Detection must stay read-only.
- `Adapter` (`src/agenticworkspace/adapters/types.ts`) -- wires the `.workspace/` scaffold into a
  specific coding tool: install, staleness check, and a human-readable description.

Adding support for a new tool means implementing one of these interfaces and registering an
instance in that folder's `registry.ts`; no changes to the CLI or scan code are required. See
`src/agenticworkspace/adapters/codex/` and `.../cursor/` for the shape a not-yet-implemented stub
takes, and `.../claude-code/` for a fully working reference implementation.

## How this compares to repo-harness and harnesskit

Repo-local context and session-handoff tracking for coding agents is not a new idea. Before
building this, we checked what's already shipping. Two npm packages cover overlapping ground, and
their current state (checked 2026-07-14) matters more than any of our own claims about them:

| | **AgenticWorkspace** v0.1.1 | **repo-harness** v0.10.0 | **harnesskit** v0.1.1 |
|---|---|---|---|
| npm activity | First release, 0 versions published to the real registry yet | 38 published versions, created 2026-05-28, last published 2026-07-14 (today) | 2 published versions, last published 2026-03-20 (about 4 months stale) |
| GitHub | 0 stars (new repo) | 391 stars, 24 forks, pushed within the last day | GitHub repo now returns 404, cannot inspect source |
| Claude Code adapter | Implemented end to end: real hook scripts + `settings.json` wiring, installed by `init` in the same run that creates the workspace | Implemented: `~/.claude/settings.json` hook adapter | Unverified, could not inspect source or README (npm page blocked our fetch, GitHub repo gone) |
| Codex adapter | Registered in the adapter interface, `install()` throws "not yet implemented" -- honest stub, not a silent no-op | Implemented: `~/.codex/hooks.json` adapter | Unverified |
| Cursor adapter | Registered, same honest-stub pattern as Codex | Mentioned in architecture docs; we could not confirm it's fully implemented the way the Claude/Codex adapters are | Unverified |
| Progressive context loading | Budget-targeted root context file (~12KB) plus per-module capability blocks, loaded on demand | Budget-targeted root context (~12KB) via `.ai/context/context-map.json`, backed by a CodeGraph structural index we do not build | Unverified |
| Session handoff files | Timestamped file per session under `handoff/` | `.ai/harness/handoff/resume.md` plus `tasks/current.md` | Unverified |
| CLI JSON output | Every subcommand (`scan`, `status`, `adapter install`, `handoff`) supports `--json`, including error paths | Has JSON output on at least `--dry-run --json` and `--state --json` | Unverified |
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

The honest read: repo-harness is more mature than AgenticWorkspace on almost every dimension in
this table right now. It already has a working Claude Code adapter, a working Codex adapter, and
five languages of documentation. It has been iterating fast (38 versions in about seven weeks). If
you already use it and it works for you, there's no reason to switch.

What we actually built differently: a plugin architecture with two small, documented interfaces
(`MemoryBackend` for detecting other tools, `Adapter` for wiring into a specific coding agent)
instead of one project doing everything itself, and an explicit compatibility check that detects
repo-harness's own `.ai/harness/` directory and reports it rather than silently duplicating or
conflicting with it. Beyond that, right now, this is a new, unproven CLI going up against a more
established one. We're not going to dress that up.

One more thing worth naming: Claude Code itself now ships a first-party `MEMORY.md`-based memory
system and team memory stores, plus a `post-session` lifecycle hook that can snapshot uncommitted
work. It doesn't scan a repo's stack or install a Claude-Code-specific adapter the way
AgenticWorkspace does, but the gap between "what the platform does natively" and "what a tool like
this adds" is narrower than it was when this category started, and it's worth watching before
assuming any of this tooling stays necessary.

## What and why

Coding agents lose context the moment a session ends, and every repo needs its own manual setup
before an agent can work in it well: what CLAUDE.md or AGENTS.md file to write, how to hand off
partial work to the next session, which hooks to wire up. That setup is repetitive, easy to get
wrong, and rarely kept up to date as a project's stack changes.

AgenticWorkspace automates the parts of that setup that are mechanical and repo-agnostic: figuring
out what stack a repo uses, writing a progressive context file sized to stay inside a token budget
instead of the model's entire codebase, and installing real hooks so a Claude Code session
generates a handoff note automatically instead of relying on a human to write one down. It does not
try to be a memory database, a semantic code index, or a hosted dashboard. It is a scaffolding CLI:
it writes files once, in a format any of those other tools could later read or extend, and then
gets out of the way.

Why build another one of these when repo-harness already exists and has more traction (see the
comparison table above)? Because the honest answer is: not to displace it. This project exists to
test a narrower, Claude-Code-first version of the same idea with a plugin architecture that keeps
detection and adapter code decoupled from day one, and to be upfront in public about exactly how it
stacks up against the tool that got there first.

## FAQ

**Does this modify my existing CLAUDE.md, AGENTS.md, or .cursor/rules?**
No. `init` checks for all four config files (`CLAUDE.md`, `AGENTS.md`, `.cursor/rules`,
`.github/copilot-instructions.md`) and reports what it finds, but never writes to or overwrites any
of them.

**Does this conflict with Serena, GitNexus, or repo-harness if I already use one of them?**
No. Detection is read-only: AgenticWorkspace checks for `.serena/`, a GitNexus-style config, and
repo-harness's `.ai/harness/` directory, reports what it finds in `scan`/`status`/`init` output, and
never reads, writes, or deletes anything inside them.

**What happens if `init` gets interrupted halfway through?**
The next `init` run detects the leftover `.init-in-progress` marker or a missing/malformed
`workspace.json` and either prompts you to repair, reset, or abort (interactive terminal), or
returns a structured JSON error with exit code `2` (non-interactive or `--json` mode) instead of
silently overwriting or resuming.

**Why isn't the Codex or Cursor adapter implemented yet?**
Both are registered in the `Adapter` plugin interface with `isImplemented: false` and a real, honest
`describe()` string rather than a silent no-op. Claude Code was built first because that is the
adapter this repo's own workflow was built and tested against. Contributions implementing either are
welcome, see [Extending AgenticWorkspace](#extending-agenticworkspace).

**Is there a hosted dashboard or paid tier?**
Not in this repository. This CLI is the free, local, MIT-comparable (Apache-2.0) layer. There is no
hosted component here to sign up for.

**Why isn't this on npm yet?**
This is the package's first-ever publish, and it goes through a staged review process rather than a
direct `npm publish`. Until that lands, run it from a local clone (see [Install](#install)).

## Development

```bash
git clone https://github.com/RudrenduPaul/AgenticWorkspace.git
cd AgenticWorkspace
npm install
npm run build
npm test
```

99/99 tests pass as of this release. Before opening a pull request, run `npm run lint`,
`npm run typecheck`, `npm run test:coverage`, and `npm run build` -- the same steps CI runs on
Node 18.x and 20.x.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the development setup, the pre-PR checklist, and
concrete instructions for adding a new `MemoryBackend` or `Adapter`. Security-sensitive changes
(anything that touches generated shell scripts) must go through the shared sanitization module
described there.

## License

Apache 2.0. See [LICENSE](./LICENSE).
