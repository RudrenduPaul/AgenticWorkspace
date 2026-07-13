import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { adapterRegistry, getAdapter } from "../../src/workspaceforge/adapters/registry.js";
import { codexAdapter } from "../../src/workspaceforge/adapters/codex/index.js";
import { cursorAdapter } from "../../src/workspaceforge/adapters/cursor/index.js";
import { claudeCodeAdapter } from "../../src/workspaceforge/adapters/claude-code/install.js";

describe("adapter registry", () => {
  it("registers claude-code, codex, and cursor", () => {
    const names = adapterRegistry.map((a) => a.name).sort();
    expect(names).toEqual(["claude-code", "codex", "cursor"]);
  });

  it("getAdapter finds a registered adapter by name", () => {
    expect(getAdapter("claude-code")).toBe(claudeCodeAdapter);
    expect(getAdapter("nonexistent")).toBeUndefined();
  });

  it("only claude-code is marked implemented in v0.1", () => {
    expect(claudeCodeAdapter.isImplemented).toBe(true);
    expect(codexAdapter.isImplemented).toBe(false);
    expect(cursorAdapter.isImplemented).toBe(false);
  });
});

describe("codex adapter (not yet implemented stub)", () => {
  it("reports not installed", async () => {
    expect(await codexAdapter.isInstalled("/tmp/whatever")).toBe(false);
  });

  it("install() throws rather than silently doing nothing", async () => {
    await expect(codexAdapter.install("/tmp/whatever", { repoPath: "/tmp/whatever" })).rejects.toThrow(
      /not yet implemented/,
    );
  });

  it("checkStale() reports false", async () => {
    expect(await codexAdapter.checkStale("/tmp/whatever")).toBe(false);
  });

  it("describe() clearly states not-yet-implemented", () => {
    expect(codexAdapter.describe()).toMatch(/NOT YET IMPLEMENTED/);
  });
});

describe("cursor adapter (not yet implemented stub)", () => {
  it("reports not installed", async () => {
    expect(await cursorAdapter.isInstalled("/tmp/whatever")).toBe(false);
  });

  it("install() throws rather than silently doing nothing", async () => {
    await expect(cursorAdapter.install("/tmp/whatever", { repoPath: "/tmp/whatever" })).rejects.toThrow(
      /not yet implemented/,
    );
  });

  it("describe() clearly states not-yet-implemented", () => {
    expect(cursorAdapter.describe()).toMatch(/NOT YET IMPLEMENTED/);
  });
});

describe("claude-code adapter install/staleness", () => {
  let workspaceDir: string;

  beforeEach(async () => {
    const tmp = await fs.mkdtemp(path.join(os.tmpdir(), "wf-adapter-test-"));
    workspaceDir = path.join(tmp, ".workspace");
  });

  afterEach(async () => {
    await fs.rm(path.dirname(workspaceDir), { recursive: true, force: true });
  });

  it("is not installed before install() is called", async () => {
    expect(await claudeCodeAdapter.isInstalled(workspaceDir)).toBe(false);
  });

  it("is installed and current immediately after install()", async () => {
    await claudeCodeAdapter.install(workspaceDir, { repoPath: "/tmp/fake-repo", moduleNames: ["auth"] });
    expect(await claudeCodeAdapter.isInstalled(workspaceDir)).toBe(true);
    expect(await claudeCodeAdapter.checkStale(workspaceDir)).toBe(false);
  });

  it("skips unsafe module names but still installs successfully", async () => {
    await claudeCodeAdapter.install(workspaceDir, {
      repoPath: "/tmp/fake-repo",
      moduleNames: ["auth", "$(evil)", "api"],
    });
    const scriptPath = path.join(workspaceDir, "adapters", "claude-code", "hooks", "session-start.sh");
    const content = await fs.readFile(scriptPath, "utf-8");
    expect(content).toContain("'auth'");
    expect(content).toContain("'api'");
    expect(content).not.toContain("$(evil)");
  });
});
