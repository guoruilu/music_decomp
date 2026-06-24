# Recording Separation Pipeline Log

Date: 2026-06-24

## Scope

Executor assignment: implement only Step 9 - Wire End-To-End Recording
Separation.

Constraints followed:

- no Step 10 CLI work
- no dependency locking or packaging work
- no commit or push
- no real SoundCard, PySide6, FFmpeg, Demucs, torch, model files, network, or
  Windows device requirement for normal tests
- preserve existing file-separation behavior

## Files Added Or Updated

- `src/music_decomp/services/file_pipeline.py`
- `src/music_decomp/ui/workers.py`
- `src/music_decomp/ui/main_window.py`
- `tests/test_file_pipeline.py`
- `tests/test_gui_shell.py`
- `docs/INDEX.md`
- `docs/by-date/2026-06-24-step-9-recording-separation.md`
- `docs/by-feature/current-project-status.md`
- `docs/by-feature/recording-separation-pipeline.md`
- `logs/INDEX.md`
- `logs/by-date/2026-06-24-step-9-recording-separation.md`
- `logs/by-feature/recording-separation-pipeline.md`

## Implementation Notes

- Added a recording-specific pipeline entry point instead of making the GUI
  treat recorder output as a normal local file.
- `run_recording` validates `MediaInput(kind="recording")`, creates normal job
  artifacts, probes the finalized WAV, extracts it through `MediaService` into
  canonical stereo 44.1 kHz `_intermediate/input.wav`, and runs the same
  separation/metadata path as file inputs.
- The file path still uses the existing probe and FFmpeg extraction flow.
- `RecordingWorker` now supports list/start/stop actions with an injectable
  recorder service for tests.
- `SeparationWorker` now accepts `media_input` and calls `run_recording` for
  recording inputs.
- The Record tab refreshes devices lazily when the tab is first opened.
- The Record tab starts/stops through workers, polls elapsed time and peak level
  with a timer, stores the stopped `MediaInput`, and queues recording
  separation through the same Jobs tab progress UI.

## Checks Run During Implementation

- Passed: `PYTHONPATH=src python3 -m compileall -q src/music_decomp`
- Passed: `PYTHONPATH=src python3 -m compileall -q src tests`
- Passed: `PYTHONPATH=src python3 -m music_decomp --version`
  - Output: `music-decomp 0.1.0`
- Passed: `PYTHONPATH=src python3 -c "from music_decomp.services.file_pipeline import FileSeparationPipeline; from music_decomp.ui.workers import RecordingWorker, SeparationWorker; print('imports ok')"`
  - Output: `imports ok`
- Passed: inline fake recording canonicalization pipeline smoke test
  - Output: `recording canonical smoke ok`
- Not run: `PYTHONPATH=src python3 -m pytest tests/test_file_pipeline.py tests/test_gui_shell.py tests/test_recorder_service.py`
  - Result: `/usr/bin/python3: No module named pytest`

## Known Risks Or Incomplete Items

- Pytest was unavailable in this environment, so the new tests were compiled
  but not executed.
- No real PySide6 GUI launch was run.
- No Windows WASAPI loopback manual test was run.
- No real FFmpeg/Demucs/model separation run was executed.
- Initial reviewer result: APPROVED, no blocking findings.
- Main-agent post-review canonicalization finding was fixed by routing
  recordings through `MediaService.probe` and `MediaService.extract_audio`
  before separation.
- Reviewer re-review result after canonicalization fix: APPROVED, no blocking
  findings.
- Final commit and push are handled by the main agent after docs/log updates.
