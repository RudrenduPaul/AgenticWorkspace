import path from "node:path";
import { readJsonIfExists, writeJson } from "../util/fs-utils.js";
import type { StackDetectionResult } from "../scan/stack-detector.js";
import type { MemoryBackendDetectionResult } from "../memory-backends/registry.js";

/** Bumped whenever the shape of workspace.json changes in a way partial-state detection must know about. */
export const WORKSPACE_MANIFEST_SCHEMA_VERSION = "1";

export interface AdapterManifestEntry {
  installed: boolean;
  hookSchemaVersion: string | null;
}

export interface WorkspaceManifest {
  manifestSchemaVersion: string;
  workspaceforgeVersion: string;
  createdAt: string;
  lastScanAt: string;
  stack: {
    language: StackDetectionResult["language"];
    packageManager: StackDetectionResult["packageManager"];
    packages: number;
  };
  existingConfig: {
    claudeMd: boolean;
    agentsMd: boolean;
    cursorRules: boolean;
    copilotInstructions: boolean;
  };
  memoryBackends: MemoryBackendDetectionResult[];
  context: {
    rootContextKb: number;
    modules: string[];
  };
  adapters: Record<string, AdapterManifestEntry>;
}

/** Required top-level keys a valid workspace.json must have. Used by partial-state detection. */
export const REQUIRED_MANIFEST_KEYS: Array<keyof WorkspaceManifest> = [
  "manifestSchemaVersion",
  "workspaceforgeVersion",
  "createdAt",
  "lastScanAt",
  "stack",
  "existingConfig",
  "memoryBackends",
  "context",
  "adapters",
];

export function manifestPath(workspaceDir: string): string {
  return path.join(workspaceDir, "workspace.json");
}

export async function readManifest(workspaceDir: string): Promise<WorkspaceManifest | null> {
  return readJsonIfExists<WorkspaceManifest>(manifestPath(workspaceDir));
}

export async function writeManifest(workspaceDir: string, manifest: WorkspaceManifest): Promise<void> {
  await writeJson(manifestPath(workspaceDir), manifest);
}

/**
 * True if the given parsed value has every key a valid manifest requires.
 * Does not validate value types deeply -- partial-state detection only needs
 * to know "does this look like an interrupted or hand-edited manifest,"
 * not perform full schema validation.
 */
export function isManifestShapeValid(value: unknown): value is WorkspaceManifest {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return REQUIRED_MANIFEST_KEYS.every((key) => key in record);
}
