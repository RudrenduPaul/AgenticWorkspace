#!/usr/bin/env python3
"""
01 -- basic scaffold.

The simplest possible use of the agenticworkspace library: build a small
synthetic JS repo in a temp directory, call run_init_engine() against it,
and read back what it wrote. Runs standalone with no setup beyond
`pip install -e .` (or `pip install agenticworkspace-cli`) from the python/
directory -- it creates its own throwaway sample repo, it does not touch
anything in this checkout.

Run:
    python3 examples/01-basic-scaffold/run.py
"""
import json
import shutil
import tempfile
from pathlib import Path

from agenticworkspace import run_init_engine


def build_sample_repo(root: Path) -> None:
    (root / "package.json").write_text(json.dumps({"name": "sample-app", "version": "1.0.0"}))
    (root / "package-lock.json").write_text("{}")
    for module in ("auth", "billing"):
        module_dir = root / "src" / module
        module_dir.mkdir(parents=True)
        (module_dir / "index.js").write_text("module.exports = {};\n")


def main() -> None:
    tmp_dir = Path(tempfile.mkdtemp(prefix="agenticworkspace-example-"))
    try:
        build_sample_repo(tmp_dir)
        workspace_dir = tmp_dir / ".workspace"

        result = run_init_engine(str(tmp_dir), str(workspace_dir))

        print(f"repo:            {result.repo_path}")
        print(f"language:        {result.stack.language}")
        print(f"package manager: {result.stack.package_manager}")
        print(f"modules found:   {result.context.module_names}")
        print(f"root context:    {result.context.root_context_bytes} bytes "
              f"(of {result.context.budget_bytes} budget)")
        print(f"claude code adapter installed: "
              f"{(workspace_dir / 'adapters' / 'claude-code' / 'settings.json').exists()}")
        print()
        print("Files written under .workspace/:")
        for path in sorted(workspace_dir.rglob("*")):
            if path.is_file():
                print(f"  {path.relative_to(workspace_dir)}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
