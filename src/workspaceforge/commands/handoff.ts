import path from "node:path";
import { detectPartialState } from "../state/partial-state.js";
import { writeHandoff } from "../scaffold/handoff-generator.js";
import { EXIT_CODES } from "../util/exit-codes.js";

export interface HandoffNewCommandOptions {
  path?: string;
  json?: boolean;
}

export interface HandoffNewCommandOutcome {
  exitCode: number;
  json: Record<string, unknown>;
  humanLines: string[];
}

export async function runHandoffNewCommand(
  message: string,
  options: HandoffNewCommandOptions,
): Promise<HandoffNewCommandOutcome> {
  const repoPath = path.resolve(options.path ?? process.cwd());
  const workspaceDir = path.join(repoPath, ".workspace");

  if (!message || message.trim().length === 0) {
    return {
      exitCode: EXIT_CODES.GENERAL_ERROR,
      json: { ok: false, error: "empty_message", message: "handoff new requires a non-empty message." },
      humanLines: ["Error: handoff new requires a non-empty message."],
    };
  }

  const partialState = await detectPartialState(workspaceDir);
  if (partialState.type === "none") {
    return {
      exitCode: EXIT_CODES.NO_WORKSPACE_FOUND,
      json: {
        ok: false,
        error: "no_workspace_found",
        message: "No .workspace/ directory found. Run 'workspaceforge init' first.",
      },
      humanLines: ["No .workspace/ directory found. Run 'workspaceforge init' first."],
    };
  }

  const written = await writeHandoff(workspaceDir, repoPath, message.trim());

  return {
    exitCode: EXIT_CODES.OK,
    json: {
      ok: true,
      file: written.fileName,
      path: written.filePath,
      message: written.message,
      metadata: written.metadata,
    },
    humanLines: [`Handoff written: .workspace/handoff/${written.fileName}`],
  };
}
