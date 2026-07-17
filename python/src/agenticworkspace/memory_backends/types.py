"""
A MemoryBackend describes a third-party (or first-party) memory/context tool
that may already be wired into a target repository. AgenticWorkspace never
assumes a specific backend is present -- it detects what is already there and
reports it, so `init` can avoid silently duplicating or conflicting with a
tool a team has already adopted.

This is one of AgenticWorkspace's two plugin extension points (the other is
Adapter, see adapters/types.py). New backends are added by implementing this
interface and registering an instance in the registry (see registry.py) --
no changes to scan or CLI code are needed beyond that registration. This is
a direct, faithful port of the same contract in
src/agenticworkspace/memory-backends/types.ts (a TypeScript interface); this
port uses Python's abc.ABC to keep the same "implement this shape, register
it" extensibility model in idiomatic Python rather than a looser Protocol,
so a plugin author gets a clear, enforced contract to implement against.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class MemoryBackend(ABC):
    """Stable identifier, used in workspace.json and --json output."""

    name: str

    @abstractmethod
    def detect(self, repo_path: str) -> bool:
        """
        Does this repo already have this backend's configuration present?
        Must be a read-only filesystem check -- detect only, never write,
        modify, or delete anything belonging to another tool.
        """
        raise NotImplementedError

    @abstractmethod
    def describe(self) -> str:
        """Human-readable description, used in terminal status output."""
        raise NotImplementedError
