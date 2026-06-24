# CLI Workflows

Date: 2026-06-24

Related execution plan step: [Step 10 - Add CLI For Automation And Testing](step-by-step-execution-plan.md#step-10---add-cli-for-automation-and-testing)

## Status

Step 10 implementation is complete in this change set. The executor added the
non-GUI CLI workflows, the separate reviewer approved the change with no
blocking findings, and the main agent completed final documentation and
validation. Real FFmpeg/Demucs/SoundCard acceptance remains pending because the
current environment does not include those runtime dependencies.

## Implemented Commands

- `music-decomp gui`
- `music-decomp probe INPUT`
- `music-decomp separate INPUT --out OUTPUT_DIR --device auto --format wav`
- `music-decomp list-recording-devices`

## Behavior

- `probe` creates a `FileSeparationPipeline` and calls `probe_input`, then
  prints stable JSON with media kind, path, title, duration, sample rate, and
  stream summaries.
- `separate` creates a `FileSeparationPipeline` and calls `run_file`, sending
  progress messages to stderr and printing stable success JSON to stdout.
- `list-recording-devices` creates a `RecorderService` and prints available
  output devices as JSON.
- `gui` still launches the existing PySide6 GUI entry point.
- Normal command failures return exit code `1` and print a readable error
  without a Python traceback.
- Passing `--debug` before or after a subcommand prints the traceback for
  diagnosis.

## Tests

Executor-added tests cover:

- `probe` with mocked FFprobe output
- `separate` with a short local input and fake media/separation services
- recording device listing JSON through a fake recorder service
- default readable errors without tracebacks
- `--debug` traceback output

## Handoff Notes

- The CLI intentionally reuses `FileSeparationPipeline` and `RecorderService`
  instead of duplicating media probing, separation, or recorder logic.
- Normal stdout is JSON so future smoke scripts and packaging tests can parse
  it.
- Progress for long-running separation is printed to stderr so stdout remains
  machine-readable.
- The current environment does not have `pytest`; added tests were compiled but
  not executed here.
- Real integration still needs a Windows or fully provisioned environment with
  configured FFmpeg, Demucs/model files, and optional SoundCard.
