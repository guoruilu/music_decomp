# 2026-06-13 Step 7 GUI Shell

## User Requirement Recorded

The required verbatim user request was added to `docs/by-date/2026-06-13-user-requirements.md`:

```text
继续执行
```

## Initial Worktree Check

Before implementing Step 7, `git status --short` showed only:

```text
?? docs/codex-review/
```

`docs/codex-review/` was treated as user-owned untracked content and was not modified, removed, staged, or otherwise touched.

## Scope

Executor assignment: implement only Step 7 - Build The GUI Shell from `docs/by-feature/step-by-step-execution-plan.md`.

## Implemented

- Added GUI launch path through `music_decomp.app.run_gui`.
- Added `music-decomp gui` / `python -m music_decomp gui` CLI routing.
- Kept PySide6 imports lazy so normal imports and tests pass without PySide6 installed.
- Added optional `gui` extra with `PySide6>=6.6`.
- Added `src/music_decomp/ui/` package.
- Added stable pure-Python tab/control specs for Files, Record, Jobs, and Settings.
- Added a Qt main-window factory that builds the required compact desktop controls when PySide6 is installed.
- Added drag/drop file zone and file picker shell behavior.
- Added output format selector with WAV, FLAC, MP3.
- Added device selector with Auto, CPU, CUDA.
- Added placeholder separation action that runs through a background-capable `SeparationWorker` and updates job progress/status.
- Added record-tab placeholder controls for output device, refresh, record/stop, elapsed time, level meter, and send-to-separation.
- Added jobs-tab shell controls for queue, progress, status, and open output folder.
- Added settings-tab shell controls for output root, FFmpeg status, model status, and CPU/GPU status.
- Added visible GUI error status for missing selected file and unavailable output folder.
- Added `highest` approximate wording through `Outputs include highest (approx.).`
- Added shell worker classes for media probing, recording, and separation.
- Added tests that validate behavior without real PySide6.

## Status

- Executor implementation and local focused validation are complete.
- Separate reviewer inspection approved the implementation with no blocking findings.
- Main agent completed final validation and will commit/push the accepted result.

## Validation

- Passed: `.venv/bin/python -m pytest tests/test_gui_shell.py`
  - Result: 9 passed.
- Passed: `.venv/bin/python -m pytest`
  - Result: 55 passed, 1 skipped.
- Passed: `.venv/bin/python -m music_decomp --version`
  - Output: `music-decomp 0.1.0`.
- Passed: `git diff --check`
  - Result: no whitespace errors.
- Expected missing-dependency result: `.venv/bin/python -m music_decomp gui`
  - Exit code: 1 because PySide6 is not installed in `.venv`.
  - Output:

```text
PySide6 is not installed. Install the optional GUI dependencies with `python -m pip install 'music-decomp[gui]'`.
```

- Ran: `git status --short`
  - Result: expected Step 7 files plus pre-existing untracked `docs/codex-review/`.
- Reviewer checks also passed:
  - `.venv/bin/python -m pytest -p no:cacheprovider`: 55 tests passed, 1 skipped.
  - `.venv/bin/python -m music_decomp --version`: `music-decomp 0.1.0`.
  - `.venv/bin/python -m music_decomp gui`: exited 1 with the expected missing-PySide6 optional-extra message.
  - `.venv/bin/music-decomp gui`: exited 1 with the same expected message.
  - `git diff --check`: passed.
  - `docs/codex-review/` remained untracked and unstaged.

## Deviations

- PySide6 was added only as optional `gui` extra because the current `.venv` does not have PySide6 installed.
- GUI launch was not manually opened in this environment.
- Separation, media probing, and recording workers are placeholders only; actual service wiring remains Step 8 and Step 9.
- The shell uses fallback signals in tests and Qt signals/QRunnable only when PySide6 is present.

## Next Action

Start Step 8 from the detailed execution plan: wire local file probing, extraction, and separation into the GUI shell.
