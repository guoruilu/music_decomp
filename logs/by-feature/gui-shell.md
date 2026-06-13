# GUI Shell Log

Date: 2026-06-13

## Scope

Executor assignment: implement only Step 7 - Build The GUI Shell.

## Files Added Or Updated

- `pyproject.toml`
- `src/music_decomp/app.py`
- `src/music_decomp/cli.py`
- `src/music_decomp/ui/__init__.py`
- `src/music_decomp/ui/main_window.py`
- `src/music_decomp/ui/widgets.py`
- `src/music_decomp/ui/workers.py`
- `tests/test_gui_shell.py`
- `docs/INDEX.md`
- `docs/by-date/2026-06-13-step-7-gui-shell.md`
- `docs/by-date/2026-06-13-user-requirements.md`
- `docs/by-feature/gui-shell.md`
- `logs/INDEX.md`
- `logs/by-date/2026-06-13-step-7-gui-shell.md`
- `logs/by-feature/gui-shell.md`

## Implementation Notes

- Added `music_decomp.app.run_gui()` with lazy PySide6 import.
- Added `MissingGuiDependencyError` and a clear install hint for the optional `gui` extra.
- Added `gui` CLI subcommand while preserving top-level `--version`.
- Added optional dependency extra: `gui = ["PySide6>=6.6"]`.
- Added pure-Python `TabSpec`, `ControlSpec`, and `OptionSpec` metadata.
- Added main-window tabs: Files, Record, Jobs, Settings.
- Added Files tab controls for drag/drop, file picker, selected file details, output format, device, and start separation.
- Added Record tab controls for output device, refresh devices, record/stop, elapsed time, level meter, and send recording.
- Added Jobs tab controls for queue, progress, status, and open output folder.
- Added Settings tab controls for output root, FFmpeg status, model status, and CPU/GPU status.
- Added visible GUI error label for user-facing errors.
- Added `Outputs include highest (approx.).` as the shell's highest-stem approximation notice.
- Added worker abstractions for media probe, recording, and separation.
- Worker defaults are placeholder-only and do not call FFmpeg, Demucs, or SoundCard.
- Workers can use Qt signals and `QRunnable` when PySide6 is installed, or fallback test signals without PySide6.

## Checks Run

- Passed: `.venv/bin/python -m pytest tests/test_gui_shell.py`
  - Result: 9 passed.

Final validation is recorded below after docs/logs were updated.

## Final Validation

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

## Known Risks Or Incomplete Items

- PySide6 is not installed in `.venv`, so the real GUI was not manually launched.
- Drag/drop and file-picker widgets are implemented for the Qt path but not exercised by an installed-PySide6 GUI test in this environment.
- The separation, media probe, and recording workers are shell placeholders only.
- Step 8 must wire local file probing/extraction/separation.
- Step 9 must wire real system-audio recording and handoff to separation.
- `docs/codex-review/` remains user-owned untracked content and was not touched.

## Result

Step 7 is complete. The executor implemented the GUI shell, the reviewer approved it with no blocking findings, and the main agent completed final validation before commit and push.

Next step: Step 8 - Wire End-To-End File Separation.
