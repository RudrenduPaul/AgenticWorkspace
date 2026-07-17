"""
Git metadata used to stamp session handoff files. Ported from
src/agenticworkspace/util/git-info.ts.

Security note: both calls use subprocess.run with a fixed argument list
(never shell=True, never string-interpolated into a shell command), so
repo_path -- which comes from the CLI's --path flag or a caller-supplied
value -- cannot inject additional shell commands. Any failure (git not
installed, not a git repo, non-zero exit) is caught and turned into None
rather than raised, matching the TypeScript original's never-throws contract.
"""
from __future__ import annotations

import subprocess
from typing import List, Optional


def _run_git(args: List[str], repo_path: str) -> Optional[str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = completed.stdout.strip()
    return output if output else None


def get_current_branch(repo_path: str) -> Optional[str]:
    """Return the current git branch name for the given repo path, or None."""
    return _run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_path)


def get_current_commit(repo_path: str) -> Optional[str]:
    """Return the short commit SHA for HEAD, or None if unavailable."""
    return _run_git(["rev-parse", "--short", "HEAD"], repo_path)
