"""
Builds the real content of the three Claude Code hook shell scripts. Every
detected value (module names) is passed through the shared sanitization
module before being embedded, per the project's security requirement -- an
allowlist check plus shell quoting, defense in depth. Ported verbatim
(byte-for-byte equivalent script bodies) from
src/agenticworkspace/adapters/claude-code/hook-scripts.ts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ...util.sanitize import SanitizeWarning, sanitize_list_for_shell_embedding

_SCRIPT_HEADER = "#!/usr/bin/env bash\nset -euo pipefail\n"


@dataclass
class HookScriptInputs:
    module_names: List[str]
    warn: Optional[SanitizeWarning] = None


def build_session_start_script(inputs: HookScriptInputs) -> str:
    warn = inputs.warn or (lambda message: None)
    sanitized_modules = sanitize_list_for_shell_embedding(
        inputs.module_names, warn, label="session-start.sh module list"
    )
    module_array_literal = " ".join(sanitized_modules) if sanitized_modules else ""

    return f"""{_SCRIPT_HEADER}
# AgenticWorkspace Claude Code adapter -- session-start hook.
# Loads .workspace/context/root-context.md, then each per-module capability
# block detected at install time, so a fresh Claude Code session picks up
# progressive context instead of the whole repo at once.
#
# Module names embedded below were validated against an allowlist
# (alphanumeric, dash, underscore, slash only) and shell-quoted at install
# time. Do not hand-edit this array with unsanitized input.

WORKSPACE_DIR=".workspace"
CONTEXT_DIR="${{WORKSPACE_DIR}}/context"
ROOT_CONTEXT="${{CONTEXT_DIR}}/root-context.md"

MODULES=({module_array_literal})

if [ -f "${{ROOT_CONTEXT}}" ]; then
  echo "--- AgenticWorkspace root context (${{ROOT_CONTEXT}}) ---"
  cat "${{ROOT_CONTEXT}}"
else
  echo "AgenticWorkspace: no root-context.md found at ${{ROOT_CONTEXT}}; run 'agenticworkspace init' first." >&2
fi

for module in "${{MODULES[@]:-}}"; do
  MODULE_FILE="${{CONTEXT_DIR}}/modules/${{module}}.md"
  if [ -f "${{MODULE_FILE}}" ]; then
    echo "--- AgenticWorkspace module context: ${{module}} ---"
    cat "${{MODULE_FILE}}"
  fi
done
"""


def build_pre_tool_call_script(inputs: HookScriptInputs) -> str:
    return f"""{_SCRIPT_HEADER}
# AgenticWorkspace Claude Code adapter -- pre-tool-call hook.
# Lightweight guard, extendable per project. v0.1 ships one real check: block
# any tool call whose target path attempts to write outside the repository
# root via a "../" path-traversal component. Extend this script directly to
# add project-specific guards -- AgenticWorkspace will not overwrite a
# hand-edited copy of this file on re-install (see install.py).

TOOL_INPUT="${{CLAUDE_TOOL_INPUT:-}}"

if printf '%s' "${{TOOL_INPUT}}" | grep -q '\\.\\./'; then
  echo "AgenticWorkspace pre-tool-call guard: blocked a tool call with a path-traversal component (../)." >&2
  exit 1
fi

exit 0
"""


def build_session_end_handoff_script(inputs: HookScriptInputs) -> str:
    return f"""{_SCRIPT_HEADER}
# AgenticWorkspace Claude Code adapter -- session-end handoff hook.
# Writes the next .workspace/handoff/ file automatically when a Claude Code
# session ends, so the next session (human or agent) has a timestamped note
# to pick up from instead of starting cold.

SUMMARY="${{CLAUDE_SESSION_SUMMARY:-session ended, no summary provided by the host tool}}"

if command -v agenticworkspace >/dev/null 2>&1; then
  agenticworkspace handoff new "${{SUMMARY}}" --json >/dev/null 2>&1 || \\
    echo "AgenticWorkspace: session-end handoff write failed; run 'agenticworkspace handoff new' manually." >&2
else
  echo "AgenticWorkspace: 'agenticworkspace' CLI not found on PATH; skipping automatic handoff write." >&2
fi
"""
