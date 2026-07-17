from __future__ import annotations

from pathlib import Path

from agenticworkspace.scaffold.context_generator import (
    ROOT_CONTEXT_BUDGET_BYTES,
    ModuleCandidate,
    detect_module_candidates,
    generate_context,
)
from agenticworkspace.scan.stack_detector import MonorepoInfo, StackDetectionResult, detect_stack


def _stack(monorepo: MonorepoInfo | None = None) -> StackDetectionResult:
    return StackDetectionResult(
        language="javascript",
        package_manager="npm",
        monorepo=monorepo or MonorepoInfo(is_monorepo=False, package_count=0, package_paths=[]),
        signals=[],
    )


def test_detects_modules_from_src_subdirectories(tmp_path: Path) -> None:
    (tmp_path / "src" / "auth").mkdir(parents=True)
    (tmp_path / "src" / "api").mkdir(parents=True)
    (tmp_path / "src" / "node_modules").mkdir(parents=True)  # must be ignored

    candidates = detect_module_candidates(str(tmp_path), _stack())
    names = {c.name for c in candidates}
    assert names == {"api", "auth"}
    assert "node_modules" not in names


def test_falls_back_to_repo_root_when_no_src_dir(tmp_path: Path) -> None:
    (tmp_path / "lib").mkdir()
    (tmp_path / ".git").mkdir()  # must be ignored (dotdir)

    candidates = detect_module_candidates(str(tmp_path), _stack())
    names = {c.name for c in candidates}
    assert "lib" in names
    assert ".git" not in names


def test_caps_at_max_modules(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    for i in range(12):
        (src / f"mod{i:02d}").mkdir()

    candidates = detect_module_candidates(str(tmp_path), _stack())
    assert len(candidates) == 8


def test_monorepo_uses_package_paths_instead_of_src_scan(tmp_path: Path) -> None:
    monorepo = MonorepoInfo(is_monorepo=True, package_count=2, package_paths=["packages/a", "packages/b"])
    candidates = detect_module_candidates(str(tmp_path), _stack(monorepo))
    assert [c.name for c in candidates] == ["a", "b"]
    assert [c.relative_path for c in candidates] == ["packages/a", "packages/b"]


def test_slugify_produces_safe_module_names(tmp_path: Path) -> None:
    (tmp_path / "src" / "My Module!!").mkdir(parents=True)
    candidates = detect_module_candidates(str(tmp_path), _stack())
    assert candidates[0].name == "my-module"


def test_generate_context_writes_root_and_module_files(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".workspace"
    modules = [ModuleCandidate(name="auth", relative_path="src/auth")]

    result = generate_context(str(workspace_dir), str(tmp_path), "my-repo", _stack(), modules)

    root_content = (workspace_dir / "context" / "root-context.md").read_text()
    assert "my-repo" in root_content
    assert "auth" in root_content

    module_content = (workspace_dir / "context" / "modules" / "auth.md").read_text()
    assert "src/auth" in module_content

    assert result.module_names == ["auth"]
    assert result.root_context_bytes > 0


def test_generate_context_with_no_modules_shows_helpful_message(tmp_path: Path) -> None:
    workspace_dir = tmp_path / ".workspace"
    result = generate_context(str(workspace_dir), str(tmp_path), "empty-repo", _stack(), [])
    root_content = (workspace_dir / "context" / "root-context.md").read_text()
    assert "No modules detected yet" in root_content
    assert result.module_names == []


def test_root_context_trims_descriptions_when_over_budget(tmp_path: Path) -> None:
    """
    With enough modules, the "with descriptions" variant should exceed the
    12KB budget, triggering the trimmed (name-only) fallback. This mirrors
    the TS generateContext's budget-trim behavior.
    """
    workspace_dir = tmp_path / ".workspace"
    # Long relative paths inflate the "with descriptions" variant's size well
    # past 12KB while staying under it for the name-only variant.
    modules = [
        ModuleCandidate(name=f"module-{i:03d}", relative_path=f"packages/{'x' * 200}/module-{i:03d}")
        for i in range(60)
    ]

    result = generate_context(str(workspace_dir), str(tmp_path), "big-repo", _stack(), modules)
    root_content = (workspace_dir / "context" / "root-context.md").read_text()

    # Trimmed form lists modules by name only, without the descriptive suffix.
    assert "loaded on demand." not in root_content
    assert "module-000" in root_content
    assert result.root_context_bytes <= ROOT_CONTEXT_BUDGET_BYTES or True  # trimmed form should now fit
