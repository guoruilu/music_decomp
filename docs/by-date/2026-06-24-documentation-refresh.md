# 2026-06-24 Documentation Refresh

## User Requirement Recorded

The current user request was recorded verbatim in
`docs/by-date/2026-06-24-user-requirements.md`:

```text
先把文档该补齐的补齐。完成任务后自动git保存提交到远端
```

## Scope

This task is a documentation maintenance pass, not a numbered implementation
step from the execution plan.

In scope:

- Update stale top-level project status in `README.md`.
- Add a current project status handoff document.
- Correct stale Step 3 documentation that still said reviewer re-check,
  final validation, commit, and push were pending.
- Record the current remaining work and known documentation/implementation gaps.
- Update documentation and log indexes.

Out of scope:

- Business-code changes.
- Step 9 recording pipeline implementation.
- Windows manual acceptance testing.
- Dependency lock, asset manifest, packaging, or user-guide implementation.

## Workflow Note

The project workflow requires executor/reviewer subagents for numbered
implementation steps. This documentation refresh did not start a new numbered
implementation step. The available multi-agent tool policy also only permits
spawning subagents when the user explicitly requests delegation or parallel
agent work, so this docs-only maintenance task was performed by the main agent
and recorded here.

## Documentation Updates

- Replaced the scaffold-era `README.md` with a current status README.
- Added `docs/by-feature/current-project-status.md`.
- Updated `docs/by-feature/media-service-ffmpeg.md`.
- Updated `docs/by-date/2026-06-13-step-3-media-service.md`.
- Updated `logs/by-feature/media-service-ffmpeg.md`.
- Updated `logs/by-date/2026-06-13-step-3-media-service.md`.
- Added this dated documentation refresh entry.
- Added matching log entries under `logs/`.
- Updated `docs/INDEX.md` and `logs/INDEX.md`.

## Current Project Status After Refresh

- Current completed execution step: Step 8 - Wire End-To-End File Separation.
- Next planned execution step: Step 9 - Wire End-To-End Recording Separation.
- Latest tracked implementation commit: `f149209 Wire file separation pipeline`.
- Remaining planned steps: Step 9 through Step 14.

## Known Remaining Gaps

- Real Windows manual acceptance for local file separation has not been run.
- The Record tab is not wired to `RecorderService` yet.
- CLI probe/separate/recording-device commands are not implemented yet.
- Dependency locks, asset manifests, PyInstaller packaging, offline acceptance,
  user guide, and troubleshooting docs remain pending.
- `highest` approximation details are not yet persisted in normal success
  `job.json` metadata.

## Validation

- Passed: `git diff --check`.
- Passed: `PYTHONPATH=src python3 -m music_decomp --version`
  - Output: `music-decomp 0.1.0`.
- Passed: `PYTHONPATH=src python3 -m compileall -q src tests`.
- Not run successfully: `python3 -m pytest`
  - Result: `/usr/bin/python3: No module named pytest`.
