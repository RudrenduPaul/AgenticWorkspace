import path from "node:path";
import { dirExists } from "../util/fs-utils.js";
import type { MemoryBackend } from "./types.js";

/**
 * repo-harness detection: a `.ai/harness/` directory at the repo root. This
 * is a real, actively maintained competitor (Ancienttwo/repo-harness on npm
 * and GitHub) that ships its own repo-local context and session-handoff
 * tracking. AgenticWorkspace detects its presence purely so `init` can report
 * it and avoid silently duplicating or conflicting with an already-present
 * repo-harness install -- this backend is never read from, written to, or
 * modified in any way.
 */
export const repoHarnessBackend: MemoryBackend = {
  name: "repo-harness",
  async detect(repoPath: string): Promise<boolean> {
    return dirExists(path.join(repoPath, ".ai", "harness"));
  },
  describe(): string {
    return "repo-harness (.ai/harness/ directory) -- detected only, never modified";
  },
};
