# 2026-06-24 Step 11 Dependency And Asset Manifest

## Scope

Executor subagent implementation for Step 11 - Add Dependency Locks And Asset
Manifests.

## Changes Drafted

- Added `requirements/base.in` with direct dependency inputs for Windows lock
  generation.
- Added `requirements/win-cpu.txt` and `requirements/win-cuda.txt` as explicit
  placeholders, not fake generated locks.
- Added `vendor/README.md` to document expected FFmpeg staging layout and asset
  tracking policy.
- Narrowed `.gitignore` so only `vendor/README.md` is trackable while all other
  vendor assets remain ignored.
- Kept `models/` fully ignored and did not create `models/README.md` because
  the user has not approved tracking files under that ignored directory.
- Added `docs/by-feature/dependency-and-asset-manifest.md` with dependency,
  FFmpeg, and model manifest fields plus Windows generation instructions.

## Validation

- Passed: `git diff --check`
- Passed: `git check-ignore -v vendor/README.md`
  - Result: README is allowed through the `.gitignore` exception.
- Passed: `git check-ignore -v vendor/ffmpeg/bin/ffmpeg.exe`
  - Result: staged FFmpeg binaries remain ignored.
- Passed: `PYTHONPATH=src python3 -m compileall -q src tests`
- Passed: `PYTHONPATH=src python3 -m music_decomp --version`
  - Output: `music-decomp 0.1.0`
- Not run successfully: `PYTHONPATH=src python3 -m pytest`
  - Result: `/usr/bin/python3: No module named pytest`

## Reviewer Notes

- Initial reviewer result: APPROVED, no blocking findings.
- Reviewer confirmed direct dependencies, placeholder lock strategy, FFmpeg
  manifest fields, model manifest fields, and narrow `.gitignore` behavior.
- Reviewer suggested rewording the lock strategy so placeholder files are not
  described as already tested locks.
- Executor made the wording fix.
- Reviewer re-review result: APPROVED, no blocking findings.

## Main-Agent Finalization

- Main agent updated docs/logs indexes, current status, and README.
- Step 11 remains clear that real Windows lock generation, FFmpeg staging, and
  model checksum recording must happen on the Windows build machine before
  packaging or release claims.
- Commit and push are handled by the main agent after final checks.
