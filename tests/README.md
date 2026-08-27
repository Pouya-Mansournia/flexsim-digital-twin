# tests

Unit tests for the `rms/` scaffolding (the RMS core described in the
root README's RMS vision section). This is separate from
[`bridge/tests/`](../bridge/README.md#testing), which tests the FastAPI
service and requires `bridge/.venv`.

## Running

```powershell
pip install pytest
pytest
```

Run from the repository root. `rms/` and `adapters/` have no third-party
dependencies, so no virtual environment is required beyond `pytest`
itself; `bridge/`'s own `.venv` works fine too if you already have it.
