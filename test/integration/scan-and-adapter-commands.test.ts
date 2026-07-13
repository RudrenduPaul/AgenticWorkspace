import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { runScanCommand } from "../../src/agenticworkspace/commands/scan.js";
import { runAdapterInstallCommand } from "../../src/agenticworkspace/commands/adapter.js";
import { runInitCommand } from "../../src/agenticworkspace/commands/init.js";
import { EXIT_CODES } from "../../src/agenticworkspace/util/exit-codes.js";

async function makeTempRepo(): Promise<string> {
  const repoPath = await fs.mkdtemp(path.join(os.tmpdir(), "wf-scan-adapter-"));
  await fs.writeFile(path.join(repoPath, "package.json"), JSON.stringify({ name: "fixture" }));
  await fs.writeFile(path.join(repoPath, "package-lock.json"), "{}");
  return repoPath;
}

describe("scan command", () => {
  let repoPath: string;

  beforeEach(async () => {
    repoPath = await makeTempRepo();
  });

  afterEach(async () => {
    await fs.rm(repoPath, { recursive: true, force: true });
  });

  it("detects stack without writing any files", async () => {
    const outcome = await runScanCommand({ path: repoPath, json: true });
    expect(outcome.exitCode).toBe(EXIT_CODES.OK);
    const stack = outcome.json.stack as { language: string; package_manager: string };
    expect(stack.language).toBe("javascript");
    expect(stack.package_manager).toBe("npm");

    const workspaceExists = await fs
      .stat(path.join(repoPath, ".workspace"))
      .then(() => true)
      .catch(() => false);
    expect(workspaceExists).toBe(false);
  });
});

describe("adapter install command", () => {
  let repoPath: string;

  beforeEach(async () => {
    repoPath = await makeTempRepo();
  });

  afterEach(async () => {
    await fs.rm(repoPath, { recursive: true, force: true });
  });

  it("errors with NO_WORKSPACE_FOUND if init has never run", async () => {
    const outcome = await runAdapterInstallCommand("claude-code", { path: repoPath, json: true });
    expect(outcome.exitCode).toBe(EXIT_CODES.NO_WORKSPACE_FOUND);
  });

  it("errors with ADAPTER_NOT_IMPLEMENTED for codex", async () => {
    await runInitCommand({ path: repoPath, json: true });
    const outcome = await runAdapterInstallCommand("codex", { path: repoPath, json: true });
    expect(outcome.exitCode).toBe(EXIT_CODES.ADAPTER_NOT_IMPLEMENTED);
  });

  it("errors for an unknown adapter name", async () => {
    const outcome = await runAdapterInstallCommand("totally-made-up", { path: repoPath, json: true });
    expect(outcome.exitCode).toBe(EXIT_CODES.GENERAL_ERROR);
    expect(outcome.json.error).toBe("unknown_adapter");
  });

  it("reinstalls the claude-code adapter after init has already run", async () => {
    await runInitCommand({ path: repoPath, json: true });
    const outcome = await runAdapterInstallCommand("claude-code", { path: repoPath, json: true });
    expect(outcome.exitCode).toBe(EXIT_CODES.OK);
    expect(outcome.json.adapter).toBe("claude-code");
  });
});
