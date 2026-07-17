"""
`agenticworkspace status` -- workspace health report: stack, context budget
usage, handoff count, adapter staleness. Ported from
src/agenticworkspace/commands/status.ts.
"""
from __future__ import annotations

import os
from typing import Optional

from ..adapters.claude_code.install import claude_code_adapter, get_installed_hook_schema_version
from ..scaffold.handoff_generator import list_handoffs
from ..scaffold.workspace_manifest import read_manifest
from ..state.partial_state import detect_partial_state
from ..util.exit_codes import EXIT_CODES
from .init import CommandOutcome


class StatusCommandOptions:
    def __init__(self, path: Optional[str] = None, json: bool = False) -> None:
        self.path = path
        self.json = json


def run_status_command(options: StatusCommandOptions) -> CommandOutcome:
    repo_path = os.path.abspath(options.path or os.getcwd())
    workspace_dir = os.path.join(repo_path, ".workspace")

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

    if partial_state.type != "complete":
        return CommandOutcome(
            exit_code=EXIT_CODES["PARTIAL_STATE_DETECTED"],
            json={
                "ok": False,
                "error": "partial_state_detected",
                "partial_state": partial_state.type,
                "message": partial_state.message,
            },
            human_lines=[f"Error: {partial_state.message}", "Run 'agenticworkspace init' to repair, reset, or abort."],
        )

    manifest = read_manifest(workspace_dir)
    if not manifest:
        # Should not happen given partial_state.type == "complete", but guard anyway.
        return CommandOutcome(
            exit_code=EXIT_CODES["PARTIAL_STATE_DETECTED"],
            json={"ok": False, "error": "manifest_unreadable"},
            human_lines=["Error: workspace.json could not be read."],
        )

    handoff_summary = list_handoffs(workspace_dir)
    installed_hook_schema_version = get_installed_hook_schema_version(workspace_dir)
    is_installed = claude_code_adapter.is_installed(workspace_dir)
    is_stale = claude_code_adapter.check_stale(workspace_dir) if is_installed else False

    other_backends = [b for b in manifest.get("memoryBackends", []) if b.get("detected")]

    human_lines = []
    human_lines.append("AgenticWorkspace status")
    human_lines.append(f"Target: {repo_path}")
    human_lines.append(f"Last scan: {manifest['lastScanAt']}")
    human_lines.append("")
    human_lines.append(
        f"Stack: {manifest['stack']['language']}, {manifest['stack']['packageManager']}, "
        f"{manifest['stack']['packages']} package(s)"
    )
    human_lines.append(
        f"Context budget: {manifest['context']['rootContextKb']}KB of 12KB "
        f"({len(manifest['context']['modules'])} module block(s))"
    )
    human_lines.append(
        f"Handoffs: {handoff_summary.count} file(s), most recent: {handoff_summary.most_recent or 'none'}"
    )
    adapter_suffix = (
        f", schema {installed_hook_schema_version}, {'STALE (update available)' if is_stale else 'current'}"
        if is_installed
        else ""
    )
    human_lines.append(f"Claude Code adapter: {'installed' if is_installed else 'not installed'}{adapter_suffix}")
    if other_backends:
        human_lines.append(f"Other backends detected: {', '.join(b['name'] for b in other_backends)} (not modified)")
    else:
        human_lines.append("Other backends detected: none")

    return CommandOutcome(
        exit_code=EXIT_CODES["OK"],
        json={
            "ok": True,
            "workspace_version": manifest["agenticworkspaceVersion"],
            "scanned_at": manifest["lastScanAt"],
            "stack": {
                "language": manifest["stack"]["language"],
                "package_manager": manifest["stack"]["packageManager"],
                "packages": manifest["stack"]["packages"],
            },
            "context": {
                "root_context_kb": manifest["context"]["rootContextKb"],
                "budget_kb": 12,
                "modules": len(manifest["context"]["modules"]),
                "stale": False,
            },
            "handoff": {
                "files": handoff_summary.count,
                "most_recent": handoff_summary.most_recent,
            },
            "adapters": {
                "claude_code": {
                    "installed": is_installed,
                    "hook_schema_version": installed_hook_schema_version,
                    "current_schema_version": claude_code_adapter.hook_schema_version,
                    "current": is_installed and not is_stale,
                }
            },
            "compatibility_check": {
                f"existing_{backend['name'].replace('-', '_')}_dir": backend["detected"]
                for backend in manifest.get("memoryBackends", [])
            },
        },
        human_lines=human_lines,
    )
