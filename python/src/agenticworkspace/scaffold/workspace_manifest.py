"""
workspace.json read/write plus the shape-validation check partial-state
detection relies on. Ported from
src/agenticworkspace/scaffold/workspace-manifest.ts.

The manifest is represented as a plain dict with the same camelCase keys the
TypeScript CLI writes/reads, on purpose: both distributions can operate
against the same .workspace/ directory in the same repo, and workspace.json
is the one file both CLIs read back, so its wire shape must stay identical
across languages rather than being translated to snake_case internally.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from ..util.fs_utils import read_json_if_exists, write_json

# Bumped whenever the shape of workspace.json changes in a way partial-state
# detection must know about.
WORKSPACE_MANIFEST_SCHEMA_VERSION = "1"

WorkspaceManifest = Dict[str, Any]

# Required top-level keys a valid workspace.json must have. Used by
# partial-state detection.
REQUIRED_MANIFEST_KEYS: List[str] = [
    "manifestSchemaVersion",
    "agenticworkspaceVersion",
    "createdAt",
    "lastScanAt",
    "stack",
    "existingConfig",
    "memoryBackends",
    "context",
    "adapters",
]


def manifest_path(workspace_dir: str) -> str:
    return os.path.join(workspace_dir, "workspace.json")


def read_manifest(workspace_dir: str) -> Optional[WorkspaceManifest]:
    return read_json_if_exists(manifest_path(workspace_dir))


def write_manifest(workspace_dir: str, manifest: WorkspaceManifest) -> None:
    write_json(manifest_path(workspace_dir), manifest)


def is_manifest_shape_valid(value: Any) -> bool:
    """
    True if the given parsed value has every key a valid manifest requires.
    Does not validate value types deeply -- partial-state detection only
    needs to know "does this look like an interrupted or hand-edited
    manifest," not perform full schema validation.
    """
    if not isinstance(value, dict):
        return False
    return all(key in value for key in REQUIRED_MANIFEST_KEYS)
