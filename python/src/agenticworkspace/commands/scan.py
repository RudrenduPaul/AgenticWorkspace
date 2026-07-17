"""
`agenticworkspace scan` -- read-only stack + tooling-surface detection, no
writes. Ported from src/agenticworkspace/commands/scan.ts.
"""
from __future__ import annotations

import os
from typing import Optional

from ..memory_backends.registry import detect_all_memory_backends
from ..scan.config_detector import detect_existing_config
from ..scan.stack_detector import detect_stack
from ..util.exit_codes import EXIT_CODES
from .init import CommandOutcome


class ScanCommandOptions:
    def __init__(self, path: Optional[str] = None, json: bool = False) -> None:
        self.path = path
        self.json = json


def run_scan_command(options: ScanCommandOptions) -> CommandOutcome:
    repo_path = os.path.abspath(options.path or os.getcwd())

    stack = detect_stack(repo_path)
    existing_config = detect_existing_config(repo_path)
    memory_backends = detect_all_memory_backends(repo_path)

    human_lines = []
    human_lines.append(f"AgenticWorkspace scan -- {repo_path}")
    monorepo_suffix = (
        f", monorepo ({stack.monorepo.package_count} packages)" if stack.monorepo.is_monorepo else ""
    )
    human_lines.append(f"Stack: {stack.language}, {stack.package_manager}{monorepo_suffix}")
    human_lines.append(f"Signals: {', '.join(stack.signals) if stack.signals else 'none'}")

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
        human_lines.append(f"Existing agent config: yes ({', '.join(found)})")
    else:
        human_lines.append("Existing agent config: no")

    detected = [b for b in memory_backends if b.detected]
    human_lines.append(
        f"Memory/context backends detected: {', '.join(b.name for b in detected) if detected else 'none'}"
    )

    return CommandOutcome(
        exit_code=EXIT_CODES["OK"],
        json={
            "ok": True,
            "target": repo_path,
            "stack": {
                "language": stack.language,
                "package_manager": stack.package_manager,
                "monorepo": stack.monorepo.is_monorepo,
                "packages": stack.monorepo.package_count,
                "signals": stack.signals,
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
        },
        human_lines=human_lines,
    )
