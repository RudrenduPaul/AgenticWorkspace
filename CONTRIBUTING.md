# Contributing to AgenticWorkspace

AgenticWorkspace ships two independently maintained, equally first-class
distributions of the same tool: an npm package (`agenticworkspace-cli`,
TypeScript, repo root) and a PyPI package (`agenticworkspace-cli`, Python,
`python/`). Both implement the same scan/scaffold/adapter pipeline, the same
`.workspace/` directory shape, and the same two plugin interfaces
(`MemoryBackend`, `Adapter`), and are expected to produce the same
`workspace.json` manifest shape against the same target repo. Which section
below applies depends on which codebase you're touching.

## Ground rules

- Every change lands with tests. Neither test suite is optional scaffolding
  -- both are the mechanism that keeps the two implementations in parity.
- A behavior change to stack detection, the `.workspace/` manifest shape, an
  adapter's hook output, or a memory backend's detection logic must be made
  in **both** `src/agenticworkspace/` (TypeScript) and
  `python/src/agenticworkspace/` (Python), with equivalent test coverage
  added to both suites. A change that only exists in one language is a
  silent behavior gap between the two CLIs -- avoid it.
- CLI flags, exit codes, and `--json` output shape should read identically
  between the two CLIs wherever the underlying behavior is the same. If you
  intentionally diverge the two (e.g. a Python-only convenience flag), say
  so explicitly in the PR description.
- No `eval`/`exec`/dynamic `require`/`import` of anything read from a
  scanned target repo, in either codebase. AgenticWorkspace's entire premise
  is that it's safe to run against a repo you haven't fully audited yet; a
  "fix" that breaks that invariant is not a fix.
- Any value derived from scanning a target repository that ends up embedded
  in a generated shell script must go through the shared sanitization
  module (`src/agenticworkspace/util/sanitize.ts` /
  `python/src/agenticworkspace/util/sanitize.py`) first. Do not add a
  second, duplicate sanitization path elsewhere in either codebase.

## Working on the TypeScript package (repo root)

```bash
git clone https://github.com/RudrenduPaul/AgenticWorkspace.git
cd AgenticWorkspace
npm install
npm run build
npm test
```

Before opening a pull request:

- `npm run lint`
- `npm run typecheck`
- `npm run test:coverage`
- `npm run build`

Source lives under `src/agenticworkspace/`; tests under `test/unit/` and
`test/integration/` (`vitest`).

## Working on the Python package (`python/`)

```bash
cd python
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Source lives under `python/src/agenticworkspace/`, laid out to mirror the
TypeScript module structure 1:1 (`scan/`, `memory_backends/`, `adapters/`,
`scaffold/`, `state/`, `util/`, `commands/`, `cli.py`) so a change in one
codebase has an obvious counterpart to check in the other. Tests use
`pytest` (`python/tests/test_*.py`).

Build and verify a real install before opening a PR that touches packaging:

```bash
python3 -m build python --outdir /tmp/aw-dist
python3 -m venv /tmp/aw-verify && /tmp/aw-verify/bin/pip install /tmp/aw-dist/*.whl
/tmp/aw-verify/bin/agenticworkspace init --path . --json
```

## Adding a new memory-tool backend

Implement the `MemoryBackend` interface
(`src/agenticworkspace/memory-backends/types.ts` for TypeScript,
`python/src/agenticworkspace/memory_backends/types.py` for Python) and
register your instance in that language's `registry.ts`/`registry.py`.
Detection must stay read-only: a backend must never write, modify, or
delete anything belonging to another tool. See
[docs/integrations/custom-plugin.md](./docs/integrations/custom-plugin.md)
for a worked example in both languages.

## Adding a new adapter

Implement the `Adapter` interface
(`src/agenticworkspace/adapters/types.ts` /
`python/src/agenticworkspace/adapters/types.py`) and register your instance
in that language's `registry.ts`/`registry.py`. See each language's
`adapters/codex/` and `adapters/cursor/` for the shape a not-yet-implemented
stub should take, and `adapters/claude-code/` (or `claude_code/` in Python)
for a fully working reference implementation.

## Security

Any value derived from scanning a target repository that ends up embedded
in a generated shell script must go through
`src/agenticworkspace/util/sanitize.ts` (TypeScript) or
`python/src/agenticworkspace/util/sanitize.py` (Python) first. Do not add a
second, duplicate sanitization path elsewhere in either codebase. See
[SECURITY.md](./SECURITY.md) for the vulnerability disclosure process.

## License

By contributing, you agree your contribution is licensed under the same
Apache License, Version 2.0 that covers the rest of this repository (see
[LICENSE](./LICENSE)).
