import path from "node:path";
import { fileExists, dirExists } from "../util/fs-utils.js";
import type { MemoryBackend } from "./types.js";

/**
 * GitNexus-style config detection. GitNexus-family tools commonly place
 * either a `.gitnexus/` directory or a root-level `gitnexus.config.json`
 * file -- this checks both, since exact conventions vary by fork/version,
 * and any one of them being present is enough to report it. Detect only.
 */
export const gitNexusBackend: MemoryBackend = {
  name: "gitnexus",
  async detect(repoPath: string): Promise<boolean> {
    const [hasDir, hasConfigFile] = await Promise.all([
      dirExists(path.join(repoPath, ".gitnexus")),
      fileExists(path.join(repoPath, "gitnexus.config.json")),
    ]);
    return hasDir || hasConfigFile;
  },
  describe(): string {
    return "GitNexus-style config (.gitnexus/ or gitnexus.config.json)";
  },
};
