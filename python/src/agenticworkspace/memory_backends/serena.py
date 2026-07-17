"""
Serena detection: a `.serena/` directory at the repo root. Detect only --
AgenticWorkspace never reads, writes, or modifies anything inside it. Ported
from src/agenticworkspace/memory-backends/serena.ts.
"""
from __future__ import annotations

import os

from ..util.fs_utils import dir_exists
from .types import MemoryBackend


class SerenaBackend(MemoryBackend):
    name = "serena"

    def detect(self, repo_path: str) -> bool:
        return dir_exists(os.path.join(repo_path, ".serena"))

    def describe(self) -> str:
        return "Serena memory/context tool (.serena/ directory)"


serena_backend = SerenaBackend()
