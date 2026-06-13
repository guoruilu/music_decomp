# 2026-06-13 Step 1 Python Scaffold

## User Requirement Recorded

The required verbatim user request was added to `docs/by-date/2026-06-13-user-requirements.md`:

```text
现在开始执行方案
```

## Summary

Step 1 created the minimal Python project scaffold for the planned Windows offline music stem separation application.

## Result

- Added package metadata and package discovery in `pyproject.toml`.
- Added a runnable package under `src/music_decomp`.
- Added `--version` support for the CLI.
- Added source/frozen path helper functions.
- Added path helper tests in `tests/test_paths.py`.
- Updated documentation and log indexes for this step.
- Executor subagent completed the implementation.
- Reviewer subagent approved the diff with no blocking findings.

## Validation

- Passed: `env PYTHONPATH=src python3 -m music_decomp --version`.
- Passed: path helper smoke check through `python3 -c`.
- Passed: `pyproject.toml` parse check through `tomllib`.
- Passed: `git diff --check`.
- Passed after creating a local `.venv`: `.venv/bin/python -m pip install -e '.[dev]'`.
- Passed: `.venv/bin/python -m pytest` with 6 tests.
- Passed: `.venv/bin/python -m music_decomp --version`.
- Passed: `.venv/bin/music-decomp --version`.
- Local validation generated ignored artifacts including `.venv/`, `src/music_decomp.egg-info/`, `__pycache__/`, and `.pytest_cache/`. They are not to be staged or committed.

## Next Action

Start Step 2 from the detailed execution plan: add core domain types.
