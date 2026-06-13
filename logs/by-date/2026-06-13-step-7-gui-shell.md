# 2026-06-13 Step 7 GUI Shell Log

## Task

Executor assignment: implement only Step 7 - Build The GUI Shell.

Required verbatim user request recorded:

```text
继续执行
```

## Precheck

Command: `git status --short`

Result before Step 7 implementation:

```text
?? docs/codex-review/
```

No changed files existed outside `docs/codex-review/` before Step 7 work started. The executor did not touch `docs/codex-review/`.

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

- `src/music_decomp/app.py` now exposes `run_gui()` and keeps PySide6 imports lazy.
- `src/music_decomp/cli.py` now supports `gui`.
- Missing PySide6 is reported with an explicit optional `gui` extra install hint.
- `src/music_decomp/ui/main_window.py` defines inspectable `MAIN_WINDOW_TABS` and a lazy `MainWindow` factory.
- The main-window shell includes Files, Record, Jobs, and Settings tabs with the controls required by Step 7.
- The Files tab includes the short output note `Outputs include highest (approx.).`
- `src/music_decomp/ui/widgets.py` contains pure metadata types and Qt widget helper factories.
- `src/music_decomp/ui/workers.py` contains `MediaProbeWorker`, `RecordingWorker`, and `SeparationWorker`.
- Worker classes are background-capable through `QRunnable` when PySide6 exists and testable through fallback signals without PySide6.
- No actual Step 8/9 FFmpeg, Demucs, or SoundCard workflow was wired.

## Checks Run

- Passed: `.venv/bin/python -m pytest tests/test_gui_shell.py`
  - Result: 9 passed.

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

- Real GUI launch was not possible because `.venv` does not have PySide6 installed.
- GUI rendering, drag/drop, and file dialog behavior need manual validation after installing the optional `gui` extra.
- Worker classes are placeholders and intentionally do not execute heavy workflows yet.
- Step 8 still needs to wire local file probing, extraction, and separation into the shell.

## Result

Step 7 is complete. The executor implemented the GUI shell, the reviewer approved it with no blocking findings, and the main agent completed final validation before commit and push.
