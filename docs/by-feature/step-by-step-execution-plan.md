# Step-by-Step Execution Plan

Date: 2026-06-13

This is the executable implementation plan for the Windows offline music stem separation software. A new agent should be able to start from this file, execute steps in order, and update docs/logs after each completed task.

## 0. Mandatory Working Rules

1. Before starting any task, read:
   - `AGENTS.md`
   - `docs/INDEX.md`
   - `docs/by-feature/windows-offline-stem-separation-plan.md`
   - this file
2. Record every new user requirement verbatim in `docs/by-date/YYYY-MM-DD-user-requirements.md`.
3. Keep detailed progress notes in both:
   - `docs/by-date/`
   - `logs/by-date/`
4. Keep feature-oriented handoff notes in:
   - `docs/by-feature/`
   - `logs/by-feature/`
5. Keep `AGENTS.md` short. Only add index entries or durable top-level rules.
6. Do not commit generated audio/video, model weights, FFmpeg binaries, build artifacts, caches, virtual environments, or temporary output unless the user explicitly approves.
7. At the end of each completed task:
   - run relevant checks
   - update docs and logs
   - run `git status --short`
   - commit
   - push to `origin/main`

## 1. Target V1 Definition

The first usable version is complete when all conditions below are true.

1. The user can run a Windows GUI app from a portable folder without installing Python, FFmpeg, Demucs, or other tools.
2. The app accepts common local audio/video files through file picker and drag/drop.
3. The app can record system audio while the user plays online video or any other audio source.
4. The app separates an input into:
   - `vocals.wav`
   - `drums.wav`
   - `bass.wav`
   - `other.wav`
   - `lowest.wav`
   - `highest.wav`
5. The app works offline after delivery.
6. CPU separation works on a Windows machine with no CUDA GPU.
7. If a compatible NVIDIA CUDA environment is bundled and available, the app can use GPU acceleration. If GPU startup fails, it falls back to CPU and tells the user.
8. Each job creates a timestamped output directory with output files, a job metadata JSON file, and a readable job log.
9. The UI labels `highest` as an approximation. It must not claim guaranteed instrument-level highest-instrument extraction.
10. A portable package can be smoke-tested on Windows without using anything from the developer environment.

## 2. Fixed Technical Decisions

Use these choices unless the user explicitly changes them.

- Language: Python.
- GUI: PySide6.
- Separation backend: bundled Demucs-compatible pretrained model, with 4-stem `htdemucs` as the default.
- Media decoding/conversion: bundled FFmpeg and FFprobe.
- System audio recording: Windows WASAPI loopback through `SoundCard` or an equivalent Python-accessible WASAPI wrapper.
- Packaging: PyInstaller one-folder mode.
- Branch and remote: `main`, `origin = git@github.com:guoruilu/music_decomp.git`.
- Default output format: WAV.
- Optional export formats: FLAC and MP3 through FFmpeg.
- Development target Python: Python 3.11 x64 on Windows for build and packaging.
- Linux development may be used for pure tests and documentation, but final packaging and WASAPI testing must be done on Windows.

## 3. Repository Structure To Create

Create this structure during implementation. Do not create generated or binary directories until needed.

```text
.
├── AGENTS.md
├── README.md
├── pyproject.toml
├── requirements/
│   ├── base.in
│   ├── win-cpu.txt
│   └── win-cuda.txt
├── src/
│   └── music_decomp/
│       ├── __init__.py
│       ├── __main__.py
│       ├── app.py
│       ├── cli.py
│       ├── config.py
│       ├── paths.py
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── jobs.py
│       │   └── media.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── export_service.py
│       │   ├── media_service.py
│       │   ├── recorder_service.py
│       │   └── separation_service.py
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── main_window.py
│       │   ├── widgets.py
│       │   └── workers.py
│       └── utils/
│           ├── __init__.py
│           ├── logging.py
│           └── subprocesses.py
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   ├── test_export_service.py
│   ├── test_media_service.py
│   ├── test_paths.py
│   └── test_synthetic_audio.py
├── packaging/
│   ├── pyinstaller/
│   │   └── music_decomp.spec
│   └── windows/
│       ├── build.ps1
│       └── smoke-test.ps1
├── scripts/
│   ├── check_env.py
│   ├── make_synthetic_audio.py
│   └── verify_portable_package.py
├── docs/
└── logs/
```

Runtime and release artifact directories are ignored by `.gitignore`:

```text
models/
vendor/
outputs/
recordings/
build/
dist/
.venv/
```

## 4. Implementation Steps

Execute the steps in order. Do not start a later phase until the current phase acceptance criteria pass.

### Step 1 - Scaffold The Python Project

Goal: create a runnable empty application with test infrastructure.

Files to create:

- `README.md`
- `pyproject.toml`
- `src/music_decomp/__init__.py`
- `src/music_decomp/__main__.py`
- `src/music_decomp/app.py`
- `src/music_decomp/cli.py`
- `src/music_decomp/paths.py`
- `tests/test_paths.py`

Implementation details:

1. In `pyproject.toml`, define project metadata, package discovery from `src`, pytest config, and console script:
   - package name: `music-decomp`
   - import package: `music_decomp`
   - console script: `music-decomp = music_decomp.cli:main`
2. Add minimal dependencies only at this step:
   - `pytest`
3. In `paths.py`, implement:
   - `project_root()`
   - `app_data_dir()`
   - `resource_path(relative_path)`
   - `is_frozen()`
4. `resource_path` must work both in source mode and PyInstaller frozen mode.
5. `cli.py` must accept `--version` and exit successfully.
6. `__main__.py` must call `cli.main()`.

Commands:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e . pytest
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m music_decomp --version
```

Acceptance:

- `pytest` passes.
- `python -m music_decomp --version` prints a version and exits 0.
- Docs/logs updated.
- Commit message: `Scaffold Python project`.

### Step 2 - Add Core Domain Types

Goal: define data models that all services and UI workers use.

Files to create or update:

- `src/music_decomp/domain/media.py`
- `src/music_decomp/domain/jobs.py`
- `tests/test_paths.py`
- new tests for domain validation if useful

Implement dataclasses:

```python
MediaInput:
    kind: Literal["audio", "video", "recording"]
    path: Path
    title: str
    duration_seconds: float | None
    sample_rate: int | None

SeparationJob:
    input: MediaInput
    output_dir: Path
    device: Literal["auto", "cpu", "cuda"]
    model_name: str
    output_format: Literal["wav", "flac", "mp3"]
    stems: tuple[str, ...]

JobResult:
    job: SeparationJob
    output_files: dict[str, Path]
    metadata_path: Path
    log_path: Path
```

Rules:

- Default model is `htdemucs`.
- Default stems are `vocals`, `drums`, `bass`, `other`, `lowest`, `highest`.
- Default output format is `wav`.
- Paths must be stored as `Path`, not strings.
- Validate unsupported device or format early with clear `ValueError`.

Acceptance:

- Unit tests cover defaults and invalid device/format.
- Commit message: `Add core domain models`.

### Step 3 - Implement MediaService With FFmpeg

Goal: support common audio/video input using bundled or configured FFmpeg.

Files to create or update:

- `src/music_decomp/services/media_service.py`
- `src/music_decomp/utils/subprocesses.py`
- `src/music_decomp/config.py`
- `tests/test_media_service.py`

Implementation details:

1. `config.py` must resolve FFmpeg paths in this order:
   - environment variables `MUSIC_DECOMP_FFMPEG` and `MUSIC_DECOMP_FFPROBE`
   - bundled paths under `vendor/ffmpeg/bin/ffmpeg.exe` and `vendor/ffmpeg/bin/ffprobe.exe`
   - system `ffmpeg` and `ffprobe` only in development mode
2. `MediaService.probe(path)` must call FFprobe with JSON output:

```text
ffprobe -v error -print_format json -show_format -show_streams INPUT
```

3. `MediaService.extract_audio(input_path, output_wav)` must produce stereo 44.1 kHz WAV:

```text
ffmpeg -y -i INPUT -vn -ac 2 -ar 44100 -sample_fmt s16 OUTPUT.wav
```

4. `MediaService.detect_kind(path)` returns:
   - `audio` if at least one audio stream and no video stream
   - `video` if at least one video stream
5. All subprocess calls must use list arguments, not shell strings.
6. Error messages must include executable path, exit code, and stderr tail.

Tests:

- Mock subprocess for command construction.
- Test missing FFmpeg path error.
- Test FFprobe JSON parsing with fixture JSON.

Acceptance:

- Unit tests pass without real FFmpeg.
- On a developer machine with FFmpeg available, a manual command can extract a sample audio file.
- Commit message: `Add FFmpeg media service`.

### Step 4 - Implement Output Directory And Metadata

Goal: make every job reproducible and easy to debug.

Files:

- `src/music_decomp/services/export_service.py`
- `src/music_decomp/utils/logging.py`
- `tests/test_export_service.py`

Implementation details:

1. Output root defaults to `outputs/` in source mode and a user-selected directory in GUI mode.
2. Job directory format:

```text
YYYYMMDD-HHMMSS-safe_input_title/
```

3. Create:
   - `job.json`
   - `job.log`
   - stem files
4. `job.json` must include:
   - app version
   - input path
   - input kind
   - input duration if known
   - model name
   - requested device
   - actual device
   - output format
   - stem filenames
   - start/end timestamps
   - success/failure status
5. Safe filename function must replace characters invalid on Windows: `< > : " / \ | ? *`.
6. Job logs must be plain UTF-8 text.

Acceptance:

- Tests cover safe names, timestamped directory creation, metadata writing, and failure metadata.
- Commit message: `Add export metadata service`.

### Step 5 - Implement SeparationService

Goal: perform 4-stem model separation and derive `lowest`/`highest`.

Files:

- `src/music_decomp/services/separation_service.py`
- `tests/test_synthetic_audio.py`
- possibly `scripts/make_synthetic_audio.py`

Dependencies to add:

- `torch`
- `torchaudio` if required by chosen Demucs path
- `demucs`
- `numpy`

Implementation details:

1. Use the Demucs Python API if available, preferably `demucs.api.Separator`.
2. Load model only when first needed. Cache loaded model per process.
3. Device resolution:
   - if requested `cpu`, use CPU.
   - if requested `cuda`, require `torch.cuda.is_available()`, otherwise raise a clear error.
   - if requested `auto`, use CUDA when available, otherwise CPU.
   - if CUDA fails during model load or separation in `auto`, log the failure and retry CPU once.
4. Source audio for model input is the 44.1 kHz stereo WAV produced by `MediaService`.
5. Write raw 4 stems first:
   - `vocals.wav`
   - `drums.wav`
   - `bass.wav`
   - `other.wav`
6. Derive `lowest.wav`:
   - if `bass.wav` exists, copy or convert it to the requested output format.
   - if `bass.wav` is missing, create a fallback from the mixture using FFmpeg low-pass at 250 Hz.
7. Derive `highest.wav`:
   - create an approximation from the mixture using FFmpeg high-pass at 2500 Hz and low-pass at 12000 Hz.
   - normalize only if clipping would occur.
   - record in `job.json` that this is an approximation.
8. Keep all intermediate WAV files inside the job directory or a job-local temp directory.
9. Provide progress callbacks:
   - `preparing`
   - `loading_model`
   - `separating`
   - `exporting`
   - `done`
   - `failed`

Tests:

- Synthetic sine-wave fixture: 120 Hz plus 4000 Hz. Verify fallback filters place energy in expected bands.
- Mock Demucs for service-level job flow without loading real model.
- Mark real Demucs smoke test as integration and skip unless `RUN_DEMUCS_INTEGRATION=1`.

Acceptance:

- Mocked unit tests pass.
- Real integration test on a short file produces all 6 outputs.
- Commit message: `Add separation service`.

### Step 6 - Implement RecorderService

Goal: record system audio for online videos and any playback source.

Files:

- `src/music_decomp/services/recorder_service.py`
- recorder tests with mocks

Dependencies:

- `SoundCard`
- `soundfile` or an equivalent WAV writer

Implementation details:

1. Use Windows WASAPI loopback through SoundCard speaker recording.
2. Record stereo at 48 kHz by default.
3. Provide:
   - `list_output_devices()`
   - `default_output_device()`
   - `start_recording(device_id, output_path)`
   - `stop_recording()`
   - `is_recording`
4. Recording must run on a background worker, never on the GUI thread.
5. Write to a temporary WAV first:

```text
recordings/YYYYMMDD-HHMMSS-recording.wav
```

6. On stop, finalize the WAV and return a `MediaInput(kind="recording", path=...)`.
7. Show elapsed recording time and peak level in the UI.
8. If loopback is unavailable, show a clear message:

```text
System audio recording is unavailable for this output device. Try another output device or use a local file.
```

Tests:

- Mock SoundCard device enumeration.
- Mock recording chunks and verify WAV writer receives stereo data.
- Test stop behavior when no recording is active.

Acceptance:

- Mocked tests pass.
- Manual Windows test records browser playback into a WAV that FFprobe can read.
- Commit message: `Add system audio recorder`.

### Step 7 - Build The GUI Shell

Goal: create a practical Windows desktop interface.

Files:

- `src/music_decomp/app.py`
- `src/music_decomp/ui/main_window.py`
- `src/music_decomp/ui/widgets.py`
- `src/music_decomp/ui/workers.py`
- update `src/music_decomp/cli.py`

Dependencies:

- `PySide6`

Required UI:

1. Main window with tabs:
   - Files
   - Record
   - Jobs
   - Settings
2. Files tab:
   - drag/drop zone
   - file picker button
   - selected file details
   - output format selector: WAV, FLAC, MP3
   - device selector: Auto, CPU, CUDA
   - start separation button
3. Record tab:
   - output device selector
   - refresh devices button
   - record/stop button
   - elapsed time
   - level meter
   - send recording to separation button after stop
4. Jobs tab:
   - current queue
   - progress text
   - status
   - open output folder button
5. Settings tab:
   - output root selector
   - FFmpeg status
   - model status
   - CPU/GPU status
6. Workers:
   - media probe worker
   - recording worker
   - separation worker
7. UI thread safety:
   - all long work runs in `QThread` or `QRunnable`
   - UI updates through Qt signals
   - cancel button may be present, but if implemented it must leave metadata/logs in a consistent failed or canceled state

Design rules:

- Use compact desktop controls, not a landing page.
- Use clear labels and progress states.
- Do not hide errors in console output only.
- Label `highest` as approximate in output summary.

Acceptance:

- App launches with `python -m music_decomp gui`.
- Drag/drop and file picker both populate selected file.
- Starting a mocked separation shows progress and completion.
- Commit message: `Add GUI shell`.

### Step 8 - Wire End-To-End File Separation

Goal: local audio/video files can run through the complete pipeline from GUI.

Implementation details:

1. User selects or drops file.
2. GUI calls `MediaService.probe`.
3. GUI shows kind, duration, and stream summary.
4. Start button creates a `SeparationJob`.
5. Worker creates job directory and log.
6. `MediaService.extract_audio` creates canonical input WAV.
7. `SeparationService` creates stems.
8. `ExportService` writes metadata.
9. GUI shows completed output directory.

Acceptance:

- On Windows dev machine, one short local audio file produces all outputs.
- One short local video file produces all outputs from its audio stream.
- Failure on unreadable file is shown in GUI and written in job log.
- Commit message: `Wire file separation pipeline`.

### Step 9 - Wire End-To-End Recording Separation

Goal: browser playback can be recorded and separated.

Implementation details:

1. User opens Record tab.
2. User selects output device or default device.
3. User clicks Record.
4. App records system audio while user plays source.
5. User clicks Stop.
6. Recording is finalized as WAV.
7. User starts separation using the same `SeparationJob` flow.

Acceptance:

- Manual Windows test records at least 30 seconds of browser playback.
- Recorded WAV can be probed and separated.
- Recording failure does not crash the app.
- Commit message: `Wire recording separation pipeline`.

### Step 10 - Add CLI For Automation And Testing

Goal: provide a stable non-GUI path for smoke tests and batch usage.

Files:

- `src/music_decomp/cli.py`

Commands:

```text
music-decomp gui
music-decomp probe INPUT
music-decomp separate INPUT --out OUTPUT_DIR --device auto --format wav
music-decomp list-recording-devices
```

Rules:

- CLI must return nonzero on failure.
- CLI errors must be readable without stack traces unless `--debug` is passed.
- CLI should use the same services as GUI.

Acceptance:

- CLI probe works with mocked FFprobe in tests.
- CLI separate works in integration mode with a short local file.
- Commit message: `Add CLI workflows`.

### Step 11 - Add Dependency Locks And Asset Manifests

Goal: make builds reproducible and offline behavior auditable.

Files:

- `requirements/base.in`
- `requirements/win-cpu.txt`
- `requirements/win-cuda.txt`
- `vendor/README.md`
- `models/README.md` only if user approves tracking these README files despite ignored directories
- `docs/by-feature/dependency-and-asset-manifest.md`

Implementation details:

1. `requirements/base.in` should include direct dependencies:
   - `PySide6`
   - `demucs`
   - `torch`
   - `torchaudio` if required
   - `numpy`
   - `SoundCard`
   - `soundfile` or chosen WAV writer
   - `pytest`
   - `pyinstaller`
2. Generate locked Windows requirements on the Windows build machine after testing.
3. Record exact versions in `docs/by-feature/dependency-and-asset-manifest.md`.
4. Record FFmpeg source, version, license, and checksum.
5. Record model name, source, license/terms, local path, and checksum.
6. Do not commit binaries or model weights unless user explicitly approves.

Acceptance:

- Dependency manifest exists.
- Build instructions can recreate the environment.
- Commit message: `Document dependency and asset manifest`.

### Step 12 - Package With PyInstaller

Goal: create a portable Windows folder.

Files:

- `packaging/pyinstaller/music_decomp.spec`
- `packaging/windows/build.ps1`
- `packaging/windows/smoke-test.ps1`
- `scripts/verify_portable_package.py`

Implementation details:

1. Use PyInstaller one-folder mode.
2. Include:
   - Python app
   - PySide6 runtime files
   - Demucs and PyTorch runtime files
   - FFmpeg binaries from `vendor/ffmpeg/`
   - model files from `models/`
   - license files
3. Do not rely on system PATH for FFmpeg in packaged mode.
4. The packaged app should find resources via `resource_path`.
5. `build.ps1` should:
   - check Python version
   - install requirements
   - run tests
   - run PyInstaller
   - copy licenses and manifests
   - run portable verification
6. `verify_portable_package.py` should check:
   - executable exists
   - FFmpeg exists inside package
   - model manifest exists
   - `music-decomp --version` works from packaged folder
   - no source `.venv` path is required

Acceptance:

- `dist/MusicDecomp/` launches on Windows.
- Running from a machine without Python and without system FFmpeg reaches the GUI.
- Commit message: `Add Windows packaging`.

### Step 13 - Offline Acceptance Test

Goal: prove that the package is self-contained.

Test environment:

- Windows x64.
- No Python on PATH, or PATH temporarily cleared for Python.
- No FFmpeg on PATH.
- Network disabled.
- Package copied to a clean directory.

Manual test steps:

1. Launch `MusicDecomp.exe`.
2. Open Settings and verify:
   - FFmpeg status is bundled.
   - model status is bundled.
   - device status shows CPU and optional GPU.
3. Import a short MP3 or WAV.
4. Run separation with `device=CPU`.
5. Verify six outputs exist and play.
6. Import a short MP4 or MKV with audio.
7. Run separation.
8. Record 30 seconds of browser or local player audio.
9. Run separation on the recording.
10. Open each job directory and inspect:
   - `job.json`
   - `job.log`
   - output files

Acceptance:

- All three input modes pass: audio file, video file, system recording.
- No network access is required.
- No missing-DLL dialog appears.
- Any quality limitation is documented, not hidden.
- Commit message: `Record offline acceptance results`.

### Step 14 - User Documentation

Goal: provide enough user-facing documentation for first use.

Files:

- `README.md`
- `docs/by-feature/user-guide.md`
- `docs/by-feature/troubleshooting.md`

Required content:

1. What the app does.
2. What the app cannot guarantee.
3. How to run from the portable folder.
4. How to separate local audio.
5. How to separate local video.
6. How to handle online video by recording system audio.
7. Output files explained.
8. CPU/GPU expectations.
9. Troubleshooting:
   - no audio recorded
   - FFmpeg missing
   - model missing
   - CUDA failed and CPU fallback occurred
   - separation is slow
   - output has bleed or artifacts

Acceptance:

- A non-developer can follow the guide.
- Troubleshooting includes exact messages used by the app.
- Commit message: `Add user documentation`.

## 5. Testing Matrix

Run these checks before marking v1 complete.

| Area | Test | Required |
| --- | --- | --- |
| Unit | `pytest` on services and domain models | yes |
| CLI | `music-decomp --version` | yes |
| CLI | `music-decomp probe sample.wav` | yes |
| CLI | `music-decomp separate sample.wav --device cpu` | yes |
| GUI | launch from source | yes |
| GUI | drag/drop file | yes |
| GUI | select file by dialog | yes |
| GUI | record system audio | yes, Windows only |
| Packaging | PyInstaller build | yes, Windows only |
| Offline | run package with network disabled | yes, Windows only |
| GPU | auto CUDA path | optional, if compatible test machine exists |
| Fallback | CUDA unavailable falls back to CPU in auto mode | yes |

## 6. Commit And Handoff Protocol

After each step:

1. Update requirement records if the user changed or added requirements.
2. Update the relevant `docs/by-feature/` file.
3. Add or update a `docs/by-date/YYYY-MM-DD-*.md` entry.
4. Update `logs/by-feature/*.md`.
5. Add or update `logs/by-date/YYYY-MM-DD-*.md`.
6. Run checks for the step.
7. Inspect pending files:

```bash
git status --short
git status --ignored --short
```

8. Confirm ignored/generated files are not staged.
9. Commit:

```bash
git add .
git commit -m "Short imperative summary"
git push
```

10. In final handoff, report:
   - files changed
   - checks run
   - commit hash
   - push status
   - next recommended step

## 7. First Next Action For A New Agent

Start with Step 1. Create the Python project scaffold and make `python -m music_decomp --version` plus `pytest` pass. Do not attempt Demucs, FFmpeg, recording, or GUI implementation until the scaffold is committed and pushed.

