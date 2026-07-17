# Changelog

All notable changes to this project are documented in this file. This
changelog covers both distributions -- the npm package (`agenticworkspace-cli`,
JS/TS) and the PyPI package (`agenticworkspace-cli`, Python) -- since they
implement the same `.workspace/` scaffold, the same `MemoryBackend`/`Adapter`
plugin contract, and the same CLI shape; entries are tagged with which
distribution they apply to. The two packages are versioned independently
(same convention as this account's `skillguard-cli`), so a "Python 0.1.0"
entry does not imply a matching npm 0.1.0 release, and vice versa.

## [Python 0.1.0] - 2026-07-17

Initial Python port, built, tested, and packaged as `agenticworkspace-cli`.
**Not yet published to PyPI**: the first upload attempt hit PyPI's own
new-project-creation anti-abuse rate limit (`429 Too many new projects
created`) on this account, confirmed across two attempts -- an
account-level throttle, not a problem with this code. It will be published
(`pip install agenticworkspace-cli`) once the limit clears; install from
source in the meantime (see `python/README.md`). Complementary to, not a
replacement for, the existing npm package -- both are first-class and
maintained together.

### Added

- `agenticworkspace init` / `scan` / `status` / `adapter install <name>` /
  `handoff new <message>` CLI (console scripts `agenticworkspace` and
  `agenticworkspace-cli`, package `agenticworkspace`) with the same flags
  (`-p/--path`, `--json`), exit-code contract (0/1/2/3/4), and JSON output
  shape as the npm CLI, including the top-level `--json` error contract for
  errors that escape a command's own error handling.
- Programmatic library API: `from agenticworkspace import detect_stack,
  run_init_engine, ...` -- the same scan/scaffold/adapter functions the CLI
  calls, importable for agent frameworks that want to call AgenticWorkspace
  in-process instead of shelling out.
- Both plugin interfaces reimplemented as genuine Python `abc.ABC` classes
  with the same registration contract as the TypeScript originals:
  `MemoryBackend` (`agenticworkspace.memory_backends.types.MemoryBackend`,
  registry list `memory_backend_registry`) and `Adapter`
  (`agenticworkspace.adapters.types.Adapter`, registry list
  `adapter_registry`). Three first-party `MemoryBackend` implementations
  (Serena, GitNexus, repo-harness, all detect-only) and three registered
  `Adapter` implementations (Claude Code fully implemented; Codex and
  Cursor honest not-yet-implemented stubs that raise rather than no-op).
- Shared sanitization module (`agenticworkspace.util.sanitize`) ported with
  the same allowlist pattern (`[A-Za-z0-9_/-]`, 512-char max) and POSIX
  single-quote shell-quoting technique as the TypeScript original, applied
  to every scanned value the Claude Code adapter embeds into a generated
  hook script.
- Path-traversal defense in monorepo workspace-glob resolution: a resolved
  package path that escapes the scanned repo root (e.g. a `workspaces`
  entry like `../sibling-project`) is dropped rather than followed, ported
  from the same check in the TypeScript stack detector.
- Full pytest suite (132 tests) covering stack detection (JS/TS/Python/
  Rust/Go/Ruby signals, monorepo glob resolution, the path-traversal
  defense), config detection, all three memory backends, the sanitization
  module (including the same real injection-attempt-string test cases as
  the TypeScript suite), context generation (including the 12KB budget-trim
  fallback), handoff generation (including same-minute filename collision
  handling), workspace-manifest shape validation, partial-state detection
  and the full repair/reset/abort flow, all three adapters, and CLI
  subprocess-level integration tests including the `--json` error-contract
  regression test.

### Notes

- Verified end to end against a real sample repo: built wheel + sdist,
  installed into a fresh venv, ran `agenticworkspace init` and confirmed
  `.workspace/` was written with the same shape (`workspace.json`,
  `context/`, `handoff/`, `adapters/claude-code/`) the TypeScript CLI
  documents in the project README.
- This Python package's own version number (`0.1.0`) is independent of the
  npm package's version (`0.1.1` at the time of this release) -- see the
  note at the top of this file.

## [npm 0.1.1] - 2026-07-15 (first version actually published to the npm registry)

- Fix: the top-level CLI error handler now honors `--json` for errors that escape a command's own
  try/catch (e.g. an unwritable or nonexistent `--path`). Previously every subcommand's `--json`
  contract had one gap -- an unexpected filesystem error printed a plain-text line to stderr
  instead of a structured `{ "ok": false, ... }` object, which broke a calling agent's ability to
  parse the output. Covered by a new process-level integration test that spawns the real CLI.

## [npm 0.1.0] (not published to the npm registry -- superseded by 0.1.1 same-day, see above)

Initial release, local/pre-publish history.

- `agenticworkspace init`: scans a repo's stack (npm/pnpm/yarn, TypeScript/JavaScript, Python,
  with lighter-weight detection for Rust/Go/Ruby), checks for existing agent-config files without
  overwriting them, runs the MemoryBackend registry against the repo, and writes the `.workspace/`
  scaffold (manifest, progressive context, empty handoff directory) plus a working Claude Code
  adapter.
- `agenticworkspace scan`: read-only stack and tooling-surface detection.
- `agenticworkspace status`: workspace health report (stack, context budget usage, handoff count,
  adapter staleness, other detected backends).
- `agenticworkspace handoff new`: writes a timestamped session handoff file.
- `agenticworkspace adapter install <name>`: (re)installs a single adapter's hook wiring.
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
