# Concepts

## The init pipeline

Both the npm and PyPI packages run the same pipeline (TypeScript:
`src/agenticworkspace/scaffold/init-engine.ts`; Python:
`agenticworkspace/scaffold/init_engine.py`):

```
repo path
     |
     v
partial-state check   -> is there a leftover .workspace/ from an interrupted
     |                    or malformed prior run? If so: repair/reset/abort
     |                    (interactive), or a structured JSON error with
     |                    exit code 2 (non-interactive / --json).
     v
stack detector          -> language, package manager, monorepo info
     +
config detector         -> CLAUDE.md / AGENTS.md / .cursor/rules / copilot-instructions.md
     +                      presence only -- never overwritten
memory-backend registry -> Serena / GitNexus / repo-harness presence, detect-only
     |
     v
module candidate detection -> monorepo packages, or src/* subdirectories
     |
     v
progressive context generation -> root-context.md (~12KB budget) + per-module files
     |
     v
Claude Code adapter install -> sanitized hook scripts + settings.json
     |
     v
workspace.json manifest written
```

Every step through module candidate detection is read-only against the
target repo; only the last two steps (context generation, adapter install)
write files, and only under `.workspace/`. Detection failures in one
memory-backend plugin are caught and reported as not-detected, never allowed
to abort the whole scan.

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
      adapter-meta.json        hook schema version + install timestamp, used for staleness checks
      hooks/
        session-start.sh       loads root-context.md + relevant module blocks
        pre-tool-call.sh        lightweight guard, extendable per project
        session-end-handoff.sh writes the next handoff/ file automatically
```

`workspace.json` uses the same camelCase field shape in both the
TypeScript and Python packages -- both CLIs can read and write the same
`.workspace/` directory in the same repo interchangeably; the manifest is
the one file both languages agree on byte-for-byte.

## The two plugin interfaces

AgenticWorkspace is built around two small extension points rather than one
project doing everything itself. Both are ported with the same contract in
Python and TypeScript.

### `MemoryBackend`

Detects whether a repo already has a memory/context tool wired in, so
`init` can report it and avoid silently duplicating or conflicting with a
tool a team has already adopted. A backend's `detect()` must be a read-only
filesystem check -- never write, modify, or delete anything belonging to
another tool.

```ts
// TypeScript: src/agenticworkspace/memory-backends/types.ts
export interface MemoryBackend {
  name: string;
  detect(repoPath: string): Promise<boolean>;
  describe(): string;
}
```

```python
# Python: agenticworkspace/memory_backends/types.py
class MemoryBackend(ABC):
    name: str

    @abstractmethod
    def detect(self, repo_path: str) -> bool: ...

    @abstractmethod
    def describe(self) -> str: ...
```

Three backends ship first-party in both packages: Serena (`.serena/`),
GitNexus (`.gitnexus/` or `gitnexus.config.json`), and repo-harness
(`.ai/harness/`). Add a new one by implementing the interface and appending
an instance to the registry list (`memory_backend_registry` in Python,
`memoryBackendRegistry` in TypeScript) -- no CLI or scan code changes
required. See [integrations/custom-plugin.md](./integrations/custom-plugin.md)
for a worked example.

### `Adapter`

Wires the `.workspace/` scaffold into a specific coding tool: install, a
staleness check against the adapter's own hook-schema version, and a
human-readable description.

```ts
// TypeScript: src/agenticworkspace/adapters/types.ts
export interface Adapter {
  name: string;
  hookSchemaVersion: string;
  isImplemented: boolean;
  describe(): string;
  isInstalled(workspaceDir: string): Promise<boolean>;
  install(workspaceDir: string, opts: AdapterInstallOptions): Promise<void>;
  checkStale(workspaceDir: string): Promise<boolean>;
}
```

```python
# Python: agenticworkspace/adapters/types.py
class Adapter(ABC):
    name: str
    hook_schema_version: str
    is_implemented: bool

    @abstractmethod
    def describe(self) -> str: ...
    @abstractmethod
    def is_installed(self, workspace_dir: str) -> bool: ...
    @abstractmethod
    def install(self, workspace_dir: str, opts: AdapterInstallOptions) -> None: ...
    @abstractmethod
    def check_stale(self, workspace_dir: str) -> bool: ...
```

Three adapters are registered in both packages: Claude Code (fully
implemented -- real hook scripts plus `settings.json` wiring), Codex, and
Cursor. The latter two are honest stubs: `is_implemented = False`, and
`install()` raises rather than silently doing nothing, so a caller cannot
mistake a no-op for a real install. Add a new adapter by implementing the
interface and appending an instance to the registry list (`adapter_registry`
in Python, `adapterRegistry` in TypeScript).

## Stack detection

Real filesystem checks against the target repo, no network calls, no
guessing from file extensions alone:

| Signal | Language | Package manager |
| --- | --- | --- |
| `package.json` + `pnpm-lock.yaml` or `pnpm-workspace.yaml` | JS/TS | pnpm |
| `package.json` + `yarn.lock` | JS/TS | yarn |
| `package.json` + `package-lock.json` | JS/TS | npm |
| `package.json` alone (no lockfile) | JS/TS | npm (ecosystem default) |
| `package.json` + `tsconfig.json` | TypeScript | (per above) |
| `pyproject.toml` | Python | poetry |
| `Pipfile` | Python | pip |
| `requirements.txt` | Python | pip |
| `Cargo.toml` | Rust | cargo |
| `go.mod` | Go | go |
| `Gemfile` | Ruby | bundler |

Monorepo detection resolves `package.json`'s `workspaces` field (array or
`{ packages: [...] }` form) or `pnpm-workspace.yaml`'s `packages:` block,
supporting the common `dir/*` glob and exact-path entries. Negation globs
(`!pattern`) are recognized and skipped rather than mis-included -- full glob
negation is not implemented in v0.1. Every resolved package path is checked
to stay within the scanned repo root; a workspace glob that resolves outside
it (e.g. `../sibling-project`, whether malicious or just a stale config) is
dropped rather than silently followed -- see the "Trust boundaries" section
of [SECURITY.md](../SECURITY.md).

## Shell-injection defense in the Claude Code adapter

The one first-party adapter that writes executable content (Claude Code)
embeds detected module names into generated `.sh` hook scripts. Every value
passes through a shared sanitization module first, in both languages:

1. **Allowlist**: only `[A-Za-z0-9_/-]` is accepted, max 512 characters.
   Anything else is rejected and dropped with a warning, not embedded.
2. **POSIX single-quote shell quoting**: applied to every value that does
   pass the allowlist, even though the allowlist already excludes shell
   metacharacters -- defense in depth against a future allowlist regression.

A module name that fails the allowlist is skipped (with a warning printed to
stderr); it does not abort the whole adapter install.

## Partial-state detection

An interrupted or hand-edited `.workspace/` directory is classified before
`init` touches anything:

| State | Meaning |
| --- | --- |
| `none` | No `.workspace/` -- fresh init. |
| `complete` | Valid manifest, no leftover marker -- safe to re-scan idempotently. |
| `interrupted-init` | A `.init-in-progress` marker file is still present -- a prior run crashed or was killed mid-write. |
| `missing-manifest` | `.workspace/` exists but has no `workspace.json` at all. |
| `malformed-manifest` | `workspace.json` exists but is missing required top-level keys. |

In an interactive terminal, `init` prompts to repair (re-run the idempotent
engine over what's there), reset (wipe `.workspace/` and start clean), or
abort (leave everything untouched). In `--json` mode or a non-interactive
terminal, `init` never prompts -- it returns a structured error with exit
code `2` instead, so an agent or CI pipeline never gets stuck waiting on
stdin.
