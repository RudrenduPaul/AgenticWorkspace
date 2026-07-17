"""
Stack and package-manager detection. Real filesystem checks, no network
calls. Covers, at minimum, npm/pnpm/yarn + TypeScript/JavaScript, plus Python
(pip/poetry), with lighter-weight signals for cargo, go modules, and
bundler/Gemfile. Ported from src/agenticworkspace/scan/stack-detector.ts.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import List, Set

from ..util.fs_utils import file_exists, list_dir

PackageManager = str  # "npm" | "pnpm" | "yarn" | "pip" | "poetry" | "cargo" | "go" | "bundler" | "unknown"
PrimaryLanguage = str  # "typescript" | "javascript" | "python" | "rust" | "go" | "ruby" | "unknown"


@dataclass
class MonorepoInfo:
    is_monorepo: bool
    package_count: int
    package_paths: List[str]


@dataclass
class StackDetectionResult:
    language: PrimaryLanguage
    package_manager: PackageManager
    monorepo: MonorepoInfo
    # Raw signals found, for status/debug output -- e.g. ["package-lock.json", "tsconfig.json"].
    signals: List[str] = field(default_factory=list)


def detect_stack(repo_path: str) -> StackDetectionResult:
    signals: List[str] = []

    has_package_json = file_exists(os.path.join(repo_path, "package.json"))
    has_package_lock = file_exists(os.path.join(repo_path, "package-lock.json"))
    has_pnpm_lock = file_exists(os.path.join(repo_path, "pnpm-lock.yaml"))
    has_yarn_lock = file_exists(os.path.join(repo_path, "yarn.lock"))
    has_pnpm_workspace_yaml = file_exists(os.path.join(repo_path, "pnpm-workspace.yaml"))
    has_tsconfig = file_exists(os.path.join(repo_path, "tsconfig.json"))
    has_requirements_txt = file_exists(os.path.join(repo_path, "requirements.txt"))
    has_pyproject_toml = file_exists(os.path.join(repo_path, "pyproject.toml"))
    has_pipfile = file_exists(os.path.join(repo_path, "Pipfile"))
    has_cargo_toml = file_exists(os.path.join(repo_path, "Cargo.toml"))
    has_go_mod = file_exists(os.path.join(repo_path, "go.mod"))
    has_gemfile = file_exists(os.path.join(repo_path, "Gemfile"))

    package_manager: PackageManager = "unknown"
    language: PrimaryLanguage = "unknown"

    if has_package_json:
        signals.append("package.json")
        if has_pnpm_lock or has_pnpm_workspace_yaml:
            package_manager = "pnpm"
            signals.append("pnpm-lock.yaml" if has_pnpm_lock else "pnpm-workspace.yaml")
        elif has_yarn_lock:
            package_manager = "yarn"
            signals.append("yarn.lock")
        elif has_package_lock:
            package_manager = "npm"
            signals.append("package-lock.json")
        else:
            # package.json present with no lockfile detected yet -- default to npm,
            # the ecosystem default, rather than leaving it unknown.
            package_manager = "npm"

        if has_tsconfig:
            language = "typescript"
            signals.append("tsconfig.json")
        else:
            language = "javascript"
    elif has_pyproject_toml:
        signals.append("pyproject.toml")
        package_manager = "poetry"
        language = "python"
    elif has_pipfile:
        signals.append("Pipfile")
        package_manager = "pip"
        language = "python"
    elif has_requirements_txt:
        signals.append("requirements.txt")
        package_manager = "pip"
        language = "python"
    elif has_cargo_toml:
        signals.append("Cargo.toml")
        package_manager = "cargo"
        language = "rust"
    elif has_go_mod:
        signals.append("go.mod")
        package_manager = "go"
        language = "go"
    elif has_gemfile:
        signals.append("Gemfile")
        package_manager = "bundler"
        language = "ruby"

    monorepo = _detect_monorepo(repo_path, package_manager, has_package_json)

    return StackDetectionResult(language=language, package_manager=package_manager, monorepo=monorepo, signals=signals)


def _detect_monorepo(repo_path: str, package_manager: PackageManager, has_package_json: bool) -> MonorepoInfo:
    if not has_package_json:
        return MonorepoInfo(is_monorepo=False, package_count=0, package_paths=[])

    workspace_globs: List[str] = []

    if package_manager == "pnpm":
        pnpm_workspace_path = os.path.join(repo_path, "pnpm-workspace.yaml")
        if file_exists(pnpm_workspace_path):
            with open(pnpm_workspace_path, "r", encoding="utf-8") as handle:
                raw = handle.read()
            workspace_globs = _parse_simple_yaml_list(raw)

    if len(workspace_globs) == 0:
        package_json_path = os.path.join(repo_path, "package.json")
        try:
            with open(package_json_path, "r", encoding="utf-8") as handle:
                raw = handle.read()
            parsed = json.loads(raw)
            workspaces = parsed.get("workspaces") if isinstance(parsed, dict) else None
            if isinstance(workspaces, list):
                workspace_globs = workspaces
            elif isinstance(workspaces, dict) and isinstance(workspaces.get("packages"), list):
                workspace_globs = workspaces["packages"]
        except (OSError, ValueError):
            # Malformed package.json -- treat as no workspace info rather than raise.
            pass

    if len(workspace_globs) == 0:
        return MonorepoInfo(is_monorepo=False, package_count=0, package_paths=[])

    package_paths = _resolve_workspace_packages(repo_path, workspace_globs)
    return MonorepoInfo(
        is_monorepo=len(package_paths) > 0,
        package_count=len(package_paths),
        package_paths=package_paths,
    )


def _resolve_workspace_packages(repo_path: str, globs: List[str]) -> List[str]:
    """
    Minimal glob resolution for the common `dir/*` workspace pattern plus exact
    directory entries. This intentionally does not pull in a glob dependency --
    v0.1's monorepo detection covers the overwhelmingly common shapes
    (`packages/*`, `apps/*`, explicit paths) without adding a runtime dep.
    """
    resolved: Set[str] = set()

    for glob in globs:
        if glob.startswith("!"):
            continue  # negation patterns -- not supported in v0.1, skip rather than mis-include.
        if glob.endswith("/*"):
            base_dir = glob[:-2]
            absolute_base = os.path.join(repo_path, base_dir)
            entries = list_dir(absolute_base)
            for entry in entries:
                candidate = os.path.join(absolute_base, entry)
                if file_exists(os.path.join(candidate, "package.json")):
                    _add_if_within_repo(resolved, repo_path, candidate)
        else:
            absolute = os.path.join(repo_path, glob)
            if file_exists(os.path.join(absolute, "package.json")):
                _add_if_within_repo(resolved, repo_path, absolute)

    return sorted(resolved)


def _add_if_within_repo(resolved: Set[str], repo_path: str, candidate: str) -> None:
    """
    The scanned repo's own package.json/pnpm-workspace.yaml declares these
    workspace globs, so a malicious or untrusted repo (this tool's whole
    purpose is onboarding arbitrary repos) could declare a glob like
    "../sibling-project" to make AgenticWorkspace resolve and reference a path
    outside the repo it was asked to scan. Confine every resolved candidate to
    repo_path; drop anything that escapes it rather than silently including it.
    """
    relative = os.path.relpath(candidate, repo_path)
    if relative.startswith("..") or os.path.isabs(relative):
        return
    resolved.add(relative)


_PACKAGES_KEY_RE = re.compile(r"^packages\s*:")
_YAML_LIST_ITEM_RE = re.compile(r"^\s*-\s*['\"]?([^'\"#]+)['\"]?")


def _parse_simple_yaml_list(raw: str) -> List[str]:
    """Extremely small YAML list parser, just for pnpm-workspace.yaml's `packages:` block."""
    lines = raw.split("\n")
    items: List[str] = []
    in_packages_block = False
    for line in lines:
        if _PACKAGES_KEY_RE.match(line.strip()):
            in_packages_block = True
            continue
        if in_packages_block:
            match = _YAML_LIST_ITEM_RE.match(line)
            if match and match.group(1):
                items.append(match.group(1).strip())
            elif len(line.strip()) > 0 and not line.startswith(" ") and not line.startswith("-"):
                break  # dedented past the packages block
    return items
