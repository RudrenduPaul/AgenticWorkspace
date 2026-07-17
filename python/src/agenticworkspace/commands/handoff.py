"""
`agenticworkspace handoff new <message>` -- write a new timestamped session
handoff file. Ported from src/agenticworkspace/commands/handoff.ts.
"""
from __future__ import annotations

import os
from typing import Optional

from ..scaffold.handoff_generator import write_handoff
from ..state.partial_state import detect_partial_state
from ..util.exit_codes import EXIT_CODES
from .init import CommandOutcome


class HandoffNewCommandOptions:
    def __init__(self, path: Optional[str] = None, json: bool = False) -> None:
        self.path = path
        self.json = json


def run_handoff_new_command(message: str, options: HandoffNewCommandOptions) -> CommandOutcome:
    repo_path = os.path.abspath(options.path or os.getcwd())
    workspace_dir = os.path.join(repo_path, ".workspace")

    if not message or len(message.strip()) == 0:
        return CommandOutcome(
            exit_code=EXIT_CODES["GENERAL_ERROR"],
            json={"ok": False, "error": "empty_message", "message": "handoff new requires a non-empty message."},
            human_lines=["Error: handoff new requires a non-empty message."],
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

    written = write_handoff(workspace_dir, repo_path, message.strip())

    return CommandOutcome(
        exit_code=EXIT_CODES["OK"],
        json={
            "ok": True,
            "file": written.file_name,
            "path": written.file_path,
            "message": written.message,
            "metadata": {
                "timestamp": written.metadata.timestamp,
                "branch": written.metadata.branch,
                "commit": written.metadata.commit,
            },
        },
        human_lines=[f"Handoff written: .workspace/handoff/{written.file_name}"],
    )
