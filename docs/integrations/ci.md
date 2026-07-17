# CI integrations

AgenticWorkspace's `init`/`status` commands are meant to run as an
onboarding or drift-check step: initialize a fresh `.workspace/` scaffold on
first setup, or verify an existing one hasn't gone stale. Both packages
support the same `--json`/exit-code contract, so pick whichever matches your
pipeline's existing toolchain.

## GitHub Actions -- npm CLI

```yaml
name: AgenticWorkspace check
on: [pull_request]

jobs:
  workspace-status:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Check workspace status
        run: |
          npx agenticworkspace-cli status --json > status.json || true
          cat status.json
      - name: Fail if the adapter is stale
        run: |
          node -e "
            const s = require('./status.json');
            if (s.ok && s.adapters.claude_code.current === false) {
              console.error('Claude Code adapter is stale -- run agenticworkspace init to update.');
              process.exit(1);
            }
          "
```

## GitHub Actions -- Python CLI

```yaml
name: AgenticWorkspace check (Python)
on: [pull_request]

jobs:
  workspace-status:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install agenticworkspace-cli
      - name: Check workspace status
        run: agenticworkspace status --json > status.json || true
      - name: Fail if the adapter is stale
        run: |
          python3 -c "
          import json, sys
          status = json.load(open('status.json'))
          if status.get('ok') and status['adapters']['claude_code']['current'] is False:
              print('Claude Code adapter is stale -- run agenticworkspace init to update.', file=sys.stderr)
              sys.exit(1)
          "
```

## Exit codes for scripting

Both CLIs share one exit-code contract, stable across `--json` and
human-readable modes, so a script can branch on the process exit code
without parsing text:

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | General error (bad input, unexpected filesystem failure) |
| `2` | Partial/malformed `.workspace/` state detected |
| `3` | Adapter not yet implemented (`codex`, `cursor`) |
| `4` | No `.workspace/` found (run `init` first) |

A CI check that only cares "is the workspace present and current" can gate
purely on the exit code of `agenticworkspace status`, without inspecting
JSON at all:

```bash
agenticworkspace status --path . > /dev/null
echo "exit code: $?"
```

## Pre-commit hook (Python CLI)

For a local pre-push check rather than CI, wire the Python CLI into
[pre-commit](https://pre-commit.com/) to keep `.workspace/` from drifting
silently:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: agenticworkspace-status
        name: AgenticWorkspace status check
        entry: agenticworkspace status
        language: system
        pass_filenames: false
```

This assumes `agenticworkspace` is already on `PATH` (installed via `pip
install agenticworkspace-cli` in your dev environment).
