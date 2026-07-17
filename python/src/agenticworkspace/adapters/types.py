"""
An Adapter wires AgenticWorkspace's `.workspace/` scaffold into a specific AI
coding tool (Claude Code, Codex, Cursor, ...). Each adapter owns its own
hook/settings format and versioning; the CLI only depends on this interface,
so adding a new tool means implementing Adapter and registering it (see
registry.py), not touching CLI or scaffold code.

This is the second of AgenticWorkspace's two plugin extension points (the
other is MemoryBackend, see memory_backends/types.py). Ported from the
TypeScript interface in src/agenticworkspace/adapters/types.ts, using
Python's abc.ABC for the same enforced-contract reason described there.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AdapterInstallOptions:
    # Absolute path to the repo being converted into a workspace.
    repo_path: str
    # Detected stack info, so hooks can reference real package/module names safely.
    module_names: Optional[List[str]] = field(default_factory=list)


class Adapter(ABC):
    # Stable identifier, e.g. "claude-code". Used as the directory name under .workspace/adapters/.
    name: str

    # Version of this adapter's hook/settings schema. Bumped whenever the shape
    # of what install() writes changes in a way that matters for staleness
    # detection (a new required hook, a renamed settings field).
    hook_schema_version: str

    # True if this adapter is fully implemented and safe to install in this
    # version of AgenticWorkspace.
    is_implemented: bool

    @abstractmethod
    def describe(self) -> str:
        """Human-readable one-liner, used in status output (especially for not-yet-implemented adapters)."""
        raise NotImplementedError

    @abstractmethod
    def is_installed(self, workspace_dir: str) -> bool:
        """True if this adapter is already installed under the given .workspace/ directory."""
        raise NotImplementedError

    @abstractmethod
    def install(self, workspace_dir: str, opts: AdapterInstallOptions) -> None:
        """Install (or reinstall) this adapter's files under the given .workspace/ directory."""
        raise NotImplementedError

    @abstractmethod
    def check_stale(self, workspace_dir: str) -> bool:
        """
        True if the installed adapter's recorded hook schema version is older
        than this adapter's current hook_schema_version -- i.e. it needs
        updating.
        """
        raise NotImplementedError
