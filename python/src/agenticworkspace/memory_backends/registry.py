"""
The registry of all known MemoryBackend implementations. Adding a new
backend means writing a MemoryBackend implementation and adding it here --
nothing else in scan or CLI code needs to change. Ported from
src/agenticworkspace/memory-backends/registry.ts.

This list-based registry is the actual extension point: a third-party or
downstream project adds support for a new memory/context tool by
implementing MemoryBackend (types.py) and appending an instance to
memory_backend_registry (or passing a custom list into
detect_all_memory_backends), exactly mirroring the TypeScript original's
mechanism -- no CLI or scan code changes required either way.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .gitnexus import git_nexus_backend
from .repo_harness import repo_harness_backend
from .serena import serena_backend
from .types import MemoryBackend

memory_backend_registry: List[MemoryBackend] = [
    serena_backend,
    git_nexus_backend,
    repo_harness_backend,
]


@dataclass
class MemoryBackendDetectionResult:
    name: str
    detected: bool
    description: str


def detect_all_memory_backends(
    repo_path: str,
    registry: Optional[List[MemoryBackend]] = None,
) -> List[MemoryBackendDetectionResult]:
    """
    Run detect() across every registered backend. Detection failures in one
    backend (an unexpected filesystem error) are caught and reported as
    not-detected rather than aborting the whole scan.
    """
    backends = registry if registry is not None else memory_backend_registry
    results: List[MemoryBackendDetectionResult] = []
    for backend in backends:
        try:
            detected = backend.detect(repo_path)
        except Exception:  # noqa: BLE001 -- one backend's failure must not abort the scan
            detected = False
        results.append(
            MemoryBackendDetectionResult(name=backend.name, detected=detected, description=backend.describe())
        )
    return results


def any_backend_detected(results: List[MemoryBackendDetectionResult]) -> bool:
    """True if any registered backend was detected -- init uses this to decide whether to prompt."""
    return any(result.detected for result in results)
