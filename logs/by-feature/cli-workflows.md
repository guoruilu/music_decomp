# CLI Workflows Log

Date: 2026-06-24

## Scope

Executor assignment: implement only Step 10 - Add CLI For Automation And
Testing.

Constraints followed:

- no Step 11 dependency lock or asset manifest work
- no packaging work
- no commit or push by executor or reviewer
- no real FFmpeg, Demucs, SoundCard, PySide6, torch, model files, network, or
  Windows device requirement for normal tests
- preserve existing GUI and pipeline behavior

## Files Added Or Updated

- `src/music_decomp/cli.py`
- `tests/test_cli.py`
- `docs/INDEX.md`
- `docs/by-date/2026-06-24-step-10-cli-workflows.md`
- `docs/by-feature/cli-workflows.md`
- `docs/by-feature/current-project-status.md`
- `logs/INDEX.md`
- `logs/by-date/2026-06-24-step-10-cli-workflows.md`
- `logs/by-feature/cli-workflows.md`
- `README.md`

## Implementation Notes

- The CLI builds all subcommands from `argparse`.
- `probe` calls `FileSeparationPipeline.probe_input`.
- `separate` calls `FileSeparationPipeline.run_file`.
- `list-recording-devices` calls `RecorderService.list_output_devices`.
- `gui` calls the existing application GUI entry point.
- Success output is JSON on stdout.
- Separation progress is line-oriented text on stderr.
- Normal exceptions are caught and rendered as readable errors with exit code
  `1`.
- `--debug` switches the same failure paths to traceback output.

## Checks Run During Implementation

- Passed: `python3 -B` syntax/compile smoke checks run by executor.
- Passed: `PYTHONPATH=src python3 -m compileall -q src tests`.
- Passed: `PYTHONPATH=src python3 -m music_decomp --version`
  - Output: `music-decomp 0.1.0`
- Passed: `PYTHONPATH=src python3 -m music_decomp`
  - Output included all Step 10 subcommands.
- Passed: `PYTHONPATH=src python3 -m music_decomp probe definitely-missing.wav`
  - Result: exit code `1`, readable missing-FFmpeg error, no traceback.
- Passed: `PYTHONPATH=src python3 -m music_decomp --debug probe definitely-missing.wav`
  - Result: exit code `1`, traceback printed for debugging.
- Passed: `PYTHONPATH=src python3 -m music_decomp probe definitely-missing.wav --debug`
  - Result: exit code `1`, traceback printed for debugging.
- Not run successfully: `PYTHONPATH=src python3 -m pytest tests/test_cli.py`
  - Result: `/usr/bin/python3: No module named pytest`

## Reviewer Outcome

- Result: APPROVED, no blocking findings.
- Reviewer confirmed the planned commands, error behavior, service reuse, and
  focused test coverage.
- Reviewer suggested optional extra coverage for `--debug` before the subcommand;
  manual review showed the current parser supports this.

## Known Risks Or Incomplete Items

- Pytest was unavailable in this environment, so the new tests were compiled
  but not executed.
- No real FFmpeg/Demucs/model separation run was executed.
- No real SoundCard device enumeration was executed.
- No Windows packaged CLI smoke test was run.
- Final commit and push are handled by the main agent after docs/log updates.
