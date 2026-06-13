# Core Domain Types

Date: 2026-06-13

Related execution plan step: [Step 2 - Add Core Domain Types](step-by-step-execution-plan.md#step-2---add-core-domain-types)

## Status

Step 2 is complete. The executor implemented the domain models, the separate reviewer approved the work with no blocking findings, and the main agent completed final validation.

## Implemented Files

- `src/music_decomp/domain/__init__.py`
- `src/music_decomp/domain/media.py`
- `src/music_decomp/domain/jobs.py`
- `tests/test_domain_models.py`

## Domain Models

- `MediaInput(kind, path, title, duration_seconds=None, sample_rate=None)`
- `SeparationJob(input, output_dir, device="auto", model_name="htdemucs", output_format="wav", stems=DEFAULT_STEMS)`
- `JobResult(job, output_files, metadata_path, log_path)`

## Behavior

- Path-like values are converted to `pathlib.Path` before storage.
- Default stems are `vocals`, `drums`, `bass`, `other`, `lowest`, and `highest`.
- Unsupported separation devices raise `ValueError`.
- Unsupported output formats raise `ValueError`.
- The implementation does not add audio, GUI, model, FFmpeg, or packaging dependencies.

## Handoff Notes

- This step only defines shared domain types.
- Later services should import these types from `music_decomp.domain`.
- Step 3 should build FFmpeg media handling on top of `MediaInput` without changing the Step 2 defaults unless the plan changes.
- Next step: Step 3 - Implement MediaService With FFmpeg.
