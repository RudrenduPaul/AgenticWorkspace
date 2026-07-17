# agenticworkspace-cli (Python)

Point it at any repo. It detects the stack, writes a `.workspace/` directory
with progressive context and session handoffs, and installs a working Claude
Code adapter -- all in one command.

[![PyPI version](https://img.shields.io/pypi/v/agenticworkspace-cli.svg)](https://pypi.org/project/agenticworkspace-cli/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/RudrenduPaul/AgenticWorkspace/blob/main/LICENSE)
[![Python versions](https://img.shields.io/pypi/pyversions/agenticworkspace-cli.svg)](https://pypi.org/project/agenticworkspace-cli/)
[![npm version](https://img.shields.io/npm/v/agenticworkspace-cli.svg)](https://www.npmjs.com/package/agenticworkspace-cli)

## Why this exists

Coding agents lose context the moment a session ends, and every repo needs
its own manual setup before an agent can work in it well: what `CLAUDE.md`
or `AGENTS.md` file to write, how to hand off partial work to the next
session, which hooks to wire up. AgenticWorkspace automates the mechanical,
repo-agnostic parts of that setup: detecting what stack a repo uses, writing
a progressive context file sized to stay inside a token budget, and
installing real hooks so a Claude Code session generates a handoff note
automatically. This package is the Python distribution -- a genuine,
independent port, not a wrapper around the Node binary.

## Install

**Not yet live on PyPI.** This Python package is built, tested (132/132
pytest tests passing), and verified end-to-end from a real built wheel in a
fresh virtualenv -- publishing itself is blocked by PyPI's own
new-project-creation anti-abuse rate limit (`429 Too many new projects
created`) on this account, confirmed across two upload attempts. That is an
account-level PyPI throttle, not a problem with this code; it will be
retried once the limit clears. Until then:

```bash
git clone https://github.com/RudrenduPaul/AgenticWorkspace.git
cd AgenticWorkspace/python
pip install -e .
agenticworkspace init --path /path/to/your/repo
```

Once published, the intended install is:

```bash
pip install agenticworkspace-cli
```

or with [uv](https://docs.astral.sh/uv/):

```bash
uv add agenticworkspace-cli
```

The npm package (`agenticworkspace-cli`, TypeScript) is unaffected and
already live -- see [Install](../README.md#install) in the project README.

The complementary JS/TS distribution installs the same way on the npm side:
`npx agenticworkspace-cli init` (no install needed) or
`npm install -g agenticworkspace-cli` -- see the
[project README](https://github.com/RudrenduPaul/AgenticWorkspace#readme) for
that package. Both are first-class, maintained together; neither is
deprecated in favor of the other.

## Quickstart

```bash
agenticworkspace init --path ./my-app
```

Real output against a small JavaScript repo:

```
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

Add `--json` for structured output any calling agent can parse directly:

```bash
agenticworkspace init --path ./my-app --json
```

Or call the library directly (the agent-native path):

```python
from agenticworkspace import detect_stack, run_init_engine

stack = detect_stack("./my-app")
print(stack.language, stack.package_manager, stack.monorepo.is_monorepo)

result = run_init_engine("./my-app", "./my-app/.workspace")
print(result.manifest["context"]["rootContextKb"], "KB of root context written")
```

## CLI reference

Every command accepts `-p, --path <path>` (defaults to the current
directory) and `--json` (structured output instead of the human-readable
default).

| Command | Description |
| --- | --- |
| `agenticworkspace init` | Scan the repo and write the `.workspace/` scaffold plus the Claude Code adapter. Idempotent -- safe to re-run. |
| `agenticworkspace scan` | Detect stack and existing agent-tooling surface only. No writes. |
| `agenticworkspace status` | Report workspace health: stack, context budget usage, handoff count, adapter staleness. |
| `agenticworkspace adapter install <name>` | (Re)install a single adapter's hook wiring, e.g. `claude-code`. Returns exit code 3 for `codex` or `cursor` (not yet implemented). |
| `agenticworkspace handoff new <message>` | Write a new timestamped session handoff file under `.workspace/handoff/`. |

Exit codes are stable across `--json` and human-readable modes:

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | General error (bad input, unexpected filesystem failure) |
| `2` | Partial/malformed `.workspace/` state detected |
| `3` | Adapter not yet implemented (`codex`, `cursor`) |
| `4` | No `.workspace/` found (run `init` first) |

## How it works

```
target path -> stack detector + config detector + memory-backend registry
   -> module candidate detection (monorepo packages, or src/* subdirectories)
   -> progressive context generation (~12KB root-context.md budget)
   -> Claude Code adapter install (sanitized hook scripts + settings.json)
   -> workspace.json manifest written
```

Every scanned value (module names) that ends up embedded into a generated
shell script passes through an allowlist check plus POSIX shell quoting
first (`agenticworkspace/util/sanitize.py`) -- see
[docs/concepts.md](https://github.com/RudrenduPaul/AgenticWorkspace/blob/main/docs/concepts.md)
for the full pipeline and the two plugin interfaces (`MemoryBackend`,
`Adapter`) this package reimplements as genuine Python code.

## Extending AgenticWorkspace

Two documented plugin interfaces, reimplemented faithfully from the
TypeScript original's contract:

- `MemoryBackend` (`agenticworkspace.memory_backends.types.MemoryBackend`) --
  detects whether a repo already has a memory/context tool wired in.
  Detection must stay read-only.
- `Adapter` (`agenticworkspace.adapters.types.Adapter`) -- wires the
  `.workspace/` scaffold into a specific coding tool: install, staleness
  check, and a human-readable description.

Add support for a new tool by implementing one of these `abc.ABC` classes
and appending an instance to that package's registry list
(`memory_backend_registry` or `adapter_registry`) -- no changes to the CLI or
scan code are required, same extension contract the npm package documents.
See [docs/integrations/custom-plugin.md](https://github.com/RudrenduPaul/AgenticWorkspace/blob/main/docs/integrations/custom-plugin.md)
for a worked example.

## Adapter status (v0.1)

| Adapter | Status |
| --- | --- |
| Claude Code | Implemented, works end to end |
| Codex | Registered, not yet implemented |
| Cursor | Registered, not yet implemented |

## Security

The plugin-loading mechanism in both distributions is a real code-execution
surface worth naming plainly: a `MemoryBackend` or `Adapter` you register
runs as regular imported Python code with your process's full permissions --
AgenticWorkspace does not sandbox plugins, the same way it does not sandbox
the target repo's own source files it reads during detection. Only register
plugins you trust the source of, same as any other Python import. Detection
logic in every first-party backend is read-only by contract (see each
backend's docstring); the one first-party adapter that writes files (Claude
Code) passes every scanned value through the shared sanitization module
(`agenticworkspace/util/sanitize.py`, allowlist plus shell quoting) before
embedding it into a generated shell script. See
[SECURITY.md](https://github.com/RudrenduPaul/AgenticWorkspace/blob/main/SECURITY.md)
for the disclosure process. **Honest note**: this project does not currently
publish SLSA provenance, Sigstore signatures, or an SBOM, and has no OpenSSF
Scorecard badge set up -- none of that infrastructure exists yet for either
distribution, so it isn't claimed here.

## Contributing

See [CONTRIBUTING.md](https://github.com/RudrenduPaul/AgenticWorkspace/blob/main/CONTRIBUTING.md)
for the full guide, covering both the TypeScript and Python codebases.

```bash
cd python
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## License

Apache 2.0, see [LICENSE](https://github.com/RudrenduPaul/AgenticWorkspace/blob/main/LICENSE).
