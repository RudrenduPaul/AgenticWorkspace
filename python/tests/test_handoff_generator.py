from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from agenticworkspace.scaffold.handoff_generator import (
    ensure_handoff_dir_exists,
    list_handoffs,
    read_handoff_file,
    write_handoff,
)


def test_write_handoff_creates_timestamped_file(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".workspace"
    now = datetime(2026, 7, 13, 14, 21, tzinfo=timezone.utc)

    written = write_handoff(str(workspace_dir), str(tmp_path), "did some work", now=now)

    assert written.file_name == "2026-07-13-1421.md"
    content = read_handoff_file(str(workspace_dir), written.file_name)
    assert "did some work" in content
    assert "2026-07-13T14:21:00" in content


def test_write_handoff_appends_numeric_suffix_on_collision(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".workspace"
    now = datetime(2026, 7, 13, 14, 21, tzinfo=timezone.utc)

    first = write_handoff(str(workspace_dir), str(tmp_path), "first", now=now)
    second = write_handoff(str(workspace_dir), str(tmp_path), "second", now=now)
    third = write_handoff(str(workspace_dir), str(tmp_path), "third", now=now)

    assert first.file_name == "2026-07-13-1421.md"
    assert second.file_name == "2026-07-13-1421-2.md"
    assert third.file_name == "2026-07-13-1421-3.md"


def test_write_handoff_records_no_git_info_outside_a_repo(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".workspace"
    written = write_handoff(str(workspace_dir), str(tmp_path), "no git here")
    assert written.metadata.branch is None
    assert written.metadata.commit is None


def test_list_handoffs_returns_newest_first(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".workspace"
    write_handoff(str(workspace_dir), str(tmp_path), "one", now=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc))
    write_handoff(str(workspace_dir), str(tmp_path), "two", now=datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc))

    summary = list_handoffs(str(workspace_dir))
    assert summary.count == 2
    assert summary.most_recent == "2026-01-02-0000.md"
    assert summary.files[0] == "2026-01-02-0000.md"


def test_list_handoffs_empty_when_no_dir(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".workspace"
    summary = list_handoffs(str(workspace_dir))
    assert summary.count == 0
    assert summary.most_recent is None
    assert summary.files == []


def test_ensure_handoff_dir_exists_creates_empty_dir(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".workspace"
    ensure_handoff_dir_exists(str(workspace_dir))
    assert (workspace_dir / "handoff").is_dir()
