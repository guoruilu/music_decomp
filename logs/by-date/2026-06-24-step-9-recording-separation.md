# 2026-06-24 Step 9 Recording Separation Log

## Assignment

Executor subagent implementation for Step 9 - Wire End-To-End Recording
Separation.

## Worktree Notes

Initial `git status --short --branch` showed:

```text
## main...origin/main
 M docs/by-date/2026-06-24-user-requirements.md
```

The pre-existing requirement-record update was preserved.

## Actions

- Read required project instructions, product plan, execution plan, workflow,
  current status, recorder service docs, GUI shell docs, and file pipeline docs.
- Read existing `RecorderService`, `FileSeparationPipeline`, GUI workers,
  main window, and related tests.
- Added `FileSeparationPipeline.run_recording(...)`.
- Shared the post-input-preparation separation/metadata path between file
  inputs and recording inputs.
- Updated `run_recording` after main-agent post-review feedback so recordings
  are probed and extracted through `MediaService` into canonical stereo 44.1
  kHz `_intermediate/input.wav` before separation.
- Extended GUI workers for recorder device listing, start, stop, and recording
  separation routing.
- Replaced Record tab placeholder behavior with real recorder-service wiring.
- Added focused fake-based tests for the new service and worker behavior.
- Added Step 9 documentation and logs.

## Validation

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

## Handoff To Reviewer

Review focus areas:

- Confirm file separation behavior is preserved after the shared helper
  extraction in `FileSeparationPipeline`.
- Confirm GUI record start/stop workers cannot leave the UI in a stuck disabled
  state on recorder failures.
- Confirm recording input metadata/log behavior matches Step 8 file job
  behavior closely enough for downstream packaging and CLI work.
- Run targeted pytest in an environment with dev dependencies installed.

## Initial Reviewer Outcome

- Result: APPROVED, no blocking findings.
- Reviewer confirmed Step 9 wiring matches the plan.
- Reviewer confirmed Record tab device refresh/start/stop use `RecordingWorker`
  and `RecorderService`, while actual capture remains in the recorder service
  background worker.
- Reviewer confirmed stopped recordings are handed to
  `SeparationWorker(media_input=...)` and routed to
  `FileSeparationPipeline.run_recording`.
- Reviewer confirmed tests are fake-based and do not require PySide6,
  SoundCard, FFmpeg, Demucs, torch, model files, network, or Windows devices.

## Main-Agent Post-Review Fix

- Finding: Step 9 directly copied the finalized 48 kHz recording WAV to
  `_intermediate/input.wav`, bypassing the canonical stereo 44.1 kHz
  preparation required before `SeparationService.separate`.
- Fix: `run_recording` now calls `MediaService.probe` and
  `MediaService.extract_audio(recording.path, canonical_wav)`.
- Updated tests now assert recording probe/extract calls occur before
  separation.
- Reviewer re-review result: APPROVED, no blocking findings.
- Main agent completed final validation after reviewer re-review.
- Main-agent final checks:
  - Passed: `git diff --check`.
  - Passed: `PYTHONPATH=src python3 -m compileall -q src tests`.
  - Passed: `PYTHONPATH=src python3 -m music_decomp --version`
    - Output: `music-decomp 0.1.0`.
  - Not run successfully:
    `PYTHONPATH=src python3 -m pytest tests/test_file_pipeline.py tests/test_gui_shell.py tests/test_recorder_service.py`
    - Result: `/usr/bin/python3: No module named pytest`.
- No commit or push was performed by the executor or reviewer.
