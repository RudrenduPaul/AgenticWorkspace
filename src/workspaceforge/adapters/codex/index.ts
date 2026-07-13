import type { Adapter } from "../types.js";

/**
 * Codex adapter -- registered so the adapter registry and CLI plumbing are
 * real and extensible, but NOT YET IMPLEMENTED in v0.1. install() throws
 * rather than silently doing nothing, so a caller cannot mistake a no-op for
 * a real install. Tracked as v0.2 scope (WF07 in the workspace-surface scan
 * table) -- a community-contributed shim following the same handoff/context
 * model as the Claude Code adapter.
 */
export const codexAdapter: Adapter = {
  name: "codex",
  hookSchemaVersion: "unreleased",
  isImplemented: false,

  describe(): string {
    return "Codex adapter -- NOT YET IMPLEMENTED (planned for v0.2, community-contributed shim)";
  },

  async isInstalled(): Promise<boolean> {
    return false;
  },

  async install(): Promise<void> {
    throw new Error(
      "workspaceforge: the Codex adapter is not yet implemented (planned for v0.2). " +
        "Only the Claude Code adapter works end to end in v0.1.",
    );
  },

  async checkStale(): Promise<boolean> {
    return false;
  },
};
