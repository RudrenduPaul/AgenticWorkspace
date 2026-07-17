"""
Public library exports. Most users will invoke the `agenticworkspace` CLI
binary directly (see cli.py), but the underlying scan/scaffold/adapter logic
is also importable for programmatic use -- e.g. another tool that wants to
run AgenticWorkspace's detection logic without shelling out, or a custom
plugin author who wants to register a new MemoryBackend or Adapter.

This is the Python port of the agenticworkspace-cli npm package
(https://www.npmjs.com/package/agenticworkspace-cli). Both distributions
implement the same two plugin interfaces (MemoryBackend, Adapter) and the
same .workspace/ scaffold contract; see
https://github.com/RudrenduPaul/AgenticWorkspace for the canonical
documentation and the original TypeScript source.
"""
from .adapters.registry import adapter_registry, get_adapter
from .adapters.types import Adapter, AdapterInstallOptions
from .memory_backends.registry import (
    MemoryBackendDetectionResult,
    any_backend_detected,
    detect_all_memory_backends,
    memory_backend_registry,
)
from .memory_backends.types import MemoryBackend
from .scaffold.init_engine import AGENTICWORKSPACE_VERSION, InitEngineResult, run_init_engine
from .scaffold.workspace_manifest import WorkspaceManifest, read_manifest, write_manifest
from .scan.config_detector import ExistingConfigResult, detect_existing_config
from .scan.stack_detector import PackageManager, PrimaryLanguage, StackDetectionResult, detect_stack
from .util.sanitize import sanitize_for_shell_embedding, shell_quote, validate_against_allowlist

__version__ = AGENTICWORKSPACE_VERSION

__all__ = [
    "detect_stack",
    "StackDetectionResult",
    "PackageManager",
    "PrimaryLanguage",
    "detect_existing_config",
    "ExistingConfigResult",
    "memory_backend_registry",
    "detect_all_memory_backends",
    "any_backend_detected",
    "MemoryBackend",
    "MemoryBackendDetectionResult",
    "adapter_registry",
    "get_adapter",
    "Adapter",
    "AdapterInstallOptions",
    "run_init_engine",
    "InitEngineResult",
    "AGENTICWORKSPACE_VERSION",
    "read_manifest",
    "write_manifest",
    "WorkspaceManifest",
    "sanitize_for_shell_embedding",
    "validate_against_allowlist",
    "shell_quote",
    "__version__",
]
