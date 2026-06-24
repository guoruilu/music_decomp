# Music Decomp

Music Decomp is a planned Windows offline desktop application for separating
local music and recorded system audio into stems. The target delivery is a
portable Windows folder that runs without installing Python, FFmpeg, Demucs, or
other tools on the user machine.

## Current Status

- Package name: `music-decomp`
- Import package: `music_decomp`
- Console script: `music-decomp`
- Current implementation step: Step 12, Windows PyInstaller packaging
- Latest committed baseline before this Step 12 change set:
  `6ac49b7 Document dependency and asset manifest`

Implemented so far:

- Python project scaffold and path helpers.
- Core media and job domain models.
- FFmpeg/FFprobe media probing and audio extraction service.
- Output directory, job log, and `job.json` metadata service.
- Demucs-backed separation service with derived `lowest` and approximate
  `highest` outputs.
- System-audio recorder service with mocked test coverage.
- PySide6 GUI shell with Files, Record, Jobs, and Settings tabs.
- End-to-end local audio/video file pipeline wired into the GUI worker layer.
- Recording-to-separation GUI flow wired through `RecorderService` and the
  shared separation pipeline.
- CLI workflows for `gui`, `probe`, `separate`, and
  `list-recording-devices`, with JSON success output and readable default
  errors.
- Dependency input files and asset manifest scaffolding for future Windows
  CPU/CUDA locks, FFmpeg staging, and Demucs model checksum tracking.
- Windows PyInstaller packaging scripts, one-folder spec, portable verifier,
  and packaged model-resource resolution.

Not complete yet:

- Real Windows dependency locks, a built `dist/MusicDecomp/` package, offline
  acceptance testing, and user documentation are still pending.
- Real Windows manual acceptance with bundled/configured FFmpeg, Demucs, model
  files, and WASAPI loopback has not been completed.

## Development

Run source-mode checks from the repository root:

```bash
PYTHONPATH=src python3 -m music_decomp --version
PYTHONPATH=src python3 -m compileall -q src tests
```

When local development dependencies are installed, run:

```bash
python3 -m pip install -e .[dev]
PYTHONPATH=src python3 -m pytest
```

Optional feature extras are declared in `pyproject.toml`:

- `gui`: PySide6 GUI dependency.
- `separation`: Demucs, Torch, Torchaudio, and NumPy dependencies.
- `recorder`: SoundCard dependency for system-audio recording.

Step 11 also adds `requirements/base.in` as the direct dependency input for
future Windows lock generation. The CPU/CUDA lock files are placeholders until
they are generated and validated on a Windows x64 Python 3.11 build machine.

Step 12 adds packaging entry points:

```bash
python3 scripts/verify_portable_package.py --help
```

The real package build must run on Windows:

```powershell
.\packaging\windows\build.ps1 -Profile cpu
```

## Documentation

Start with these files:

- [Project agent index](AGENTS.md)
- [Documentation index](docs/INDEX.md)
- [Current project status](docs/by-feature/current-project-status.md)
- [Step-by-step execution plan](docs/by-feature/step-by-step-execution-plan.md)
- [Windows offline stem separation plan](docs/by-feature/windows-offline-stem-separation-plan.md)

The execution plan remains the source of truth for the required step order and
acceptance criteria. Each completed step must update both `docs/` and `logs/`
before commit and push.
