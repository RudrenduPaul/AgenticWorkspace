"""
repo-harness detection: a `.ai/harness/` directory at the repo root. This is
a real, actively maintained competitor (Ancienttwo/repo-harness on npm and
GitHub) that ships its own repo-local context and session-handoff tracking.
AgenticWorkspace detects its presence purely so `init` can report it and
avoid silently duplicating or conflicting with an already-present
repo-harness install -- this backend is never read from, written to, or
modified in any way. Ported from
src/agenticworkspace/memory-backends/repo-harness.ts.
"""
from __future__ import annotations

import os

from ..util.fs_utils import dir_exists
from .types import MemoryBackend


class RepoHarnessBackend(MemoryBackend):
    name = "repo-harness"

    def detect(self, repo_path: str) -> bool:
        return dir_exists(os.path.join(repo_path, ".ai", "harness"))

    def describe(self) -> str:
        return "repo-harness (.ai/harness/ directory) -- detected only, never modified"


repo_harness_backend = RepoHarnessBackend()
