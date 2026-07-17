"""
Cursor adapter -- registered so the adapter registry and CLI plumbing are
real and extensible, but NOT YET IMPLEMENTED in v0.1. install() raises rather
than silently doing nothing, so a caller cannot mistake a no-op for a real
install. Tracked as v0.2 scope -- a community-contributed shim following the
same handoff/context model as the Claude Code adapter. Ported from
src/agenticworkspace/adapters/cursor/index.ts.
"""
from __future__ import annotations

from ..types import Adapter, AdapterInstallOptions


class CursorAdapter(Adapter):
    name = "cursor"
    hook_schema_version = "unreleased"
    is_implemented = False

    def describe(self) -> str:
        return "Cursor adapter -- NOT YET IMPLEMENTED (planned for v0.2, community-contributed shim)"

    def is_installed(self, workspace_dir: str) -> bool:
        return False

    def install(self, workspace_dir: str, opts: AdapterInstallOptions) -> None:
        raise NotImplementedError(
            "agenticworkspace: the Cursor adapter is not yet implemented (planned for v0.2). "
            "Only the Claude Code adapter works end to end in v0.1."
        )

    def check_stale(self, workspace_dir: str) -> bool:
        return False


cursor_adapter = CursorAdapter()
