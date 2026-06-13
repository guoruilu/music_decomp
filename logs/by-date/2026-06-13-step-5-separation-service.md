# 2026-06-13 Step 5 Separation Service Log

## Task

Executor assignment: implement only Step 5 - Implement SeparationService.

Required verbatim user request recorded:

```text
继续执行
```

## Precheck

Command: `git status --short`

Result:

```text
?? docs/codex-review/
```

No changed files existed outside `docs/codex-review/` before Step 5 work started. The executor did not touch `docs/codex-review/`.

## Files Added Or Updated

- `pyproject.toml`
- `src/music_decomp/services/__init__.py`
- `src/music_decomp/services/separation_service.py`
- `tests/test_synthetic_audio.py`
- `docs/INDEX.md`
- `docs/by-date/2026-06-13-step-5-separation-service.md`
- `docs/by-date/2026-06-13-user-requirements.md`
- `docs/by-feature/separation-service-demucs.md`
- `logs/INDEX.md`
- `logs/by-date/2026-06-13-step-5-separation-service.md`
- `logs/by-feature/separation-service-demucs.md`

## Implementation Notes

- `SeparationService.separate(...)` takes an existing `JobResult` plus a canonical mixture WAV path.
- Demucs and Torch are never imported at module import time.
- Real Demucs model loading happens through `DemucsSeparatorBackend.separate_to_wav(...)` on first use.
- Loaded Demucs separators are cached by `(model_name, device)`.
- `auto` device uses CUDA when available, otherwise CPU.
- `auto` CUDA backend failures are logged and retried on CPU once.
- FFmpeg filter commands are list arguments and are mocked in unit tests.
- `lowest` uses the bass stem when present and falls back to `lowpass=f=250` from the mixture when absent.
- If `bass` itself is requested and the raw Demucs output does not include it, the service fails with `SeparationError` instead of silently deriving only `lowest`.
- `highest` uses `highpass=f=2500,lowpass=f=12000` from the mixture and is returned as approximate.
- Intermediate WAV files stay under the job directory.
- Heavy dependencies are optional under the `separation` extra.

## Checks Run

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

## Known Risks Or Incomplete Items

- `highest` is an approximation and no clipping-dependent normalization is applied in Step 5.
- `ExportService.write_job_metadata(...)` has not yet been extended to persist `StemOutputInfo`; Step 5 returns the required data for a later metadata wiring step.
- The real Demucs smoke test is skipped by default and was not run in this Linux executor environment.

## Result

Step 5 is complete after addressing the first reviewer change request. The reviewer approved the revised work, and the main agent completed final validation before commit and push.
