"""
`agenticworkspace init` -- scan the repo and write the .workspace/ scaffold
plus the Claude Code adapter. Ported from
src/agenticworkspace/commands/init.ts.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..scaffold.init_engine import InitEngineResult, run_init_engine
from ..state.partial_state import detect_partial_state, reset_workspace
from ..util.exit_codes import EXIT_CODES
from ..util.prompt import ask_repair_reset_abort, is_interactive_terminal


@dataclass
class InitCommandOptions:
    path: Optional[str] = None
    json: bool = False


@dataclass
class CommandOutcome:
    exit_code: int
    json: Dict[str, Any] = field(default_factory=dict)
    human_lines: List[str] = field(default_factory=list)


def _workspace_dir_for(repo_path: str) -> str:
    return os.path.join(repo_path, ".workspace")


def run_init_command(options: InitCommandOptions) -> CommandOutcome:
    """
    Core init command logic, separated from process-exit/print side effects
    so it is directly unit- and integration-testable.
    """
    repo_path = os.path.abspath(options.path or os.getcwd())
    workspace_dir = _workspace_dir_for(repo_path)
    json_mode = bool(options.json)

    partial_state = detect_partial_state(workspace_dir)

    if partial_state.type in ("interrupted-init", "missing-manifest", "malformed-manifest"):
        if json_mode or not is_interactive_terminal():
            return CommandOutcome(
                exit_code=EXIT_CODES["PARTIAL_STATE_DETECTED"],
                json={
                    "ok": False,
                    "error": "partial_state_detected",
                    "partial_state": partial_state.type,
                    "message": partial_state.message,
                    "missing_keys": partial_state.missing_keys,
                    "hint": (
                        "Re-run with an interactive terminal to choose repair/reset/abort, "
                        "or pass --repair / --reset explicitly."
                    ),
                },
                human_lines=[f"Error: {partial_state.message}"],
            )

        print(f"\nAgenticWorkspace detected a partial or malformed .workspace/ state:\n  {partial_state.message}\n")
        choice = ask_repair_reset_abort()

        if choice == "abort":
            return CommandOutcome(
                exit_code=EXIT_CODES["GENERAL_ERROR"],
                json={"ok": False, "error": "aborted_by_user", "partial_state": partial_state.type},
                human_lines=["Aborted. No changes were made to .workspace/."],
            )

        if choice == "reset":
            reset_workspace(workspace_dir)
        # "repair" and "reset" both fall through to a normal init engine run below --
        # reset already wiped the directory, repair re-runs the idempotent engine
        # over what's left, filling in whatever was missing.

    result = run_init_engine(repo_path, workspace_dir)
    return _build_success_outcome(result, partial_state.type not in ("none", "complete"))


def _build_success_outcome(result: InitEngineResult, was_repair_or_reset: bool) -> CommandOutcome:
    stack = result.stack
    existing_config = result.existing_config
    memory_backends = result.memory_backends
    context = result.context
    manifest = result.manifest

    detected_backend_names = [b.name for b in memory_backends if b.detected]

    human_lines: List[str] = []
    human_lines.append("AgenticWorkspace v0.1 -- Repo-to-Agent-Workspace Converter")
    human_lines.append(f"Target: {result.repo_path}")
    human_lines.append("")
    human_lines.append("Scanning repository...")
    monorepo_suffix = (
        f" monorepo, {stack.monorepo.package_count} packages" if stack.monorepo.is_monorepo else ""
    )
    human_lines.append(f"[OK] Stack detected: {stack.language}, {stack.package_manager}{monorepo_suffix}")

    if existing_config.any_detected:
        found = [
            name
            for present, name in (
                (existing_config.claude_md, "CLAUDE.md"),
                (existing_config.agents_md, "AGENTS.md"),
                (existing_config.cursor_rules, ".cursor/rules"),
                (existing_config.copilot_instructions, ".github/copilot-instructions.md"),
            )
            if present
        ]
        human_lines.append(f"[OK] Existing config found: {', '.join(found)} (will not overwrite)")
    else:
        human_lines.append("[--] No existing agent-config files found")

    if detected_backend_names:
        human_lines.append(
            f"[--] Memory/context backend(s) detected: {', '.join(detected_backend_names)} (not modified)"
        )
    else:
        human_lines.append("[--] No memory/context tool detected")

    human_lines.append("")
    human_lines.append(f"{'Repairing' if was_repair_or_reset else 'Writing'} .workspace/ scaffold...")
    human_lines.append("  .workspace/workspace.json                created")
    human_lines.append(
        f"  .workspace/context/root-context.md        created "
        f"({manifest['context']['rootContextKb']}KB of 12KB budget)"
    )
    for module_name in context.module_names:
        human_lines.append(f"  .workspace/context/modules/{module_name}.md         created")
    human_lines.append("  .workspace/handoff/                       created (empty, ready for first session)")
    human_lines.append("")
    human_lines.append("Installing Claude Code adapter...")
    human_lines.append("  .workspace/adapters/claude-code/settings.json         written")
    human_lines.append("  .workspace/adapters/claude-code/hooks/session-start.sh  written")
    human_lines.append("  .workspace/adapters/claude-code/hooks/pre-tool-call.sh  written")
    human_lines.append("  .workspace/adapters/claude-code/hooks/session-end-handoff.sh  written")
    human_lines.append("")
    human_lines.append(
        "Workspace ready. Next Claude Code session in this repo will load root-context.md "
        "automatically and write a handoff file on exit."
    )
    human_lines.append("")
    human_lines.append(f"Full manifest: {os.path.join(result.workspace_dir, 'workspace.json')}")

    return CommandOutcome(
        exit_code=EXIT_CODES["OK"],
        json={
            "ok": True,
            "agenticworkspace_version": manifest["agenticworkspaceVersion"],
            "scanned_at": manifest["lastScanAt"],
            "target": result.repo_path,
            "stack": {
                "language": stack.language,
                "package_manager": stack.package_manager,
                "monorepo": stack.monorepo.is_monorepo,
                "packages": manifest["stack"]["packages"],
            },
            "existing_config": {
                "claudeMd": existing_config.claude_md,
                "agentsMd": existing_config.agents_md,
                "cursorRules": existing_config.cursor_rules,
                "copilotInstructions": existing_config.copilot_instructions,
                "anyDetected": existing_config.any_detected,
            },
            "memory_backends": [
                {"name": b.name, "detected": b.detected, "description": b.description} for b in memory_backends
            ],
            "context": {
                "root_context_kb": manifest["context"]["rootContextKb"],
                "budget_kb": 12,
                "modules": context.module_names,
            },
            "adapters": {
                "claude_code": {"installed": True, "hook_schema_version": result.adapter_hook_schema_version}
            },
            "workspace_dir": result.workspace_dir,
        },
        human_lines=human_lines,
    )
