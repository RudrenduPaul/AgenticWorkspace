"""
Inspect an existing .workspace/ directory (if any) and classify its state.
Never mutates anything -- pure detection, so callers can decide what to do
(repair / reset / abort) with the answer. Ported from
src/agenticworkspace/state/partial-state.ts.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List

from ..scaffold.workspace_manifest import REQUIRED_MANIFEST_KEYS, is_manifest_shape_valid, manifest_path
from ..util.fs_utils import dir_exists, file_exists, read_json_if_exists, remove_dir, write_text

INIT_IN_PROGRESS_MARKER = ".init-in-progress"

# "none" | "complete" | "interrupted-init" | "missing-manifest" | "malformed-manifest"
PartialStateType = str


@dataclass
class PartialStateReport:
    type: PartialStateType
    workspace_dir_exists: bool
    marker_present: bool
    manifest_present: bool
    manifest_valid: bool
    missing_keys: List[str] = field(default_factory=list)
    message: str = ""


def _marker_path(workspace_dir: str) -> str:
    return os.path.join(workspace_dir, INIT_IN_PROGRESS_MARKER)


def detect_partial_state(workspace_dir: str) -> PartialStateReport:
    workspace_dir_exists = dir_exists(workspace_dir)
    if not workspace_dir_exists:
        return PartialStateReport(
            type="none",
            workspace_dir_exists=False,
            marker_present=False,
            manifest_present=False,
            manifest_valid=False,
            missing_keys=[],
            message="No .workspace/ directory found -- this is a fresh init.",
        )

    marker_present = file_exists(_marker_path(workspace_dir))
    manifest_present = file_exists(manifest_path(workspace_dir))

    if not manifest_present:
        return PartialStateReport(
            type="interrupted-init" if marker_present else "missing-manifest",
            workspace_dir_exists=True,
            marker_present=marker_present,
            manifest_present=False,
            manifest_valid=False,
            missing_keys=list(REQUIRED_MANIFEST_KEYS),
            message=(
                ".workspace/ exists with a leftover .init-in-progress marker and no "
                "workspace.json -- a prior init run was interrupted."
                if marker_present
                else ".workspace/ exists but has no workspace.json manifest."
            ),
        )

    try:
        manifest_json = read_json_if_exists(manifest_path(workspace_dir))
    except (OSError, ValueError):
        manifest_json = None  # malformed JSON -- treated as invalid below

    manifest_valid = is_manifest_shape_valid(manifest_json)
    if manifest_valid:
        missing_keys: List[str] = []
    elif isinstance(manifest_json, dict):
        missing_keys = [key for key in REQUIRED_MANIFEST_KEYS if key not in manifest_json]
    else:
        missing_keys = list(REQUIRED_MANIFEST_KEYS)

    if marker_present or not manifest_valid:
        return PartialStateReport(
            type="interrupted-init" if marker_present else "malformed-manifest",
            workspace_dir_exists=True,
            marker_present=marker_present,
            manifest_present=True,
            manifest_valid=manifest_valid,
            missing_keys=missing_keys,
            message=(
                ".workspace/ exists with a leftover .init-in-progress marker -- a prior "
                "init run was interrupted."
                if marker_present
                else f".workspace/workspace.json is missing expected keys: {', '.join(missing_keys)}."
            ),
        )

    return PartialStateReport(
        type="complete",
        workspace_dir_exists=True,
        marker_present=False,
        manifest_present=True,
        manifest_valid=True,
        missing_keys=[],
        message=".workspace/ is complete and valid.",
    )


def write_in_progress_marker(workspace_dir: str) -> None:
    write_text(_marker_path(workspace_dir), f"{datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}\n")


def remove_in_progress_marker(workspace_dir: str) -> None:
    marker = _marker_path(workspace_dir)
    try:
        os.remove(marker)
    except FileNotFoundError:
        pass


def reset_workspace(workspace_dir: str) -> None:
    remove_dir(workspace_dir)
