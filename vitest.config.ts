import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["test/**/*.test.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      include: ["src/**/*.ts"],
      // cli.ts and index.ts are thin wiring/re-export files (argument parsing,
      // process.exit plumbing) with no independent logic to unit test --
      // every code path they call into is covered via the command modules
      // directly. adapters/types.ts is a type-only interface file.
      exclude: [
        "src/agenticworkspace/cli.ts",
        "src/agenticworkspace/index.ts",
        "src/agenticworkspace/adapters/types.ts",
        "src/agenticworkspace/memory-backends/types.ts",
      ],
      thresholds: {
        lines: 80,
        statements: 80,
        functions: 75,
        branches: 70,
      },
    },
  },
});
