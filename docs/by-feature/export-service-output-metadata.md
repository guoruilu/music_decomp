# Export Service Output Metadata

Date: 2026-06-13

Related execution plan step: [Step 4 - Implement Output Directory And Metadata](step-by-step-execution-plan.md#step-4---implement-output-directory-and-metadata)

## Status

Step 4 is complete. The executor implemented output metadata support, the separate reviewer approved it with no findings, and the main agent completed final validation.

## Implemented Files

- `src/music_decomp/services/export_service.py`
- `src/music_decomp/services/__init__.py`
- `src/music_decomp/utils/logging.py`
- `tests/test_export_service.py`

## Behavior

- `ExportService` defaults to `outputs/` under `project_root()` when no output root is passed.
- Callers can pass an explicit output root to `ExportService(...)` or to `prepare_job(..., output_root=...)`; this is the hook intended for GUI-selected destinations.
- Job directories use `YYYYMMDD-HHMMSS-safe_input_title/`.
- `safe_filename(...)` replaces Windows-invalid filename characters: `< > : " / \ | ? *`.
- `prepare_job(...)` creates the timestamped job directory, creates an empty plain UTF-8 `job.log`, and returns a `JobResult` with `job.json` and stem output paths.
- `build_stem_output_paths(...)` returns expected stem paths without writing generated media files.
- `write_job_metadata(...)` writes UTF-8 JSON metadata for success and failure states.
- `write_text_log(...)` and `append_text_log(...)` write plain UTF-8 text with LF newlines.

## Metadata Fields

`job.json` includes:

- `app_version`
- `input_path`
- `input_title`
- `input_kind`
- `input_duration_seconds`
- `input_sample_rate`
- `model_name`
- `requested_device`
- `actual_device`
- `output_format`
- `stem_filenames`
- `start_timestamp`
- `end_timestamp`
- `status`
- `error_message` when provided for failures

## Tests

- Safe filename replacement and fallback behavior.
- Default source-mode output root under `outputs/`.
- Explicit caller-selected output root.
- Timestamped job directory creation.
- `job.json`, `job.log`, and stem path construction.
- Required success metadata fields.
- Failure metadata with error message.
- Plain UTF-8 job log bytes.

## Handoff Notes

- No generated audio files, model weights, FFmpeg binaries, build artifacts, or output directories were committed.
- Tests use `tmp_path` and fixed clocks; no real media, FFmpeg, or Demucs calls are made.
- `docs/codex-review/` existed as user-owned untracked content before this work and was not modified.
- Next step: Step 5 - Implement SeparationService.
