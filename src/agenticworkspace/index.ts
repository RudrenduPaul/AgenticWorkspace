/**
 * Public library exports. Most users will invoke the `agenticworkspace` CLI
 * binary directly (see cli.ts), but the underlying scan/scaffold/adapter
 * logic is also importable for programmatic use (e.g. another tool that
 * wants to run AgenticWorkspace's detection logic without shelling out).
 */

export { detectStack } from "./scan/stack-detector.js";
export type { StackDetectionResult, PackageManager, PrimaryLanguage } from "./scan/stack-detector.js";

export { detectExistingConfig } from "./scan/config-detector.js";
export type { ExistingConfigResult } from "./scan/config-detector.js";

export { memoryBackendRegistry, detectAllMemoryBackends } from "./memory-backends/registry.js";
export type { MemoryBackend } from "./memory-backends/types.js";
export type { MemoryBackendDetectionResult } from "./memory-backends/registry.js";

export { adapterRegistry, getAdapter } from "./adapters/registry.js";
export type { Adapter, AdapterInstallOptions } from "./adapters/types.js";

export { runInitEngine } from "./scaffold/init-engine.js";
export { readManifest, writeManifest } from "./scaffold/workspace-manifest.js";
export type { WorkspaceManifest } from "./scaffold/workspace-manifest.js";

export { sanitizeForShellEmbedding, validateAgainstAllowlist, shellQuote } from "./util/sanitize.js";
