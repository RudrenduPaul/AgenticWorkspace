"""MCP server for AgenticWorkspace: a single generic `run` tool that shells
out to the installed `agenticworkspace` CLI, rather than hand-mirroring each
subcommand (`init`, `scan`, `status`, `adapter install`, `handoff new`) as
its own typed MCP tool. Every subcommand already emits structured JSON via
`--json` (see cli.py's `_emit`), so this wrapper stays correct as new
subcommands are added to the CLI without needing to be updated in lockstep.

Requires the `mcp` extra (`pip install "agenticworkspace-cli[mcp]"`). Started
via the `agenticworkspace-mcp` console script (stdio transport), so any
MCP-compatible agent runtime (Claude Desktop, Claude Code, etc.) can call
AgenticWorkspace as a tool instead of parsing CLI text output itself.
"""
from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from mcp.server.mcpserver import MCPServer

_TIMEOUT_SECONDS = 120
_FALLBACK_DESCRIPTION = (
    "Run the agenticworkspace CLI with the given argument list (e.g. "
    '["init", "--json", "--path", "/path/to/repo"]) and return its result. '
    "Subcommands: init, scan, status, adapter install <name>, handoff new "
    '<message>. Pass "--json" to get structured output back as a dict; '
    'otherwise the raw stdout text is returned under "output".'
)


def _resolve_cli_command() -> list[str]:
    """Always invokes the CLI as `python -m agenticworkspace.cli` under the
    *same* interpreter this MCP server is running in, rather than searching
    PATH for a binary literally named `agenticworkspace`. Both the npm and
    PyPI packages install a console script with that exact name, so on a
    machine with both installed, `shutil.which("agenticworkspace")` can
    resolve to the Node CLI instead of this package's own -- silently
    talking to the wrong implementation. `python -m` sidesteps that
    ambiguity entirely by staying inside this interpreter's environment."""
    return [sys.executable, "-m", "agenticworkspace.cli"]


def _tool_description() -> str:
    """Builds the `run` tool's description from the CLI's real `--help`
    output at import time, so what an agent sees never drifts from the
    actual command surface. Falls back to a static description if the CLI
    can't be introspected -- this function must never raise."""
    try:
        command = _resolve_cli_command() + ["--help"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
        help_text = (result.stdout or result.stderr or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        return _FALLBACK_DESCRIPTION
    if not help_text:
        return _FALLBACK_DESCRIPTION
    return (
        "Run the agenticworkspace CLI with the given argument list and return "
        f"its result. Real `agenticworkspace --help` output:\n\n{help_text}"
    )


mcp = MCPServer(name="agenticworkspace-cli")


@mcp.tool(description=_tool_description())
def run(args: list[str]) -> dict[str, Any]:
    """Shells out to the installed `agenticworkspace` CLI with `args` and
    returns the result. Never raises: a missing binary, a timeout, a
    non-zero exit, or unparsable stdout all come back as a `{"error": ...}`
    dict instead of an exception. Example: `run(["scan", "--json", "--path",
    "/path/to/repo"])` returns the same parsed JSON object `agenticworkspace
    scan --json --path /path/to/repo` prints to stdout.
    """
    command = _resolve_cli_command() + list(args)
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=_TIMEOUT_SECONDS, check=False
        )
    except OSError as err:
        return {"error": f"failed to launch agenticworkspace CLI: {err}"}
    except subprocess.TimeoutExpired:
        return {"error": f"agenticworkspace CLI timed out after {_TIMEOUT_SECONDS}s"}

    if result.returncode != 0:
        return {
            "error": "agenticworkspace CLI exited non-zero",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"output": result.stdout, "stderr": result.stderr}


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
