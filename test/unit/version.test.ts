import { describe, it, expect } from "vitest";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { AGENTICWORKSPACE_VERSION } from "../../src/agenticworkspace/scaffold/init-engine.js";

const packageJsonPath = path.join(path.dirname(fileURLToPath(import.meta.url)), "../../package.json");

describe("AGENTICWORKSPACE_VERSION", () => {
  it("matches package.json's version instead of a hand-maintained constant", async () => {
    // A previous hardcoded string here drifted out of sync with package.json/npm on
    // every release (shipped "0.1.1" while npm had already published 0.1.4), so
    // --version and every JSON output's agenticworkspace_version field silently lied
    // about which release was actually running. This locks the two together.
    const pkg = JSON.parse(await readFile(packageJsonPath, "utf-8"));
    expect(AGENTICWORKSPACE_VERSION).toBe(pkg.version);
  });

  it("is never the fs-read-failure fallback", () => {
    expect(AGENTICWORKSPACE_VERSION).not.toBe("0.0.0");
  });
});
