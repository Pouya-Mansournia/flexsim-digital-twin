# Contributing

Issues and pull requests are welcome.

## Getting set up

```powershell
git clone https://github.com/Pouya-Mansournia/flexsim-digital-twin.git
cd flexsim-digital-twin/bridge
.\run.ps1
```

`run.ps1` creates a virtual environment, installs dependencies, and starts
the bridge on `http://127.0.0.1:8000`. See the [root README](README.md)
and [`bridge/README.md`](bridge/README.md) for the full picture.

## Running tests

```powershell
cd bridge
.venv\Scripts\Activate.ps1
pytest
```

All tests must pass before a pull request is merged. Add tests for new
API endpoints or service logic.

`rms/`'s tests are separate, since `rms/` has no dependency on
`bridge/`'s virtual environment:

```powershell
pip install pytest
pytest    # from the repository root
```

## Project structure

- `bridge/app/` — FastAPI service (routes, Pydantic models, in-memory
  stores). Keep `api/` thin: validation and delegation only, logic
  belongs in `services/`.
- `bridge/ros2_sim/` — the mock real-environment simulator.
- `bridge/flexsim/` — FlexSim-side integration docs and FlexScript.
- `flexsim-model/` — the FlexSim 2027 model file.
- `rms/`, `adapters/` — Robot Management System scaffolding (domain
  model, manager/adapter interfaces). Not wired into `bridge/` yet; see
  [`rms/README.md`](rms/README.md) and
  [`adapters/README.md`](adapters/README.md) before extending them.

## Extending this to a different FlexSim model

Don't assume FlexSim object paths. Click each object once in FlexSim and
read the status bar for its real path before referencing it in a Custom
Code block. See
[`bridge/flexsim/verified_scripts/README.md`](bridge/flexsim/verified_scripts/README.md)
for the reasoning and every gotcha found doing this the first time.

## Code style

- Python 3.11+, type hints on function signatures.
- Small, single-purpose functions; no unnecessary abstraction.
- No comments explaining *what* code does; only *why*, when it's
  non-obvious.
- Keep `api/` route handlers thin.

## Reporting issues

Include: what you expected, what happened instead, and steps to
reproduce. For FlexSim-related issues, include the FlexSim version and
the relevant Custom Code snippet.

## License

By contributing, you agree that your contributions will be licensed
under the [MIT License](LICENSE).
