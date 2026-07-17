"""
Console entry point: `agenticworkspace <command> [options]`, installed via
the `agenticworkspace` console-script defined in python/pyproject.toml.

Ported from src/agenticworkspace/cli.ts (which uses `commander`); this port
uses the stdlib `argparse` to avoid a CLI-framework dependency, matching the
same convention skillguard's Python port uses. Subcommands, flags, defaults,
and JSON/human output shape are kept identical to the npm CLI's `--help`
output and the documented CLI reference in the README.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from .commands.adapter import AdapterInstallCommandOptions, run_adapter_install_command
from .commands.handoff import HandoffNewCommandOptions, run_handoff_new_command
from .commands.init import CommandOutcome, InitCommandOptions, run_init_command
from .commands.scan import ScanCommandOptions, run_scan_command
from .commands.status import StatusCommandOptions, run_status_command
from .scaffold.init_engine import AGENTICWORKSPACE_VERSION
from .util.exit_codes import EXIT_CODES

_DESCRIPTION = (
    "Convert any repository into an agent-ready workspace: stack detection, "
    "progressive context, session handoffs, and a Claude Code adapter."
)


def _add_common_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-p", "--path", default=None, help="path to the target repo (default: current directory)")
    parser.add_argument("--json", action="store_true", default=False, help="output structured JSON instead of human-readable text")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agenticworkspace", description=_DESCRIPTION)
    parser.add_argument(
        "--version", action="version", version=f"agenticworkspace-cli {AGENTICWORKSPACE_VERSION}"
    )

    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser(
        "init", help="Scan the repo and write the .workspace/ scaffold plus the Claude Code adapter"
    )
    _add_common_flags(init_parser)

    scan_parser = subparsers.add_parser(
        "scan", help="Detect stack and existing agent-tooling surface, no writes"
    )
    _add_common_flags(scan_parser)

    status_parser = subparsers.add_parser(
        "status", help="Report workspace health: stack, context budget, handoffs, adapter staleness"
    )
    _add_common_flags(status_parser)

    adapter_parser = subparsers.add_parser("adapter", help="Manage tool adapters")
    adapter_subparsers = adapter_parser.add_subparsers(dest="adapter_command")
    adapter_install_parser = adapter_subparsers.add_parser(
        "install", help="(Re)install a single adapter's hook wiring (e.g. claude-code)"
    )
    adapter_install_parser.add_argument("name", help="adapter name, e.g. claude-code, codex, cursor")
    _add_common_flags(adapter_install_parser)

    handoff_parser = subparsers.add_parser("handoff", help="Manage session handoff files")
    handoff_subparsers = handoff_parser.add_subparsers(dest="handoff_command")
    handoff_new_parser = handoff_subparsers.add_parser("new", help="Write a new timestamped handoff file")
    handoff_new_parser.add_argument("message", help="handoff note to record")
    _add_common_flags(handoff_new_parser)

    return parser


def _emit(outcome: CommandOutcome, json_mode: bool) -> None:
    if json_mode:
        print(json.dumps(outcome.json, indent=2))
    else:
        for line in outcome.human_lines:
            print(line)


def run_cli(argv: List[str]) -> int:
    """
    `argv` follows the sys.argv convention: argv[0] is the program name, the
    real arguments start at argv[1]. Returns the process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    json_mode = bool(getattr(args, "json", False))

    if args.command == "init":
        outcome = run_init_command(InitCommandOptions(path=args.path, json=json_mode))
    elif args.command == "scan":
        outcome = run_scan_command(ScanCommandOptions(path=args.path, json=json_mode))
    elif args.command == "status":
        outcome = run_status_command(StatusCommandOptions(path=args.path, json=json_mode))
    elif args.command == "adapter":
        if getattr(args, "adapter_command", None) != "install":
            parser.parse_args(["adapter", "--help"])
            return EXIT_CODES["OK"]
        outcome = run_adapter_install_command(args.name, AdapterInstallCommandOptions(path=args.path, json=json_mode))
    elif args.command == "handoff":
        if getattr(args, "handoff_command", None) != "new":
            parser.parse_args(["handoff", "--help"])
            return EXIT_CODES["OK"]
        outcome = run_handoff_new_command(args.message, HandoffNewCommandOptions(path=args.path, json=json_mode))
    else:
        parser.print_help()
        return EXIT_CODES["OK"]

    _emit(outcome, json_mode)
    return outcome.exit_code


def main(argv: Optional[List[str]] = None) -> None:
    real_argv = argv if argv is not None else sys.argv
    try:
        code = run_cli(real_argv)
    except SystemExit:
        raise
    except Exception as error:  # noqa: BLE001 -- top-level crash guard, mirrors cli.ts's catch-all
        # Any error that escapes a command's own try/except (e.g. an
        # unwritable or nonexistent --path) still has to honor --json -- an
        # agent invoking this CLI programmatically parses stdout as JSON and
        # must never be handed a bare stderr string instead.
        message = str(error)
        json_mode = "--json" in real_argv
        if json_mode:
            print(json.dumps({"ok": False, "error": "unexpected_error", "message": message}, indent=2))
        else:
            print(f"agenticworkspace: {message}", file=sys.stderr)
        sys.exit(EXIT_CODES["GENERAL_ERROR"])
    else:
        sys.exit(code)


if __name__ == "__main__":
    main()
