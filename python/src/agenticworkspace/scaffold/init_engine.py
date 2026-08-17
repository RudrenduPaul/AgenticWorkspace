"""
Runs the full scan + scaffold + adapter-install sequence. Used for both a
fresh `init` and a `repair` of a partial workspace -- repair re-runs the same
steps, which is safe because every step here is idempotent (detection is
read-only, writes overwrite deterministically-named files). Ported from
src/agenticworkspace/scaffold/init-engine.ts.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata as _importlib_metadata

from ..adapters.claude_code.install import claude_code_adapter
from ..adapters.types import AdapterInstallOptions
from ..memory_backends.registry import MemoryBackendDetectionResult, detect_all_memory_backends
from ..scan.config_detector import ExistingConfigResult, detect_existing_config
from ..scan.stack_detector import StackDetectionResult, detect_stack
from ..state.partial_state import remove_in_progress_marker, write_in_progress_marker
from ..util.fs_utils import ensure_dir
from .context_generator import GeneratedContext, detect_module_candidates, generate_context
from .handoff_generator import ensure_handoff_dir_exists
from .workspace_manifest import (
    WORKSPACE_MANIFEST_SCHEMA_VERSION,
    WorkspaceManifest,
    read_manifest,
    write_manifest,
)


def _read_package_version() -> str:
    """
    Read the real installed version from package metadata instead of a
    hand-maintained constant. The previous hardcoded string drifted out of
    sync with pyproject.toml/PyPI on every release (found shipping "0.1.0"
    while PyPI had already published 0.1.2), silently handing every
    --version call and workspace.json manifest a stale version. This
    intentionally tracks this Python package's own release number, not the
    npm package's -- the two distributions are versioned independently, same
    as skillguard-cli's two packages. Falls back to "0.0.0" for an editable
    "pip install -e ." checkout with no installed distribution metadata.
    """
    try:
        return _importlib_metadata.version("agenticworkspace-cli")
    except _importlib_metadata.PackageNotFoundError:
        return "0.0.0"


AGENTICWORKSPACE_VERSION = _read_package_version()


@dataclass
class InitEngineResult:
    repo_path: str
    workspace_dir: str
    stack: StackDetectionResult
    existing_config: ExistingConfigResult
    memory_backends: list
    context: GeneratedContext
    adapter_hook_schema_version: str
    manifest: WorkspaceManifest


def run_init_engine(repo_path: str, workspace_dir: str) -> InitEngineResult:
    ensure_dir(workspace_dir)
    write_in_progress_marker(workspace_dir)

    try:
        existing_manifest = read_manifest(workspace_dir)

        stack = detect_stack(repo_path)
        existing_config = detect_existing_config(repo_path)
        memory_backends = detect_all_memory_backends(repo_path)
        module_candidates = detect_module_candidates(repo_path, stack)
        context = generate_context(
            workspace_dir,
            repo_path,
            os.path.basename(repo_path),
            stack,
            module_candidates,
        )

        ensure_handoff_dir_exists(workspace_dir)

        claude_code_adapter.install(
            workspace_dir,
            AdapterInstallOptions(repo_path=repo_path, module_names=context.module_names),
        )

        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        manifest: WorkspaceManifest = {
            "manifestSchemaVersion": WORKSPACE_MANIFEST_SCHEMA_VERSION,
            "agenticworkspaceVersion": AGENTICWORKSPACE_VERSION,
            "createdAt": (existing_manifest or {}).get("createdAt", now) if existing_manifest else now,
            "lastScanAt": now,
            "stack": {
                "language": stack.language,
                "packageManager": stack.package_manager,
                "packages": stack.monorepo.package_count if stack.monorepo.is_monorepo else 1,
            },
            "existingConfig": {
                "claudeMd": existing_config.claude_md,
                "agentsMd": existing_config.agents_md,
                "cursorRules": existing_config.cursor_rules,
                "copilotInstructions": existing_config.copilot_instructions,
            },
            "memoryBackends": [
                {"name": backend.name, "detected": backend.detected, "description": backend.description}
                for backend in memory_backends
            ],
            "context": {
                "rootContextKb": round((context.root_context_bytes / 1024) * 10) / 10,
                "modules": context.module_names,
            },
            "adapters": {
                claude_code_adapter.name: {
                    "installed": True,
                    "hookSchemaVersion": claude_code_adapter.hook_schema_version,
                }
            },
        }

        write_manifest(workspace_dir, manifest)

        return InitEngineResult(
            repo_path=repo_path,
            workspace_dir=workspace_dir,
            stack=stack,
            existing_config=existing_config,
            memory_backends=memory_backends,
            context=context,
            adapter_hook_schema_version=claude_code_adapter.hook_schema_version,
            manifest=manifest,
        )
    finally:
        remove_in_progress_marker(workspace_dir)
