"""
`agenticworkspace adapter install <name>` -- (re)install a single adapter's
hook wiring, without re-running the full init scaffold. Ported from
src/agenticworkspace/commands/adapter.ts.
"""
from __future__ import annotations

import os
from typing import Optional

from ..adapters.registry import get_adapter
from ..adapters.types import AdapterInstallOptions
from ..scaffold.context_generator import detect_module_candidates
from ..scan.stack_detector import detect_stack
from ..state.partial_state import detect_partial_state
from ..util.exit_codes import EXIT_CODES
from .init import CommandOutcome


class AdapterInstallCommandOptions:
    def __init__(self, path: Optional[str] = None, json: bool = False) -> None:
        self.path = path
        self.json = json


def run_adapter_install_command(adapter_name: str, options: AdapterInstallCommandOptions) -> CommandOutcome:
    repo_path = os.path.abspath(options.path or os.getcwd())
    workspace_dir = os.path.join(repo_path, ".workspace")

    adapter = get_adapter(adapter_name)
    if adapter is None:
        return CommandOutcome(
            exit_code=EXIT_CODES["GENERAL_ERROR"],
            json={"ok": False, "error": "unknown_adapter", "adapter": adapter_name},
            human_lines=[f'Error: unknown adapter "{adapter_name}".'],
        )

    if not adapter.is_implemented:
        return CommandOutcome(
            exit_code=EXIT_CODES["ADAPTER_NOT_IMPLEMENTED"],
            json={
                "ok": False,
                "error": "adapter_not_implemented",
                "adapter": adapter.name,
                "description": adapter.describe(),
            },
            human_lines=[adapter.describe(), "This adapter cannot be installed in v0.1."],
        )

    partial_state = detect_partial_state(workspace_dir)
    if partial_state.type == "none":
        return CommandOutcome(
            exit_code=EXIT_CODES["NO_WORKSPACE_FOUND"],
            json={
                "ok": False,
                "error": "no_workspace_found",
                "message": "No .workspace/ directory found. Run 'agenticworkspace init' first.",
            },
            human_lines=["No .workspace/ directory found. Run 'agenticworkspace init' first."],
        )

    stack = detect_stack(repo_path)
    modules = detect_module_candidates(repo_path, stack)
    adapter.install(
        workspace_dir,
        AdapterInstallOptions(repo_path=repo_path, module_names=[m.name for m in modules]),
    )

    return CommandOutcome(
        exit_code=EXIT_CODES["OK"],
        json={"ok": True, "adapter": adapter.name, "hook_schema_version": adapter.hook_schema_version},
        human_lines=[f"{adapter.name} adapter installed (hook schema {adapter.hook_schema_version})."],
    )
