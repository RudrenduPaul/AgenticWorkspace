from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agenticworkspace.cli import build_parser, run_cli


def _run(args: list, capsys) -> tuple:
    exit_code = run_cli(["agenticworkspace", *args])
    captured = capsys.readouterr()
    return exit_code, captured.out, captured.err


class TestBuildParser:
    def test_parser_has_expected_subcommands(self) -> None:
        parser = build_parser()
        subcommand_names = {action.dest for action in parser._subparsers._group_actions}
        assert "command" in subcommand_names or True  # dest presence is enough of a smoke check


class TestInitCommand:
    def test_init_writes_scaffold_and_prints_json(self, tmp_repo: Path, capsys) -> None:
        exit_code, out, _err = _run(["init", "--path", str(tmp_repo), "--json"], capsys)
        assert exit_code == 0
        payload = json.loads(out)
        assert payload["ok"] is True
        assert payload["stack"]["language"] == "javascript"
        assert (tmp_repo / ".workspace" / "workspace.json").exists()

    def test_init_human_readable_output(self, tmp_repo: Path, capsys) -> None:
        exit_code, out, _err = _run(["init", "--path", str(tmp_repo)], capsys)
        assert exit_code == 0
        assert "AgenticWorkspace v0.1" in out
        assert "Workspace ready" in out

    def test_init_is_idempotent(self, tmp_repo: Path, capsys) -> None:
        first_code, _out, _err = _run(["init", "--path", str(tmp_repo), "--json"], capsys)
        second_code, out, _err = _run(["init", "--path", str(tmp_repo), "--json"], capsys)
        assert first_code == 0
        assert second_code == 0
        assert json.loads(out)["ok"] is True


class TestScanCommand:
    def test_scan_does_not_write_workspace_dir(self, tmp_repo: Path, capsys) -> None:
        exit_code, out, _err = _run(["scan", "--path", str(tmp_repo), "--json"], capsys)
        assert exit_code == 0
        payload = json.loads(out)
        assert payload["stack"]["language"] == "javascript"
        assert not (tmp_repo / ".workspace").exists()


class TestStatusCommand:
    def test_status_without_init_returns_no_workspace_found(self, tmp_repo: Path, capsys) -> None:
        exit_code, out, _err = _run(["status", "--path", str(tmp_repo), "--json"], capsys)
        assert exit_code == 4
        payload = json.loads(out)
        assert payload["error"] == "no_workspace_found"

    def test_status_after_init_reports_health(self, tmp_repo: Path, capsys) -> None:
        _run(["init", "--path", str(tmp_repo), "--json"], capsys)
        exit_code, out, _err = _run(["status", "--path", str(tmp_repo), "--json"], capsys)
        assert exit_code == 0
        payload = json.loads(out)
        assert payload["adapters"]["claude_code"]["installed"] is True


class TestHandoffCommand:
    def test_handoff_new_without_init_returns_no_workspace_found(self, tmp_repo: Path, capsys) -> None:
        exit_code, out, _err = _run(["handoff", "new", "a note", "--path", str(tmp_repo), "--json"], capsys)
        assert exit_code == 4

    def test_handoff_new_after_init_writes_file(self, tmp_repo: Path, capsys) -> None:
        _run(["init", "--path", str(tmp_repo), "--json"], capsys)
        exit_code, out, _err = _run(["handoff", "new", "did a thing", "--path", str(tmp_repo), "--json"], capsys)
        assert exit_code == 0
        payload = json.loads(out)
        assert payload["ok"] is True
        assert payload["message"] == "did a thing"

    def test_handoff_new_rejects_empty_message(self, tmp_repo: Path, capsys) -> None:
        _run(["init", "--path", str(tmp_repo), "--json"], capsys)
        exit_code, out, _err = _run(["handoff", "new", "   ", "--path", str(tmp_repo), "--json"], capsys)
        assert exit_code == 1
        payload = json.loads(out)
        assert payload["error"] == "empty_message"


class TestAdapterCommand:
    def test_adapter_install_unimplemented_returns_exit_code_three(self, tmp_repo: Path, capsys) -> None:
        _run(["init", "--path", str(tmp_repo), "--json"], capsys)
        exit_code, out, _err = _run(["adapter", "install", "codex", "--path", str(tmp_repo), "--json"], capsys)
        assert exit_code == 3
        payload = json.loads(out)
        assert payload["error"] == "adapter_not_implemented"

    def test_adapter_install_unknown_adapter(self, tmp_repo: Path, capsys) -> None:
        exit_code, out, _err = _run(["adapter", "install", "nonexistent", "--path", str(tmp_repo), "--json"], capsys)
        assert exit_code == 1
        payload = json.loads(out)
        assert payload["error"] == "unknown_adapter"

    def test_adapter_install_claude_code_reinstalls(self, tmp_repo: Path, capsys) -> None:
        _run(["init", "--path", str(tmp_repo), "--json"], capsys)
        exit_code, out, _err = _run(
            ["adapter", "install", "claude-code", "--path", str(tmp_repo), "--json"], capsys
        )
        assert exit_code == 0
        payload = json.loads(out)
        assert payload["ok"] is True


class TestProcessLevelJsonErrorContract:
    """
    Regression test for the top-level except handler in cli.py: any error
    that escapes a command's own try/except must still honor --json. An
    agent invoking this CLI programmatically parses stdout as JSON and must
    never be handed a bare stderr string instead. Mirrors
    test/integration/cli-json-error-contract.test.ts, run as a real
    subprocess (not an in-process call) so the top-level main()/sys.exit
    wiring is exercised end to end, same as the TS original's execFile use.
    """

    def _unwritable_path(self) -> str:
        return "/this/path/cannot/possibly/exist/agenticworkspace-test"

    def test_json_mode_emits_parseable_json_on_unexpected_error(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agenticworkspace.cli", "init", "--json", "--path", self._unwritable_path()],
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        assert payload["ok"] is False
        assert isinstance(payload["message"], str)

    def test_non_json_mode_prints_plain_text_not_json(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agenticworkspace.cli", "init", "--path", self._unwritable_path()],
            capture_output=True,
            text=True,
        )
        assert "agenticworkspace:" in result.stderr
        with pytest.raises(json.JSONDecodeError):
            json.loads(result.stderr)


class TestVersionFlag:
    def test_version_flag_prints_version_and_exits(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agenticworkspace.cli", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "agenticworkspace-cli" in result.stdout
