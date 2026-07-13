import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { detectStack } from "../../src/workspaceforge/scan/stack-detector.js";

async function makeTempRepo(): Promise<string> {
  return fs.mkdtemp(path.join(os.tmpdir(), "wf-stack-test-"));
}

async function write(repoPath: string, relPath: string, content = ""): Promise<void> {
  const full = path.join(repoPath, relPath);
  await fs.mkdir(path.dirname(full), { recursive: true });
  await fs.writeFile(full, content, "utf-8");
}

describe("detectStack", () => {
  let repoPath: string;

  beforeEach(async () => {
    repoPath = await makeTempRepo();
  });

  afterEach(async () => {
    await fs.rm(repoPath, { recursive: true, force: true });
  });

  it("detects npm + JavaScript with only package-lock.json present", async () => {
    await write(repoPath, "package.json", "{}");
    await write(repoPath, "package-lock.json", "{}");
    const result = await detectStack(repoPath);
    expect(result.packageManager).toBe("npm");
    expect(result.language).toBe("javascript");
  });

  it("detects npm + TypeScript when tsconfig.json is present", async () => {
    await write(repoPath, "package.json", "{}");
    await write(repoPath, "package-lock.json", "{}");
    await write(repoPath, "tsconfig.json", "{}");
    const result = await detectStack(repoPath);
    expect(result.packageManager).toBe("npm");
    expect(result.language).toBe("typescript");
  });

  it("detects pnpm via pnpm-lock.yaml", async () => {
    await write(repoPath, "package.json", "{}");
    await write(repoPath, "pnpm-lock.yaml", "");
    const result = await detectStack(repoPath);
    expect(result.packageManager).toBe("pnpm");
  });

  it("detects yarn via yarn.lock", async () => {
    await write(repoPath, "package.json", "{}");
    await write(repoPath, "yarn.lock", "");
    const result = await detectStack(repoPath);
    expect(result.packageManager).toBe("yarn");
  });

  it("prefers pnpm over yarn/npm when multiple lockfiles somehow exist", async () => {
    await write(repoPath, "package.json", "{}");
    await write(repoPath, "pnpm-lock.yaml", "");
    await write(repoPath, "yarn.lock", "");
    await write(repoPath, "package-lock.json", "{}");
    const result = await detectStack(repoPath);
    expect(result.packageManager).toBe("pnpm");
  });

  it("detects Python via pyproject.toml (poetry)", async () => {
    await write(repoPath, "pyproject.toml", "[tool.poetry]\nname = 'x'\n");
    const result = await detectStack(repoPath);
    expect(result.packageManager).toBe("poetry");
    expect(result.language).toBe("python");
  });

  it("detects Python via requirements.txt (pip)", async () => {
    await write(repoPath, "requirements.txt", "requests==2.0\n");
    const result = await detectStack(repoPath);
    expect(result.packageManager).toBe("pip");
    expect(result.language).toBe("python");
  });

  it("detects Rust via Cargo.toml", async () => {
    await write(repoPath, "Cargo.toml", "[package]\nname = 'x'\n");
    const result = await detectStack(repoPath);
    expect(result.packageManager).toBe("cargo");
    expect(result.language).toBe("rust");
  });

  it("detects Go via go.mod", async () => {
    await write(repoPath, "go.mod", "module example.com/x\n");
    const result = await detectStack(repoPath);
    expect(result.packageManager).toBe("go");
    expect(result.language).toBe("go");
  });

  it("returns unknown for a repo with no recognized stack files", async () => {
    await write(repoPath, "README.md", "hello");
    const result = await detectStack(repoPath);
    expect(result.packageManager).toBe("unknown");
    expect(result.language).toBe("unknown");
  });

  it("detects an npm workspaces monorepo via package.json workspaces field", async () => {
    await write(
      repoPath,
      "package.json",
      JSON.stringify({ workspaces: ["packages/*"] }),
    );
    await write(repoPath, "package-lock.json", "{}");
    await write(repoPath, "packages/pkg-a/package.json", "{}");
    await write(repoPath, "packages/pkg-b/package.json", "{}");
    const result = await detectStack(repoPath);
    expect(result.monorepo.isMonorepo).toBe(true);
    expect(result.monorepo.packageCount).toBe(2);
    expect(result.monorepo.packagePaths.sort()).toEqual(
      [path.join("packages", "pkg-a"), path.join("packages", "pkg-b")].sort(),
    );
  });

  it("detects a pnpm workspace monorepo via pnpm-workspace.yaml", async () => {
    await write(repoPath, "package.json", "{}");
    await write(repoPath, "pnpm-lock.yaml", "");
    await write(repoPath, "pnpm-workspace.yaml", "packages:\n  - 'apps/*'\n");
    await write(repoPath, "apps/web/package.json", "{}");
    const result = await detectStack(repoPath);
    expect(result.monorepo.isMonorepo).toBe(true);
    expect(result.monorepo.packageCount).toBe(1);
  });

  it("reports isMonorepo false for a single-package repo", async () => {
    await write(repoPath, "package.json", "{}");
    await write(repoPath, "package-lock.json", "{}");
    const result = await detectStack(repoPath);
    expect(result.monorepo.isMonorepo).toBe(false);
    expect(result.monorepo.packageCount).toBe(0);
  });
});
