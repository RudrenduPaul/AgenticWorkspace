import path from "node:path";
import { promises as fs } from "node:fs";
import type { Adapter, AdapterInstallOptions } from "../types.js";
import { fileExists, readJsonIfExists, writeJson, writeText, ensureDir } from "../../util/fs-utils.js";
import {
  buildSessionStartScript,
  buildPreToolCallScript,
  buildSessionEndHandoffScript,
} from "./hook-scripts.js";

/** Bumped whenever the shape of settings.json or the hook scripts changes in a way staleness detection should catch. */
export const CLAUDE_CODE_HOOK_SCHEMA_VERSION = "2026-07-01";

const ADAPTER_DIR_NAME = "claude-code";

interface ClaudeCodeAdapterMeta {
  hookSchemaVersion: string;
  installedAt: string;
}

interface ClaudeCodeSettingsHookEntry {
  matcher: string;
  hooks: Array<{ type: "command"; command: string }>;
}

interface ClaudeCodeSettings {
  hooks: {
    SessionStart: ClaudeCodeSettingsHookEntry[];
    PreToolUse: ClaudeCodeSettingsHookEntry[];
    SessionEnd: ClaudeCodeSettingsHookEntry[];
  };
}

function adapterDir(workspaceDir: string): string {
  return path.join(workspaceDir, "adapters", ADAPTER_DIR_NAME);
}

function metaPath(workspaceDir: string): string {
  return path.join(adapterDir(workspaceDir), "adapter-meta.json");
}

function settingsPath(workspaceDir: string): string {
  return path.join(adapterDir(workspaceDir), "settings.json");
}

function hooksDir(workspaceDir: string): string {
  return path.join(adapterDir(workspaceDir), "hooks");
}

function buildSettings(): ClaudeCodeSettings {
  const hookCommand = (script: string) => `bash .workspace/adapters/claude-code/hooks/${script}`;
  return {
    hooks: {
      SessionStart: [
        { matcher: "", hooks: [{ type: "command", command: hookCommand("session-start.sh") }] },
      ],
      PreToolUse: [
        { matcher: "", hooks: [{ type: "command", command: hookCommand("pre-tool-call.sh") }] },
      ],
      SessionEnd: [
        { matcher: "", hooks: [{ type: "command", command: hookCommand("session-end-handoff.sh") }] },
      ],
    },
  };
}

export const claudeCodeAdapter: Adapter = {
  name: ADAPTER_DIR_NAME,
  hookSchemaVersion: CLAUDE_CODE_HOOK_SCHEMA_VERSION,
  isImplemented: true,

  describe(): string {
    return "Claude Code adapter -- real hook + settings wiring (session-start, pre-tool-call, session-end handoff)";
  },

  async isInstalled(workspaceDir: string): Promise<boolean> {
    return fileExists(settingsPath(workspaceDir));
  },

  async install(workspaceDir: string, opts: AdapterInstallOptions): Promise<void> {
    const dir = adapterDir(workspaceDir);
    const scriptsDir = hooksDir(workspaceDir);
    await ensureDir(scriptsDir);

    const moduleNames = opts.moduleNames ?? [];
    const warnings: string[] = [];
    const warn = (message: string) => warnings.push(message);

    const scripts: Array<[string, string]> = [
      ["session-start.sh", buildSessionStartScript({ moduleNames, warn })],
      ["pre-tool-call.sh", buildPreToolCallScript({ moduleNames, warn })],
      ["session-end-handoff.sh", buildSessionEndHandoffScript({ moduleNames, warn })],
    ];

    for (const [fileName, content] of scripts) {
      const targetPath = path.join(scriptsDir, fileName);
      await writeText(targetPath, content);
      await fs.chmod(targetPath, 0o755);
    }

    for (const warning of warnings) {
      // Logged, never thrown -- a rejected value is skipped, not fatal.
      console.warn(`[workspaceforge] ${warning}`);
    }

    await writeJson(settingsPath(workspaceDir), buildSettings());

    const meta: ClaudeCodeAdapterMeta = {
      hookSchemaVersion: CLAUDE_CODE_HOOK_SCHEMA_VERSION,
      installedAt: new Date().toISOString(),
    };
    await writeJson(metaPath(workspaceDir), meta);
    void dir; // dir is used only to establish paths above; kept for readability.
  },

  async checkStale(workspaceDir: string): Promise<boolean> {
    const meta = await readJsonIfExists<ClaudeCodeAdapterMeta>(metaPath(workspaceDir));
    if (!meta) {
      return false; // not installed at all is reported separately via isInstalled()
    }
    return meta.hookSchemaVersion !== CLAUDE_CODE_HOOK_SCHEMA_VERSION;
  },
};

export async function getInstalledHookSchemaVersion(workspaceDir: string): Promise<string | null> {
  const meta = await readJsonIfExists<ClaudeCodeAdapterMeta>(metaPath(workspaceDir));
  return meta?.hookSchemaVersion ?? null;
}
