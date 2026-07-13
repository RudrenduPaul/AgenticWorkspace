/**
 * An Adapter wires WorkspaceForge's `.workspace/` scaffold into a specific
 * AI coding tool (Claude Code, Codex, Cursor, ...). Each adapter owns its own
 * hook/settings format and versioning; the CLI only depends on this
 * interface, so adding a new tool means implementing Adapter and registering
 * it (see registry.ts), not touching CLI or scaffold code.
 */
export interface Adapter {
  /** Stable identifier, e.g. "claude-code". Used as the directory name under .workspace/adapters/. */
  name: string;

  /**
   * Version of this adapter's hook/settings schema. Bumped whenever the
   * shape of what install() writes changes in a way that matters for
   * staleness detection (a new required hook, a renamed settings field).
   */
  hookSchemaVersion: string;

  /** True if this adapter is fully implemented and safe to install in this version of WorkspaceForge. */
  isImplemented: boolean;

  /** Human-readable one-liner, used in status output (especially for not-yet-implemented adapters). */
  describe(): string;

  /** True if this adapter is already installed under the given .workspace/ directory. */
  isInstalled(workspaceDir: string): Promise<boolean>;

  /** Install (or reinstall) this adapter's files under the given .workspace/ directory. */
  install(workspaceDir: string, opts: AdapterInstallOptions): Promise<void>;

  /**
   * True if the installed adapter's recorded hook schema version is older
   * than this adapter's current hookSchemaVersion -- i.e. it needs updating.
   */
  checkStale(workspaceDir: string): Promise<boolean>;
}

export interface AdapterInstallOptions {
  /** Absolute path to the repo being converted into a workspace. */
  repoPath: string;
  /** Detected stack info, so hooks can reference real package/module names safely. */
  moduleNames?: string[];
}
