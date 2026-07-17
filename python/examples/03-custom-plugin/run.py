#!/usr/bin/env python3
"""
03 -- custom plugin.

Demonstrates AgenticWorkspace's real extensibility contract: a MemoryBackend
and an Adapter are both small interfaces (agenticworkspace.memory_backends.
types.MemoryBackend, agenticworkspace.adapters.types.Adapter) that you
implement and register into a plain list -- memory_backend_registry /
adapter_registry -- with no change to AgenticWorkspace's own code required.

This example registers:
  1. TeamCtxBackend -- a MemoryBackend that detects a made-up ".teamctx/"
     directory (detect-only, matching the read-only contract every
     first-party backend follows).
  2. MarkerAdapter -- a minimal Adapter that writes one marker file under
     .workspace/adapters/marker/ instead of real hook scripts, just to show
     the full interface (describe/is_installed/install/check_stale) without
     the complexity of the real Claude Code adapter.

Then it runs run_init_engine() against a throwaway sample repo (one with a
real .teamctx/ directory so the custom backend actually detects something)
and shows both plugins took effect.

Run:
    python3 examples/03-custom-plugin/run.py
"""
from __future__ import annotations

import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from agenticworkspace import run_init_engine
from agenticworkspace.adapters.registry import adapter_registry
from agenticworkspace.adapters.types import Adapter, AdapterInstallOptions
from agenticworkspace.memory_backends.registry import memory_backend_registry
from agenticworkspace.memory_backends.types import MemoryBackend
from agenticworkspace.util.fs_utils import ensure_dir, write_text


class TeamCtxBackend(MemoryBackend):
    name = "team-ctx"

    def detect(self, repo_path: str) -> bool:
        # Detection must stay read-only, same contract as the three
        # first-party backends (Serena, GitNexus, repo-harness).
        return os.path.isdir(os.path.join(repo_path, ".teamctx"))

    def describe(self) -> str:
        return "Internal team context tool (.teamctx/ directory) -- example plugin"


class MarkerAdapter(Adapter):
    name = "marker"
    hook_schema_version = "example-v1"
    is_implemented = True

    def describe(self) -> str:
        return "Example adapter -- writes a single marker file, no real hooks"

    def _marker_path(self, workspace_dir: str) -> str:
        return os.path.join(workspace_dir, "adapters", self.name, "marker.txt")

    def is_installed(self, workspace_dir: str) -> bool:
        return os.path.isfile(self._marker_path(workspace_dir))

    def install(self, workspace_dir: str, opts: AdapterInstallOptions) -> None:
        marker = self._marker_path(workspace_dir)
        ensure_dir(os.path.dirname(marker))
        write_text(
            marker,
            f"installed at {datetime.now(timezone.utc).isoformat()} "
            f"for repo {opts.repo_path}\n",
        )

    def check_stale(self, workspace_dir: str) -> bool:
        return False  # example adapter has one schema version, never stale


def build_sample_repo(root: Path) -> None:
    (root / "package.json").write_text('{"name": "sample-app"}')
    (root / ".teamctx").mkdir()
    (root / ".teamctx" / "config.json").write_text("{}")


def main() -> None:
    # Register both plugins -- this is the entire extension mechanism.
    memory_backend_registry.append(TeamCtxBackend())
    adapter_registry.append(MarkerAdapter())

    tmp_dir = Path(tempfile.mkdtemp(prefix="agenticworkspace-plugin-example-"))
    try:
        build_sample_repo(tmp_dir)
        workspace_dir = tmp_dir / ".workspace"

        result = run_init_engine(str(tmp_dir), str(workspace_dir))

        team_ctx_result = next(b for b in result.memory_backends if b.name == "team-ctx")
        print(f"custom MemoryBackend 'team-ctx' detected: {team_ctx_result.detected}")
        assert team_ctx_result.detected is True, "expected the .teamctx/ fixture dir to be detected"

        marker_adapter = next(a for a in adapter_registry if a.name == "marker")
        # The custom adapter is registered but init_engine only auto-installs
        # the Claude Code adapter (same as the TypeScript original) -- install
        # a registered-but-not-auto-installed adapter explicitly, the same
        # path `agenticworkspace adapter install marker` takes.
        marker_adapter.install(str(workspace_dir), AdapterInstallOptions(repo_path=str(tmp_dir)))
        print(f"custom Adapter 'marker' installed: {marker_adapter.is_installed(str(workspace_dir))}")

        marker_content = (workspace_dir / "adapters" / "marker" / "marker.txt").read_text()
        print(f"marker file content: {marker_content.strip()}")
    finally:
        # Restore the module-level registries so this example is re-runnable
        # and doesn't leak state into anything else importing this package
        # in the same process.
        memory_backend_registry.pop()
        adapter_registry.pop()
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
