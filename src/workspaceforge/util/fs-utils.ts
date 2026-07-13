import { promises as fs } from "node:fs";
import path from "node:path";

/** True if the given path exists and is a directory. Never throws. */
export async function dirExists(targetPath: string): Promise<boolean> {
  try {
    const stat = await fs.stat(targetPath);
    return stat.isDirectory();
  } catch {
    return false;
  }
}

/** True if the given path exists and is a regular file. Never throws. */
export async function fileExists(targetPath: string): Promise<boolean> {
  try {
    const stat = await fs.stat(targetPath);
    return stat.isFile();
  } catch {
    return false;
  }
}

/** True if the given path exists at all (file, directory, or otherwise). */
export async function pathExists(targetPath: string): Promise<boolean> {
  try {
    await fs.stat(targetPath);
    return true;
  } catch {
    return false;
  }
}

/** mkdir -p, wrapped for readability at call sites. */
export async function ensureDir(targetPath: string): Promise<void> {
  await fs.mkdir(targetPath, { recursive: true });
}

/** Read a JSON file and parse it. Returns null if the file does not exist. */
export async function readJsonIfExists<T>(targetPath: string): Promise<T | null> {
  if (!(await fileExists(targetPath))) {
    return null;
  }
  const raw = await fs.readFile(targetPath, "utf-8");
  return JSON.parse(raw) as T;
}

/** Write a value as pretty-printed JSON, creating parent directories first. */
export async function writeJson(targetPath: string, value: unknown): Promise<void> {
  await ensureDir(path.dirname(targetPath));
  await fs.writeFile(targetPath, `${JSON.stringify(value, null, 2)}\n`, "utf-8");
}

/** Write a text file, creating parent directories first. */
export async function writeText(targetPath: string, content: string): Promise<void> {
  await ensureDir(path.dirname(targetPath));
  await fs.writeFile(targetPath, content, "utf-8");
}

/** Byte length of a UTF-8 string, used for the context size budget. */
export function byteLength(content: string): number {
  return Buffer.byteLength(content, "utf-8");
}

/** List entries directly inside a directory, or an empty array if it does not exist. */
export async function listDir(targetPath: string): Promise<string[]> {
  try {
    return await fs.readdir(targetPath);
  } catch {
    return [];
  }
}

/** Remove a directory and everything in it. No-op if it does not exist. */
export async function removeDir(targetPath: string): Promise<void> {
  await fs.rm(targetPath, { recursive: true, force: true });
}
