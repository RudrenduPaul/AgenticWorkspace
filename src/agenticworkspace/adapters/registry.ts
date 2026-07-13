import type { Adapter } from "./types.js";
import { claudeCodeAdapter } from "./claude-code/install.js";
import { codexAdapter } from "./codex/index.js";
import { cursorAdapter } from "./cursor/index.js";

/**
 * The registry of all known Adapter implementations. Adding a new tool
 * adapter means implementing Adapter and adding it here -- nothing else in
 * scaffold or CLI code needs to change. Only claudeCodeAdapter is fully
 * implemented in v0.1; codex and cursor are registered stubs.
 */
export const adapterRegistry: Adapter[] = [claudeCodeAdapter, codexAdapter, cursorAdapter];

export function getAdapter(name: string): Adapter | undefined {
  return adapterRegistry.find((adapter) => adapter.name === name);
}
