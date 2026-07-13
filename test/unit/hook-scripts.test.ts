import { describe, it, expect } from "vitest";
import { execFile } from "node:child_process";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { promisify } from "node:util";
import { buildPreToolCallScript } from "../../src/workspaceforge/adapters/claude-code/hook-scripts.js";

const execFileAsync = promisify(execFile);

async function runGuard(toolInput: string): Promise<{ exitCode: number; stderr: string }> {
  const tmp = await fs.mkdtemp(path.join(os.tmpdir(), "wf-hook-test-"));
  const scriptPath = path.join(tmp, "pre-tool-call.sh");
  await fs.writeFile(scriptPath, buildPreToolCallScript({ moduleNames: [] }), { mode: 0o755 });
  try {
    await execFileAsync("bash", [scriptPath], {
      env: { ...process.env, CLAUDE_TOOL_INPUT: toolInput },
    });
    return { exitCode: 0, stderr: "" };
  } catch (err) {
    const e = err as { code?: number; stderr?: string };
    return { exitCode: e.code ?? 1, stderr: e.stderr ?? "" };
  } finally {
    await fs.rm(tmp, { recursive: true, force: true });
  }
}

describe("pre-tool-call.sh path-traversal guard", () => {
  it("blocks a single ../ segment (real gap the deep-pattern-only regex used to miss)", async () => {
    const result = await runGuard("write ../secrets.env");
    expect(result.exitCode).toBe(1);
    expect(result.stderr).toContain("path-traversal");
  });

  it("blocks a double ../../ segment", async () => {
    const result = await runGuard("write ../../outside-repo/file.txt");
    expect(result.exitCode).toBe(1);
  });

  it("blocks the original deep ../../../ pattern (no regression)", async () => {
    const result = await runGuard("write ../../../etc/passwd");
    expect(result.exitCode).toBe(1);
  });

  it("allows a normal in-repo path with no traversal", async () => {
    const result = await runGuard("write src/index.ts");
    expect(result.exitCode).toBe(0);
  });

  it("does not false-positive on a filename that merely contains dots", async () => {
    const result = await runGuard("write src/my..file.ts");
    expect(result.exitCode).toBe(0);
  });
});
