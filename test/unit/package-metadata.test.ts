import { describe, it, expect } from "vitest";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const packageJsonPath = path.join(path.dirname(fileURLToPath(import.meta.url)), "../../package.json");

describe("package.json bin field", () => {
  it("registers both 'workspaceforge' and 'workspaceforge-cli' as bin names", async () => {
    const pkg = JSON.parse(await readFile(packageJsonPath, "utf-8"));
    // README's documented first command is `npx workspaceforge-cli init`. npx only
    // auto-resolves to a bin matching the package name (workspaceforge-cli) -- a
    // package that only registers a differently-named bin (workspaceforge) makes
    // that documented command fail with "command not found". Both names must be
    // registered so npx works regardless of which name a user or the README uses.
    expect(pkg.bin).toHaveProperty("workspaceforge");
    expect(pkg.bin).toHaveProperty("workspaceforge-cli");
    expect(pkg.bin["workspaceforge-cli"]).toBe(pkg.bin["workspaceforge"]);
  });
});
