from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """A minimal JS/npm repo fixture: package.json + package-lock.json."""
    (tmp_path / "package.json").write_text(json.dumps({"name": "fixture", "version": "1.0.0"}))
    (tmp_path / "package-lock.json").write_text("{}")
    return tmp_path


@pytest.fixture
def empty_repo(tmp_path: Path) -> Path:
    """A directory with no stack signals at all."""
    return tmp_path
