import path from "node:path";
import { fileExists, dirExists } from "../util/fs-utils.js";

export interface ExistingConfigResult {
  /** file/dir key -> whether it was found. */
  claudeMd: boolean;
  agentsMd: boolean;
  cursorRules: boolean;
  copilotInstructions: boolean;
  /** True if any agent-config surface already exists -- init must never overwrite these. */
  anyDetected: boolean;
}

/**
 * Existing agent-config detection. AgenticWorkspace never overwrites
 * any of these files; init only reports their presence.
 */
export async function detectExistingConfig(repoPath: string): Promise<ExistingConfigResult> {
  const [claudeMd, agentsMd, cursorRules, copilotInstructions] = await Promise.all([
    fileExists(path.join(repoPath, "CLAUDE.md")),
    fileExists(path.join(repoPath, "AGENTS.md")),
    dirExists(path.join(repoPath, ".cursor", "rules")),
    fileExists(path.join(repoPath, ".github", "copilot-instructions.md")),
  ]);

  return {
    claudeMd,
    agentsMd,
    cursorRules,
    copilotInstructions,
    anyDetected: claudeMd || agentsMd || cursorRules || copilotInstructions,
  };
}
