"""
Progressive root context + per-module capability block generation. Ported
from src/agenticworkspace/scaffold/context-generator.ts.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List

from ..scan.stack_detector import StackDetectionResult
from ..util.fs_utils import byte_length, dir_exists, list_dir, write_text

# Root context budget (~12KB, progressive loading, not a whole-repo dump).
ROOT_CONTEXT_BUDGET_BYTES = 12 * 1024

_IGNORED_DIRS = {
    "node_modules",
    ".git",
    ".workspace",
    ".github",
    "dist",
    "build",
    "coverage",
    "test",
    "tests",
    "__tests__",
    "vendor",
    ".venv",
    "venv",
    "target",
    ".next",
    ".cache",
}

_MAX_MODULES = 8


@dataclass
class ModuleCandidate:
    # Sanitizable module name -- always derived from a real directory basename, lowercased and slug-safe.
    name: str
    # Path relative to the repo root.
    relative_path: str


def detect_module_candidates(repo_path: str, stack: StackDetectionResult) -> List[ModuleCandidate]:
    """
    Determine per-module capability blocks. For a monorepo, one module per
    workspace package. Otherwise, one module per top-level source directory
    (src/* if present, else repo root subdirectories), excluding common
    non-source directories. This is real filesystem-derived detection, never
    an invented/hardcoded module list.
    """
    if stack.monorepo.is_monorepo and len(stack.monorepo.package_paths) > 0:
        return [
            ModuleCandidate(name=_slugify(os.path.basename(relative_path)), relative_path=relative_path)
            for relative_path in stack.monorepo.package_paths[:_MAX_MODULES]
        ]

    src_dir = os.path.join(repo_path, "src")
    has_src = dir_exists(src_dir)
    scan_root = src_dir if has_src else repo_path
    scan_root_relative = "src" if has_src else "."

    entries = list_dir(scan_root)
    candidates: List[ModuleCandidate] = []

    for entry in sorted(entries):
        if entry.startswith(".") or entry in _IGNORED_DIRS:
            continue
        absolute = os.path.join(scan_root, entry)
        if dir_exists(absolute):
            relative_path = entry if scan_root_relative == "." else os.path.join(scan_root_relative, entry)
            candidates.append(ModuleCandidate(name=_slugify(entry), relative_path=relative_path))
        if len(candidates) >= _MAX_MODULES:
            break

    return candidates


_SLUG_INVALID_RE = re.compile(r"[^a-z0-9_-]+")
_SLUG_TRIM_RE = re.compile(r"^-+|-+$")


def _slugify(name: str) -> str:
    lowered = name.lower()
    replaced = _SLUG_INVALID_RE.sub("-", lowered)
    trimmed = _SLUG_TRIM_RE.sub("", replaced)
    return trimmed or "module"


@dataclass
class GeneratedContext:
    root_context_path: str
    root_context_bytes: int
    budget_bytes: int
    module_paths: List[str] = field(default_factory=list)
    module_names: List[str] = field(default_factory=list)


def generate_context(
    workspace_dir: str,
    repo_path: str,
    repo_name: str,
    stack: StackDetectionResult,
    modules: List[ModuleCandidate],
) -> GeneratedContext:
    """
    Write root-context.md plus one file per detected module under
    .workspace/context/, respecting the root-context byte budget. If the
    generated root context would exceed budget, module summaries are
    trimmed (listed by name only, without descriptions) until it fits.
    """
    context_dir = os.path.join(workspace_dir, "context")
    modules_dir = os.path.join(context_dir, "modules")
    root_context_path = os.path.join(context_dir, "root-context.md")

    module_paths: List[str] = []
    for module in modules:
        module_path = os.path.join(modules_dir, f"{module.name}.md")
        content = _build_module_content(module)
        write_text(module_path, content)
        module_paths.append(module_path)

    root_content = _build_root_context(repo_name, stack, modules, True)
    if byte_length(root_content) > ROOT_CONTEXT_BUDGET_BYTES:
        root_content = _build_root_context(repo_name, stack, modules, False)

    write_text(root_context_path, root_content)

    return GeneratedContext(
        root_context_path=root_context_path,
        root_context_bytes=byte_length(root_content),
        budget_bytes=ROOT_CONTEXT_BUDGET_BYTES,
        module_paths=module_paths,
        module_names=[module.name for module in modules],
    )


def _build_root_context(
    repo_name: str,
    stack: StackDetectionResult,
    modules: List[ModuleCandidate],
    with_descriptions: bool,
) -> str:
    module_lines: List[str] = []
    for module in modules:
        if with_descriptions:
            module_lines.append(
                f"- **{module.name}** (`{module.relative_path}`) -- see "
                f"`.workspace/context/modules/{module.name}.md` for details, loaded on demand."
            )
        else:
            module_lines.append(f"- {module.name}")

    monorepo_line = (
        f"yes, {stack.monorepo.package_count} packages" if stack.monorepo.is_monorepo else "no"
    )
    modules_section = (
        "\n".join(module_lines)
        if module_lines
        else "No modules detected yet. Re-run `agenticworkspace init` after adding source directories."
    )

    return f"""# Root Context -- {repo_name}

Generated by AgenticWorkspace. This file is loaded at the start of every
Claude Code session in this repo. It stays small on purpose: detail lives in
per-module files under `.workspace/context/modules/`, loaded on demand
instead of all at once.

## Stack

- Language: {stack.language}
- Package manager: {stack.package_manager}
- Monorepo: {monorepo_line}

## Modules

{modules_section}

## Session handoff

Check `.workspace/handoff/` for the most recent session's notes before
starting new work. Run `agenticworkspace status --json` for a machine-readable
snapshot of workspace health.
"""


def _build_module_content(module: ModuleCandidate) -> str:
    return f"""# Module: {module.name}

Path: `{module.relative_path}`

This is a per-module capability block, loaded on demand rather than always
included in the root context. Extend this file with what a session working
in `{module.relative_path}` actually needs to know: key entry points,
conventions specific to this module, and anything that would otherwise need
rediscovering every session.
"""
