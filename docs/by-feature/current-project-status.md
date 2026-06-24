# Current Project Status

Date: 2026-06-24

This page summarizes the current repository state for a new agent before the
next implementation task starts. The detailed source of truth remains
`docs/by-feature/step-by-step-execution-plan.md`.

## Repository State

- Remote: `git@github.com:guoruilu/music_decomp.git`
- Branch: `main`
- Latest committed baseline:
  `1976823 Add Windows packaging`
- Current completed execution step: Step 12 - Package With PyInstaller
- Step 13 preflight status: blocked in the current Linux environment; no real
  Windows offline acceptance was run.
- Next planned execution step: Step 13 - Offline Acceptance Test remains pending
  on Windows x64.

## Required Workflow

Before starting a task, read:

- `AGENTS.md`
- `docs/INDEX.md`
- `docs/by-feature/windows-offline-stem-separation-plan.md`
- `docs/by-feature/step-by-step-execution-plan.md`
- this status file

Keep the durable workflow rules from `AGENTS.md`:

- Record every new user requirement verbatim under `docs/by-date/`.
- Keep docs and logs organized by feature and by date, with top-level indexes.
- For numbered implementation steps, coordinate a dedicated executor subagent
  and a separate reviewer subagent, then repeat until no blocking review issues
  remain.
- After completing a task, run relevant checks, update docs/logs, inspect git
  status, commit, and push.

## Completed Work

The following planned steps have tracked commits:

| Step | Commit | Status |
| --- | --- | --- |
| Initial docs | `554c298` | Complete |
| Repository workflow | `c9f8a98` | Complete |
| Detailed execution plan | `98ebd6c` | Complete |
| Agent coordination workflow | `3d8c442` | Complete |
| Step 1 Python scaffold | `d635a3b` | Complete |
| Step 2 core domain models | `0a032b7` | Complete |
| Step 3 FFmpeg media service | `f732474` | Complete |
| Step 4 export metadata service | `9c0d0ee` | Complete |
| Step 5 separation service | `1f962db` | Complete |
| Step 6 system audio recorder | `4aec90f` | Complete |
| Step 7 GUI shell | `52b49cd` | Complete |
| Step 8 file separation pipeline | `f149209` | Complete |
| Documentation refresh | `55cb0e8` | Complete |
| Step 9 recording separation pipeline | `76becab` | Complete |
| Step 10 CLI workflows | `9dcc73c` | Complete |
| Step 11 dependency and asset manifest | `6ac49b7` | Complete |
| Step 12 Windows packaging | `1976823` | Complete |

## Current Implementation Capabilities

- `music_decomp` imports from `src/`.
- `python -m music_decomp --version` prints the package version.
- Domain models validate supported devices and output formats.
- FFmpeg/FFprobe paths resolve from environment variables, bundled paths, or
  development PATH fallback.
- `MediaService` can probe media metadata and extract canonical stereo 44.1 kHz
  WAV input through FFmpeg command lists.
- `ExportService` creates collision-safe timestamped job directories, job logs,
  expected stem paths, and success/failure `job.json` metadata.
- `SeparationService` lazily runs Demucs-compatible separation, writes the raw
  four stems, derives `lowest`, and derives approximate `highest`.
- `RecorderService` implements background system-audio recording primitives and
  mocked test coverage.
- The PySide6 GUI shell has Files, Record, Jobs, and Settings tabs.
- The Files tab and GUI worker layer are wired to the local file separation
  pipeline from media probe through metadata writing.
- The Record tab is wired to `RecorderService`, stores stopped recordings as
  `MediaInput(kind="recording")`, and routes them through
  `FileSeparationPipeline.run_recording`.
- The Step 9 post-review fix makes `run_recording` probe the finalized WAV and
  call `MediaService.extract_audio` so separation receives canonical stereo
  44.1 kHz `_intermediate/input.wav`.
- The CLI supports `gui`, `probe`, `separate`, and
  `list-recording-devices`.
- CLI success output for non-GUI workflows is JSON; separation progress goes to
  stderr.
- CLI failures return nonzero and default to readable errors without tracebacks
  unless `--debug` is passed.
- `requirements/base.in` records direct dependency input for future Windows
  lock generation.
- `requirements/win-cpu.txt` and `requirements/win-cuda.txt` exist as explicit
  placeholders until a Windows x64 Python 3.11 build machine generates and
  validates real pinned locks.
- `docs/by-feature/dependency-and-asset-manifest.md` tracks required dependency,
  FFmpeg, and Demucs model provenance fields.
- `vendor/README.md` documents expected FFmpeg staging layout; `.gitignore`
  keeps all other vendor assets ignored.
- `packaging/pyinstaller/music_decomp.spec` defines a PyInstaller one-folder
  package for `dist/MusicDecomp/`.
- `packaging/windows/build.ps1` runs Windows package prerequisites,
  dependency install, tests, PyInstaller, metadata/license copy, and smoke
  verification.
- `packaging/windows/smoke-test.ps1` runs package verification and optional GUI
  launch smoke with isolated runtime environment.
- `scripts/verify_portable_package.py` verifies package structure, bundled
  FFmpeg/FFprobe, model manifest, dependency manifest, license files, no source
  `.venv` references, version smoke, and bundled FFprobe probe smoke.
- Packaged separation resolves `resource_path("models")` and passes the bundled
  model repository to Demucs when `models/manifest.json` is present.

## Step 13 Preflight Notes

The 2026-06-24 Step 13 executor pass could only perform non-destructive
preflight checks. It did not create or run a package. The current environment is
Linux WSL2 x86_64, `dist/MusicDecomp/` is missing, `vendor/ffmpeg/bin/` is
missing, `models/` is missing, and both Windows lock files are still explicit
placeholders. `python3 scripts/verify_portable_package.py --package-dir
dist/MusicDecomp --structure-only` fails because the package directory does not
exist.

Step 13 must still be run on Windows x64 from a clean copied package with
network disabled and without Python or system FFmpeg on PATH.

## Remaining Planned Work

- Step 13: clean Windows offline acceptance test on a real packaged build.
- Step 14: user guide and troubleshooting documentation.

## Known Gaps And Risks

- Real Windows manual acceptance for Step 8 has not been run in the repository
  logs. It still needs bundled or configured FFmpeg, Demucs, model files, and
  actual short audio/video inputs.
- Real Windows WASAPI loopback recording has not been manually validated.
- `models/` is not present yet because model assets have not been staged.
- Real Windows CPU/CUDA dependency locks have not been generated; the current
  files are placeholders by design.
- FFmpeg binaries and model weights are not staged, and their checksum fields
  remain pending in the manifest.
- Real Windows PyInstaller build has not been run in this environment.
- `dist/MusicDecomp/` has not been produced or launched on Windows.
- Real Windows WASAPI loopback recording and separation has not been manually
  accepted; Step 9 tests are fake-based in this Linux/no-heavy-deps environment.
- Real CLI `probe`/`separate` integration with actual FFmpeg, Demucs, and model
  files has not been manually accepted in this environment.
- `highest` is labeled as approximate in service results and GUI text, but the
  regular success `job.json` metadata does not yet persist per-stem
  approximation details.
- Full test execution requires local development dependencies. In the
  2026-06-24 documentation refresh and Step 9/10/11/12 executor environments,
  `pytest` was not installed.
- Step 9 real Windows WASAPI loopback acceptance remains pending until a
  Windows machine with browser playback, FFmpeg, Demucs, and model files is
  available.
- Step 13 was not run in the 2026-06-24 Linux executor pass; the result is
  blocked/preflight only and must not be treated as an acceptance pass.

## Documentation Maintenance Notes

The 2026-06-24 documentation refresh updated stale status text that still said
Step 3 was waiting for reviewer re-check. The commit history and later Step 4-8
records show Step 3 was accepted, committed, and pushed before later steps were
completed.
