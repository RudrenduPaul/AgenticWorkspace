import path from "node:path";
import { detectPartialState, resetWorkspace } from "../state/partial-state.js";
import { runInitEngine, type InitEngineResult } from "../scaffold/init-engine.js";
import { askRepairResetAbort, isInteractiveTerminal } from "../util/prompt.js";
import { EXIT_CODES } from "../util/exit-codes.js";

export interface InitCommandOptions {
  path?: string;
  json?: boolean;
}

export interface InitCommandOutcome {
  exitCode: number;
  json: Record<string, unknown>;
  humanLines: string[];
}

function workspaceDirFor(repoPath: string): string {
  return path.join(repoPath, ".workspace");
}

/**
 * Core init command logic, separated from process.exit()/console side
 * effects so it is directly unit- and integration-testable.
 */
export async function runInitCommand(options: InitCommandOptions): Promise<InitCommandOutcome> {
  const repoPath = path.resolve(options.path ?? process.cwd());
  const workspaceDir = workspaceDirFor(repoPath);
  const jsonMode = Boolean(options.json);

  const partialState = await detectPartialState(workspaceDir);

  if (partialState.type === "interrupted-init" || partialState.type === "missing-manifest" || partialState.type === "malformed-manifest") {
    if (jsonMode || !isInteractiveTerminal()) {
      return {
        exitCode: EXIT_CODES.PARTIAL_STATE_DETECTED,
        json: {
          ok: false,
          error: "partial_state_detected",
          partial_state: partialState.type,
          message: partialState.message,
          missing_keys: partialState.missingKeys,
          hint: "Re-run with an interactive terminal to choose repair/reset/abort, or pass --repair / --reset explicitly.",
        },
        humanLines: [`Error: ${partialState.message}`],
      };
    }

    console.log(`\nWorkspaceForge detected a partial or malformed .workspace/ state:\n  ${partialState.message}\n`);
    const choice = await askRepairResetAbort();

    if (choice === "abort") {
      return {
        exitCode: EXIT_CODES.GENERAL_ERROR,
        json: { ok: false, error: "aborted_by_user", partial_state: partialState.type },
        humanLines: ["Aborted. No changes were made to .workspace/."],
      };
    }

    if (choice === "reset") {
      await resetWorkspace(workspaceDir);
    }
    // "repair" and "reset" both fall through to a normal init engine run below --
    // reset already wiped the directory, repair re-runs the idempotent engine
    // over what's left, filling in whatever was missing.
  }

  const result = await runInitEngine(repoPath, workspaceDir);
  return buildSuccessOutcome(result, partialState.type !== "none" && partialState.type !== "complete");
}

function buildSuccessOutcome(result: InitEngineResult, wasRepairOrReset: boolean): InitCommandOutcome {
  const { stack, existingConfig, memoryBackends, context, manifest } = result;

  const detectedBackendNames = memoryBackends.filter((b) => b.detected).map((b) => b.name);

  const humanLines: string[] = [];
  humanLines.push("WorkspaceForge v0.1 -- Repo-to-Agent-Workspace Converter");
  humanLines.push(`Target: ${result.repoPath}`);
  humanLines.push("");
  humanLines.push("Scanning repository...");
  humanLines.push(
    `[OK] Stack detected: ${stack.language}, ${stack.packageManager}${
      stack.monorepo.isMonorepo ? ` monorepo, ${stack.monorepo.packageCount} packages` : ""
    }`,
  );
  if (existingConfig.anyDetected) {
    const found = [
      existingConfig.claudeMd && "CLAUDE.md",
      existingConfig.agentsMd && "AGENTS.md",
      existingConfig.cursorRules && ".cursor/rules",
      existingConfig.copilotInstructions && ".github/copilot-instructions.md",
    ].filter(Boolean);
    humanLines.push(`[OK] Existing config found: ${found.join(", ")} (will not overwrite)`);
  } else {
    humanLines.push("[--] No existing agent-config files found");
  }
  if (detectedBackendNames.length > 0) {
    humanLines.push(`[--] Memory/context backend(s) detected: ${detectedBackendNames.join(", ")} (not modified)`);
  } else {
    humanLines.push("[--] No memory/context tool detected");
  }
  humanLines.push("");
  humanLines.push(`${wasRepairOrReset ? "Repairing" : "Writing"} .workspace/ scaffold...`);
  humanLines.push("  .workspace/workspace.json                created");
  humanLines.push(
    `  .workspace/context/root-context.md        created (${manifest.context.rootContextKb}KB of 12KB budget)`,
  );
  for (const moduleName of context.moduleNames) {
    humanLines.push(`  .workspace/context/modules/${moduleName}.md         created`);
  }
  humanLines.push("  .workspace/handoff/                       created (empty, ready for first session)");
  humanLines.push("");
  humanLines.push("Installing Claude Code adapter...");
  humanLines.push("  .workspace/adapters/claude-code/settings.json         written");
  humanLines.push("  .workspace/adapters/claude-code/hooks/session-start.sh  written");
  humanLines.push("  .workspace/adapters/claude-code/hooks/pre-tool-call.sh  written");
  humanLines.push("  .workspace/adapters/claude-code/hooks/session-end-handoff.sh  written");
  humanLines.push("");
  humanLines.push(
    "Workspace ready. Next Claude Code session in this repo will load root-context.md automatically and write a handoff file on exit.",
  );
  humanLines.push("");
  humanLines.push(`Full manifest: ${path.join(result.workspaceDir, "workspace.json")}`);

  return {
    exitCode: EXIT_CODES.OK,
    json: {
      ok: true,
      workspaceforge_version: manifest.workspaceforgeVersion,
      scanned_at: manifest.lastScanAt,
      target: result.repoPath,
      stack: {
        language: stack.language,
        package_manager: stack.packageManager,
        monorepo: stack.monorepo.isMonorepo,
        packages: manifest.stack.packages,
      },
      existing_config: existingConfig,
      memory_backends: memoryBackends,
      context: {
        root_context_kb: manifest.context.rootContextKb,
        budget_kb: 12,
        modules: context.moduleNames,
      },
      adapters: {
        claude_code: { installed: true, hook_schema_version: result.adapterHookSchemaVersion },
      },
      workspace_dir: result.workspaceDir,
    },
    humanLines,
  };
}
