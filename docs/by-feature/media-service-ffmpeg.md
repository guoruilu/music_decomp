# FFmpeg Media Service

Date: 2026-06-13

Related execution plan step: [Step 3 - Implement MediaService With FFmpeg](step-by-step-execution-plan.md#step-3---implement-mediaservice-with-ffmpeg)

## Status

 Step 3 executor implementation is complete after addressing the first reviewer change request. Reviewer re-check, final main-agent validation, commit, and push are still pending.

## Implemented Files

- `src/music_decomp/config.py`
- `src/music_decomp/services/__init__.py`
- `src/music_decomp/services/media_service.py`
- `src/music_decomp/utils/__init__.py`
- `src/music_decomp/utils/subprocesses.py`
- `tests/test_media_service.py`
- `tests/fixtures/ffprobe_audio.json`
- `tests/fixtures/ffprobe_video.json`

## Behavior

- FFmpeg path resolution checks `MUSIC_DECOMP_FFMPEG`, then `vendor/ffmpeg/bin/ffmpeg.exe`, then system `ffmpeg` only when not frozen.
- FFprobe path resolution checks `MUSIC_DECOMP_FFPROBE`, then `vendor/ffmpeg/bin/ffprobe.exe`, then system `ffprobe` only when not frozen.
- `MediaService.probe(path)` runs FFprobe with JSON output:

```text
ffprobe -v error -print_format json -show_format -show_streams INPUT
```

- `MediaService.extract_audio(input_path, output_wav)` runs FFmpeg list arguments equivalent to:

```text
ffmpeg -y -i INPUT -vn -ac 2 -ar 44100 -sample_fmt s16 OUTPUT.wav
```

- `MediaService.detect_kind(path)` returns `video` when any video stream exists and `audio` when audio streams exist without video streams.
- Subprocess calls use list arguments and reject shell-string commands.
- Failed subprocesses raise `CommandExecutionError` with the executable path, exit code, and stderr tail.

## Tests

- Tests mock subprocess execution and do not require real FFmpeg.
- Tests cover FFmpeg/FFprobe path resolution order, development-only system fallback, explicit missing FFmpeg and missing FFprobe errors, FFprobe fixture JSON parsing, media kind detection, command construction, shell-string rejection, and subprocess error message contents.

## Validation

- Passed: `.venv/bin/python -m pytest`
  - Result: 22 tests passed after reviewer-requested missing-FFprobe coverage was added.
- Passed: `.venv/bin/python -m music_decomp --version`
  - Result: `music-decomp 0.1.0`.
- Passed: `git diff --check`.
- Ran: `git status --short`.
  - Result: expected Step 3 files plus pre-existing untracked `docs/codex-review/`.
- Ran: `git status --ignored --short`.
  - Result: expected Step 3 files, pre-existing untracked `docs/codex-review/`, and ignored cache/env artifacts.

Additional final checks are recorded in `logs/by-date/2026-06-13-step-3-media-service.md`.

## Handoff Notes

- No audio, model, GUI, or packaging dependencies were added.
- No real FFmpeg invocation or manual media extraction was run in this executor step.
- `docs/codex-review/` existed as user-owned untracked content before this work and was not modified.
- Next workflow action: main agent should return the updated Step 3 diff to the separate reviewer subagent.
