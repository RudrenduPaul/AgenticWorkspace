/**
 * Exit codes used across the CLI. Kept in one place so JSON output and
 * process.exit() calls stay consistent, and so an agent parsing --json
 * output can rely on a stable contract.
 */
export const EXIT_CODES = {
  OK: 0,
  GENERAL_ERROR: 1,
  PARTIAL_STATE_DETECTED: 2,
  ADAPTER_NOT_IMPLEMENTED: 3,
  NO_WORKSPACE_FOUND: 4,
} as const;

export type ExitCode = (typeof EXIT_CODES)[keyof typeof EXIT_CODES];
