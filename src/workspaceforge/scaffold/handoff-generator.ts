import path from "node:path";
import { promises as fs } from "node:fs";
import { listDir, ensureDir, pathExists, writeText } from "../util/fs-utils.js";
import { getCurrentBranch, getCurrentCommit } from "../util/git-info.js";

export function handoffDir(workspaceDir: string): string {
  return path.join(workspaceDir, "handoff");
}

export interface HandoffMetadata {
  timestamp: string;
  branch: string | null;
  commit: string | null;
}

export interface WrittenHandoff {
  fileName: string;
  filePath: string;
  message: string;
  metadata: HandoffMetadata;
}

function timestampSlug(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  const y = date.getUTCFullYear();
  const mo = pad(date.getUTCMonth() + 1);
  const d = pad(date.getUTCDate());
  const h = pad(date.getUTCHours());
  const mi = pad(date.getUTCMinutes());
  return `${y}-${mo}-${d}-${h}${mi}`;
}

/**
 * Write a new timestamped handoff file into .workspace/handoff/. If a file
 * for the same minute already exists (two handoffs written within the same
 * 60-second window), a numeric suffix is appended so nothing is overwritten.
 */
export async function writeHandoff(
  workspaceDir: string,
  repoPath: string,
  message: string,
  now: Date = new Date(),
): Promise<WrittenHandoff> {
  const dir = handoffDir(workspaceDir);
  await ensureDir(dir);

  const [branch, commit] = await Promise.all([getCurrentBranch(repoPath), getCurrentCommit(repoPath)]);
  const metadata: HandoffMetadata = {
    timestamp: now.toISOString(),
    branch,
    commit,
  };

  const baseSlug = timestampSlug(now);
  let fileName = `${baseSlug}.md`;
  let counter = 2;
  while (await pathExists(path.join(dir, fileName))) {
    fileName = `${baseSlug}-${counter}.md`;
    counter += 1;
  }

  const filePath = path.join(dir, fileName);
  const content = buildHandoffContent(message, metadata);
  await writeText(filePath, content);

  return { fileName, filePath, message, metadata };
}

function buildHandoffContent(message: string, metadata: HandoffMetadata): string {
  return `# Session Handoff

- Timestamp: ${metadata.timestamp}
- Branch: ${metadata.branch ?? "unknown (not a git repo, or git unavailable)"}
- Commit: ${metadata.commit ?? "unknown"}

## Notes

${message}
`;
}

export interface HandoffSummary {
  files: string[];
  count: number;
  mostRecent: string | null;
}

/** List handoff files, newest first (filenames sort lexicographically = chronologically here). */
export async function listHandoffs(workspaceDir: string): Promise<HandoffSummary> {
  const dir = handoffDir(workspaceDir);
  const entries = await listDir(dir);
  const mdFiles = entries.filter((entry) => entry.endsWith(".md")).sort().reverse();
  return {
    files: mdFiles,
    count: mdFiles.length,
    mostRecent: mdFiles[0] ?? null,
  };
}

export async function ensureHandoffDirExists(workspaceDir: string): Promise<void> {
  await ensureDir(handoffDir(workspaceDir));
}

// Re-exported for tests that need to assert directory contents directly.
export async function readHandoffFile(workspaceDir: string, fileName: string): Promise<string> {
  return fs.readFile(path.join(handoffDir(workspaceDir), fileName), "utf-8");
}
