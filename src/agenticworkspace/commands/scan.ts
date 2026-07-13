import path from "node:path";
import { detectStack } from "../scan/stack-detector.js";
import { detectExistingConfig } from "../scan/config-detector.js";
import { detectAllMemoryBackends } from "../memory-backends/registry.js";
import { EXIT_CODES } from "../util/exit-codes.js";

export interface ScanCommandOptions {
  path?: string;
  json?: boolean;
}

export interface ScanCommandOutcome {
  exitCode: number;
  json: Record<string, unknown>;
  humanLines: string[];
}

/** Read-only scan: detects stack + existing tooling surface, writes nothing. */
export async function runScanCommand(options: ScanCommandOptions): Promise<ScanCommandOutcome> {
  const repoPath = path.resolve(options.path ?? process.cwd());

  const [stack, existingConfig, memoryBackends] = await Promise.all([
    detectStack(repoPath),
    detectExistingConfig(repoPath),
    detectAllMemoryBackends(repoPath),
  ]);

  const humanLines: string[] = [];
  humanLines.push(`AgenticWorkspace scan -- ${repoPath}`);
  humanLines.push(
    `Stack: ${stack.language}, ${stack.packageManager}${
      stack.monorepo.isMonorepo ? `, monorepo (${stack.monorepo.packageCount} packages)` : ""
    }`,
  );
  humanLines.push(`Signals: ${stack.signals.join(", ") || "none"}`);
  humanLines.push(
    `Existing agent config: ${existingConfig.anyDetected ? "yes" : "no"}${
      existingConfig.anyDetected
        ? ` (${[
            existingConfig.claudeMd && "CLAUDE.md",
            existingConfig.agentsMd && "AGENTS.md",
            existingConfig.cursorRules && ".cursor/rules",
            existingConfig.copilotInstructions && ".github/copilot-instructions.md",
          ]
            .filter(Boolean)
            .join(", ")})`
        : ""
    }`,
  );
  const detected = memoryBackends.filter((b) => b.detected);
  humanLines.push(`Memory/context backends detected: ${detected.length > 0 ? detected.map((b) => b.name).join(", ") : "none"}`);

  return {
    exitCode: EXIT_CODES.OK,
    json: {
      ok: true,
      target: repoPath,
      stack: {
        language: stack.language,
        package_manager: stack.packageManager,
        monorepo: stack.monorepo.isMonorepo,
        packages: stack.monorepo.packageCount,
        signals: stack.signals,
      },
      existing_config: existingConfig,
      memory_backends: memoryBackends,
    },
    humanLines,
  };
}
