# 2026-06-13 Step 6 Recorder Service

## User Requirement Recorded

The required verbatim user request was added to `docs/by-date/2026-06-13-user-requirements.md`:

```text
继续执行
```

## Initial Worktree Check

Before implementing Step 6, `git status --short` showed only:

```text
?? docs/codex-review/
```

`docs/codex-review/` was treated as user-owned untracked content and was not modified, removed, staged, or otherwise touched.

## Scope

Executor assignment: implement only Step 6 - Implement RecorderService from `docs/by-feature/step-by-step-execution-plan.md`.

## Implemented

- Added `RecorderService` with `list_output_devices()`, `default_output_device()`, `start_recording(...)`, `stop_recording()`, `is_recording`, `elapsed_seconds`, and `peak_level`.
- Added injectable backend and WAV writer protocols for deterministic Linux/unit testing.
- Added `SoundCardLoopbackBackend` with lazy `soundcard` import.
- Added Windows WASAPI loopback path through `get_microphone(device_id, include_loopback=True)`.
- Added stereo 48 kHz default recording with chunked background worker capture.
- Added default output path naming under `recordings/YYYYMMDD-HHMMSS-recording.wav`.
- Added explicit output path support for tests and future UI.
- Added stdlib `wave`-based stereo PCM WAV writer, avoiding mandatory `soundfile`.
- Added exact unavailable-loopback message for open-time and worker-time failures.
- Added `MediaInput(kind="recording", path=...)` return on stop.
- Exported `RecorderService` from `music_decomp.services`.
- Declared `SoundCard>=0.4.6` only under the optional `recorder` extra.
- Added focused mocked tests in `tests/test_recorder_service.py`.

## Status

- Executor implementation and local validation are complete.
- Separate reviewer inspection approved the implementation with no blocking findings.
- Main agent completed final validation and will commit/push the accepted result.

## Validation

- Passed: `.venv/bin/python -m pytest tests/test_recorder_service.py`
  - Result after initial test file: 8 passed.
  - Result after worker-side failure coverage: 9 passed.
- Passed: `.venv/bin/python -m pytest`
  - Interim result before final docs: 45 passed, 1 skipped.
- Passed: `.venv/bin/python -m pytest`
  - Final result after Step 6 docs/logs: 46 passed, 1 skipped.
- Passed: `.venv/bin/python -m music_decomp --version`
  - Output: `music-decomp 0.1.0`.
- Passed: `git diff --check`
  - Result: no whitespace errors.
- Ran: `git status --short`
  - Result: expected Step 6 files plus pre-existing untracked `docs/codex-review/`.
- Reviewer checks also passed:
  - `.venv/bin/python -m pytest -p no:cacheprovider`: 46 tests passed, 1 skipped.
  - `.venv/bin/python -m music_decomp --version`: `music-decomp 0.1.0`.
  - `git diff --check`: passed.
  - Lazy import check confirmed `soundcard` is not loaded by importing `music_decomp.services`.
  - `docs/codex-review/` remained untracked and unstaged.

## Deviations

- The implementation uses Python stdlib `wave` instead of `soundfile`, so normal tests do not require recorder/audio dependencies.
- `SoundCard` is optional under the `recorder` extra instead of a mandatory project dependency.
- No manual Windows WASAPI/browser playback test was run in this Linux executor environment.
- `peak_level` is live worker state and resets after the recording lifecycle ends.

## Next Action

Start Step 7 from the detailed execution plan: build the GUI shell.
