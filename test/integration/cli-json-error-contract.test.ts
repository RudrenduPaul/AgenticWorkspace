import { describe, it, expect } from "vitest";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";
import { fileURLToPath } from "node:url";

const execFileAsync = promisify(execFile);

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "../..");
const tsxBin = path.join(repoRoot, "node_modules", ".bin", "tsx");
const cliEntry = path.join(repoRoot, "src", "agenticworkspace", "cli.ts");

/**
 * Regression test for the top-level catch handler in cli.ts: any error that
 * escapes a command's own try/catch (e.g. mkdir failing on an unwritable or
 * nonexistent --path) must still honor --json. An agent invoking this CLI
 * programmatically parses stdout as JSON and must never be handed a bare
 * stderr string instead -- that was a real bug (fixed alongside this test)
 * where unexpected errors always printed plain text via console.error
 * regardless of --json.
 */
describe("CLI process-level --json error contract", () => {
  it("emits a parseable JSON object with ok:false when an unexpected error escapes to the top-level catch", async () => {
    const unwritablePath = "/this/path/cannot/possibly/exist/agenticworkspace-test";

    let stdout = "";
    try {
      const result = await execFileAsync(tsxBin, [cliEntry, "init", "--json", "--path", unwritablePath]);
      stdout = result.stdout;
    } catch (error) {
      // execFile rejects on non-zero exit code; the CLI is expected to exit
      // non-zero here, so pull stdout off the rejected error instead.
      stdout = (error as { stdout?: string }).stdout ?? "";
    }

    const parsed = JSON.parse(stdout);
    expect(parsed.ok).toBe(false);
    expect(typeof parsed.message).toBe("string");
  });

  it("prints plain text (not JSON) for the same failure when --json is not passed", async () => {
    const unwritablePath = "/this/path/cannot/possibly/exist/agenticworkspace-test";

    let stderr = "";
    try {
      await execFileAsync(tsxBin, [cliEntry, "init", "--path", unwritablePath]);
    } catch (error) {
      stderr = (error as { stderr?: string }).stderr ?? "";
    }

    expect(stderr).toContain("agenticworkspace:");
    expect(() => JSON.parse(stderr)).toThrow();
  });
});
