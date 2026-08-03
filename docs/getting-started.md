# Getting started

AgenticWorkspace scans a repository, detects its stack, and writes a
`.workspace/` directory with progressive context and session handoffs, plus
installs a working Claude Code adapter. It ships as two independent,
equally first-class packages that implement the same scan/scaffold/adapter
contract: an npm package (`agenticworkspace-cli`, JavaScript/TypeScript) and
a PyPI package (`agenticworkspace-cli`, Python). Pick whichever fits your
toolchain, or install both.

## Install

**npm (JS/TS CLI):**

```bash
npx agenticworkspace-cli init
# or, for repeat use:
npm install -g agenticworkspace-cli
agenticworkspace init
```

**pip (Python library + CLI):**

```bash
pip install agenticworkspace-cli
```

The PyPI package is live and installable today. See the root
[README](../README.md#install) for the full install matrix (npm, PyPI, and
from-source options for both).

## Your first run

Both packages write the same `.workspace/` shape, so a repo initialized by
one CLI is fully readable by the other.

```bash
# npm CLI
npx agenticworkspace-cli init --path ./my-app

# Python CLI (after `pip install agenticworkspace-cli`)
agenticworkspace init --path ./my-app
```

Real output (Python CLI shown; the npm CLI's human-readable output is
line-for-line identical apart from the invocation itself):

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

Add `--json` for structured output any calling agent can parse directly
instead of scraping the human-readable text:

```bash
agenticworkspace init --path ./my-app --json
```

`init` is idempotent -- re-running it re-scans the repo and rewrites the
scaffold deterministically; it never duplicates files or corrupts a prior
run.

## Using the library instead of the CLI

Both packages export the underlying scan/scaffold/adapter functions for
programmatic use -- an agent framework that wants to call AgenticWorkspace
in-process instead of shelling out to a CLI binary.

**TypeScript:**

```ts
import { detectStack, runInitEngine } from 'agenticworkspace-cli';

const stack = await detectStack('./my-app');
console.log(stack.language, stack.packageManager, stack.monorepo.isMonorepo);
```

**Python:**

```python
from agenticworkspace import detect_stack, run_init_engine

stack = detect_stack("./my-app")
print(stack.language, stack.package_manager, stack.monorepo.is_monorepo)
```

See [concepts.md](./concepts.md) for the full data model and the two plugin
interfaces (`MemoryBackend`, `Adapter`) both packages implement.

## Next steps

- [concepts.md](./concepts.md) -- the scan/scaffold/adapter pipeline, the
  `.workspace/` directory shape, and the two plugin extension points.
- [integrations/ci.md](./integrations/ci.md) -- running `agenticworkspace
  init`/`status` as a CI check.
- [integrations/custom-plugin.md](./integrations/custom-plugin.md) -- writing
  a custom `MemoryBackend` or `Adapter` plugin.
- The [project README](../README.md) for the full CLI reference, the
  `.workspace/` directory layout, and the comparison against repo-harness and
  harnesskit.
