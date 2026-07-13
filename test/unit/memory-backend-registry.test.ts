import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  memoryBackendRegistry,
  detectAllMemoryBackends,
  anyBackendDetected,
} from "../../src/agenticworkspace/memory-backends/registry.js";
import type { MemoryBackend } from "../../src/agenticworkspace/memory-backends/types.js";

async function makeTempRepo(): Promise<string> {
  return fs.mkdtemp(path.join(os.tmpdir(), "wf-backend-test-"));
}

describe("memoryBackendRegistry", () => {
  it("registers serena, gitnexus, and repo-harness by default", () => {
    const names = memoryBackendRegistry.map((b) => b.name).sort();
    expect(names).toEqual(["gitnexus", "repo-harness", "serena"]);
  });
});

describe("detectAllMemoryBackends", () => {
  let repoPath: string;

  beforeEach(async () => {
    repoPath = await makeTempRepo();
  });

  afterEach(async () => {
    await fs.rm(repoPath, { recursive: true, force: true });
  });

  it("reports every backend as not detected on a clean repo", async () => {
    const results = await detectAllMemoryBackends(repoPath);
    expect(results).toHaveLength(3);
    expect(results.every((r) => r.detected === false)).toBe(true);
    expect(anyBackendDetected(results)).toBe(false);
  });

  it("detects a .serena/ directory", async () => {
    await fs.mkdir(path.join(repoPath, ".serena"), { recursive: true });
    const results = await detectAllMemoryBackends(repoPath);
    const serena = results.find((r) => r.name === "serena");
    expect(serena?.detected).toBe(true);
    expect(anyBackendDetected(results)).toBe(true);
  });

  it("detects a .ai/harness/ directory (repo-harness) and does not touch it", async () => {
    const harnessDir = path.join(repoPath, ".ai", "harness");
    await fs.mkdir(harnessDir, { recursive: true });
    await fs.writeFile(path.join(harnessDir, "marker.txt"), "do-not-touch");

    const results = await detectAllMemoryBackends(repoPath);
    const repoHarness = results.find((r) => r.name === "repo-harness");
    expect(repoHarness?.detected).toBe(true);

    const contents = await fs.readFile(path.join(harnessDir, "marker.txt"), "utf-8");
    expect(contents).toBe("do-not-touch");
  });

  it("detects a gitnexus.config.json file", async () => {
    await fs.writeFile(path.join(repoPath, "gitnexus.config.json"), "{}");
    const results = await detectAllMemoryBackends(repoPath);
    const gitnexus = results.find((r) => r.name === "gitnexus");
    expect(gitnexus?.detected).toBe(true);
  });

  it("continues detecting other backends even if a custom backend throws", async () => {
    const throwingBackend: MemoryBackend = {
      name: "broken-backend",
      async detect(): Promise<boolean> {
        throw new Error("simulated filesystem failure");
      },
      describe: () => "a backend that always throws",
    };
    const customRegistry = [...memoryBackendRegistry, throwingBackend];
    const results = await detectAllMemoryBackends(repoPath, customRegistry);
    const broken = results.find((r) => r.name === "broken-backend");
    expect(broken?.detected).toBe(false);
    expect(results).toHaveLength(4);
  });
});
