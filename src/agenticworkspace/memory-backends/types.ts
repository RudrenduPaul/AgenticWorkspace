/**
 * A MemoryBackend describes a third-party (or first-party) memory/context
 * tool that may already be wired into a target repository. AgenticWorkspace
 * never assumes a specific backend is present -- it detects what is already
 * there and reports it, so `init` can avoid silently duplicating or
 * conflicting with a tool a team has already adopted.
 *
 * New backends are added by implementing this interface and registering an
 * instance in the registry (see registry.ts) -- no changes to scan or CLI
 * code are needed beyond that registration.
 */
export interface MemoryBackend {
  /** Stable identifier, used in workspace.json and --json output. */
  name: string;

  /**
   * Does this repo already have this backend's configuration present?
   * Must be a read-only filesystem check -- detect only, never write,
   * modify, or delete anything belonging to another tool.
   */
  detect(repoPath: string): Promise<boolean>;

  /** Human-readable description, used in terminal status output. */
  describe(): string;
}
