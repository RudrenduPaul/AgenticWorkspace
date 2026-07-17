from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from agenticworkspace.adapters.claude_code.install import (
    CLAUDE_CODE_HOOK_SCHEMA_VERSION,
    claude_code_adapter,
    get_installed_hook_schema_version,
)
from agenticworkspace.adapters.codex import codex_adapter
from agenticworkspace.adapters.cursor import cursor_adapter
from agenticworkspace.adapters.registry import adapter_registry, get_adapter
from agenticworkspace.adapters.types import AdapterInstallOptions


def test_registry_has_three_adapters() -> None:
    names = {a.name for a in adapter_registry}
    assert names == {"claude-code", "codex", "cursor"}


def test_get_adapter_by_name() -> None:
    assert get_adapter("claude-code") is claude_code_adapter
    assert get_adapter("nonexistent") is None


class TestClaudeCodeAdapter:
    def test_is_implemented(self) -> None:
        assert claude_code_adapter.is_implemented is True

    def test_not_installed_initially(self, tmp_path: Path) -> None:
        workspace_dir = tmp_path / ".workspace"
        assert claude_code_adapter.is_installed(str(workspace_dir)) is False

    def test_install_writes_settings_and_hooks(self, tmp_path: Path) -> None:
        workspace_dir = tmp_path / ".workspace"
        claude_code_adapter.install(
            str(workspace_dir), AdapterInstallOptions(repo_path=str(tmp_path), module_names=["auth", "api"])
        )

        assert claude_code_adapter.is_installed(str(workspace_dir)) is True

        adapter_dir = workspace_dir / "adapters" / "claude-code"
        assert (adapter_dir / "settings.json").exists()
        assert (adapter_dir / "adapter-meta.json").exists()

        for script_name in ("session-start.sh", "pre-tool-call.sh", "session-end-handoff.sh"):
            script_path = adapter_dir / "hooks" / script_name
            assert script_path.exists()
            mode = script_path.stat().st_mode
            assert mode & stat.S_IXUSR  # executable bit set (chmod 755)

        session_start = (adapter_dir / "hooks" / "session-start.sh").read_text()
        assert "'auth'" in session_start
        assert "'api'" in session_start

    def test_install_rejects_unsafe_module_names_but_continues(self, tmp_path: Path) -> None:
        workspace_dir = tmp_path / ".workspace"
        claude_code_adapter.install(
            str(workspace_dir),
            AdapterInstallOptions(repo_path=str(tmp_path), module_names=["good", "$(evil)"]),
        )
        session_start = (workspace_dir / "adapters" / "claude-code" / "hooks" / "session-start.sh").read_text()
        assert "'good'" in session_start
        assert "evil" not in session_start

    def test_check_stale_false_for_freshly_installed(self, tmp_path: Path) -> None:
        workspace_dir = tmp_path / ".workspace"
        claude_code_adapter.install(str(workspace_dir), AdapterInstallOptions(repo_path=str(tmp_path)))
        assert claude_code_adapter.check_stale(str(workspace_dir)) is False

    def test_check_stale_false_when_never_installed(self, tmp_path: Path) -> None:
        workspace_dir = tmp_path / ".workspace"
        assert claude_code_adapter.check_stale(str(workspace_dir)) is False

    def test_get_installed_hook_schema_version(self, tmp_path: Path) -> None:
        workspace_dir = tmp_path / ".workspace"
        assert get_installed_hook_schema_version(str(workspace_dir)) is None
        claude_code_adapter.install(str(workspace_dir), AdapterInstallOptions(repo_path=str(tmp_path)))
        assert get_installed_hook_schema_version(str(workspace_dir)) == CLAUDE_CODE_HOOK_SCHEMA_VERSION


@pytest.mark.parametrize("adapter", [codex_adapter, cursor_adapter])
class TestStubAdapters:
    def test_not_implemented(self, adapter) -> None:
        assert adapter.is_implemented is False

    def test_is_installed_always_false(self, adapter, tmp_path: Path) -> None:
        assert adapter.is_installed(str(tmp_path)) is False

    def test_install_raises(self, adapter, tmp_path: Path) -> None:
        with pytest.raises(NotImplementedError, match="not yet implemented"):
            adapter.install(str(tmp_path), AdapterInstallOptions(repo_path=str(tmp_path)))

    def test_check_stale_always_false(self, adapter, tmp_path: Path) -> None:
        assert adapter.check_stale(str(tmp_path)) is False
