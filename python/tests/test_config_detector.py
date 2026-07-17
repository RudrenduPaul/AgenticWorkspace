from __future__ import annotations

from pathlib import Path

from agenticworkspace.scan.config_detector import detect_existing_config


def test_no_config_detected_in_empty_repo(empty_repo: Path) -> None:
    result = detect_existing_config(str(empty_repo))
    assert result.any_detected is False
    assert result.claude_md is False
    assert result.agents_md is False
    assert result.cursor_rules is False
    assert result.copilot_instructions is False


def test_detects_claude_md(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("# instructions\n")
    result = detect_existing_config(str(tmp_path))
    assert result.claude_md is True
    assert result.any_detected is True


def test_detects_agents_md(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# instructions\n")
    result = detect_existing_config(str(tmp_path))
    assert result.agents_md is True
    assert result.any_detected is True


def test_detects_cursor_rules_directory(tmp_path: Path) -> None:
    (tmp_path / ".cursor" / "rules").mkdir(parents=True)
    result = detect_existing_config(str(tmp_path))
    assert result.cursor_rules is True
    assert result.any_detected is True


def test_detects_copilot_instructions(tmp_path: Path) -> None:
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "copilot-instructions.md").write_text("# instructions\n")
    result = detect_existing_config(str(tmp_path))
    assert result.copilot_instructions is True
    assert result.any_detected is True


def test_multiple_configs_detected_together(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("x")
    (tmp_path / "AGENTS.md").write_text("x")
    result = detect_existing_config(str(tmp_path))
    assert result.claude_md is True
    assert result.agents_md is True
    assert result.cursor_rules is False
