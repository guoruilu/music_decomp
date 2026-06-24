# 2026-06-24 Step 10 CLI Workflows

## Scope

Executor subagent implementation for Step 10 - Add CLI For Automation And
Testing.

## Changes Drafted

- Added `probe`, `separate`, and `list-recording-devices` subcommands.
- Kept the existing `gui` command and routed it through the shared CLI error
  handler.
- Added a shared `--debug` flag that shows tracebacks for command failures.
- Made default failures return `1` and print readable errors without
  tracebacks.
- Printed command success payloads as stable JSON.
- Sent separation progress to stderr so stdout remains parseable JSON.
- Reused `FileSeparationPipeline` for probe/separate workflows.
- Reused `RecorderService` for recording device enumeration.
- Added focused CLI tests for mocked FFprobe probing, fake-service separation,
  recording device listing, and error handling.

## Validation

- Passed: `PYTHONPATH=src python3 -m compileall -q src tests`
- Passed: `PYTHONPATH=src python3 -m music_decomp --version`
  - Output: `music-decomp 0.1.0`
- Passed: `PYTHONPATH=src python3 -m music_decomp`
  - Output: top-level help with `gui`, `probe`, `separate`, and
    `list-recording-devices`
- Passed: `PYTHONPATH=src python3 -m music_decomp probe definitely-missing.wav`
  - Result: exit code `1`, readable missing-FFmpeg error, no traceback
- Passed: `PYTHONPATH=src python3 -m music_decomp --debug probe definitely-missing.wav`
  - Result: exit code `1`, traceback printed for debugging
- Passed: `PYTHONPATH=src python3 -m music_decomp probe definitely-missing.wav --debug`
  - Result: exit code `1`, traceback printed for debugging
- Not run successfully: `PYTHONPATH=src python3 -m pytest tests/test_cli.py`
  - Result: `/usr/bin/python3: No module named pytest`

## Reviewer Notes

- Reviewer result: APPROVED, no blocking findings.
- Reviewer confirmed all four planned commands are implemented.
- Reviewer confirmed failure paths return nonzero and default errors hide
  tracebacks.
- Reviewer confirmed `--debug` prints tracebacks.
- Reviewer confirmed CLI workflows reuse existing services.
- Reviewer confirmed tests cover mocked probe, fake-service separation,
  recording device listing, and readable/debug error paths.

## Main-Agent Finalization

- The repeated Requirement 3 in
  `docs/by-date/2026-06-24-user-requirements.md` is intentional because the
  user repeated the same original request text and project rules require every
  new user requirement to be recorded verbatim.
- Commit and push are handled by the main agent after documentation/log updates.
