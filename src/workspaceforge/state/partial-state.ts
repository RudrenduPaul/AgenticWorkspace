import path from "node:path";
import { dirExists, fileExists, readJsonIfExists, writeText, removeDir as fsRemoveDir } from "../util/fs-utils.js";
import { promises as fs } from "node:fs";
import { manifestPath, isManifestShapeValid, REQUIRED_MANIFEST_KEYS } from "../scaffold/workspace-manifest.js";

export const INIT_IN_PROGRESS_MARKER = ".init-in-progress";

export type PartialStateType = "none" | "complete" | "interrupted-init" | "missing-manifest" | "malformed-manifest";

export interface PartialStateReport {
  type: PartialStateType;
  workspaceDirExists: boolean;
  markerPresent: boolean;
  manifestPresent: boolean;
  manifestValid: boolean;
  missingKeys: string[];
  message: string;
}

function markerPath(workspaceDir: string): string {
  return path.join(workspaceDir, INIT_IN_PROGRESS_MARKER);
}

/**
 * Inspect an existing .workspace/ directory (if any) and classify its state.
 * Never mutates anything -- pure detection, so callers can decide what to do
 * (repair / reset / abort) with the answer.
 */
export async function detectPartialState(workspaceDir: string): Promise<PartialStateReport> {
  const workspaceDirExists = await dirExists(workspaceDir);
  if (!workspaceDirExists) {
    return {
      type: "none",
      workspaceDirExists: false,
      markerPresent: false,
      manifestPresent: false,
      manifestValid: false,
      missingKeys: [],
      message: "No .workspace/ directory found -- this is a fresh init.",
    };
  }

  const markerPresent = await fileExists(markerPath(workspaceDir));
  const manifestPresent = await fileExists(manifestPath(workspaceDir));

  if (!manifestPresent) {
    return {
      type: markerPresent ? "interrupted-init" : "missing-manifest",
      workspaceDirExists: true,
      markerPresent,
      manifestPresent: false,
      manifestValid: false,
      missingKeys: [...REQUIRED_MANIFEST_KEYS],
      message: markerPresent
        ? ".workspace/ exists with a leftover .init-in-progress marker and no workspace.json -- a prior init run was interrupted."
        : ".workspace/ exists but has no workspace.json manifest.",
    };
  }

  let manifestJson: unknown = null;
  try {
    manifestJson = await readJsonIfExists(manifestPath(workspaceDir));
  } catch {
    manifestJson = null; // malformed JSON -- treated as invalid below
  }

  const manifestValid = isManifestShapeValid(manifestJson);
  const missingKeys = manifestValid
    ? []
    : REQUIRED_MANIFEST_KEYS.filter((key) => {
        if (manifestJson === null || typeof manifestJson !== "object") {
          return true;
        }
        return !(key in (manifestJson as Record<string, unknown>));
      });

  if (markerPresent || !manifestValid) {
    return {
      type: markerPresent ? "interrupted-init" : "malformed-manifest",
      workspaceDirExists: true,
      markerPresent,
      manifestPresent: true,
      manifestValid,
      missingKeys,
      message: markerPresent
        ? ".workspace/ exists with a leftover .init-in-progress marker -- a prior init run was interrupted."
        : `.workspace/workspace.json is missing expected keys: ${missingKeys.join(", ")}.`,
    };
  }

  return {
    type: "complete",
    workspaceDirExists: true,
    markerPresent: false,
    manifestPresent: true,
    manifestValid: true,
    missingKeys: [],
    message: ".workspace/ is complete and valid.",
  };
}

export async function writeInProgressMarker(workspaceDir: string): Promise<void> {
  await writeText(markerPath(workspaceDir), `${new Date().toISOString()}\n`);
}

export async function removeInProgressMarker(workspaceDir: string): Promise<void> {
  await fs.rm(markerPath(workspaceDir), { force: true });
}

export async function resetWorkspace(workspaceDir: string): Promise<void> {
  await fsRemoveDir(workspaceDir);
}
