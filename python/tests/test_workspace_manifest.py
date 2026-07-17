from __future__ import annotations

from pathlib import Path

from agenticworkspace.scaffold.workspace_manifest import (
    REQUIRED_MANIFEST_KEYS,
    is_manifest_shape_valid,
    read_manifest,
    write_manifest,
)

_VALID_MANIFEST = {
    "manifestSchemaVersion": "1",
    "agenticworkspaceVersion": "0.1.0",
    "createdAt": "2026-01-01T00:00:00Z",
    "lastScanAt": "2026-01-01T00:00:00Z",
    "stack": {"language": "javascript", "packageManager": "npm", "packages": 1},
    "existingConfig": {},
    "memoryBackends": [],
    "context": {"rootContextKb": 0.5, "modules": []},
    "adapters": {},
}


def test_valid_manifest_shape_passes() -> None:
    assert is_manifest_shape_valid(_VALID_MANIFEST) is True


def test_missing_key_fails_shape_check() -> None:
    incomplete = dict(_VALID_MANIFEST)
    del incomplete["adapters"]
    assert is_manifest_shape_valid(incomplete) is False


def test_non_dict_fails_shape_check() -> None:
    assert is_manifest_shape_valid(None) is False
    assert is_manifest_shape_valid("not a manifest") is False
    assert is_manifest_shape_valid(["a", "list"]) is False


def test_required_keys_list_is_stable() -> None:
    assert set(REQUIRED_MANIFEST_KEYS) == set(_VALID_MANIFEST.keys())


def test_write_then_read_manifest_round_trips(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".workspace"
    write_manifest(str(workspace_dir), _VALID_MANIFEST)

    read_back = read_manifest(str(workspace_dir))
    assert read_back == _VALID_MANIFEST


def test_read_manifest_returns_none_when_absent(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".workspace"
    assert read_manifest(str(workspace_dir)) is None
