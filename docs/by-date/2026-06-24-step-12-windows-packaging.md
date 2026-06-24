# 2026-06-24 Step 12 Windows Packaging

## Scope

Executor subagent implementation for Step 12 - Package With PyInstaller.

## Changes Drafted

- Added a PyInstaller one-folder spec for `dist/MusicDecomp/`.
- Added a Windows build script that checks Windows x64 Python 3.11, usable
  dependency locks, staged FFmpeg/model assets, tests, PyInstaller execution,
  manifest/license copying, and portable verification.
- Added a Windows smoke script that runs verifier checks with an isolated
  runtime environment and optionally launches the GUI.
- Added a portable package verifier for executable, FFmpeg, model manifest,
  dependency manifest, license, `.venv` reference, version, and bundled FFprobe
  checks.
- Wired packaged Demucs model resolution through `resource_path("models")` and
  the Demucs `Separator(repo=...)` argument.
- Added tests for packaged model repo resolution and Demucs separator cache
  behavior.

## Validation

- Passed: `python3 -m py_compile scripts/verify_portable_package.py packaging/pyinstaller/music_decomp.spec src/music_decomp/services/separation_service.py tests/test_synthetic_audio.py`
- Passed: `PYTHONPATH=src python3 -m compileall -q src tests scripts packaging/pyinstaller`
- Passed: `python3 scripts/verify_portable_package.py --help`
- Passed: `python3 scripts/verify_portable_package.py --package-dir <fake-package> --structure-only`
- Passed: `git diff --check`
- Not run successfully: `PYTHONPATH=src python3 -m pytest`
  - Result: `/usr/bin/python3: No module named pytest`
- Not run: real Windows PyInstaller build and GUI smoke
  - Reason: current environment is Linux and does not contain staged Windows
    FFmpeg/model assets or generated Windows lock files.

## Reviewer Notes

- Initial reviewer result: blocking findings.
- Finding 1: copied `models/` were not used by runtime separation.
- Finding 2: windowed `MusicDecomp.exe` was used for CLI smoke.
- Finding 3: FFprobe validation could false-pass.
- Executor fixed all three findings.
- Reviewer re-review result: APPROVED, no blocking findings.

## Main-Agent Finalization

- Main agent updated docs/logs indexes, current status, and README.
- Commit and push are handled by the main agent after final checks.
