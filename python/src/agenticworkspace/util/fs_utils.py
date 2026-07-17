"""
Small filesystem helpers shared across the package. Ported from
src/agenticworkspace/util/fs-utils.ts. The TypeScript original is async
(node:fs/promises); this port uses plain synchronous stdlib calls, which is
the idiomatic choice for a CLI-shaped Python tool and keeps every call site a
direct one-to-one match with its TS counterpart minus the await keyword.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, List, Optional, TypeVar

T = TypeVar("T")


def dir_exists(target_path: str) -> bool:
    """True if the given path exists and is a directory. Never raises."""
    try:
        return Path(target_path).is_dir()
    except OSError:
        return False


def file_exists(target_path: str) -> bool:
    """True if the given path exists and is a regular file. Never raises."""
    try:
        return Path(target_path).is_file()
    except OSError:
        return False


def path_exists(target_path: str) -> bool:
    """True if the given path exists at all (file, directory, or otherwise)."""
    try:
        return Path(target_path).exists() or Path(target_path).is_symlink()
    except OSError:
        return False


def ensure_dir(target_path: str) -> None:
    """mkdir -p, wrapped for readability at call sites."""
    os.makedirs(target_path, exist_ok=True)


def read_json_if_exists(target_path: str) -> Optional[Any]:
    """Read a JSON file and parse it. Returns None if the file does not exist."""
    if not file_exists(target_path):
        return None
    with open(target_path, "r", encoding="utf-8") as handle:
        raw = handle.read()
    return json.loads(raw)


def write_json(target_path: str, value: Any) -> None:
    """Write a value as pretty-printed JSON, creating parent directories first."""
    ensure_dir(str(Path(target_path).parent))
    with open(target_path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(value, indent=2))
        handle.write("\n")


def write_text(target_path: str, content: str) -> None:
    """Write a text file, creating parent directories first."""
    ensure_dir(str(Path(target_path).parent))
    with open(target_path, "w", encoding="utf-8") as handle:
        handle.write(content)


def byte_length(content: str) -> int:
    """Byte length of a UTF-8 string, used for the context size budget."""
    return len(content.encode("utf-8"))


def list_dir(target_path: str) -> List[str]:
    """List entries directly inside a directory, or an empty list if it does not exist."""
    try:
        return os.listdir(target_path)
    except OSError:
        return []


def remove_dir(target_path: str) -> None:
    """Remove a directory and everything in it. No-op if it does not exist."""
    shutil.rmtree(target_path, ignore_errors=True)
