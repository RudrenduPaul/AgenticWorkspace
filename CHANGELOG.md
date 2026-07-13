# Changelog

All notable changes to this project are documented in this file.

## 0.1.0

Initial release.

- `workspaceforge init`: scans a repo's stack (npm/pnpm/yarn, TypeScript/JavaScript, Python,
  with lighter-weight detection for Rust/Go/Ruby), checks for existing agent-config files without
  overwriting them, runs the MemoryBackend registry against the repo, and writes the `.workspace/`
  scaffold (manifest, progressive context, empty handoff directory) plus a working Claude Code
  adapter.
- `workspaceforge scan`: read-only stack and tooling-surface detection.
- `workspaceforge status`: workspace health report (stack, context budget usage, handoff count,
  adapter staleness, other detected backends).
- `workspaceforge handoff new`: writes a timestamped session handoff file.
- `workspaceforge adapter install <name>`: (re)installs a single adapter's hook wiring.
- `MemoryBackend` plugin interface with registered detectors for Serena, GitNexus-style configs,
  and repo-harness (`.ai/harness/`), detect-only, never modified.
- `Adapter` plugin interface. Claude Code is fully implemented (real hook scripts for
  session-start, pre-tool-call, and session-end handoff generation). Codex and Cursor are
  registered stubs, marked not yet implemented.
- Shared sanitization module: every scanned value embedded into a generated shell script passes
  through an allowlist check plus shell quoting before it is written.
- Partial-state detection for `.workspace/`: an interrupted or malformed prior `init` run is
  detected and surfaced (interactive repair/reset/abort prompt, or a structured JSON error with a
  dedicated exit code in `--json` mode) instead of being silently overwritten or resumed.
