import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { runInitCommand } from "../../src/workspaceforge/commands/init.js";
import { runStatusCommand } from "../../src/workspaceforge/commands/status.js";
import { runHandoffNewCommand } from "../../src/workspaceforge/commands/handoff.js";

async function makeTempRepo(): Promise<string> {
  const repoPath = await fs.mkdtemp(path.join(os.tmpdir(), "wf-init-integration-"));
  await fs.writeFile(path.join(repoPath, "package.json"), JSON.stringify({ name: "fixture" }));
  await fs.writeFile(path.join(repoPath, "package-lock.json"), "{}");
  await fs.writeFile(path.join(repoPath, "tsconfig.json"), "{}");
  await fs.mkdir(path.join(repoPath, "src", "auth"), { recursive: true });
  await fs.mkdir(path.join(repoPath, "src", "api"), { recursive: true });
  await fs.writeFile(path.join(repoPath, "src", "auth", "index.ts"), "export {};");
  await fs.writeFile(path.join(repoPath, "src", "api", "index.ts"), "export {};");
  return repoPath;
}

async function fileExists(p: string): Promise<boolean> {
  try {
    await fs.stat(p);
    return true;
  } catch {
    return false;
  }
}

describe("init end to end", () => {
  let repoPath: string;

  beforeEach(async () => {
    repoPath = await makeTempRepo();
  });

  afterEach(async () => {
    await fs.rm(repoPath, { recursive: true, force: true });
  });

  it("writes the full .workspace/ scaffold on a fresh repo", async () => {
    const outcome = await runInitCommand({ path: repoPath, json: true });

    expect(outcome.exitCode).toBe(0);
    expect(outcome.json.ok).toBe(true);

    const workspaceDir = path.join(repoPath, ".workspace");
    expect(await fileExists(path.join(workspaceDir, "workspace.json"))).toBe(true);
    expect(await fileExists(path.join(workspaceDir, "context", "root-context.md"))).toBe(true);
    expect(await fileExists(path.join(workspaceDir, "context", "modules", "auth.md"))).toBe(true);
    expect(await fileExists(path.join(workspaceDir, "context", "modules", "api.md"))).toBe(true);
    expect(await fileExists(path.join(workspaceDir, "handoff"))).toBe(true);
    expect(await fileExists(path.join(workspaceDir, "adapters", "claude-code", "settings.json"))).toBe(true);
    expect(await fileExists(path.join(workspaceDir, "adapters", "claude-code", "hooks", "session-start.sh"))).toBe(
      true,
    );
    expect(
      await fileExists(path.join(workspaceDir, "adapters", "claude-code", "hooks", "pre-tool-call.sh")),
    ).toBe(true);
    expect(
      await fileExists(path.join(workspaceDir, "adapters", "claude-code", "hooks", "session-end-handoff.sh")),
    ).toBe(true);

    // No leftover in-progress marker after a successful run.
    expect(await fileExists(path.join(workspaceDir, ".init-in-progress"))).toBe(false);
  });

  it("never overwrites an existing CLAUDE.md and reports it as detected", async () => {
    await fs.writeFile(path.join(repoPath, "CLAUDE.md"), "# hand-written, do not touch\n");
    const before = await fs.readFile(path.join(repoPath, "CLAUDE.md"), "utf-8");

    const outcome = await runInitCommand({ path: repoPath, json: true });
    expect(outcome.exitCode).toBe(0);

    const after = await fs.readFile(path.join(repoPath, "CLAUDE.md"), "utf-8");
    expect(after).toBe(before);

    const existingConfig = outcome.json.existing_config as { claudeMd: boolean };
    expect(existingConfig.claudeMd).toBe(true);
  });

  it("produces a status --json output consistent with what init wrote", async () => {
    await runInitCommand({ path: repoPath, json: true });
    const statusOutcome = await runStatusCommand({ path: repoPath, json: true });

    expect(statusOutcome.exitCode).toBe(0);
    const stack = statusOutcome.json.stack as { language: string; package_manager: string };
    expect(stack.language).toBe("typescript");
    expect(stack.package_manager).toBe("npm");

    const adapters = statusOutcome.json.adapters as { claude_code: { installed: boolean; current: boolean } };
    expect(adapters.claude_code.installed).toBe(true);
    expect(adapters.claude_code.current).toBe(true);
  });

  it("writes a handoff file discoverable by status after init", async () => {
    await runInitCommand({ path: repoPath, json: true });
    const handoffOutcome = await runHandoffNewCommand("did the thing, next: do the other thing", {
      path: repoPath,
      json: true,
    });
    expect(handoffOutcome.exitCode).toBe(0);

    const statusOutcome = await runStatusCommand({ path: repoPath, json: true });
    const handoff = statusOutcome.json.handoff as { files: number; most_recent: string | null };
    expect(handoff.files).toBe(1);
    expect(handoff.most_recent).toMatch(/\.md$/);
  });

  it("is idempotent: running init twice on a valid workspace succeeds both times", async () => {
    const first = await runInitCommand({ path: repoPath, json: true });
    expect(first.exitCode).toBe(0);
    const second = await runInitCommand({ path: repoPath, json: true });
    expect(second.exitCode).toBe(0);
  });
});
