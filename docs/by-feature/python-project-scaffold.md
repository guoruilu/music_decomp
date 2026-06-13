# Python Project Scaffold

Date: 2026-06-13

Related execution plan step: [Step 1 - Scaffold The Python Project](step-by-step-execution-plan.md#step-1---scaffold-the-python-project)

## Status

Step 1 is implemented and reviewed. The executor completed the scaffold, the reviewer approved it with no blocking findings, and the main agent completed final validation in a local `.venv`.

## Implemented Files

- `README.md`
- `pyproject.toml`
- `src/music_decomp/__init__.py`
- `src/music_decomp/__main__.py`
- `src/music_decomp/app.py`
- `src/music_decomp/cli.py`
- `src/music_decomp/paths.py`
- `tests/test_paths.py`

## Scaffold Behavior

- Project metadata uses package name `music-decomp` and import package `music_decomp`.
- Console script is declared as `music-decomp = music_decomp.cli:main`.
- Runtime dependencies are empty for this step.
- `pytest` is declared only under optional development dependencies.
- `python -m music_decomp --version` prints the package version and exits successfully when `src` is on `PYTHONPATH` or the package is installed.
- `__main__.py` delegates to `cli.main()`.
- `paths.py` provides:
  - `project_root()`
  - `app_data_dir()`
  - `resource_path(relative_path)`
  - `is_frozen()`
- `resource_path()` resolves from the repository root in source mode and from PyInstaller `_MEIPASS` when frozen.

## Validation

- `env PYTHONPATH=src python3 -m music_decomp --version`: passed, printed `music-decomp 0.1.0`.
- `env PYTHONPATH=src python3 -c "...path helper smoke..."`: passed.
- `python3 -c "...tomllib..."`: passed; `pyproject.toml` parsed successfully.
- `git diff --check`: passed.
- `.venv/bin/python -m pip install -e '.[dev]'`: passed after approved network escalation for pytest dependency installation.
- `.venv/bin/python -m pytest`: passed, 6 tests.
- `.venv/bin/python -m music_decomp --version`: passed, printed `music-decomp 0.1.0`.
- `.venv/bin/music-decomp --version`: passed, printed `music-decomp 0.1.0`.
- Local validation generated ignored files/directories such as `.venv/`, `src/music_decomp.egg-info/`, `__pycache__/`, and `.pytest_cache/`; these are intentionally ignored and must not be committed.

## Handoff Notes

- The implementation is intentionally limited to Step 1.
- Later workflow commands, GUI, media services, model dependencies, FFmpeg, and packaging are not implemented yet.
- Next implementation step is Step 2 - Add Core Domain Types.
