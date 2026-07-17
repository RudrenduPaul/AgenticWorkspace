"""
Session handoff file writing/listing. Ported from
src/agenticworkspace/scaffold/handoff-generator.ts.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from ..util.fs_utils import ensure_dir, list_dir, path_exists, write_text
from ..util.git_info import get_current_branch, get_current_commit


def handoff_dir(workspace_dir: str) -> str:
    return os.path.join(workspace_dir, "handoff")


@dataclass
class HandoffMetadata:
    timestamp: str
    branch: Optional[str]
    commit: Optional[str]


@dataclass
class WrittenHandoff:
    file_name: str
    file_path: str
    message: str
    metadata: HandoffMetadata


def _timestamp_slug(date: datetime) -> str:
    return (
        f"{date.year:04d}-{date.month:02d}-{date.day:02d}-"
        f"{date.hour:02d}{date.minute:02d}"
    )


def write_handoff(
    workspace_dir: str,
    repo_path: str,
    message: str,
    now: Optional[datetime] = None,
) -> WrittenHandoff:
    """
    Write a new timestamped handoff file into .workspace/handoff/. If a file
    for the same minute already exists (two handoffs written within the same
    60-second window), a numeric suffix is appended so nothing is
    overwritten.
    """
    moment = now or datetime.now(timezone.utc)
    directory = handoff_dir(workspace_dir)
    ensure_dir(directory)

    branch = get_current_branch(repo_path)
    commit = get_current_commit(repo_path)
    metadata = HandoffMetadata(
        timestamp=moment.isoformat().replace("+00:00", "Z"),
        branch=branch,
        commit=commit,
    )

    base_slug = _timestamp_slug(moment)
    file_name = f"{base_slug}.md"
    counter = 2
    while path_exists(os.path.join(directory, file_name)):
        file_name = f"{base_slug}-{counter}.md"
        counter += 1

    file_path = os.path.join(directory, file_name)
    content = _build_handoff_content(message, metadata)
    write_text(file_path, content)

    return WrittenHandoff(file_name=file_name, file_path=file_path, message=message, metadata=metadata)


def _build_handoff_content(message: str, metadata: HandoffMetadata) -> str:
    branch_line = metadata.branch or "unknown (not a git repo, or git unavailable)"
    commit_line = metadata.commit or "unknown"
    return f"""# Session Handoff

- Timestamp: {metadata.timestamp}
- Branch: {branch_line}
- Commit: {commit_line}

## Notes

{message}
"""


@dataclass
class HandoffSummary:
    files: List[str]
    count: int
    most_recent: Optional[str]


def list_handoffs(workspace_dir: str) -> HandoffSummary:
    """List handoff files, newest first (filenames sort lexicographically = chronologically here)."""
    directory = handoff_dir(workspace_dir)
    entries = list_dir(directory)
    md_files = sorted((entry for entry in entries if entry.endswith(".md")), reverse=True)
    return HandoffSummary(files=md_files, count=len(md_files), most_recent=md_files[0] if md_files else None)


def ensure_handoff_dir_exists(workspace_dir: str) -> None:
    ensure_dir(handoff_dir(workspace_dir))


def read_handoff_file(workspace_dir: str, file_name: str) -> str:
    """Re-exported for tests that need to assert directory contents directly."""
    with open(os.path.join(handoff_dir(workspace_dir), file_name), "r", encoding="utf-8") as handle:
        return handle.read()
