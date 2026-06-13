# GUI Shell

Date: 2026-06-13

Related execution plan step: [Step 7 - Build The GUI Shell](step-by-step-execution-plan.md#step-7---build-the-gui-shell)

## Status

Step 7 is complete. The executor implemented the GUI shell, the separate reviewer approved it with no blocking findings, and the main agent completed final validation. The GUI shell is intentionally limited to UI structure, lazy launch wiring, and placeholder background-capable workers. It does not run the Step 8 file-separation pipeline or the Step 9 recording pipeline.

## Implemented Files

- `src/music_decomp/app.py`
- `src/music_decomp/cli.py`
- `src/music_decomp/ui/__init__.py`
- `src/music_decomp/ui/main_window.py`
- `src/music_decomp/ui/widgets.py`
- `src/music_decomp/ui/workers.py`
- `tests/test_gui_shell.py`
- `pyproject.toml`

## Launch Behavior

- `python -m music_decomp gui` and the `music-decomp gui` console command route through `music_decomp.app.run_gui`.
- PySide6 is imported only on the GUI launch path.
- If PySide6 is missing, the GUI launch path reports:

```text
PySide6 is not installed. Install the optional GUI dependencies with `python -m pip install 'music-decomp[gui]'`.
```

- `pyproject.toml` declares `PySide6>=6.6` only under the optional `gui` extra.
- `python -m music_decomp --version` continues to work without PySide6.

## UI Structure

`src/music_decomp/ui/main_window.py` defines stable pure-Python tab/control specs so tests and future agents can inspect the GUI structure without importing PySide6.

Tabs:

- Files
- Record
- Jobs
- Settings

Files tab:

- drag/drop zone
- file picker button
- selected file details
- output format selector: WAV, FLAC, MP3
- device selector: Auto, CPU, CUDA
- start separation button
- short output note: `Outputs include highest (approx.).`

Record tab:

- output device selector
- refresh devices button
- record/stop button
- elapsed time label
- level meter
- send recording to separation button, enabled after placeholder stop

Jobs tab:

- current queue list
- progress text
- status text
- open output folder button

Settings tab:

- output root selector
- FFmpeg status
- model status
- CPU/GPU status

## Worker Design

`src/music_decomp/ui/workers.py` defines:

- `MediaProbeWorker`
- `RecordingWorker`
- `SeparationWorker`
- `WorkerState`
- `WorkerUpdate`
- `WorkerOutcome`

The worker classes can be instantiated and tested without PySide6. When PySide6 is available, each worker can be wrapped as a `QRunnable` for `QThreadPool`; signals are Qt signals when PySide6 is present and fallback test signals otherwise.

Default worker behavior is placeholder-only:

- no FFprobe call
- no FFmpeg extraction
- no Demucs model load
- no SoundCard recording

## Error Handling

- Missing PySide6 is shown as a clear CLI/app error that names the optional `gui` extra.
- The GUI shell includes a visible global error label.
- Starting separation with no selected file shows an in-window error.
- Opening an unavailable output folder shows an in-window error.

## Tests

`tests/test_gui_shell.py` covers:

- `--version` still exits successfully.
- `gui` command routes to the app GUI launch path.
- missing PySide6 returns a readable missing-`gui`-extra message.
- main-window tab/control specs are stable without PySide6.
- output format options are WAV, FLAC, MP3.
- worker classes expose expected names, states, placeholder results, and fallback signals without PySide6.
- QRunnable adapter raises a clear missing-PySide6 error when PySide6 is absent.

## Handoff Notes

- No real PySide6 launch was run because `.venv` does not have PySide6 installed by assignment.
- No screenshots or generated build artifacts were created.
- `docs/codex-review/` existed as user-owned untracked content and was not touched.
- Next step: Step 8 - Wire End-To-End File Separation.
