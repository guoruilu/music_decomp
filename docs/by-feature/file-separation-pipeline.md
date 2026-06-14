# File Separation Pipeline

Date: 2026-06-14

Related execution plan step: [Step 8 - Wire End-To-End File Separation](step-by-step-execution-plan.md#step-8---wire-end-to-end-file-separation)

## Status

Step 8 implementation is complete. The executor implemented the file-separation pipeline, the separate reviewer requested two fixes, the executor addressed them, and reviewer re-review approved the step. `docs/codex-review/` remained user-owned and was not read or modified.

## Implemented Files

- `src/music_decomp/services/file_pipeline.py`
- `src/music_decomp/services/export_service.py`
- `src/music_decomp/services/__init__.py`
- `src/music_decomp/ui/workers.py`
- `src/music_decomp/ui/main_window.py`
- `tests/test_file_pipeline.py`
- `tests/test_gui_shell.py`

## Service Behavior

`FileSeparationPipeline` coordinates the local-file flow:

1. `probe_input(path)` calls `MediaService.probe`.
2. FFprobe JSON is normalized into `MediaProbeResult`.
3. The parser requires at least one audio stream.
4. Inputs with a video stream are classified as `video`; audio-only inputs are classified as `audio`.
5. Duration, sample rate, title, stream summaries, and raw probe data are retained for GUI display and debugging.
6. `run_file(...)` creates a timestamped job directory through `ExportService`.
   If a same-second directory already exists, `ExportService` creates a suffixed
   directory such as `-2` or `-3`.
7. The canonical WAV is written to `job_dir/_intermediate/input.wav`.
8. `SeparationService.separate` writes the requested stems.
9. `ExportService.write_job_metadata` writes `job.json`.
10. The returned `FileSeparationResult` includes the probe result, job result, separation result, output directory, log path, metadata path, and `highest_is_approximate`.

## Failure Behavior

- Probe failures in `run_file` create a failure job directory under the selected output root.
- Probe failures from GUI selection also create failure artifacts through `MediaProbeWorker` and include the log path in the visible failure message.
- Probe failures write `job.log` and a failure `job.json` with `failure_stage: probe`.
- Failures after a job is prepared append the error to `job.log` and write failure metadata through `ExportService.write_job_metadata`.
- The raised `FileSeparationPipelineError` carries `stage`, `output_dir`, `log_path`, and `metadata_path` when available so GUI callers can surface useful paths.

## GUI Wiring

- File selection and drag/drop now start a `MediaProbeWorker`.
- Successful probe results update the selected-file label with kind, duration, sample rate, and stream summaries.
- `SeparationWorker` now defaults to the real file pipeline and still supports injected operations or fake pipelines for tests.
- Pipeline progress is translated to `WorkerUpdate` signals.
- Pipeline failures that carry `log_path` or `output_dir` include that path in the worker failure message shown by the GUI.
- Successful separation sets `current_output_folder` to the real output directory.
- The UI continues to label `highest` as approximate through `Outputs include highest (approx.).`

## Tests

Executor-added tests cover:

- audio and video probe parsing
- missing audio stream rejection
- successful `run_file` log, metadata, canonical WAV, progress, and output paths
- same-second repeated file runs produce `...-song` and `...-song-2`, both with log and metadata
- probe failure artifact creation
- GUI-adjacent probe worker failure artifact creation without PySide6
- separation failure log and failure metadata
- worker fallback signals with fake pipeline and no PySide6
- worker failure message formatting with log path
- probe summary formatting without PySide6

## Handoff Notes

- Tests intentionally do not require real PySide6, FFmpeg, Demucs, torch, model files, or network access.
- Real Windows manual acceptance remains necessary with bundled/configured FFmpeg and an actual short audio/video file.
- Step 9 recording end-to-end wiring was not implemented.
- Packaging work was not implemented.
