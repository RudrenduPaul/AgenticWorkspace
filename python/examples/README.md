# Python examples

Each numbered subdirectory is a real, runnable script against the actual
`agenticworkspace` Python library, not pseudocode. They scaffold a temporary
sample repo under the OS temp directory, so nothing outside the example
itself is touched -- no need for a real project to point them at.

Install the package first (editable install from this checkout, or `pip
install agenticworkspace-cli` from PyPI both work identically):

```bash
cd python
pip install -e .
```

Then run any example directly:

```bash
python3 examples/01-basic-scaffold/run.py
python3 examples/02-ci-gate/gate.py
python3 examples/03-custom-plugin/run.py
```

| Example | What it demonstrates |
| --- | --- |
| [01-basic-scaffold](./01-basic-scaffold/) | The core library call: `run_init_engine()` against a small synthetic repo, reading back the manifest and the files it wrote. |
| [02-ci-gate](./02-ci-gate/) | Using `agenticworkspace status` as a CI gate: real process exit-code propagation, suitable to drop into a CI script directly (see `../../docs/integrations/ci.md`). |
| [03-custom-plugin](./03-custom-plugin/) | Writing a minimal custom `MemoryBackend` and a minimal custom `Adapter`, registering both, then running `run_init_engine()` and showing the custom backend/adapter take effect with zero changes to AgenticWorkspace's own code. |
