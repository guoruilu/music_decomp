# Music Decomp

Music Decomp is a planned Windows offline desktop application for separating
local music and recorded system audio into stems. The target delivery is a
portable Windows folder that runs without installing Python, FFmpeg, Demucs, or
other tools on the user machine.

## Current Status

- Package name: `music-decomp`
- Import package: `music_decomp`
- Console script: `music-decomp`
- Current implementation step: Step 9, recording separation pipeline
- Latest committed baseline before this Step 9 change set:
  `55cb0e8 Refresh project documentation status`

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

Not complete yet:

- CLI workflows for `probe`, `separate`, and `list-recording-devices` are still
  Step 10 work.
- Dependency lock files, asset manifests, Windows packaging, offline acceptance
  testing, and user documentation are still pending.
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
