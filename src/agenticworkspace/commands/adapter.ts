import path from "node:path";
import { getAdapter } from "../adapters/registry.js";
import { detectModuleCandidates } from "../scaffold/context-generator.js";
import { detectStack } from "../scan/stack-detector.js";
import { detectPartialState } from "../state/partial-state.js";
import { EXIT_CODES } from "../util/exit-codes.js";

export interface AdapterInstallCommandOptions {
  path?: string;
  json?: boolean;
}

export interface AdapterInstallCommandOutcome {
  exitCode: number;
  json: Record<string, unknown>;
  humanLines: string[];
}

/** (Re)install just one adapter's hook wiring, without re-running the full init scaffold. */
export async function runAdapterInstallCommand(
  adapterName: string,
  options: AdapterInstallCommandOptions,
): Promise<AdapterInstallCommandOutcome> {
  const repoPath = path.resolve(options.path ?? process.cwd());
  const workspaceDir = path.join(repoPath, ".workspace");

  const adapter = getAdapter(adapterName);
  if (!adapter) {
    return {
      exitCode: EXIT_CODES.GENERAL_ERROR,
      json: { ok: false, error: "unknown_adapter", adapter: adapterName },
      humanLines: [`Error: unknown adapter "${adapterName}".`],
    };
  }

  if (!adapter.isImplemented) {
    return {
      exitCode: EXIT_CODES.ADAPTER_NOT_IMPLEMENTED,
      json: { ok: false, error: "adapter_not_implemented", adapter: adapter.name, description: adapter.describe() },
      humanLines: [`${adapter.describe()}`, "This adapter cannot be installed in v0.1."],
    };
  }

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

  const stack = await detectStack(repoPath);
  const modules = await detectModuleCandidates(repoPath, stack);
  await adapter.install(workspaceDir, { repoPath, moduleNames: modules.map((m) => m.name) });

  return {
    exitCode: EXIT_CODES.OK,
    json: { ok: true, adapter: adapter.name, hook_schema_version: adapter.hookSchemaVersion },
    humanLines: [`${adapter.name} adapter installed (hook schema ${adapter.hookSchemaVersion}).`],
  };
}
