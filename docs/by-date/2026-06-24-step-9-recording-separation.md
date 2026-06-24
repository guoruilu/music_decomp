# 2026-06-24 Step 9 Recording Separation

## Scope

Executor subagent implementation for Step 9 - Wire End-To-End Recording
Separation.

## Changes Drafted

- Added `FileSeparationPipeline.run_recording(...)` for finalized
  `MediaInput(kind="recording")` inputs.
- Reused the existing `SeparationJob`, `ExportService`, `SeparationService`,
  progress, log, metadata, and worker flow for recordings.
- Probed finalized recording WAV files through `MediaService.probe`.
- Extracted finalized recording WAV files through `MediaService.extract_audio`
  so `_intermediate/input.wav` remains the canonical stereo 44.1 kHz model
  input.
- Replaced the Record tab placeholder controls with real device refresh,
  record, stop, elapsed/peak polling, and send-to-separation actions.
- Extended `RecordingWorker` to list devices, start recording, and stop
  recording through an injectable recorder service.
- Extended `SeparationWorker` to route recording media inputs to
  `FileSeparationPipeline.run_recording`.
- Added fake-based tests for the recording pipeline and GUI workers.

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

## Pending

- Real Windows GUI/WASAPI manual acceptance with browser playback and a real
  separation backend.

## Reviewer Notes

- Initial separate reviewer result: APPROVED, no blocking findings.
- Reviewer confirmed that the Record tab routes device refresh/start/stop
  through `RecordingWorker` and `RecorderService`, stopped recordings are
  stored as `MediaInput(kind="recording")`, and recording separation uses the
  same `SeparationJob`/pipeline path.
- Reviewer confirmed tests are fake-based and avoid real PySide6, SoundCard,
  FFmpeg, Demucs, torch, model files, network, or Windows audio devices.

## Main-Agent Post-Review Fix

- Finding: RecorderService defaults to 48 kHz recordings, while
  `SeparationService` expects the canonical stereo 44.1 kHz WAV normally
  produced by `MediaService`.
- Fix: `FileSeparationPipeline.run_recording(...)` now probes the finalized
  recording and calls `MediaService.extract_audio(recording.path,
  canonical_wav)` before `SeparationService.separate`.
- Tests/docs were updated so the recording path no longer claims to avoid
  FFprobe/FFmpeg extraction.
- Reviewer re-review result: APPROVED, no blocking findings.

## Main-Agent Finalization

- Main agent completed final validation after reviewer re-review.
- Passed: `git diff --check`.
- Passed: `PYTHONPATH=src python3 -m compileall -q src tests`.
- Passed: `PYTHONPATH=src python3 -m music_decomp --version`
  - Output: `music-decomp 0.1.0`.
- Not run successfully:
  `PYTHONPATH=src python3 -m pytest tests/test_file_pipeline.py tests/test_gui_shell.py tests/test_recorder_service.py`
  - Result: `/usr/bin/python3: No module named pytest`.
- Commit and push are handled by the main agent after documentation/log updates.
