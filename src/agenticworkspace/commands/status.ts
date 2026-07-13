import path from "node:path";
import { readManifest } from "../scaffold/workspace-manifest.js";
import { listHandoffs } from "../scaffold/handoff-generator.js";
import { claudeCodeAdapter, getInstalledHookSchemaVersion } from "../adapters/claude-code/install.js";
import { detectPartialState } from "../state/partial-state.js";
import { EXIT_CODES } from "../util/exit-codes.js";

export interface StatusCommandOptions {
  path?: string;
  json?: boolean;
}

export interface StatusCommandOutcome {
  exitCode: number;
  json: Record<string, unknown>;
  humanLines: string[];
}

export async function runStatusCommand(options: StatusCommandOptions): Promise<StatusCommandOutcome> {
  const repoPath = path.resolve(options.path ?? process.cwd());
  const workspaceDir = path.join(repoPath, ".workspace");

  const partialState = await detectPartialState(workspaceDir);

  if (partialState.type === "none") {
    return {
      exitCode: EXIT_CODES.NO_WORKSPACE_FOUND,
      json: {
        ok: false,
        error: "no_workspace_found",
        message: "No .workspace/ directory found. Run 'agenticworkspace init' first.",
      },
      humanLines: ["No .workspace/ directory found. Run 'agenticworkspace init' first."],
    };
  }

  if (partialState.type !== "complete") {
    return {
      exitCode: EXIT_CODES.PARTIAL_STATE_DETECTED,
      json: {
        ok: false,
        error: "partial_state_detected",
        partial_state: partialState.type,
        message: partialState.message,
      },
      humanLines: [`Error: ${partialState.message}`, "Run 'agenticworkspace init' to repair, reset, or abort."],
    };
  }

  const manifest = await readManifest(workspaceDir);
  if (!manifest) {
    // Should not happen given partialState.type === "complete", but guard anyway.
    return {
      exitCode: EXIT_CODES.PARTIAL_STATE_DETECTED,
      json: { ok: false, error: "manifest_unreadable" },
      humanLines: ["Error: workspace.json could not be read."],
    };
  }

  const handoffSummary = await listHandoffs(workspaceDir);
  const installedHookSchemaVersion = await getInstalledHookSchemaVersion(workspaceDir);
  const isInstalled = await claudeCodeAdapter.isInstalled(workspaceDir);
  const isStale = isInstalled ? await claudeCodeAdapter.checkStale(workspaceDir) : false;

  const otherBackends = manifest.memoryBackends.filter((b) => b.detected);

  const humanLines: string[] = [];
  humanLines.push("AgenticWorkspace status");
  humanLines.push(`Target: ${repoPath}`);
  humanLines.push(`Last scan: ${manifest.lastScanAt}`);
  humanLines.push("");
  humanLines.push(
    `Stack: ${manifest.stack.language}, ${manifest.stack.packageManager}, ${manifest.stack.packages} package(s)`,
  );
  humanLines.push(
    `Context budget: ${manifest.context.rootContextKb}KB of 12KB (${manifest.context.modules.length} module block(s))`,
  );
  humanLines.push(`Handoffs: ${handoffSummary.count} file(s), most recent: ${handoffSummary.mostRecent ?? "none"}`);
  humanLines.push(
    `Claude Code adapter: ${isInstalled ? "installed" : "not installed"}${
      isInstalled ? `, schema ${installedHookSchemaVersion}, ${isStale ? "STALE (update available)" : "current"}` : ""
    }`,
  );
  if (otherBackends.length > 0) {
    humanLines.push(`Other backends detected: ${otherBackends.map((b) => b.name).join(", ")} (not modified)`);
  } else {
    humanLines.push("Other backends detected: none");
  }

  return {
    exitCode: EXIT_CODES.OK,
    json: {
      ok: true,
      workspace_version: manifest.agenticworkspaceVersion,
      scanned_at: manifest.lastScanAt,
      stack: {
        language: manifest.stack.language,
        package_manager: manifest.stack.packageManager,
        packages: manifest.stack.packages,
      },
      context: {
        root_context_kb: manifest.context.rootContextKb,
        budget_kb: 12,
        modules: manifest.context.modules.length,
        stale: false,
      },
      handoff: {
        files: handoffSummary.count,
        most_recent: handoffSummary.mostRecent,
      },
      adapters: {
        claude_code: {
          installed: isInstalled,
          hook_schema_version: installedHookSchemaVersion,
          current_schema_version: claudeCodeAdapter.hookSchemaVersion,
          current: isInstalled && !isStale,
        },
      },
      compatibility_check: Object.fromEntries(
        manifest.memoryBackends.map((backend) => [`existing_${backend.name.replace(/-/g, "_")}_dir`, backend.detected]),
      ),
    },
    humanLines,
  };
}
