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
    "Runs the agenticworkspace CLI (the same tool published as "
    "`agenticworkspace-cli` on PyPI and npm) as a subprocess and returns its "
    "result as structured JSON. Call this when an agent needs to turn a "
    "repository into an agent-ready workspace: detect its stack, scaffold a "
    "`.workspace/` directory with progressive context, install a Claude "
    "Code adapter, or record a session handoff -- instead of shelling out "
    "to the CLI manually or parsing its human-readable text output.\n\n"
    "Usage guidelines: call `scan` first on an unfamiliar repo (read-only, "
    "safe to call any time) to see the detected stack before deciding "
    "whether to run `init`. Call `init` once to scaffold the workspace; "
    "re-running it is safe but overwrites the existing scaffold rather than "
    "creating a duplicate, so don't call it in a loop. Call `status` to "
    "check workspace health (context budget, handoff history, adapter "
    "staleness) before deciding whether `init` needs to be re-run. Use "
    "`adapter install <name>` to (re)install one specific tool adapter, and "
    "`handoff new <message>` at the end of a session to leave a note for "
    "the next one. No API keys or network access are required; the only "
    "prerequisite is filesystem access to the target repo at `--path`.\n\n"
    "Behavioral transparency: this is a local subprocess call with a "
    f"{_TIMEOUT_SECONDS}s timeout -- it never touches the network. `scan` "
    "and `status` are strictly read-only. `init`, `adapter install`, and "
    "`handoff new` are mutating: they write files under `<path>/.workspace/` "
    "and are idempotent (safe to re-run, later runs overwrite rather than "
    "duplicate). This tool never raises on failure: a missing binary, a "
    "timed-out process, a non-zero exit, or unparsable stdout all come back "
    "as a JSON dict containing an \"error\" key instead of an exception, so "
    "check for that key before assuming success.\n\n"
    "Parameter semantics: `args` is a flat list[str] of literal CLI argv -- "
    "exactly what you would type after `agenticworkspace ` on a command "
    "line. Always include \"--json\" to get a structured dict back; without "
    'it the raw text is returned under an "output" key. Real examples:\n'
    '  ["init", "--json", "--path", "/path/to/repo"]\n'
    '  ["scan", "--json", "--path", "/path/to/repo"]\n'
    '  ["status", "--json", "--path", "/path/to/repo"]\n'
    '  ["adapter", "install", "claude-code", "--json", "--path", "/path/to/repo"]\n'
    '  ["handoff", "new", "Finished the auth refactor", "--json", "--path", "/path/to/repo"]\n\n'
    "Contextual completeness: on success, `init`/`scan`/`status` return keys "
    'such as "ok", "agenticworkspace_version", "target", "stack" '
    '(language/package_manager/monorepo/packages), "existing_config", '
    '"memory_backends", "context" (root_context_kb/budget_kb/modules), and '
    '"adapters"; `init` additionally returns "workspace_dir". On failure '
    'expect {"error", "returncode", "stdout", "stderr"}. Pass "--help" as '
    'an argv item (e.g. ["adapter", "install", "--help"]) on any '
    "subcommand to discover its exact flags without guessing."
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
    """Builds the `run` tool's description by appending the CLI's real
    `--help` output to the static prose in `_FALLBACK_DESCRIPTION`, so what
    an agent sees combines a genuinely explanatory description (purpose,
    when to call it, side effects, parameter shape, return shape) with the
    live command surface -- it never drifts from the actual subcommands and
    flags the installed CLI supports. Falls back to the static description
    alone if the CLI can't be introspected -- this function must never
    raise."""
    try:
        command = _resolve_cli_command() + ["--help"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
        help_text = (result.stdout or result.stderr or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        return _FALLBACK_DESCRIPTION
    if not help_text:
        return _FALLBACK_DESCRIPTION
    return (
        f"{_FALLBACK_DESCRIPTION}\n\n"
        f"Live `agenticworkspace --help` output from the installed CLI:\n\n{help_text}"
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
