# Offline Acceptance Test Log

Date: 2026-06-24

## Assignment

Executor subagent for Step 13 - Offline Acceptance Test.

## Outcome

Blocked before real acceptance execution. The current environment cannot run the
required Windows x64 offline test and does not contain the portable package or
bundled assets needed for structural verification.

## Actions

- Read the required project rules, execution plan, current status, packaging
  docs, dependency manifest, Windows packaging scripts, smoke script, and
  portable verifier.
- Checked repository branch and HEAD.
- Checked operating system and local Python command availability.
- Checked for `dist/MusicDecomp/`.
- Checked for staged bundled FFmpeg binaries.
- Checked for staged model assets.
- Checked Windows dependency lock files.
- Ran the portable verifier in structure-only mode against the expected package
  path to capture the current failure.
- Created Step 13 documentation and log drafts without marking the step
  complete.

## Evidence

- Branch: `main`.
- HEAD: `1976823 Add Windows packaging`.
- OS: Linux WSL2 x86_64.
- `python`: not found.
- `python3`: Linux Python 3.12.3.
- `dist/MusicDecomp`: missing.
- `vendor/ffmpeg/bin`: missing.
- `models`: missing.
- `requirements/win-cpu.txt`: placeholder, not generated.
- `requirements/win-cuda.txt`: placeholder, not generated.
- Verifier failure: `Package directory does not exist:
  /mnt/e/prjs/music_decomp/source/dist/MusicDecomp`.

## Not Run

- Windows package launch.
- Clean-directory copied package test.
- Network-disabled execution.
- PATH-isolated execution without Python or system FFmpeg.
- Audio input separation.
- Video input separation.
- System-audio recording separation.
- Successful job directory inspection.
- Missing-DLL dialog check.
- Output quality review.

## Handoff

The next executor needs a Windows x64 host and a package built from real Windows
locks, bundled FFmpeg, model assets, and license/manifest files. Run the Step 13
manual checklist in `docs/by-feature/offline-acceptance-test.md` and record real
results before completing the step.
