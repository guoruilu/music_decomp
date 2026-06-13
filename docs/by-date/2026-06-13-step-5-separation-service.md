# 2026-06-13 Step 5 Separation Service

## User Requirement Recorded

The required verbatim user request was added to `docs/by-date/2026-06-13-user-requirements.md`:

```text
继续执行
```

## Initial Worktree Check

Before implementing Step 5, `git status --short` showed only:

```text
?? docs/codex-review/
```

`docs/codex-review/` was treated as user-owned untracked content and was not modified, removed, staged, or otherwise touched.

## Scope

Executor assignment: implement only Step 5 - Implement SeparationService from `docs/by-feature/step-by-step-execution-plan.md`.

## Implemented

- Added `SeparationService` for running a Demucs-compatible backend on a canonical mixture WAV.
- Added lazy `demucs.api.Separator` and `save_audio` loading.
- Added per-process Demucs separator cache keyed by model and device.
- Added device resolution for `cpu`, `cuda`, and `auto`.
- Added auto CUDA failure warning plus one CPU retry for model load or separation failures.
- Added job-local intermediate directories for raw Demucs stems and derived WAV files.
- Added final copy/convert handling for requested output format.
- Added `lowest` derivation from `bass` when available.
- Added `lowest` low-pass fallback from mixture when `bass` is unavailable.
- Added reviewer-requested behavior: missing requested `bass` now fails with `SeparationError`; low-pass fallback is only for `lowest` when `bass` itself was not requested.
- Added `highest` band-pass approximation from mixture.
- Added progress callback stages for success and failure.
- Added returned per-stem output information so later metadata can mark `highest` as approximate.
- Added optional `separation` dependency extra without making normal tests require heavy packages.
- Added focused mocked tests in `tests/test_synthetic_audio.py`.

## Status

- Executor subagent completed the Step 5 implementation and addressed the first reviewer change request.
- Reviewer subagent re-review approved the revised work with no blocking findings.
- Main agent completed final validation and will commit/push the accepted result.

## Validation

- Passed: `.venv/bin/python -m pytest`
  - Initial result: 36 tests passed, 1 skipped.
  - After reviewer fix: 37 tests passed, 1 skipped.
- Passed: `.venv/bin/python -m music_decomp --version`
  - Initial result: `music-decomp 0.1.0`.
  - After reviewer fix: `music-decomp 0.1.0`.
- Passed: `git diff --check`
  - Initial result: no whitespace errors.
  - After reviewer fix: no whitespace errors.
- Ran: `git status --short`
  - Result after reviewer fix: expected Step 5 files plus pre-existing untracked `docs/codex-review/`.
- Reviewer re-check also passed:
  - `.venv/bin/python -m pytest -p no:cacheprovider`: 37 tests passed, 1 skipped.
  - `git diff --check`: passed.
  - `.venv/bin/python -m music_decomp --version`: `music-decomp 0.1.0`.
  - `docs/codex-review/` remained untracked and unstaged.

## Deviations

- Heavy separation dependencies were declared as an optional `separation` extra instead of mandatory project dependencies so the current unit test environment can run without Torch, NumPy, or Demucs.
- `highest` clipping-dependent normalization is deferred. The service records `normalized=False` and an approximation note in `StemOutputInfo`.
- No real Demucs run was performed. The real smoke test is skipped unless `RUN_DEMUCS_INTEGRATION=1`.

## Next Action

Start Step 6 from the detailed execution plan: implement `RecorderService`.
