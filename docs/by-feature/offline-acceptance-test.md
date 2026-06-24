# Offline Acceptance Test

Date: 2026-06-24

Related execution plan step: [Step 13 - Offline Acceptance Test](step-by-step-execution-plan.md#step-13---offline-acceptance-test)

## Status

Step 13 is blocked in the current executor environment. This file records the
preflight checks that were possible on Linux and the exact conditions still
needed to run the real Windows offline acceptance test.

This is not a pass record. Do not mark Step 13 complete from this document.

## Required Acceptance Environment

The real Step 13 run must use:

- Windows x64.
- The `dist/MusicDecomp/` package produced by `packaging/windows/build.ps1`.
- Real generated Windows dependency locks, not placeholder lock files.
- Staged bundled FFmpeg and FFprobe under `vendor/ffmpeg/bin/`.
- Staged bundled Demucs model assets and `models/manifest.json`.
- A clean copy directory outside the source checkout.
- PATH isolated so Python and system FFmpeg are unavailable.
- Network disabled before launching and using the package.
- Short local audio and video fixtures, plus a Windows system-audio recording
  input captured while offline.

## Linux Preflight Findings

| Check | Result | Evidence |
| --- | --- | --- |
| Operating system | Blocked | `uname -a` reports Linux WSL2, not Windows x64. |
| Package directory | Blocked | `dist/MusicDecomp` does not exist. |
| Bundled FFmpeg | Blocked | `vendor/ffmpeg/bin` does not exist. |
| Bundled model assets | Blocked | `models` does not exist. |
| Windows CPU lock | Blocked | `requirements/win-cpu.txt` says `Status: NOT GENERATED`. |
| Windows CUDA lock | Blocked | `requirements/win-cuda.txt` says `Status: NOT GENERATED`. |
| Portable verifier | Blocked | `python3 scripts/verify_portable_package.py --package-dir dist/MusicDecomp --structure-only` fails because the package directory does not exist. |
| Python command availability | Informational | `python` is not on PATH; `python3` is Linux Python 3.12.3, not the target Windows Python 3.11 build runtime. |

## Tests Not Run

No real Step 13 acceptance scenario was run:

- `MusicDecomp.exe` launch from the portable folder.
- Settings verification for bundled FFmpeg, bundled model, CPU, and optional
  GPU status.
- Local audio file separation.
- Local video file separation.
- Windows system-audio recording and separation.
- Offline/no-network monitoring.
- Missing-DLL dialog observation.
- Manual playback inspection of generated outputs.
- `job.json`, `job.log`, and output file inspection for successful jobs.

## Acceptance Checklist For The Real Run

Run this checklist only after the blockers above are removed:

1. Copy the built `dist/MusicDecomp/` folder to a clean test directory.
2. Disable network access.
3. Start a shell with Python, FFmpeg, and development environment variables
   removed from PATH and environment.
4. Launch `MusicDecomp.exe` from the clean copied folder.
5. Open Settings and verify bundled FFmpeg, bundled model, CPU, and optional GPU
   status.
6. Import a short local MP3 or WAV and run CPU separation.
7. Verify `vocals`, `drums`, `bass`, `other`, `lowest`, and approximate
   `highest` outputs exist and play.
8. Import a short local MP4 or MKV with audio and run separation.
9. Record at least 30 seconds of Windows system audio while playing local media
   through the default output device, then run separation on the recording.
10. Inspect every job directory for `job.json`, `job.log`, output file paths,
    status, input kind, requested and actual device, model name, and any failure
    or warning text.
11. Confirm no network access was needed and no missing-DLL dialog appeared.
12. Record any observed separation artifacts, bleed, slow CPU behavior, CUDA
    fallback, or approximate `highest` limitations.

## Current Result

Step 13 remains pending. The next executor needs a Windows x64 machine, staged
assets, real lock files, and a produced package before any pass/fail acceptance
claim can be made.
