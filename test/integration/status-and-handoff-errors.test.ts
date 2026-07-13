import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { runStatusCommand } from "../../src/workspaceforge/commands/status.js";
import { runHandoffNewCommand } from "../../src/workspaceforge/commands/handoff.js";
import { runInitCommand } from "../../src/workspaceforge/commands/init.js";
import { writeInProgressMarker } from "../../src/workspaceforge/state/partial-state.js";
import { EXIT_CODES } from "../../src/workspaceforge/util/exit-codes.js";

async function makeTempRepo(): Promise<string> {
  return fs.mkdtemp(path.join(os.tmpdir(), "wf-status-handoff-errors-"));
}

describe("status command error paths", () => {
  let repoPath: string;

  beforeEach(async () => {
    repoPath = await makeTempRepo();
  });

  afterEach(async () => {
    await fs.rm(repoPath, { recursive: true, force: true });
  });

  it("returns NO_WORKSPACE_FOUND when .workspace/ has never been created", async () => {
    const outcome = await runStatusCommand({ path: repoPath, json: true });
    expect(outcome.exitCode).toBe(EXIT_CODES.NO_WORKSPACE_FOUND);
    expect(outcome.json.error).toBe("no_workspace_found");
  });

  it("returns PARTIAL_STATE_DETECTED when .workspace/ is interrupted", async () => {
    const workspaceDir = path.join(repoPath, ".workspace");
    await fs.mkdir(workspaceDir, { recursive: true });
    await writeInProgressMarker(workspaceDir);

    const outcome = await runStatusCommand({ path: repoPath, json: true });
    expect(outcome.exitCode).toBe(EXIT_CODES.PARTIAL_STATE_DETECTED);
    expect(outcome.json.partial_state).toBe("interrupted-init");
  });

  it("reports detected other-backend directories for transparency", async () => {
    await fs.mkdir(path.join(repoPath, ".serena"), { recursive: true });
    await runInitCommand({ path: repoPath, json: true });

    const outcome = await runStatusCommand({ path: repoPath, json: true });
    const compat = outcome.json.compatibility_check as Record<string, boolean>;
    expect(compat.existing_serena_dir).toBe(true);
  });
});

describe("handoff new command error paths", () => {
  let repoPath: string;

  beforeEach(async () => {
    repoPath = await makeTempRepo();
  });

  afterEach(async () => {
    await fs.rm(repoPath, { recursive: true, force: true });
  });

  it("rejects an empty message", async () => {
    const outcome = await runHandoffNewCommand("   ", { path: repoPath, json: true });
    expect(outcome.exitCode).toBe(EXIT_CODES.GENERAL_ERROR);
    expect(outcome.json.error).toBe("empty_message");
  });

  it("returns NO_WORKSPACE_FOUND when .workspace/ has never been created", async () => {
    const outcome = await runHandoffNewCommand("a real message", { path: repoPath, json: true });
    expect(outcome.exitCode).toBe(EXIT_CODES.NO_WORKSPACE_FOUND);
  });

  it("writes two handoffs in quick succession without filename collision", async () => {
    await runInitCommand({ path: repoPath, json: true });
    const first = await runHandoffNewCommand("first note", { path: repoPath, json: true });
    const second = await runHandoffNewCommand("second note", { path: repoPath, json: true });
    expect(first.json.file).not.toBe(second.json.file);
  });
});
