from __future__ import annotations

from pathlib import Path

import pytest

from agenticworkspace.commands.init import InitCommandOptions, run_init_command
from agenticworkspace.scaffold.init_engine import run_init_engine
from agenticworkspace.state.partial_state import write_in_progress_marker

"""
Mirrors test/integration/partial-state-flow.test.ts: verifies runInitCommand
correctly branches on JSON-mode-never-prompts, and drives the interactive
repair/reset/abort flow by monkeypatching the prompt module (the TS original
mocks the same module with vitest's vi.mock for the same reason -- exercising
the interactive branch without a real TTY).
"""


def test_json_mode_never_prompts_on_interrupted_init(tmp_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace_dir = tmp_repo / ".workspace"
    workspace_dir.mkdir()
    write_in_progress_marker(str(workspace_dir))

    called = []
    monkeypatch.setattr(
        "agenticworkspace.commands.init.ask_repair_reset_abort", lambda: called.append(True)
    )

    outcome = run_init_command(InitCommandOptions(path=str(tmp_repo), json=True))

    assert outcome.exit_code == 2
    assert outcome.json["error"] == "partial_state_detected"
    assert outcome.json["partial_state"] == "interrupted-init"
    assert called == []


def test_abort_choice_leaves_workspace_untouched(tmp_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace_dir = tmp_repo / ".workspace"
    workspace_dir.mkdir()
    write_in_progress_marker(str(workspace_dir))

    monkeypatch.setattr("agenticworkspace.commands.init.is_interactive_terminal", lambda: True)
    monkeypatch.setattr("agenticworkspace.commands.init.ask_repair_reset_abort", lambda: "abort")

    outcome = run_init_command(InitCommandOptions(path=str(tmp_repo), json=False))

    assert outcome.exit_code == 1
    assert outcome.json["error"] == "aborted_by_user"
    assert (workspace_dir / ".init-in-progress").exists()
    assert not (workspace_dir / "workspace.json").exists()


def test_repair_choice_fills_in_missing_pieces_without_wiping_handoffs(
    tmp_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace_dir = tmp_repo / ".workspace"
    (workspace_dir / "handoff").mkdir(parents=True)
    (workspace_dir / "handoff" / "2026-01-01-0000.md").write_text("# earlier session\n")
    write_in_progress_marker(str(workspace_dir))

    monkeypatch.setattr("agenticworkspace.commands.init.is_interactive_terminal", lambda: True)
    monkeypatch.setattr("agenticworkspace.commands.init.ask_repair_reset_abort", lambda: "repair")

    outcome = run_init_command(InitCommandOptions(path=str(tmp_repo), json=False))

    assert outcome.exit_code == 0
    assert outcome.json["ok"] is True
    assert (workspace_dir / "workspace.json").exists()
    # Repair must not delete a handoff file that predates the repair.
    assert (workspace_dir / "handoff" / "2026-01-01-0000.md").exists()
    assert not (workspace_dir / ".init-in-progress").exists()


def test_reset_choice_wipes_workspace_and_starts_clean(tmp_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace_dir = tmp_repo / ".workspace"
    (workspace_dir / "handoff").mkdir(parents=True)
    (workspace_dir / "handoff" / "2026-01-01-0000.md").write_text("# earlier session\n")
    write_in_progress_marker(str(workspace_dir))

    monkeypatch.setattr("agenticworkspace.commands.init.is_interactive_terminal", lambda: True)
    monkeypatch.setattr("agenticworkspace.commands.init.ask_repair_reset_abort", lambda: "reset")

    outcome = run_init_command(InitCommandOptions(path=str(tmp_repo), json=False))

    assert outcome.exit_code == 0
    assert outcome.json["ok"] is True
    assert (workspace_dir / "workspace.json").exists()
    assert not (workspace_dir / "handoff" / "2026-01-01-0000.md").exists()


def test_malformed_manifest_is_reported_not_silently_overwritten(tmp_repo: Path) -> None:
    workspace_dir = tmp_repo / ".workspace"
    workspace_dir.mkdir()
    (workspace_dir / "workspace.json").write_text('{"someUnexpectedShape": true}')

    outcome = run_init_command(InitCommandOptions(path=str(tmp_repo), json=True))

    assert outcome.exit_code == 2
    assert outcome.json["partial_state"] == "malformed-manifest"
    assert isinstance(outcome.json["missing_keys"], list)
    assert len(outcome.json["missing_keys"]) > 0


def test_complete_prior_workspace_is_treated_as_complete_and_rescans_idempotently(
    tmp_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace_dir = tmp_repo / ".workspace"
    run_init_engine(str(tmp_repo), str(workspace_dir))

    called = []
    monkeypatch.setattr(
        "agenticworkspace.commands.init.ask_repair_reset_abort", lambda: called.append(True)
    )

    outcome = run_init_command(InitCommandOptions(path=str(tmp_repo), json=True))
    assert outcome.exit_code == 0
    assert called == []


def test_fresh_init_writes_full_scaffold(tmp_repo: Path) -> None:
    outcome = run_init_command(InitCommandOptions(path=str(tmp_repo), json=True))

    assert outcome.exit_code == 0
    assert outcome.json["ok"] is True
    workspace_dir = tmp_repo / ".workspace"
    assert (workspace_dir / "workspace.json").exists()
    assert (workspace_dir / "context" / "root-context.md").exists()
    assert (workspace_dir / "adapters" / "claude-code" / "settings.json").exists()
