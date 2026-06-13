# Recorder Service

Date: 2026-06-13

Related execution plan step: [Step 6 - Implement RecorderService](step-by-step-execution-plan.md#step-6---implement-recorderservice)

## Status

Step 6 is complete. The executor implemented the recorder service, the separate reviewer approved it with no blocking findings, and the main agent completed final validation.

## Implemented Files

- `src/music_decomp/services/recorder_service.py`
- `src/music_decomp/services/__init__.py`
- `tests/test_recorder_service.py`
- `pyproject.toml`

## Behavior

- `RecorderService` exposes:
  - `list_output_devices()`
  - `default_output_device()`
  - `start_recording(device_id, output_path)`
  - `stop_recording()`
  - `is_recording`
  - `elapsed_seconds`
  - `peak_level`
- Default recording format is stereo 48 kHz WAV.
- Recording always runs on a background worker thread named `RecorderServiceWorker`.
- When `output_path` is omitted, the service writes under `recordings/YYYYMMDD-HHMMSS-recording.wav`.
- The default recordings root is injectable for tests, so normal pytest does not create repository-level `recordings/` output.
- `stop_recording()` finalizes the WAV writer and returns `MediaInput(kind="recording", path=...)`.
- `peak_level` reports the latest active chunk peak clipped to `0.0..1.0`; lifecycle reset clears it after stop.
- `elapsed_seconds` is computed from an injectable clock for deterministic tests and future UI display.

## Backend And Dependencies

- Real device enumeration and recording use `SoundCardLoopbackBackend`.
- `soundcard` is imported lazily only when the SoundCard backend is used.
- The backend enumerates output speakers through `all_speakers()` and maps the default speaker through `default_speaker()`.
- Recording opens the selected output device through `get_microphone(device_id, include_loopback=True)` and records with `channels=2`, `samplerate=48000`, and chunked `record(numframes=...)`.
- WAV writing uses `StdlibWaveWriter` based on Python `wave`, so normal tests and source-mode imports do not require `soundfile`.
- `pyproject.toml` declares `SoundCard>=0.4.6` only in the optional `recorder` extra.

## Error Handling

If the selected loopback device cannot be opened or fails when the worker enters the SoundCard recorder, the service raises:

```text
System audio recording is unavailable for this output device. Try another output device or use a local file.
```

Stopping when no recording is active raises `RecorderStateError`.

## Tests

- Mocked SoundCard speaker enumeration and default-device mapping.
- Service output-device listing and default-device behavior.
- Mocked recording chunks verify stereo frame delivery to the WAV writer.
- `stop_recording()` returns a `MediaInput` with recording metadata.
- Inactive `stop_recording()` state error.
- Default path naming with injected clock and recordings root.
- Required unavailable-loopback message for open-time and worker-time failure.
- Background worker thread behavior without blocking `start_recording()` until stop.
- `StdlibWaveWriter` writes a readable stereo 48 kHz PCM WAV.

## Handoff Notes

- No manual Windows WASAPI/browser playback test was run in this Linux executor environment.
- The implementation is intentionally limited to the recorder service; GUI wiring remains a later step.
- `docs/codex-review/` existed as user-owned untracked content and was not modified.
- Next step: Step 7 - Build The GUI Shell.
