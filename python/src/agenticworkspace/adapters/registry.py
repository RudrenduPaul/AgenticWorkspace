"""
The registry of all known Adapter implementations. Adding a new tool adapter
means implementing Adapter and adding it here -- nothing else in scaffold or
CLI code needs to change. Only claude_code_adapter is fully implemented in
v0.1; codex and cursor are registered stubs. Ported from
src/agenticworkspace/adapters/registry.ts.
"""
from __future__ import annotations

from typing import List, Optional

from .claude_code.install import claude_code_adapter
from .codex import codex_adapter
from .cursor import cursor_adapter
from .types import Adapter

adapter_registry: List[Adapter] = [claude_code_adapter, codex_adapter, cursor_adapter]


def get_adapter(name: str) -> Optional[Adapter]:
    for adapter in adapter_registry:
        if adapter.name == name:
            return adapter
    return None
