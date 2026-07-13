# Contributing to WorkspaceForge

Thanks for looking at this project.

## Development setup

```bash
git clone https://github.com/RudrenduPaul/WorkspaceForge.git
cd WorkspaceForge
npm install
npm run build
npm test
```

## Before opening a pull request

- `npm run lint`
- `npm run typecheck`
- `npm run test:coverage`
- `npm run build`

## Adding a new memory-tool backend

Implement the `MemoryBackend` interface (`src/workspaceforge/memory-backends/types.ts`) and
register your instance in `src/workspaceforge/memory-backends/registry.ts`. Detection must stay
read-only: a backend must never write, modify, or delete anything belonging to another tool.

## Adding a new adapter

Implement the `Adapter` interface (`src/workspaceforge/adapters/types.ts`) and register your
instance in `src/workspaceforge/adapters/registry.ts`. See `src/workspaceforge/adapters/codex/`
and `src/workspaceforge/adapters/cursor/` for the shape a not-yet-implemented stub should take, and
`src/workspaceforge/adapters/claude-code/` for a fully working reference implementation.

## Security

Any value derived from scanning a target repository that ends up embedded in a generated shell
script must go through `src/workspaceforge/util/sanitize.ts` first. Do not add a second,
duplicate sanitization path elsewhere in the codebase.
