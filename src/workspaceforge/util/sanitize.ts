/**
 * Shared sanitization module.
 *
 * Every value derived from scanning a target repository (file paths, detected
 * module names, package names, branch names, and so on) that ends up embedded
 * into a generated shell script (the Claude Code adapter's hook .sh files)
 * must pass through this module first. Nothing else in the codebase should
 * duplicate this logic -- call into these functions instead.
 *
 * Defense in depth, two layers:
 *   1. An allowlist pattern: only alphanumeric characters, dash, underscore,
 *      and forward slash are accepted. Anything else is rejected outright.
 *   2. POSIX single-quote shell quoting on top, applied to every value that
 *      does get embedded, even though the allowlist already excludes shell
 *      metacharacters. Belt and suspenders: if the allowlist is ever loosened
 *      by mistake in the future, the quoting still holds.
 */

/** Matches only [A-Za-z0-9_/-]. Empty strings do not match. */
const ALLOWLIST_PATTERN = /^[A-Za-z0-9_/-]+$/;

/** Maximum length accepted for any sanitized value. Prevents pathological input. */
const MAX_VALUE_LENGTH = 512;

export interface SanitizeResult {
  ok: boolean;
  value: string | null;
  reason?: string;
}

/**
 * Validate a single value against the allowlist. Does not throw. Callers get
 * a structured result so they can log a warning and skip the value rather
 * than crash the whole scan/install run over one bad detected string.
 */
export function validateAgainstAllowlist(rawValue: unknown): SanitizeResult {
  if (typeof rawValue !== "string") {
    return { ok: false, value: null, reason: "value is not a string" };
  }
  if (rawValue.length === 0) {
    return { ok: false, value: null, reason: "value is empty" };
  }
  if (rawValue.length > MAX_VALUE_LENGTH) {
    return {
      ok: false,
      value: null,
      reason: `value exceeds max length of ${MAX_VALUE_LENGTH} characters`,
    };
  }
  if (!ALLOWLIST_PATTERN.test(rawValue)) {
    return {
      ok: false,
      value: null,
      reason: "value contains characters outside the allowlist (alphanumeric, dash, underscore, slash only)",
    };
  }
  return { ok: true, value: rawValue };
}

/**
 * Quote a string for safe embedding inside a POSIX shell script, using single
 * quotes. Standard technique: close the quote, escape a literal single quote,
 * reopen the quote. Applied even to already-allowlisted values, as defense in
 * depth against a future allowlist regression.
 */
export function shellQuote(value: string): string {
  return `'${value.replace(/'/g, `'\\''`)}'`;
}

export interface SanitizeForShellOptions {
  /** Used only in the emitted warning message, to identify what failed. */
  label?: string;
}

export type SanitizeWarning = (message: string) => void;

/**
 * Validate a value against the allowlist and, if it passes, return it
 * shell-quoted and ready to embed in a generated script. If it fails, call
 * the supplied warn callback (defaults to a no-op) and return null so the
 * caller can skip embedding that value and continue, rather than crash or
 * silently embed unsafe content.
 */
export function sanitizeForShellEmbedding(
  rawValue: unknown,
  warn: SanitizeWarning = () => {},
  options: SanitizeForShellOptions = {},
): string | null {
  const result = validateAgainstAllowlist(rawValue);
  if (!result.ok || result.value === null) {
    const label = options.label ? `[${options.label}] ` : "";
    warn(`${label}skipped value that failed sanitization allowlist: ${result.reason}`);
    return null;
  }
  return shellQuote(result.value);
}

/**
 * Sanitize a whole list of values in one pass, dropping any value that fails
 * the allowlist and warning for each drop, rather than failing the entire
 * batch because one value was unsafe.
 */
export function sanitizeListForShellEmbedding(
  rawValues: readonly unknown[],
  warn: SanitizeWarning = () => {},
  options: SanitizeForShellOptions = {},
): string[] {
  const out: string[] = [];
  for (const rawValue of rawValues) {
    const sanitized = sanitizeForShellEmbedding(rawValue, warn, options);
    if (sanitized !== null) {
      out.push(sanitized);
    }
  }
  return out;
}
