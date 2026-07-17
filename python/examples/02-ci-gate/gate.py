#!/usr/bin/env python3
"""
02 -- CI gate.

Demonstrates using AgenticWorkspace as an actual CI gate script: initializes
a workspace if one doesn't exist yet, then checks status and fails (non-zero
exit) if the Claude Code adapter is stale or the workspace state is
partial/malformed -- exactly what you'd drop into a CI pipeline step (see
../../../docs/integrations/ci.md for the GitHub Actions version of this same
pattern). Runs against a throwaway sample repo by default so it's runnable
with zero arguments; pass a real repo path as argv[1] to check a real
project.

Run:
    python3 examples/02-ci-gate/gate.py
    python3 examples/02-ci-gate/gate.py /path/to/a/real/repo
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

from agenticworkspace.commands.init import InitCommandOptions, run_init_command
from agenticworkspace.commands.status import StatusCommandOptions, run_status_command


def build_sample_repo(root: Path) -> None:
    (root / "requirements.txt").write_text("requests\n")
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("print('hello')\n")


def main() -> int:
    cleanup_dir = None
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    else:
        cleanup_dir = Path(tempfile.mkdtemp(prefix="agenticworkspace-ci-gate-"))
        build_sample_repo(cleanup_dir)
        target = cleanup_dir

    try:
        init_outcome = run_init_command(InitCommandOptions(path=str(target), json=True))
        if init_outcome.exit_code != 0:
            print("FAIL: init did not complete cleanly.", file=sys.stderr)
            print(json.dumps(init_outcome.json, indent=2), file=sys.stderr)
            return init_outcome.exit_code

        status_outcome = run_status_command(StatusCommandOptions(path=str(target), json=True))
        payload = status_outcome.json

        if status_outcome.exit_code != 0:
            print(f"FAIL: status check failed ({payload.get('error')}).", file=sys.stderr)
            return status_outcome.exit_code

        adapter_current = payload["adapters"]["claude_code"]["current"]
        if not adapter_current:
            print("FAIL: Claude Code adapter is stale -- run 'agenticworkspace init' to update.", file=sys.stderr)
            return 1

        print(f"PASS: workspace at {target} is current.")
        print(f"  stack: {payload['stack']['language']}, {payload['stack']['package_manager']}")
        print(f"  context budget: {payload['context']['root_context_kb']}KB of {payload['context']['budget_kb']}KB")
        return 0
    finally:
        if cleanup_dir is not None:
            shutil.rmtree(cleanup_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
