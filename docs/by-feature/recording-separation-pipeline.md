# Recording Separation Pipeline

Date: 2026-06-24

Related execution plan step: [Step 9 - Wire End-To-End Recording Separation](step-by-step-execution-plan.md#step-9---wire-end-to-end-recording-separation)

## Status

Step 9 implementation is complete in this change set. The executor implemented
the recording separation pipeline, the separate reviewer approved it, the main
agent requested a canonical recording-input fix, the executor addressed it, and
reviewer re-review approved the revised work with no blocking findings. Real
Windows manual acceptance remains pending.

## Implemented Files

- `src/music_decomp/services/file_pipeline.py`
- `src/music_decomp/ui/workers.py`
- `src/music_decomp/ui/main_window.py`
- `tests/test_file_pipeline.py`
- `tests/test_gui_shell.py`

## Service Behavior

- `FileSeparationPipeline.run_recording(...)` accepts a finalized
  `MediaInput(kind="recording")`.
- Recording inputs are probed through `MediaService.probe` to validate audio
  stream metadata while preserving `kind="recording"`.
- Recording inputs create the same `SeparationJob`, output directory, job log,
  stem paths, and `job.json` metadata shape as file inputs.
- The finalized recording WAV is converted through
  `MediaService.extract_audio(recording.path, canonical_wav)` into the same
  canonical stereo 44.1 kHz `_intermediate/input.wav` used by file inputs.
- Probe failures create probe-failure artifacts; extraction or separation
  failures write failure metadata and a job log before raising
  `FileSeparationPipelineError`.
- File input behavior remains unchanged.

## GUI Wiring

- The Record tab refreshes output devices through `RecordingWorker` and
  `RecorderService.list_output_devices`.
- The default output-device combo option maps to `device_id=None`, letting
  `RecorderService` use the system default output device.
- Listed output devices pass their recorder device id to
  `RecorderService.start_recording`.
- Start and stop actions run through `RecordingWorker`, while actual audio
  capture stays on `RecorderService`'s background worker thread.
- A Qt timer polls `RecorderService.elapsed_seconds` and `peak_level` for the
  elapsed label and level meter.
- Stopping a recording stores the returned `MediaInput(kind="recording")` and
  enables the send-to-separation button.
- Sending a recording to separation starts `SeparationWorker(media_input=...)`,
  which calls `FileSeparationPipeline.run_recording`.

## Tests

Executor-added tests cover:

- successful recording pipeline flow with fake media and separation services
- recording pipeline probes the finalized WAV and calls fake
  `MediaService.extract_audio` before separation
- missing finalized recording WAV failure metadata and log writing
- rejecting non-recording media inputs in `run_recording`
- `SeparationWorker` routing recording inputs to `run_recording`
- `RecordingWorker` list/start/stop behavior through a fake recorder service

## Handoff Notes

- Normal tests remain fake-based and do not require PySide6, SoundCard,
  FFmpeg, Demucs, torch, model files, network, or Windows audio devices.
- The executor environment did not have `pytest`, so targeted pytest execution
  is still pending in a dev environment with test dependencies installed.
- Real Windows WASAPI loopback acceptance remains pending: record at least 30
  seconds of browser playback, then probe/separate the recorded WAV.
- Initial reviewer result: APPROVED, no blocking findings.
- Main-agent post-review canonicalization finding: addressed by probing and
  extracting recordings through `MediaService` before `SeparationService`.
- Reviewer re-review result: APPROVED, no blocking findings.
