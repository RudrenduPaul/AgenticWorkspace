from __future__ import annotations

import json
from pathlib import Path

from agenticworkspace.state.partial_state import (
    detect_partial_state,
    remove_in_progress_marker,
    reset_workspace,
    write_in_progress_marker,
)


def test_none_when_workspace_dir_absent(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".workspace"
    report = detect_partial_state(str(workspace_dir))
    assert report.type == "none"
    assert report.workspace_dir_exists is False


def test_missing_manifest_when_dir_exists_but_no_manifest(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".workspace"
    workspace_dir.mkdir()
    report = detect_partial_state(str(workspace_dir))
    assert report.type == "missing-manifest"


def test_interrupted_init_when_marker_present_no_manifest(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".workspace"
    workspace_dir.mkdir()
    write_in_progress_marker(str(workspace_dir))
    report = detect_partial_state(str(workspace_dir))
    assert report.type == "interrupted-init"
    assert report.marker_present is True


def test_malformed_manifest_missing_keys(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".workspace"
    workspace_dir.mkdir()
    (workspace_dir / "workspace.json").write_text(json.dumps({"someUnexpectedShape": True}))

    report = detect_partial_state(str(workspace_dir))
    assert report.type == "malformed-manifest"
    assert len(report.missing_keys) > 0


def test_interrupted_init_when_marker_present_even_with_valid_manifest(tmp_path: Path) -> None:
    from agenticworkspace.scaffold.workspace_manifest import write_manifest

    workspace_dir = tmp_path / ".workspace"
    workspace_dir.mkdir()
    write_manifest(
        str(workspace_dir),
        {
            "manifestSchemaVersion": "1",
            "agenticworkspaceVersion": "0.1.0",
            "createdAt": "x",
            "lastScanAt": "x",
            "stack": {},
            "existingConfig": {},
            "memoryBackends": [],
            "context": {},
            "adapters": {},
        },
    )
    write_in_progress_marker(str(workspace_dir))

    report = detect_partial_state(str(workspace_dir))
    assert report.type == "interrupted-init"


def test_complete_for_fully_valid_workspace(tmp_path: Path) -> None:
    from agenticworkspace.scaffold.init_engine import run_init_engine

    workspace_dir = tmp_path / ".workspace"
    run_init_engine(str(tmp_path), str(workspace_dir))

    report = detect_partial_state(str(workspace_dir))
    assert report.type == "complete"
    assert report.manifest_valid is True


def test_remove_in_progress_marker_is_a_noop_when_absent(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".workspace"
    workspace_dir.mkdir()
    remove_in_progress_marker(str(workspace_dir))  # must not raise


def test_reset_workspace_removes_directory_entirely(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".workspace"
    (workspace_dir / "handoff").mkdir(parents=True)
    (workspace_dir / "handoff" / "note.md").write_text("x")

    reset_workspace(str(workspace_dir))
    assert not workspace_dir.exists()


def test_reset_workspace_is_a_noop_when_absent(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".workspace"
    reset_workspace(str(workspace_dir))  # must not raise
