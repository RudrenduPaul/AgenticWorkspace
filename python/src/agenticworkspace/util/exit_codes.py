"""
Exit codes used across the CLI. Kept in one place so JSON output and process
exit codes stay consistent, and so an agent parsing --json output can rely on
a stable contract. Ported verbatim from src/agenticworkspace/util/exit-codes.ts.
"""
from __future__ import annotations

OK = 0
GENERAL_ERROR = 1
PARTIAL_STATE_DETECTED = 2
ADAPTER_NOT_IMPLEMENTED = 3
NO_WORKSPACE_FOUND = 4

EXIT_CODES = {
    "OK": OK,
    "GENERAL_ERROR": GENERAL_ERROR,
    "PARTIAL_STATE_DETECTED": PARTIAL_STATE_DETECTED,
    "ADAPTER_NOT_IMPLEMENTED": ADAPTER_NOT_IMPLEMENTED,
    "NO_WORKSPACE_FOUND": NO_WORKSPACE_FOUND,
}
