# Security Policy

AgenticWorkspace scans and writes files inside a target repository that may
not be fully trusted or audited yet -- that's the whole point of a
stack-detection-and-scaffolding tool. A vulnerability in AgenticWorkspace
itself -- something that lets a crafted repo make either CLI write, read, or
execute something outside the intended `.workspace/` scope, or that lets a
crafted repo's contents get executed rather than only scanned -- is taken
seriously and handled as a priority.

## Supported versions

| Package | Version | Supported |
| --- | --- | --- |
| `agenticworkspace-cli` (npm) | 0.1.x | Yes |
| `agenticworkspace-cli` (PyPI) | 0.1.x | Yes |

Both distributions are pre-1.0 and under active development. Security fixes
land on the latest `0.1.x` release of each; there is no older supported line
to backport to yet.

## Reporting a vulnerability

**Do not open a public GitHub issue for a security vulnerability.**

Report it privately via
[GitHub Security Advisories](https://github.com/RudrenduPaul/AgenticWorkspace/security/advisories/new)
for this repository. Include:

- Which distribution is affected (npm package, PyPI package, or both).
- A minimal reproduction: the target repo content (or a description of its
  shape) and the command/library call that triggers the issue.
- What you expected AgenticWorkspace to do, and what it actually did.
- Your assessment of impact -- e.g. "a crafted `package.json` `workspaces`
  glob makes the scanner read or write outside the target repo" is exactly
  the kind of trust-boundary issue this project actively defends against
  (see the path-traversal containment check described below).

## What counts as in scope

- Any code path where content read from the *scanned target repo* (file
  contents, filenames, `package.json`/`pyproject.toml` fields, a
  `workspaces` glob) is executed, evaluated, or dynamically
  imported/required, rather than only read and pattern-matched.
- A crafted target repo causing AgenticWorkspace to read, write, or resolve
  a path outside the repo it was pointed at. The known, defended-against
  case: a monorepo `workspaces` glob (e.g. `../sibling-project`) that
  resolves outside the scanned repo root is dropped, never followed --
  covered by `_add_if_within_repo`/`addIfWithinRepo` in both stack
  detectors, with a dedicated regression test in both suites.
- Shell-injection into a generated hook script. Every scanned value the
  Claude Code adapter embeds into a `.sh` file passes through the shared
  sanitization module (allowlist plus POSIX shell quoting) first; a value
  that reaches a generated script without going through that module is a
  bug in scope for this policy.
- A plugin-registration path that AgenticWorkspace itself triggers
  automatically from data found inside a scanned repo, rather than from an
  explicit line of code a human wrote. (Registering a `MemoryBackend` or
  `Adapter` today is always an explicit, human-authored `registry.append(...)`
  / `registry.push(...)` call in the caller's own code -- see
  [docs/integrations/custom-plugin.md](./docs/integrations/custom-plugin.md)'s
  "Trust model" section for the plugin-loading trust boundary this project
  deliberately does not try to sandbox.)

## What is out of scope

- The behavior of a `MemoryBackend` or `Adapter` plugin that a user
  registered themselves, whether first-party or third-party -- plugin code
  runs with the caller's full process permissions by design (documented,
  not a bug); report issues in a specific third-party plugin to that
  plugin's own maintainer.
- Vulnerabilities in a scanned target repo itself (i.e. the thing
  AgenticWorkspace is pointed at) -- report those to the target repo's own
  maintainers.

## Response

We aim to acknowledge a report within 5 business days and to have a fix or
a mitigation plan within 30 days for a confirmed, in-scope vulnerability.
Credit is given in the release notes unless you ask to remain anonymous.
