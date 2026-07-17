from __future__ import annotations

import json
from pathlib import Path

from agenticworkspace.scan.stack_detector import detect_stack


def test_detects_npm_javascript(tmp_repo: Path) -> None:
    result = detect_stack(str(tmp_repo))
    assert result.language == "javascript"
    assert result.package_manager == "npm"
    assert "package.json" in result.signals
    assert "package-lock.json" in result.signals


def test_detects_typescript_via_tsconfig(tmp_repo: Path) -> None:
    (tmp_repo / "tsconfig.json").write_text("{}")
    result = detect_stack(str(tmp_repo))
    assert result.language == "typescript"
    assert "tsconfig.json" in result.signals


def test_detects_pnpm_via_lockfile(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "pnpm-lock.yaml").write_text("")
    result = detect_stack(str(tmp_path))
    assert result.package_manager == "pnpm"


def test_detects_yarn_via_lockfile(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "yarn.lock").write_text("")
    result = detect_stack(str(tmp_path))
    assert result.package_manager == "yarn"


def test_defaults_to_npm_when_package_json_present_no_lockfile(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}")
    result = detect_stack(str(tmp_path))
    assert result.package_manager == "npm"


def test_detects_python_poetry_via_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.poetry]\n")
    result = detect_stack(str(tmp_path))
    assert result.language == "python"
    assert result.package_manager == "poetry"


def test_detects_python_pip_via_requirements(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("requests\n")
    result = detect_stack(str(tmp_path))
    assert result.language == "python"
    assert result.package_manager == "pip"


def test_detects_python_pip_via_pipfile(tmp_path: Path) -> None:
    (tmp_path / "Pipfile").write_text("")
    result = detect_stack(str(tmp_path))
    assert result.language == "python"
    assert result.package_manager == "pip"


def test_detects_rust_via_cargo_toml(tmp_path: Path) -> None:
    (tmp_path / "Cargo.toml").write_text("[package]\n")
    result = detect_stack(str(tmp_path))
    assert result.language == "rust"
    assert result.package_manager == "cargo"


def test_detects_go_via_go_mod(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text("module example.com/x\n")
    result = detect_stack(str(tmp_path))
    assert result.language == "go"
    assert result.package_manager == "go"


def test_detects_ruby_via_gemfile(tmp_path: Path) -> None:
    (tmp_path / "Gemfile").write_text("")
    result = detect_stack(str(tmp_path))
    assert result.language == "ruby"
    assert result.package_manager == "bundler"


def test_unknown_stack_when_no_signals(empty_repo: Path) -> None:
    result = detect_stack(str(empty_repo))
    assert result.language == "unknown"
    assert result.package_manager == "unknown"
    assert result.signals == []


def test_pyproject_takes_priority_over_requirements_txt(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.poetry]\n")
    (tmp_path / "requirements.txt").write_text("requests\n")
    result = detect_stack(str(tmp_path))
    assert result.package_manager == "poetry"


class TestMonorepoDetection:
    def test_detects_monorepo_via_packages_glob(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"workspaces": ["packages/*"]}))
        (tmp_path / "package-lock.json").write_text("{}")
        for name in ("pkg-a", "pkg-b"):
            pkg_dir = tmp_path / "packages" / name
            pkg_dir.mkdir(parents=True)
            (pkg_dir / "package.json").write_text(json.dumps({"name": name}))

        result = detect_stack(str(tmp_path))
        assert result.monorepo.is_monorepo is True
        assert result.monorepo.package_count == 2
        assert sorted(result.monorepo.package_paths) == [
            str(Path("packages") / "pkg-a"),
            str(Path("packages") / "pkg-b"),
        ]

    def test_detects_monorepo_via_workspaces_packages_object(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"workspaces": {"packages": ["apps/*"]}}))
        pkg_dir = tmp_path / "apps" / "web"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "package.json").write_text(json.dumps({"name": "web"}))

        result = detect_stack(str(tmp_path))
        assert result.monorepo.is_monorepo is True
        assert result.monorepo.package_count == 1

    def test_not_a_monorepo_without_workspace_globs(self, tmp_repo: Path) -> None:
        result = detect_stack(str(tmp_repo))
        assert result.monorepo.is_monorepo is False
        assert result.monorepo.package_count == 0

    def test_ignores_negation_globs(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            json.dumps({"workspaces": ["packages/*", "!packages/excluded"]})
        )
        pkg_dir = tmp_path / "packages" / "included"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "package.json").write_text("{}")

        result = detect_stack(str(tmp_path))
        assert result.monorepo.package_count == 1

    def test_path_traversal_glob_is_dropped_not_included(self, tmp_path: Path) -> None:
        """
        Security regression test: a scanned repo's own package.json could
        declare a workspace glob like "../sibling-project" pointing outside
        the repo. resolve_workspace_packages must drop anything that
        escapes repo_path rather than silently including it.
        """
        # Create a sibling directory outside tmp_path that has a package.json,
        # simulating what an attacker-controlled glob might try to reach.
        sibling = tmp_path.parent / f"{tmp_path.name}-sibling-outside"
        sibling.mkdir(exist_ok=True)
        (sibling / "package.json").write_text("{}")
        try:
            (tmp_path / "package.json").write_text(
                json.dumps({"workspaces": [f"../{sibling.name}"]})
            )
            result = detect_stack(str(tmp_path))
            assert result.monorepo.package_count == 0
            assert result.monorepo.package_paths == []
        finally:
            import shutil

            shutil.rmtree(sibling, ignore_errors=True)

    def test_malformed_package_json_does_not_raise(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("{not valid json")
        result = detect_stack(str(tmp_path))
        assert result.monorepo.is_monorepo is False
