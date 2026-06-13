# Separation Service With Demucs

Date: 2026-06-13

Related execution plan step: [Step 5 - Implement SeparationService](step-by-step-execution-plan.md#step-5---implement-separationservice)

## Status

Step 5 is complete. The executor implemented the separation service, addressed reviewer feedback, the reviewer approved the revised work, and the main agent completed final validation.

## Implemented Files

- `src/music_decomp/services/separation_service.py`
- `src/music_decomp/services/__init__.py`
- `tests/test_synthetic_audio.py`
- `pyproject.toml`

## Behavior

- `SeparationService.separate(...)` accepts an existing `JobResult` and a canonical 44.1 kHz stereo mixture WAV path.
- Demucs is imported lazily through `demucs.api.Separator` and `demucs.api.save_audio`; importing `music_decomp.services` does not require Torch, NumPy, or Demucs.
- Demucs separators are cached per process by `(model_name, device)`.
- Optional heavy dependencies are declared only under the `separation` extra:
  - `demucs`
  - `numpy`
  - `torch`
  - `torchaudio`
- Device resolution:
  - `cpu` always uses CPU.
  - `cuda` requires `torch.cuda.is_available()` or raises `SeparationDeviceError`.
  - `auto` uses CUDA when available and CPU otherwise.
  - If an `auto` CUDA attempt fails while loading or running the backend, the service logs a warning and retries CPU once.
- Raw Demucs stems are written to `_intermediate/demucs/` inside the job directory:
  - `vocals.wav`
  - `drums.wav`
  - `bass.wav`
  - `other.wav`
- Final requested stems are copied or converted to the configured output format.
- `lowest` is derived from the Demucs bass stem when available.
- If `bass` is requested and Demucs does not produce it, the service fails clearly with `SeparationError`.
- If `bass` is not requested and no bass stem is available, `lowest` falls back to FFmpeg `lowpass=f=250` from the mixture.
- `highest` is always an approximation derived with FFmpeg `highpass=f=2500,lowpass=f=12000`.
- Derived intermediate WAV files are written to `_intermediate/derived/` inside the job directory.
- Progress callback stages are:
  - `preparing`
  - `loading_model`
  - `separating`
  - `exporting`
  - `done`
  - `failed`

## Returned Metadata For Later Job JSON

`SeparationRunResult` returns:

- `actual_device`
- actual written `output_files`
- per-stem `StemOutputInfo`
- `highest_is_approximate`
- CUDA fallback warnings, if any

This is enough for a later metadata step to label `highest` as approximate without changing Step 4 metadata writing in this executor scope.

## Limitation

Step 5 does not perform clipping-dependent normalization for `highest`. The returned `StemOutputInfo` records `normalized=False` and notes that the band-pass output is an approximation. This is deferred until there is a clear, testable audio-level analysis path.

## Tests

- Mocked service flow without real Demucs.
- CPU, CUDA, and auto device resolution.
- Auto CUDA failure fallback to CPU.
- Success and failure progress callback sequences.
- Lowest derivation from bass and low-pass fallback when bass is absent.
- Missing requested `bass` fails instead of silently using the `lowest` fallback.
- Highest high-pass plus low-pass command construction.
- Non-WAV requested output conversion command construction.
- Demucs separator process-cache behavior using a fake API.
- Real Demucs smoke test is present but skipped unless `RUN_DEMUCS_INTEGRATION=1`.

## Handoff Notes

- Normal pytest does not require Torch, NumPy, Demucs, or real FFmpeg.
- Tests generate only tiny stdlib WAV fixtures under pytest `tmp_path`.
- `docs/codex-review/` existed as user-owned untracked content and was not modified.
- Reviewer feedback round 1 requested explicit failure for missing requested `bass`; the executor implemented the fix and added a regression test.
- Next step: Step 6 - Implement RecorderService.
