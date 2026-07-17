"""
Shared sanitization module.

Every value derived from scanning a target repository (file paths, detected
module names, package names, branch names, and so on) that ends up embedded
into a generated shell script (the Claude Code adapter's hook .sh files) must
pass through this module first. Nothing else in the codebase should duplicate
this logic -- call into these functions instead.

Defense in depth, two layers:
  1. An allowlist pattern: only alphanumeric characters, dash, underscore,
     and forward slash are accepted. Anything else is rejected outright.
  2. POSIX single-quote shell quoting on top, applied to every value that
     does get embedded, even though the allowlist already excludes shell
     metacharacters. Belt and suspenders: if the allowlist is ever loosened
     by mistake in the future, the quoting still holds.

Ported verbatim (same allowlist pattern, same max length, same quoting
technique) from src/agenticworkspace/util/sanitize.ts.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Sequence

# Matches only [A-Za-z0-9_/-]. Empty strings do not match.
_ALLOWLIST_PATTERN = re.compile(r"^[A-Za-z0-9_/-]+$")

# Maximum length accepted for any sanitized value. Prevents pathological input.
MAX_VALUE_LENGTH = 512

SanitizeWarning = Callable[[str], None]


@dataclass
class SanitizeResult:
    ok: bool
    value: Optional[str]
    reason: Optional[str] = None


def validate_against_allowlist(raw_value: Any) -> SanitizeResult:
    """
    Validate a single value against the allowlist. Does not raise. Callers get
    a structured result so they can log a warning and skip the value rather
    than crash the whole scan/install run over one bad detected string.
    """
    if not isinstance(raw_value, str):
        return SanitizeResult(ok=False, value=None, reason="value is not a string")
    if len(raw_value) == 0:
        return SanitizeResult(ok=False, value=None, reason="value is empty")
    if len(raw_value) > MAX_VALUE_LENGTH:
        return SanitizeResult(
            ok=False,
            value=None,
            reason=f"value exceeds max length of {MAX_VALUE_LENGTH} characters",
        )
    if not _ALLOWLIST_PATTERN.match(raw_value):
        return SanitizeResult(
            ok=False,
            value=None,
            reason="value contains characters outside the allowlist (alphanumeric, dash, underscore, slash only)",
        )
    return SanitizeResult(ok=True, value=raw_value)


def shell_quote(value: str) -> str:
    """
    Quote a string for safe embedding inside a POSIX shell script, using
    single quotes. Standard technique: close the quote, escape a literal
    single quote, reopen the quote. Applied even to already-allowlisted
    values, as defense in depth against a future allowlist regression.
    """
    return "'" + value.replace("'", "'\\''") + "'"


def sanitize_for_shell_embedding(
    raw_value: Any,
    warn: SanitizeWarning = lambda message: None,
    label: Optional[str] = None,
) -> Optional[str]:
    """
    Validate a value against the allowlist and, if it passes, return it
    shell-quoted and ready to embed in a generated script. If it fails, call
    the supplied warn callback (defaults to a no-op) and return None so the
    caller can skip embedding that value and continue, rather than crash or
    silently embed unsafe content.
    """
    result = validate_against_allowlist(raw_value)
    if not result.ok or result.value is None:
        prefix = f"[{label}] " if label else ""
        warn(f"{prefix}skipped value that failed sanitization allowlist: {result.reason}")
        return None
    return shell_quote(result.value)


def sanitize_list_for_shell_embedding(
    raw_values: Sequence[Any],
    warn: SanitizeWarning = lambda message: None,
    label: Optional[str] = None,
) -> List[str]:
    """
    Sanitize a whole list of values in one pass, dropping any value that
    fails the allowlist and warning for each drop, rather than failing the
    entire batch because one value was unsafe.
    """
    out: List[str] = []
    for raw_value in raw_values:
        sanitized = sanitize_for_shell_embedding(raw_value, warn, label)
        if sanitized is not None:
            out.append(sanitized)
    return out
