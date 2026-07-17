"""
The Claude Code adapter -- the one fully-implemented Adapter in v0.1. Writes
real hook scripts (session-start, pre-tool-call, session-end handoff) plus
settings.json wiring under .workspace/adapters/claude-code/. Ported from
src/agenticworkspace/adapters/claude-code/install.ts.
"""
from __future__ import annotations

import os
import stat
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ...util.fs_utils import ensure_dir, file_exists, read_json_if_exists, write_json, write_text
from ..types import Adapter, AdapterInstallOptions
from .hook_scripts import (
    HookScriptInputs,
    build_pre_tool_call_script,
    build_session_end_handoff_script,
    build_session_start_script,
)

# Bumped whenever the shape of settings.json or the hook scripts changes in a
# way staleness detection should catch.
CLAUDE_CODE_HOOK_SCHEMA_VERSION = "2026-07-01"

_ADAPTER_DIR_NAME = "claude-code"


@dataclass
class ClaudeCodeAdapterMeta:
    hook_schema_version: str
    installed_at: str


def _adapter_dir(workspace_dir: str) -> str:
    return os.path.join(workspace_dir, "adapters", _ADAPTER_DIR_NAME)


def _meta_path(workspace_dir: str) -> str:
    return os.path.join(_adapter_dir(workspace_dir), "adapter-meta.json")


def _settings_path(workspace_dir: str) -> str:
    return os.path.join(_adapter_dir(workspace_dir), "settings.json")


def _hooks_dir(workspace_dir: str) -> str:
    return os.path.join(_adapter_dir(workspace_dir), "hooks")


def _build_settings() -> Dict[str, object]:
    def hook_command(script: str) -> str:
        return f"bash .workspace/adapters/claude-code/hooks/{script}"

    return {
        "hooks": {
            "SessionStart": [
                {"matcher": "", "hooks": [{"type": "command", "command": hook_command("session-start.sh")}]}
            ],
            "PreToolUse": [
                {"matcher": "", "hooks": [{"type": "command", "command": hook_command("pre-tool-call.sh")}]}
            ],
            "SessionEnd": [
                {
                    "matcher": "",
                    "hooks": [{"type": "command", "command": hook_command("session-end-handoff.sh")}],
                }
            ],
        }
    }


class ClaudeCodeAdapter(Adapter):
    name = _ADAPTER_DIR_NAME
    hook_schema_version = CLAUDE_CODE_HOOK_SCHEMA_VERSION
    is_implemented = True

    def describe(self) -> str:
        return (
            "Claude Code adapter -- real hook + settings wiring "
            "(session-start, pre-tool-call, session-end handoff)"
        )

    def is_installed(self, workspace_dir: str) -> bool:
        return file_exists(_settings_path(workspace_dir))

    def install(self, workspace_dir: str, opts: AdapterInstallOptions) -> None:
        scripts_dir = _hooks_dir(workspace_dir)
        ensure_dir(scripts_dir)

        module_names: List[str] = opts.module_names or []
        warnings: List[str] = []

        def warn(message: str) -> None:
            warnings.append(message)

        scripts = [
            ("session-start.sh", build_session_start_script(HookScriptInputs(module_names, warn))),
            ("pre-tool-call.sh", build_pre_tool_call_script(HookScriptInputs(module_names, warn))),
            (
                "session-end-handoff.sh",
                build_session_end_handoff_script(HookScriptInputs(module_names, warn)),
            ),
        ]

        for file_name, content in scripts:
            target_path = os.path.join(scripts_dir, file_name)
            write_text(target_path, content)
            os.chmod(target_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)  # 0o755

        for warning in warnings:
            # Logged, never raised -- a rejected value is skipped, not fatal.
            print(f"[agenticworkspace] {warning}", file=sys.stderr)

        write_json(_settings_path(workspace_dir), _build_settings())

        meta = {
            "hookSchemaVersion": CLAUDE_CODE_HOOK_SCHEMA_VERSION,
            "installedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        write_json(_meta_path(workspace_dir), meta)

    def check_stale(self, workspace_dir: str) -> bool:
        meta = read_json_if_exists(_meta_path(workspace_dir))
        if not meta:
            return False  # not installed at all is reported separately via is_installed()
        return meta.get("hookSchemaVersion") != CLAUDE_CODE_HOOK_SCHEMA_VERSION


claude_code_adapter = ClaudeCodeAdapter()


def get_installed_hook_schema_version(workspace_dir: str) -> Optional[str]:
    meta = read_json_if_exists(_meta_path(workspace_dir))
    if not meta:
        return None
    return meta.get("hookSchemaVersion")
