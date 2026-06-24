# Windows Packaging Log

Date: 2026-06-24

## Scope

Executor assignment: implement only Step 12 - Package With PyInstaller.

Constraints followed:

- no real Windows package generated in Linux
- no `dist/` or `build/` artifacts committed
- no FFmpeg binaries, model weights, archives, generated media, virtual
  environments, or caches committed
- no Step 13 offline acceptance claim
- no commit or push by executor or reviewer

## Files Added Or Updated

- `packaging/pyinstaller/music_decomp.spec`
- `packaging/windows/build.ps1`
- `packaging/windows/smoke-test.ps1`
- `scripts/verify_portable_package.py`
- `src/music_decomp/services/separation_service.py`
- `tests/test_synthetic_audio.py`
- `docs/INDEX.md`
- `docs/by-date/2026-06-24-step-12-windows-packaging.md`
- `docs/by-feature/current-project-status.md`
- `docs/by-feature/windows-packaging.md`
- `logs/INDEX.md`
- `logs/by-date/2026-06-24-step-12-windows-packaging.md`
- `logs/by-feature/windows-packaging.md`
- `README.md`

## Implementation Notes

- The PyInstaller spec writes a generated entry file under ignored `build/`.
- The generated entry dispatches by executable name, so the GUI executable does
  not run CLI code through a windowed/no-console process.
- `build.ps1` rejects placeholder locks unless explicitly overridden for a
  non-reproducible local build.
- `build.ps1` requires staged FFmpeg binaries, model manifest/payload files,
  and FFmpeg license/notice files before packaging.
- The verifier supports `--structure-only` for non-Windows checks and stronger
  executable checks on Windows.
- The verifier runs bundled `ffprobe.exe -version` and probes a generated tiny
  WAV through packaged `music-decomp.exe`.
- Runtime separation now passes the bundled `models/` repository to Demucs
  when `models/manifest.json` exists.

## Checks Run During Implementation

- Passed: `python3 -m py_compile scripts/verify_portable_package.py packaging/pyinstaller/music_decomp.spec src/music_decomp/services/separation_service.py tests/test_synthetic_audio.py`.
- Passed: `PYTHONPATH=src python3 -m compileall -q src tests scripts packaging/pyinstaller`.
- Passed: `python3 scripts/verify_portable_package.py --help`.
- Passed: structure-only fake package verification.
- Passed: `git diff --check`.
- Not run successfully: `PYTHONPATH=src python3 -m pytest`
  - Result: `/usr/bin/python3: No module named pytest`.
- Not run: Windows `build.ps1` or GUI smoke because this environment is not
  Windows and has no staged packaging assets.

## Reviewer Outcome

- Initial result: three blocking findings.
- Executor fixed packaged model runtime resolution, removed GUI executable CLI
  smoke, and strengthened FFprobe validation.
- Re-review result: APPROVED, no blocking findings.

## Known Risks Or Incomplete Items

- Real Windows packaging remains untested in this environment.
- Real PyInstaller collection behavior for PySide6, Torch, Torchaudio, and
  Demucs must be validated on Windows x64 Python 3.11.
- Real Windows lock files, FFmpeg assets, model assets, and license files must
  be staged before `build.ps1` can succeed.
- Step 13 offline acceptance remains pending.
