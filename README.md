# Music Decomp

Music Decomp is planned as a Windows offline desktop application for separating music into stems. The first implementation step provides only the Python project scaffold, importable package, CLI version check, and path helpers.

## Current Status

- Package name: `music-decomp`
- Import package: `music_decomp`
- Console script: `music-decomp`
- Runtime dependencies: none at this scaffold step
- Development test dependency: `pytest`

Later steps will add media probing, FFmpeg integration, separation services, recording, GUI, and Windows packaging.

## Development

Run the current checks from the repository root:

```bash
PYTHONPATH=src python3 -m pytest
PYTHONPATH=src python3 -m music_decomp --version
```

The package can also be installed in editable mode when local build dependencies are available:

```bash
python3 -m pip install -e .[dev]
music-decomp --version
```
