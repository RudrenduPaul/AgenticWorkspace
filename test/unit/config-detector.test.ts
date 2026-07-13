import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { detectExistingConfig } from "../../src/workspaceforge/scan/config-detector.js";

async function makeTempRepo(): Promise<string> {
  return fs.mkdtemp(path.join(os.tmpdir(), "wf-config-test-"));
}

describe("detectExistingConfig", () => {
  let repoPath: string;

  beforeEach(async () => {
    repoPath = await makeTempRepo();
  });

  afterEach(async () => {
    await fs.rm(repoPath, { recursive: true, force: true });
  });

  it("reports nothing detected on a clean repo", async () => {
    const result = await detectExistingConfig(repoPath);
    expect(result.anyDetected).toBe(false);
    expect(result.claudeMd).toBe(false);
    expect(result.agentsMd).toBe(false);
    expect(result.cursorRules).toBe(false);
    expect(result.copilotInstructions).toBe(false);
  });

  it("detects CLAUDE.md", async () => {
    await fs.writeFile(path.join(repoPath, "CLAUDE.md"), "# hi");
    const result = await detectExistingConfig(repoPath);
    expect(result.claudeMd).toBe(true);
    expect(result.anyDetected).toBe(true);
  });

  it("detects AGENTS.md", async () => {
    await fs.writeFile(path.join(repoPath, "AGENTS.md"), "# hi");
    const result = await detectExistingConfig(repoPath);
    expect(result.agentsMd).toBe(true);
    expect(result.anyDetected).toBe(true);
  });

  it("detects .cursor/rules directory", async () => {
    await fs.mkdir(path.join(repoPath, ".cursor", "rules"), { recursive: true });
    const result = await detectExistingConfig(repoPath);
    expect(result.cursorRules).toBe(true);
    expect(result.anyDetected).toBe(true);
  });

  it("detects .github/copilot-instructions.md", async () => {
    await fs.mkdir(path.join(repoPath, ".github"), { recursive: true });
    await fs.writeFile(path.join(repoPath, ".github", "copilot-instructions.md"), "# hi");
    const result = await detectExistingConfig(repoPath);
    expect(result.copilotInstructions).toBe(true);
    expect(result.anyDetected).toBe(true);
  });

  it("detects multiple config surfaces at once", async () => {
    await fs.writeFile(path.join(repoPath, "CLAUDE.md"), "# hi");
    await fs.writeFile(path.join(repoPath, "AGENTS.md"), "# hi");
    const result = await detectExistingConfig(repoPath);
    expect(result.claudeMd).toBe(true);
    expect(result.agentsMd).toBe(true);
    expect(result.cursorRules).toBe(false);
  });
});
