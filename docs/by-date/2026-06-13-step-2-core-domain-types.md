# 2026-06-13 Step 2 Core Domain Types

## User Requirement Recorded

The required verbatim user request was added to `docs/by-date/2026-06-13-user-requirements.md`:

```text
继续执行
```

## Scope

Executor assignment: implement only Step 2 - Add Core Domain Types from `docs/by-feature/step-by-step-execution-plan.md`.

## Implemented

- Added the `music_decomp.domain` package.
- Added `MediaInput` for audio, video, and recording inputs.
- Added `SeparationJob` with conservative defaults:
  - model: `htdemucs`
  - output format: `wav`
  - stems: `vocals`, `drums`, `bass`, `other`, `lowest`, `highest`
  - device: `auto`
- Added `JobResult` for output file, metadata, and log paths.
- Converted path-like values to `pathlib.Path` in domain `__post_init__` methods.
- Added early `ValueError` validation for unsupported device and output format values.
- Added focused unit tests for defaults, path conversion, and invalid device/format handling.

## Status

- Executor subagent completed the Step 2 implementation.
- Reviewer subagent approved the work with no blocking findings.
- Main agent completed final validation and will commit/push the accepted result.

## Validation

- Passed: `.venv/bin/python -m pytest`
  - Result: 11 tests passed.
- Passed: `.venv/bin/python -m music_decomp --version`
  - Result: `music-decomp 0.1.0`.
- Passed: `.venv/bin/python --version`
  - Result: `Python 3.12.9`.
- Passed: `git diff --check`.
- Ran: `git status --short`
  - Result: expected Step 2 modified/untracked files only.
- Reviewer checks also passed:
  - `.venv/bin/python -m pytest`: 11 tests passed.
  - `git status --short --ignored`: only expected Step 2 files plus ignored cache/env artifacts.
  - tracked generated artifact scan: no matches.

## Next Action

Start Step 3 from the detailed execution plan: implement FFmpeg media handling.
