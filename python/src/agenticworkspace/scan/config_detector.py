"""
Existing agent-config detection. AgenticWorkspace never overwrites any of
these files; init only reports their presence. Ported from
src/agenticworkspace/scan/config-detector.ts.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from ..util.fs_utils import dir_exists, file_exists


@dataclass
class ExistingConfigResult:
    claude_md: bool
    agents_md: bool
    cursor_rules: bool
    copilot_instructions: bool
    # True if any agent-config surface already exists -- init must never overwrite these.
    any_detected: bool


def detect_existing_config(repo_path: str) -> ExistingConfigResult:
    claude_md = file_exists(os.path.join(repo_path, "CLAUDE.md"))
    agents_md = file_exists(os.path.join(repo_path, "AGENTS.md"))
    cursor_rules = dir_exists(os.path.join(repo_path, ".cursor", "rules"))
    copilot_instructions = file_exists(os.path.join(repo_path, ".github", "copilot-instructions.md"))

    return ExistingConfigResult(
        claude_md=claude_md,
        agents_md=agents_md,
        cursor_rules=cursor_rules,
        copilot_instructions=copilot_instructions,
        any_detected=claude_md or agents_md or cursor_rules or copilot_instructions,
    )
