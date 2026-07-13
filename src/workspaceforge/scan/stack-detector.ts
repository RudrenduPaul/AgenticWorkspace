import path from "node:path";
import { promises as fs } from "node:fs";
import { fileExists, listDir } from "../util/fs-utils.js";

export type PackageManager = "npm" | "pnpm" | "yarn" | "pip" | "poetry" | "cargo" | "go" | "bundler" | "unknown";

export type PrimaryLanguage =
  | "typescript"
  | "javascript"
  | "python"
  | "rust"
  | "go"
  | "ruby"
  | "unknown";

export interface MonorepoInfo {
  isMonorepo: boolean;
  packageCount: number;
  packagePaths: string[];
}

export interface StackDetectionResult {
  language: PrimaryLanguage;
  packageManager: PackageManager;
  monorepo: MonorepoInfo;
  /** Raw signals found, for status/debug output -- e.g. ["package-lock.json", "tsconfig.json"]. */
  signals: string[];
}

interface PackageJsonShape {
  workspaces?: string[] | { packages?: string[] };
  devDependencies?: Record<string, string>;
  dependencies?: Record<string, string>;
}

/**
 * WF01 -- stack and package-manager detection. Real filesystem checks, no
 * network calls. Covers, at minimum, npm/pnpm/yarn + TypeScript/JavaScript,
 * plus Python (pip/poetry), with lighter-weight signals for cargo, go
 * modules, and bundler/Gemfile per the broader workspace-surface scan table.
 */
export async function detectStack(repoPath: string): Promise<StackDetectionResult> {
  const signals: string[] = [];

  const [
    hasPackageJson,
    hasPackageLock,
    hasPnpmLock,
    hasYarnLock,
    hasPnpmWorkspaceYaml,
    hasTsconfig,
    hasRequirementsTxt,
    hasPyprojectToml,
    hasPipfile,
    hasCargoToml,
    hasGoMod,
    hasGemfile,
  ] = await Promise.all([
    fileExists(path.join(repoPath, "package.json")),
    fileExists(path.join(repoPath, "package-lock.json")),
    fileExists(path.join(repoPath, "pnpm-lock.yaml")),
    fileExists(path.join(repoPath, "yarn.lock")),
    fileExists(path.join(repoPath, "pnpm-workspace.yaml")),
    fileExists(path.join(repoPath, "tsconfig.json")),
    fileExists(path.join(repoPath, "requirements.txt")),
    fileExists(path.join(repoPath, "pyproject.toml")),
    fileExists(path.join(repoPath, "Pipfile")),
    fileExists(path.join(repoPath, "Cargo.toml")),
    fileExists(path.join(repoPath, "go.mod")),
    fileExists(path.join(repoPath, "Gemfile")),
  ]);

  let packageManager: PackageManager = "unknown";
  let language: PrimaryLanguage = "unknown";

  if (hasPackageJson) {
    signals.push("package.json");
    if (hasPnpmLock || hasPnpmWorkspaceYaml) {
      packageManager = "pnpm";
      signals.push(hasPnpmLock ? "pnpm-lock.yaml" : "pnpm-workspace.yaml");
    } else if (hasYarnLock) {
      packageManager = "yarn";
      signals.push("yarn.lock");
    } else if (hasPackageLock) {
      packageManager = "npm";
      signals.push("package-lock.json");
    } else {
      // package.json present with no lockfile detected yet -- default to npm,
      // the ecosystem default, rather than leaving it unknown.
      packageManager = "npm";
    }

    if (hasTsconfig) {
      language = "typescript";
      signals.push("tsconfig.json");
    } else {
      language = "javascript";
    }
  } else if (hasPyprojectToml) {
    signals.push("pyproject.toml");
    packageManager = "poetry";
    language = "python";
  } else if (hasPipfile) {
    signals.push("Pipfile");
    packageManager = "pip";
    language = "python";
  } else if (hasRequirementsTxt) {
    signals.push("requirements.txt");
    packageManager = "pip";
    language = "python";
  } else if (hasCargoToml) {
    signals.push("Cargo.toml");
    packageManager = "cargo";
    language = "rust";
  } else if (hasGoMod) {
    signals.push("go.mod");
    packageManager = "go";
    language = "go";
  } else if (hasGemfile) {
    signals.push("Gemfile");
    packageManager = "bundler";
    language = "ruby";
  }

  const monorepo = await detectMonorepo(repoPath, packageManager, hasPackageJson);

  return { language, packageManager, monorepo, signals };
}

async function detectMonorepo(
  repoPath: string,
  packageManager: PackageManager,
  hasPackageJson: boolean,
): Promise<MonorepoInfo> {
  if (!hasPackageJson) {
    return { isMonorepo: false, packageCount: 0, packagePaths: [] };
  }

  let workspaceGlobs: string[] = [];

  if (packageManager === "pnpm") {
    const pnpmWorkspacePath = path.join(repoPath, "pnpm-workspace.yaml");
    if (await fileExists(pnpmWorkspacePath)) {
      const raw = await fs.readFile(pnpmWorkspacePath, "utf-8");
      workspaceGlobs = parseSimpleYamlList(raw);
    }
  }

  if (workspaceGlobs.length === 0) {
    const packageJsonPath = path.join(repoPath, "package.json");
    try {
      const raw = await fs.readFile(packageJsonPath, "utf-8");
      const parsed = JSON.parse(raw) as PackageJsonShape;
      if (Array.isArray(parsed.workspaces)) {
        workspaceGlobs = parsed.workspaces;
      } else if (parsed.workspaces?.packages) {
        workspaceGlobs = parsed.workspaces.packages;
      }
    } catch {
      // Malformed package.json -- treat as no workspace info rather than throw.
    }
  }

  if (workspaceGlobs.length === 0) {
    return { isMonorepo: false, packageCount: 0, packagePaths: [] };
  }

  const packagePaths = await resolveWorkspacePackages(repoPath, workspaceGlobs);
  return {
    isMonorepo: packagePaths.length > 0,
    packageCount: packagePaths.length,
    packagePaths,
  };
}

/**
 * Minimal glob resolution for the common `dir/*` workspace pattern plus exact
 * directory entries. This intentionally does not pull in a glob dependency --
 * v0.1's monorepo detection covers the overwhelmingly common shapes
 * (`packages/*`, `apps/*`, explicit paths) without adding a runtime dep.
 */
async function resolveWorkspacePackages(repoPath: string, globs: string[]): Promise<string[]> {
  const resolved = new Set<string>();

  for (const glob of globs) {
    if (glob.startsWith("!")) {
      continue; // negation patterns -- not supported in v0.1, skip rather than mis-include.
    }
    if (glob.endsWith("/*")) {
      const baseDir = glob.slice(0, -2);
      const absoluteBase = path.join(repoPath, baseDir);
      const entries = await listDir(absoluteBase);
      for (const entry of entries) {
        const candidate = path.join(absoluteBase, entry);
        if (await fileExists(path.join(candidate, "package.json"))) {
          resolved.add(path.relative(repoPath, candidate));
        }
      }
    } else {
      const absolute = path.join(repoPath, glob);
      if (await fileExists(path.join(absolute, "package.json"))) {
        resolved.add(path.relative(repoPath, absolute));
      }
    }
  }

  return Array.from(resolved).sort();
}

/** Extremely small YAML list parser, just for pnpm-workspace.yaml's `packages:` block. */
function parseSimpleYamlList(raw: string): string[] {
  const lines = raw.split("\n");
  const items: string[] = [];
  let inPackagesBlock = false;
  for (const line of lines) {
    if (/^packages\s*:/.test(line.trim())) {
      inPackagesBlock = true;
      continue;
    }
    if (inPackagesBlock) {
      const match = line.match(/^\s*-\s*['"]?([^'"#]+)['"]?/);
      if (match?.[1]) {
        items.push(match[1].trim());
      } else if (line.trim().length > 0 && !line.startsWith(" ") && !line.startsWith("-")) {
        break; // dedented past the packages block
      }
    }
  }
  return items;
}
