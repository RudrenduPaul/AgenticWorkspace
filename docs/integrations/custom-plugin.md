# Writing a custom plugin

AgenticWorkspace has two extension points: `MemoryBackend` (detect another
tool's presence) and `Adapter` (wire the `.workspace/` scaffold into a
coding tool). Both are small interfaces with a fixed registration mechanism
-- implement the interface, append an instance to the relevant registry
list, and nothing else in the CLI or scan code needs to change. This is the
real extensibility contract both the TypeScript and Python packages ship;
there is no plugin-marketplace or dynamic-loading layer in v0.1, on purpose
-- see the "Trust model" note at the end of this doc.

## Example: a custom `MemoryBackend`

Say your team uses an internal context tool that writes a `.teamctx/`
directory. Detecting it so `init` reports it (without touching it) takes one
small class.

**Python:**

```python
# my_project/team_ctx_backend.py
import os
from agenticworkspace.memory_backends.types import MemoryBackend
from agenticworkspace.memory_backends.registry import memory_backend_registry


class TeamCtxBackend(MemoryBackend):
    name = "team-ctx"

    def detect(self, repo_path: str) -> bool:
        # Detection must stay read-only -- never write, modify, or delete
        # anything belonging to another tool.
        return os.path.isdir(os.path.join(repo_path, ".teamctx"))

    def describe(self) -> str:
        return "Internal team context tool (.teamctx/ directory)"


# Register it once, at import time, before calling detect_all_memory_backends()
# or run_init_engine() -- e.g. from your own CLI wrapper's entry point.
memory_backend_registry.append(TeamCtxBackend())
```

From then on, `agenticworkspace init` / `scan` / `status` report
`team-ctx: detected` alongside the three first-party backends (Serena,
GitNexus, repo-harness) without any change to AgenticWorkspace's own code.

**TypeScript**, the same shape:

```ts
// my-project/team-ctx-backend.ts
import path from "node:path";
import { dirExists } from "agenticworkspace-cli/dist/agenticworkspace/util/fs-utils.js";
import { memoryBackendRegistry } from "agenticworkspace-cli";
import type { MemoryBackend } from "agenticworkspace-cli";

export const teamCtxBackend: MemoryBackend = {
  name: "team-ctx",
  async detect(repoPath: string): Promise<boolean> {
    return dirExists(path.join(repoPath, ".teamctx"));
  },
  describe(): string {
    return "Internal team context tool (.teamctx/ directory)";
  },
};

memoryBackendRegistry.push(teamCtxBackend);
```

## Example: a minimal custom `Adapter`

An `Adapter` writes real files under `.workspace/adapters/<name>/` and
reports install/staleness state. The Python `examples/03-custom-plugin/`
directory in this repo ships a complete, runnable no-op adapter you can copy
as a starting point -- it writes a single marker file and demonstrates the
full interface (`describe`, `is_installed`, `install`, `check_stale`)
without any real hook-writing logic, so you can see the contract in
isolation before building a real one modeled on
`agenticworkspace/adapters/claude_code/install.py`.

If your adapter writes anything that ends up embedded in a generated shell
script (a module name, a package name, anything derived from scanning the
target repo), route it through `agenticworkspace.util.sanitize` first --
`sanitize_for_shell_embedding()` or `sanitize_list_for_shell_embedding()` --
the same allowlist-plus-quoting module the Claude Code adapter uses. Do not
hand-roll your own escaping.

## Trust model

Registering a plugin means it runs as regular imported code with your
process's full permissions -- neither package sandboxes plugin code, the
same way neither package sandboxes the target repo's own source files it
reads during detection. There is no signature check, no manifest
allowlist, no dynamic marketplace lookup in v0.1: you write the plugin (or
vet a third party's before adding the import), and registration is an
explicit line of code in your own project, never something AgenticWorkspace
does automatically from data found inside the scanned repo. Treat a
third-party plugin the same way you'd treat any other dependency you `pip
install` or `npm install` -- read it before you register it.
