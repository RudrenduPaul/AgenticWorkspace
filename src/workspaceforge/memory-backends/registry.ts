import type { MemoryBackend } from "./types.js";
import { serenaBackend } from "./serena.js";
import { gitNexusBackend } from "./gitnexus.js";
import { repoHarnessBackend } from "./repo-harness.js";

/**
 * The registry of all known MemoryBackend implementations. Adding a new
 * backend means writing a MemoryBackend implementation and adding it here --
 * nothing else in scan or CLI code needs to change.
 */
export const memoryBackendRegistry: MemoryBackend[] = [
  serenaBackend,
  gitNexusBackend,
  repoHarnessBackend,
];

export interface MemoryBackendDetectionResult {
  name: string;
  detected: boolean;
  description: string;
}

/**
 * Run detect() across every registered backend. Detection failures in one
 * backend (an unexpected filesystem error) are caught and reported as
 * not-detected rather than aborting the whole scan.
 */
export async function detectAllMemoryBackends(
  repoPath: string,
  registry: MemoryBackend[] = memoryBackendRegistry,
): Promise<MemoryBackendDetectionResult[]> {
  const results = await Promise.all(
    registry.map(async (backend) => {
      let detected = false;
      try {
        detected = await backend.detect(repoPath);
      } catch {
        detected = false;
      }
      return {
        name: backend.name,
        detected,
        description: backend.describe(),
      };
    }),
  );
  return results;
}

/** True if any registered backend was detected -- init uses this to decide whether to prompt. */
export function anyBackendDetected(results: MemoryBackendDetectionResult[]): boolean {
  return results.some((result) => result.detected);
}
