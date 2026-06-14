# 2026-06-14 Step 8 File Separation Pipeline

## User Requirement Recorded

The current user request was recorded verbatim in `docs/by-date/2026-06-14-user-requirements.md`:

```text
继续执行
```

## Initial Worktree Check

Before implementation, `git status --short` showed:

```text
 M docs/by-date/2026-06-13-user-requirements.md
?? docs/codex-review/
```

The modified 2026-06-13 requirement record was treated as pre-existing user or coordinator work and was not reverted. `docs/codex-review/` was treated as user-owned untracked content and was not read, modified, moved, deleted, staged, committed, or pushed.

## Scope

Executor assignment: implement only Step 8 - Wire End-To-End File Separation.

Out of scope:

- Step 9 recording end-to-end flow
- packaging
- commit or push
- real dependency tests that require PySide6, FFmpeg, Demucs, torch, model files, or network access

## Implemented

- Added `FileSeparationPipeline` in `src/music_decomp/services/file_pipeline.py`.
- Updated `ExportService.create_job_directory` to create suffixed directories on collision.
- Added `MediaProbeResult`, `FileSeparationResult`, `MediaProbeError`, and `FileSeparationPipelineError`.
- Implemented FFprobe JSON parsing for media kind, duration, sample rate, title, raw probe data, and stream summaries.
- Required at least one audio stream before a file can proceed to separation.
- Implemented `run_file` orchestration:
  - probe
  - job directory and job log creation
  - canonical WAV extraction to `_intermediate/input.wav`
  - `SeparationService.separate`
  - success metadata write
  - failure metadata/log handling
- Implemented probe-failure artifacts so unreadable files still produce a failure job directory, `job.log`, and `job.json`.
- Made normal `ExportService` job directory creation collision-safe with `-2`, `-3`, and later suffixes.
- Exported the new service types from `src/music_decomp/services/__init__.py`.
- Updated `MediaProbeWorker` to default to real probing while supporting fake operation/pipeline injection.
- Updated `MediaProbeWorker` so GUI selection-time probe failures create failure artifacts and return a failure message with the job log path.
- Updated `SeparationWorker` to default to the real file pipeline while supporting fake operation/pipeline injection.
- Updated GUI file selection and drag/drop flow to start probe workers.
- Updated GUI start separation flow to use the real `SeparationWorker`.
- Updated GUI completion handling to store and display the real output directory.
- Updated GUI worker failure messages to include a pipeline `log_path` or `output_dir` when available.
- Kept the `highest` approximation notice visible.
- Added focused core pipeline tests and updated GUI worker tests.

## Validation

- Passed: `.venv/bin/python -m pytest tests/test_file_pipeline.py tests/test_gui_shell.py tests/test_export_service.py`
  - Result: 25 passed.
- Passed: `.venv/bin/python -m compileall -q src/music_decomp tests`
- Passed: `.venv/bin/python -m pytest`
  - Result: 64 passed, 1 skipped.
- Passed: `.venv/bin/python -m music_decomp --version`
  - Output: `music-decomp 0.1.0`.
- Passed: `git diff --check`
  - Result: no whitespace errors.
- Ran: `git status --short`
  - Result: Step 8 files, pre-existing modified `docs/by-date/2026-06-13-user-requirements.md`, and pre-existing untracked `docs/codex-review/`.

## Reviewer Notes

- First reviewer pass requested fixes for same-second job directory collisions and GUI selection-time probe failure logs.
- Executor fixed both findings, added regression tests, and reran validation.
- Reviewer re-review approved Step 8 with no blocking findings.
- Real Windows GUI, FFmpeg, and Demucs manual acceptance remains for later environment-specific testing.
