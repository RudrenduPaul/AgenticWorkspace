import path from "node:path";
import { dirExists } from "../util/fs-utils.js";
import type { MemoryBackend } from "./types.js";

/**
 * Serena detection: a `.serena/` directory at the repo root. Detect only --
 * WorkspaceForge never reads, writes, or modifies anything inside it.
 */
export const serenaBackend: MemoryBackend = {
  name: "serena",
  async detect(repoPath: string): Promise<boolean> {
    return dirExists(path.join(repoPath, ".serena"));
  },
  describe(): string {
    return "Serena memory/context tool (.serena/ directory)";
  },
};
