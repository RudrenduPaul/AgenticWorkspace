from __future__ import annotations

from importlib import metadata as importlib_metadata

from agenticworkspace.scaffold.init_engine import AGENTICWORKSPACE_VERSION


class TestVersionMatchesInstalledMetadata:
    def test_version_matches_installed_distribution(self) -> None:
        # A previous hardcoded constant here drifted out of sync with
        # pyproject.toml/PyPI on every release (shipped "0.1.0" while PyPI had
        # already published 0.1.2), so --version and every workspace.json
        # manifest silently lied about which release was actually running.
        # This locks the two together by reading real installed metadata.
        try:
            installed_version = importlib_metadata.version("agenticworkspace-cli")
        except importlib_metadata.PackageNotFoundError:
            # No installed distribution metadata in this environment (e.g. a
            # non-editable, non-installed checkout) -- fall back is expected.
            assert AGENTICWORKSPACE_VERSION == "0.0.0"
            return
        assert AGENTICWORKSPACE_VERSION == installed_version

    def test_version_is_never_the_fallback_when_installed(self) -> None:
        importlib_metadata.version("agenticworkspace-cli")  # raises if not installed
        assert AGENTICWORKSPACE_VERSION != "0.0.0"
