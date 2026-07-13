import { sanitizeListForShellEmbedding, type SanitizeWarning } from "../../util/sanitize.js";

/**
 * Builds the real content of the three Claude Code hook shell scripts.
 * Every detected value (module names) is passed through the shared
 * sanitization module before being embedded, per the project's security
 * requirement -- an allowlist check plus shell quoting, defense in depth.
 */

export interface HookScriptInputs {
  moduleNames: string[];
  warn?: SanitizeWarning;
}

const SCRIPT_HEADER = "#!/usr/bin/env bash\nset -euo pipefail\n";

export function buildSessionStartScript({ moduleNames, warn = () => {} }: HookScriptInputs): string {
  const sanitizedModules = sanitizeListForShellEmbedding(moduleNames, warn, {
    label: "session-start.sh module list",
  });
  const moduleArrayLiteral = sanitizedModules.length > 0 ? sanitizedModules.join(" ") : "";

  return `${SCRIPT_HEADER}
# WorkspaceForge Claude Code adapter -- session-start hook.
# Loads .workspace/context/root-context.md, then each per-module capability
# block detected at install time, so a fresh Claude Code session picks up
# progressive context instead of the whole repo at once.
#
# Module names embedded below were validated against an allowlist
# (alphanumeric, dash, underscore, slash only) and shell-quoted at install
# time. Do not hand-edit this array with unsanitized input.

WORKSPACE_DIR=".workspace"
CONTEXT_DIR="\${WORKSPACE_DIR}/context"
ROOT_CONTEXT="\${CONTEXT_DIR}/root-context.md"

MODULES=(${moduleArrayLiteral})

if [ -f "\${ROOT_CONTEXT}" ]; then
  echo "--- WorkspaceForge root context (\${ROOT_CONTEXT}) ---"
  cat "\${ROOT_CONTEXT}"
else
  echo "WorkspaceForge: no root-context.md found at \${ROOT_CONTEXT}; run 'workspaceforge init' first." >&2
fi

for module in "\${MODULES[@]:-}"; do
  MODULE_FILE="\${CONTEXT_DIR}/modules/\${module}.md"
  if [ -f "\${MODULE_FILE}" ]; then
    echo "--- WorkspaceForge module context: \${module} ---"
    cat "\${MODULE_FILE}"
  fi
done
`;
}

export function buildPreToolCallScript(_inputs: HookScriptInputs): string {
  return `${SCRIPT_HEADER}
# WorkspaceForge Claude Code adapter -- pre-tool-call hook.
# Lightweight guard, extendable per project. v0.1 ships one real check: block
# any tool call whose target path attempts to write outside the repository
# root via a "../" path-traversal component. Extend this script directly to
# add project-specific guards -- WorkspaceForge will not overwrite a
# hand-edited copy of this file on re-install (see install.ts).

TOOL_INPUT="\${CLAUDE_TOOL_INPUT:-}"

if printf '%s' "\${TOOL_INPUT}" | grep -q '\\.\\./'; then
  echo "WorkspaceForge pre-tool-call guard: blocked a tool call with a path-traversal component (../)." >&2
  exit 1
fi

exit 0
`;
}

export function buildSessionEndHandoffScript(_inputs: HookScriptInputs): string {
  return `${SCRIPT_HEADER}
# WorkspaceForge Claude Code adapter -- session-end handoff hook.
# Writes the next .workspace/handoff/ file automatically when a Claude Code
# session ends, so the next session (human or agent) has a timestamped note
# to pick up from instead of starting cold.

SUMMARY="\${CLAUDE_SESSION_SUMMARY:-session ended, no summary provided by the host tool}"

if command -v workspaceforge >/dev/null 2>&1; then
  workspaceforge handoff new "\${SUMMARY}" --json >/dev/null 2>&1 || \\
    echo "WorkspaceForge: session-end handoff write failed; run 'workspaceforge handoff new' manually." >&2
else
  echo "WorkspaceForge: 'workspaceforge' CLI not found on PATH; skipping automatic handoff write." >&2
fi
`;
}
