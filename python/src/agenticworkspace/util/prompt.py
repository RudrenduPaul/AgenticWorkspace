"""
Interactive terminal prompts used by the `init` command's partial-state
repair/reset/abort flow. Ported from src/agenticworkspace/util/prompt.ts.
"""
from __future__ import annotations

import sys
from typing import Literal

RepairResetAbortChoice = Literal["repair", "reset", "abort"]


def ask(question: str) -> str:
    """Ask a free-form question and return the trimmed answer."""
    answer = input(question)
    return answer.strip()


def ask_yes_no(question: str, default_yes: bool = True) -> bool:
    """Ask a yes/no question. Defaults to default_yes if the user just presses enter."""
    suffix = "[Y/n]" if default_yes else "[y/N]"
    answer = ask(f"{question} {suffix} ").lower()
    if answer == "":
        return default_yes
    return answer in ("y", "yes")


def ask_repair_reset_abort() -> RepairResetAbortChoice:
    """Ask the repair / reset / abort question used by partial-state handling."""
    answer = ask("Choose an option: [r]epair / reset ([w]ipe and start clean) / [a]bort: ").lower()
    if answer == "repair" or (answer.startswith("r") and not answer.startswith("re")):
        return "repair"
    if answer.startswith("w") or answer == "reset":
        return "reset"
    return "abort"


def is_interactive_terminal() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()
