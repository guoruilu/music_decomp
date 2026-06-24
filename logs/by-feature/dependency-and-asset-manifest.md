# Dependency And Asset Manifest Log

Date: 2026-06-24

## Scope

Executor assignment: implement only Step 11 - Add Dependency Locks And Asset
Manifests.

Constraints followed:

- no Step 12 packaging work
- no commit or push by executor or reviewer
- no network/package lock generation from this Linux environment
- no FFmpeg binaries, model weights, archives, generated media, or caches
- no `models/README.md` because the user has not approved tracking files under
  the ignored `models/` directory

## Files Added Or Updated

- `.gitignore`
- `requirements/base.in`
- `requirements/win-cpu.txt`
- `requirements/win-cuda.txt`
- `vendor/README.md`
- `docs/INDEX.md`
- `docs/by-date/2026-06-24-step-11-dependency-and-asset-manifest.md`
- `docs/by-feature/current-project-status.md`
- `docs/by-feature/dependency-and-asset-manifest.md`
- `logs/INDEX.md`
- `logs/by-date/2026-06-24-step-11-dependency-and-asset-manifest.md`
- `logs/by-feature/dependency-and-asset-manifest.md`
- `README.md`

## Implementation Notes

- `requirements/base.in` lists direct project/build/test dependencies only.
- `requirements/win-cpu.txt` and `requirements/win-cuda.txt` are tracked
  placeholders that must be replaced after Windows x64 Python 3.11 lock
  generation and validation.
- The manifest documents separate PyTorch CPU/CUDA wheel-channel handling.
- FFmpeg manifest fields are present but pending exact source, version,
  license, local path, and checksum values.
- Model manifest fields are present but pending exact source, license/terms,
  local path, and checksum values.
- `.gitignore` now ignores `vendor/*` while explicitly allowing
  `vendor/README.md`.
- `models/` remains ignored.

## Checks Run During Implementation

- Passed: `git diff --check`.
- Passed: `git check-ignore -v vendor/README.md`.
- Passed: `git check-ignore -v vendor/ffmpeg/bin/ffmpeg.exe`.
- Passed: `PYTHONPATH=src python3 -m compileall -q src tests`.
- Passed: `PYTHONPATH=src python3 -m music_decomp --version`
  - Output: `music-decomp 0.1.0`.
- Not run successfully: `PYTHONPATH=src python3 -m pytest`
  - Result: `/usr/bin/python3: No module named pytest`.

## Reviewer Outcome

- Initial result: APPROVED, no blocking findings.
- Reviewer requested one wording improvement so placeholder lock files are not
  described as already tested locks.
- Executor applied the wording fix.
- Re-review result: APPROVED, no blocking findings.

## Known Risks Or Incomplete Items

- Real Windows CPU/CUDA lock files are still pending.
- FFmpeg is not staged and no FFmpeg checksum has been recorded.
- Demucs model weights are not staged and no model checksum has been recorded.
- Windows packaging and offline acceptance remain future steps.
