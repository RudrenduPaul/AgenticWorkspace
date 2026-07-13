import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";

// Mock the prompt module so the repair/reset/abort integration test can drive
// the interactive branch of runInitCommand without a real TTY. Each test
// configures the mocked answer before calling runInitCommand.
const askRepairResetAbortMock = vi.fn();
vi.mock("../../src/workspaceforge/util/prompt.js", () => ({
  askRepairResetAbort: () => askRepairResetAbortMock(),
  isInteractiveTerminal: () => true,
}));

const { runInitCommand } = await import("../../src/workspaceforge/commands/init.js");
const { runInitEngine } = await import("../../src/workspaceforge/scaffold/init-engine.js");
const { writeInProgressMarker } = await import("../../src/workspaceforge/state/partial-state.js");

async function makeTempRepo(): Promise<string> {
  const repoPath = await fs.mkdtemp(path.join(os.tmpdir(), "wf-partial-state-"));
  await fs.writeFile(path.join(repoPath, "package.json"), JSON.stringify({ name: "fixture" }));
  await fs.writeFile(path.join(repoPath, "package-lock.json"), "{}");
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

describe("partial-state repair/reset/abort flow", () => {
  let repoPath: string;
  let workspaceDir: string;

  beforeEach(async () => {
    repoPath = await makeTempRepo();
    workspaceDir = path.join(repoPath, ".workspace");
    askRepairResetAbortMock.mockReset();
  });

  afterEach(async () => {
    await fs.rm(repoPath, { recursive: true, force: true });
  });

  it("json mode never prompts: returns exit code 2 and a partial_state_detected error for an interrupted init", async () => {
    await fs.mkdir(workspaceDir, { recursive: true });
    await writeInProgressMarker(workspaceDir);

    const outcome = await runInitCommand({ path: repoPath, json: true });

    expect(outcome.exitCode).toBe(2);
    expect(outcome.json.error).toBe("partial_state_detected");
    expect(outcome.json.partial_state).toBe("interrupted-init");
    expect(askRepairResetAbortMock).not.toHaveBeenCalled();
  });

  it("abort choice leaves .workspace/ untouched and returns a non-zero exit code", async () => {
    await fs.mkdir(workspaceDir, { recursive: true });
    await writeInProgressMarker(workspaceDir);
    askRepairResetAbortMock.mockResolvedValue("abort");

    const outcome = await runInitCommand({ path: repoPath, json: false });

    expect(outcome.exitCode).toBe(1);
    expect(outcome.json.error).toBe("aborted_by_user");
    // The marker should still be there -- abort must not touch the directory.
    expect(await fileExists(path.join(workspaceDir, ".init-in-progress"))).toBe(true);
    expect(await fileExists(path.join(workspaceDir, "workspace.json"))).toBe(false);
  });

  it("repair choice finishes writing the missing pieces without wiping existing handoff history", async () => {
    // Simulate an interrupted run: .workspace/ exists with a real handoff
    // file already written, but the manifest never got written (crash mid-run).
    await fs.mkdir(path.join(workspaceDir, "handoff"), { recursive: true });
    await fs.writeFile(path.join(workspaceDir, "handoff", "2026-01-01-0000.md"), "# earlier session\n");
    await writeInProgressMarker(workspaceDir);
    askRepairResetAbortMock.mockResolvedValue("repair");

    // Interactive mode (json: false): --json must never prompt (see the
    // "json mode never prompts" test above), so exercising the actual
    // repair/reset/abort prompt flow requires simulating a real terminal.
    const outcome = await runInitCommand({ path: repoPath, json: false });

    expect(outcome.exitCode).toBe(0);
    expect(outcome.json.ok).toBe(true);
    expect(await fileExists(path.join(workspaceDir, "workspace.json"))).toBe(true);
    // Repair must not delete a handoff file that predates the repair.
    expect(await fileExists(path.join(workspaceDir, "handoff", "2026-01-01-0000.md"))).toBe(true);
    expect(await fileExists(path.join(workspaceDir, ".init-in-progress"))).toBe(false);
  });

  it("reset choice wipes .workspace/ and starts clean, discarding prior handoff history", async () => {
    await fs.mkdir(path.join(workspaceDir, "handoff"), { recursive: true });
    await fs.writeFile(path.join(workspaceDir, "handoff", "2026-01-01-0000.md"), "# earlier session\n");
    await writeInProgressMarker(workspaceDir);
    askRepairResetAbortMock.mockResolvedValue("reset");

    const outcome = await runInitCommand({ path: repoPath, json: false });

    expect(outcome.exitCode).toBe(0);
    expect(outcome.json.ok).toBe(true);
    expect(await fileExists(path.join(workspaceDir, "workspace.json"))).toBe(true);
    // Reset must discard whatever was there before.
    expect(await fileExists(path.join(workspaceDir, "handoff", "2026-01-01-0000.md"))).toBe(false);
  });

  it("detects a malformed manifest (missing expected keys) as a partial state, not a silent overwrite", async () => {
    await fs.mkdir(workspaceDir, { recursive: true });
    await fs.writeFile(path.join(workspaceDir, "workspace.json"), JSON.stringify({ someUnexpectedShape: true }));

    const outcome = await runInitCommand({ path: repoPath, json: true });

    expect(outcome.exitCode).toBe(2);
    expect(outcome.json.partial_state).toBe("malformed-manifest");
    expect(Array.isArray(outcome.json.missing_keys)).toBe(true);
    expect((outcome.json.missing_keys as string[]).length).toBeGreaterThan(0);
  });

  it("a fully valid prior workspace is treated as complete, not partial, and init re-scans idempotently", async () => {
    await runInitEngine(repoPath, workspaceDir);
    const outcome = await runInitCommand({ path: repoPath, json: true });
    expect(outcome.exitCode).toBe(0);
    expect(askRepairResetAbortMock).not.toHaveBeenCalled();
  });
});
