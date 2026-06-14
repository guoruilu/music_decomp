# File Separation Pipeline Log

Date: 2026-06-14

## Scope

Executor assignment: implement only Step 8 - Wire End-To-End File Separation.

Constraints followed:

- no Step 9 recording pipeline
- no packaging
- no commit or push
- no dependency on PySide6, real FFmpeg, Demucs, torch, model files, or network for normal tests
- no read or modification of `docs/codex-review/`

## Files Added Or Updated

- `src/music_decomp/services/file_pipeline.py`
- `src/music_decomp/services/export_service.py`
- `src/music_decomp/services/__init__.py`
- `src/music_decomp/ui/workers.py`
- `src/music_decomp/ui/main_window.py`
- `tests/test_file_pipeline.py`
- `tests/test_gui_shell.py`
- `docs/INDEX.md`
- `docs/by-date/2026-06-14-step-8-file-separation.md`
- `docs/by-date/2026-06-14-user-requirements.md`
- `docs/by-feature/file-separation-pipeline.md`
- `logs/INDEX.md`
- `logs/by-date/2026-06-14-step-8-file-separation.md`
- `logs/by-feature/file-separation-pipeline.md`

## Implementation Notes

- Added a service-layer pipeline so GUI workers do not need to know FFprobe, FFmpeg extraction, job creation, or metadata details.
- `probe_input` preserves raw FFprobe data and creates stable GUI-facing stream summary text.
- `run_file` writes canonical input audio to `_intermediate/input.wav`.
- Normal job directory creation is collision-safe and uses suffixes such as `-2` when the timestamp and title collide.
- Each successful job appends readable phase lines to `job.log`.
- Success metadata is written through `ExportService.write_job_metadata`.
- Probe failure before job preparation creates a failure directory, `job.log`, and `job.json`.
- Failure after job preparation appends to the job log and writes failure metadata through `ExportService`.
- GUI selection-time probe failures create failure artifacts through `MediaProbeWorker` and include the log path in the failure message.
- GUI workers support fake operations/pipelines for tests and use fallback signals without PySide6.
- GUI worker failure messages include pipeline `log_path` or `output_dir` when available.
- The main window now probes selected/dropped files and displays real probe details.
- The start button now runs the file separation pipeline and records the real output folder.

## Checks Run During Implementation

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
  - Result: Step 8 files plus pre-existing modified `docs/by-date/2026-06-13-user-requirements.md` and pre-existing untracked `docs/codex-review/`.

## Known Risks Or Incomplete Items

- Real GUI behavior was not manually launched because PySide6 is not required in this environment.
- Real FFmpeg/Demucs integration was not executed by automated tests.
- Selection-time probe failure is displayed in the GUI and writes failure artifacts immediately.
- Separate reviewer re-review approved Step 8 with no blocking findings.
