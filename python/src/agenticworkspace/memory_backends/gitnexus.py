"""
GitNexus-style config detection. GitNexus-family tools commonly place either
a `.gitnexus/` directory or a root-level `gitnexus.config.json` file -- this
checks both, since exact conventions vary by fork/version, and any one of
them being present is enough to report it. Detect only. Ported from
src/agenticworkspace/memory-backends/gitnexus.ts.
"""
from __future__ import annotations

import os

from ..util.fs_utils import dir_exists, file_exists
from .types import MemoryBackend


class GitNexusBackend(MemoryBackend):
    name = "gitnexus"

    def detect(self, repo_path: str) -> bool:
        has_dir = dir_exists(os.path.join(repo_path, ".gitnexus"))
        has_config_file = file_exists(os.path.join(repo_path, "gitnexus.config.json"))
        return has_dir or has_config_file

    def describe(self) -> str:
        return "GitNexus-style config (.gitnexus/ or gitnexus.config.json)"


git_nexus_backend = GitNexusBackend()
