# Windows Packaging

Date: 2026-06-24

Related execution plan step: [Step 12 - Package With PyInstaller](step-by-step-execution-plan.md#step-12---package-with-pyinstaller)

## Status

Step 12 implementation is complete in this change set as packaging
infrastructure. It adds the PyInstaller spec, Windows build script, Windows
smoke script, and portable package verifier. A real `dist/MusicDecomp/`
package has not been produced in this Linux environment because Step 12
requires Windows x64, real Windows dependency locks, staged FFmpeg binaries,
and staged Demucs model assets.

## Implemented Files

- `packaging/pyinstaller/music_decomp.spec`
- `packaging/windows/build.ps1`
- `packaging/windows/smoke-test.ps1`
- `scripts/verify_portable_package.py`
- `src/music_decomp/services/separation_service.py`
- `tests/test_synthetic_audio.py`

## Packaging Behavior

- PyInstaller one-folder output is `dist/MusicDecomp/`.
- `MusicDecomp.exe` is the windowed GUI executable.
- `music-decomp.exe` is the console CLI executable for smoke tests and batch
  commands.
- The generated PyInstaller entry script dispatches by executable name:
  `music-decomp.exe` runs the CLI and `MusicDecomp.exe` starts the GUI.
- The spec includes project code, PySide6, Demucs, Torch, Torchaudio, NumPy,
  SoundCard, `vendor/ffmpeg/`, `models/`, dependency manifests, requirements
  files, and discovered license files.
- The spec checks for required FFmpeg files, model manifest, model payload
  files, FFmpeg license/notice files, and importable runtime packages before
  packaging.

## Runtime Resource Behavior

- FFmpeg resolution already uses `resource_path("vendor/ffmpeg/bin/...")`, so
  packaged mode does not depend on system PATH for FFmpeg.
- Step 12 adds packaged model repository resolution in
  `SeparationService`/`DemucsSeparatorBackend`.
- Source mode without `models/manifest.json` keeps the previous Demucs default
  model behavior.
- Frozen mode without `models/manifest.json` raises
  `MissingModelResourceError`.
- When `models/manifest.json` exists, Demucs `Separator` receives
  `repo=str(resource_path("models"))`.

## Build Script

`packaging/windows/build.ps1`:

- requires Windows x64 and Python 3.11
- rejects placeholder `requirements/win-cpu.txt` or `requirements/win-cuda.txt`
  by default
- checks staged FFmpeg binaries, staged model manifest/payload files, and
  FFmpeg license/notice files
- installs requirements into a venv
- installs the project editable with no extra dependency resolution
- runs pytest unless `-SkipTests` is passed
- runs PyInstaller
- copies manifests, requirement files, and license files into the package
- runs `packaging/windows/smoke-test.ps1`

## Verification Script

`scripts/verify_portable_package.py` checks:

- GUI executable exists
- CLI executable exists
- bundled FFmpeg and FFprobe exist
- model manifest exists and is valid non-empty JSON
- dependency manifest exists
- license/notice files exist
- text launch/config files do not reference a source `.venv`
- on Windows, `music-decomp.exe --version` works from the package
- on Windows, bundled `ffprobe.exe -version` works
- on Windows, `music-decomp.exe probe` succeeds against a generated tiny WAV
  fixture with isolated PATH

`--structure-only` is available for non-Windows structural checks.

## Handoff Notes

- No `dist/`, `build/`, FFmpeg binaries, model weights, archives, generated
  media, virtual environments, or caches were committed.
- Real Step 12 acceptance still requires running `build.ps1` on Windows after
  real locks and assets are staged.
- Step 13 should use the package produced by `build.ps1`, not a source-mode
  checkout.
