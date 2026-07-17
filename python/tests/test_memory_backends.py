from __future__ import annotations

from pathlib import Path

from agenticworkspace.memory_backends.gitnexus import git_nexus_backend
from agenticworkspace.memory_backends.registry import (
    any_backend_detected,
    detect_all_memory_backends,
    memory_backend_registry,
)
from agenticworkspace.memory_backends.repo_harness import repo_harness_backend
from agenticworkspace.memory_backends.serena import serena_backend
from agenticworkspace.memory_backends.types import MemoryBackend


def test_registry_has_three_backends() -> None:
    names = {backend.name for backend in memory_backend_registry}
    assert names == {"serena", "gitnexus", "repo-harness"}


def test_serena_detects_dot_serena_dir(tmp_path: Path) -> None:
    assert serena_backend.detect(str(tmp_path)) is False
    (tmp_path / ".serena").mkdir()
    assert serena_backend.detect(str(tmp_path)) is True


def test_gitnexus_detects_dir_or_config_file(tmp_path: Path) -> None:
    assert git_nexus_backend.detect(str(tmp_path)) is False
    (tmp_path / "gitnexus.config.json").write_text("{}")
    assert git_nexus_backend.detect(str(tmp_path)) is True


def test_gitnexus_detects_dot_gitnexus_dir(tmp_path: Path) -> None:
    (tmp_path / ".gitnexus").mkdir()
    assert git_nexus_backend.detect(str(tmp_path)) is True


def test_repo_harness_detects_ai_harness_dir(tmp_path: Path) -> None:
    assert repo_harness_backend.detect(str(tmp_path)) is False
    (tmp_path / ".ai" / "harness").mkdir(parents=True)
    assert repo_harness_backend.detect(str(tmp_path)) is True


def test_detect_all_returns_not_detected_for_clean_repo(empty_repo: Path) -> None:
    results = detect_all_memory_backends(str(empty_repo))
    assert len(results) == 3
    assert all(result.detected is False for result in results)
    assert any_backend_detected(results) is False


def test_detect_all_reports_detected_backend(tmp_path: Path) -> None:
    (tmp_path / ".serena").mkdir()
    results = detect_all_memory_backends(str(tmp_path))
    serena_result = next(r for r in results if r.name == "serena")
    assert serena_result.detected is True
    assert any_backend_detected(results) is True


def test_one_backend_raising_does_not_abort_the_others(tmp_path: Path) -> None:
    """
    A custom backend's detect() failure must be caught and reported as
    not-detected, without aborting detection of the other registered
    backends -- mirrors detectAllMemoryBackends' try/catch in the TS
    original.
    """

    class ExplodingBackend(MemoryBackend):
        name = "exploding"

        def detect(self, repo_path: str) -> bool:
            raise RuntimeError("boom")

        def describe(self) -> str:
            return "deliberately broken backend for testing"

    custom_registry = [serena_backend, ExplodingBackend()]
    results = detect_all_memory_backends(str(tmp_path), registry=custom_registry)

    assert len(results) == 2
    exploding_result = next(r for r in results if r.name == "exploding")
    assert exploding_result.detected is False
    serena_result = next(r for r in results if r.name == "serena")
    assert serena_result.detected is False
