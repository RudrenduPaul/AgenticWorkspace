import path from "node:path";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { detectStack, type StackDetectionResult } from "../scan/stack-detector.js";
import { detectExistingConfig, type ExistingConfigResult } from "../scan/config-detector.js";
import { detectAllMemoryBackends, type MemoryBackendDetectionResult } from "../memory-backends/registry.js";
import { detectModuleCandidates, generateContext, type GeneratedContext } from "./context-generator.js";
import { ensureHandoffDirExists } from "./handoff-generator.js";
import { claudeCodeAdapter } from "../adapters/claude-code/install.js";
import {
  readManifest,
  writeManifest,
  WORKSPACE_MANIFEST_SCHEMA_VERSION,
  type WorkspaceManifest,
} from "./workspace-manifest.js";
import { writeInProgressMarker, removeInProgressMarker } from "../state/partial-state.js";
import { ensureDir } from "../util/fs-utils.js";

/**
 * Read the real published version straight from package.json instead of a
 * hardcoded string. A hand-maintained constant here previously drifted out
 * of sync with the actual package.json/npm version on every release (found
 * shipping "0.1.1" while npm had already published 0.1.4), silently handing
 * every --version call, JSON output, and workspace.json manifest a stale
 * version. This file compiles to the same relative depth under both dist/
 * (built) and src/ (tsx dev mode) -- three directories up from here is
 * always the package root.
 */
function readPackageVersion(): string {
  try {
    const here = path.dirname(fileURLToPath(import.meta.url));
    const packageJsonPath = path.join(here, "../../../package.json");
    const raw = readFileSync(packageJsonPath, "utf-8");
    const parsed = JSON.parse(raw) as { version?: unknown };
    if (typeof parsed.version === "string" && parsed.version.length > 0) {
      return parsed.version;
    }
  } catch {
    // Fall through to the fallback below -- e.g. an unusual install layout
    // where package.json isn't reachable at the expected relative depth.
  }
  return "0.0.0";
}

export const AGENTICWORKSPACE_VERSION = readPackageVersion();

export interface InitEngineResult {
  repoPath: string;
  workspaceDir: string;
  stack: StackDetectionResult;
  existingConfig: ExistingConfigResult;
  memoryBackends: MemoryBackendDetectionResult[];
  context: GeneratedContext;
  adapterHookSchemaVersion: string;
  manifest: WorkspaceManifest;
}

/**
 * Runs the full scan + scaffold + adapter-install sequence. Used for both a
 * fresh `init` and a `repair` of a partial workspace -- repair re-runs the
 * same steps, which is safe because every step here is idempotent (detection
 * is read-only, writes overwrite deterministically-named files).
 */
export async function runInitEngine(repoPath: string, workspaceDir: string): Promise<InitEngineResult> {
  await ensureDir(workspaceDir);
  await writeInProgressMarker(workspaceDir);

  try {
    const existingManifest = await readManifest(workspaceDir);

    const [stack, existingConfig] = await Promise.all([
      detectStack(repoPath),
      detectExistingConfig(repoPath),
    ]);
    const memoryBackends = await detectAllMemoryBackends(repoPath);
    const moduleCandidates = await detectModuleCandidates(repoPath, stack);
    const context = await generateContext(
      workspaceDir,
      repoPath,
      path.basename(repoPath),
      stack,
      moduleCandidates,
    );

    await ensureHandoffDirExists(workspaceDir);

    await claudeCodeAdapter.install(workspaceDir, {
      repoPath,
      moduleNames: context.moduleNames,
    });

    const now = new Date().toISOString();
    const manifest: WorkspaceManifest = {
      manifestSchemaVersion: WORKSPACE_MANIFEST_SCHEMA_VERSION,
      agenticworkspaceVersion: AGENTICWORKSPACE_VERSION,
      createdAt: existingManifest?.createdAt ?? now,
      lastScanAt: now,
      stack: {
        language: stack.language,
        packageManager: stack.packageManager,
        packages: stack.monorepo.isMonorepo ? stack.monorepo.packageCount : 1,
      },
      existingConfig: {
        claudeMd: existingConfig.claudeMd,
        agentsMd: existingConfig.agentsMd,
        cursorRules: existingConfig.cursorRules,
        copilotInstructions: existingConfig.copilotInstructions,
      },
      memoryBackends,
      context: {
        rootContextKb: Math.round((context.rootContextBytes / 1024) * 10) / 10,
        modules: context.moduleNames,
      },
      adapters: {
        [claudeCodeAdapter.name]: {
          installed: true,
          hookSchemaVersion: claudeCodeAdapter.hookSchemaVersion,
        },
      },
    };

    await writeManifest(workspaceDir, manifest);

    return {
      repoPath,
      workspaceDir,
      stack,
      existingConfig,
      memoryBackends,
      context,
      adapterHookSchemaVersion: claudeCodeAdapter.hookSchemaVersion,
      manifest,
    };
  } finally {
    await removeInProgressMarker(workspaceDir);
  }
}
