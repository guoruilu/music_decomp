# 2026-06-24 Step 13 Offline Acceptance

## Scope

Executor subagent preflight for Step 13 - Offline Acceptance Test.

The requested acceptance is a real Windows offline test of a copied portable
package. The current environment is Linux and does not contain the portable
package or required bundled assets, so this pass records blockers and the
remaining Windows procedure. It does not claim Step 13 completion.

## Required Files Read

- `AGENTS.md`
- `docs/INDEX.md`
- `docs/by-feature/windows-offline-stem-separation-plan.md`
- `docs/by-feature/step-by-step-execution-plan.md`
- `docs/by-feature/current-project-status.md`
- `docs/by-feature/agent-coordination-workflow.md`
- `docs/by-feature/windows-packaging.md`
- `docs/by-feature/dependency-and-asset-manifest.md`
- `packaging/windows/build.ps1`
- `packaging/windows/smoke-test.ps1`
- `scripts/verify_portable_package.py`

## Preflight Checks

| Command | Result |
| --- | --- |
| `git rev-parse --abbrev-ref HEAD` | `main` |
| `git rev-parse --short HEAD` | `1976823` |
| `uname -a` | Linux WSL2 x86_64, not Windows x64 |
| `python3 -c "import platform, sys; ..."` | Linux x86_64, Python 3.12.3 |
| `python -c "import platform, sys; ..."` | Failed: `python: command not found` |
| `ls -la dist/MusicDecomp` | Failed: directory does not exist |
| `ls -la vendor/ffmpeg/bin` | Failed: directory does not exist |
| `ls -la models` | Failed: directory does not exist |
| `cat requirements/win-cpu.txt` | Placeholder, `Status: NOT GENERATED` |
| `cat requirements/win-cuda.txt` | Placeholder, `Status: NOT GENERATED` |
| `python3 scripts/verify_portable_package.py --package-dir dist/MusicDecomp --structure-only` | Failed: package directory does not exist |

## Blockers

- The executor is running on Linux WSL2, while Step 13 requires Windows x64.
- There is no `dist/MusicDecomp/` portable package to copy to a clean directory.
- Bundled FFmpeg binaries are not staged in `vendor/ffmpeg/bin/`.
- Bundled model assets and `models/manifest.json` are not staged.
- Windows CPU and CUDA dependency locks remain explicit placeholders.
- No offline Windows GUI launch, local audio separation, local video separation,
  or system-audio recording can be performed from this checkout.

## Tests Not Run

- `MusicDecomp.exe` launch in a clean offline Windows directory.
- Settings tab verification for bundled FFmpeg, bundled model, CPU, and optional
  GPU status.
- CPU separation of a short audio file.
- Separation of a short video file with audio.
- Windows system-audio recording followed by separation.
- Inspection of successful `job.json`, `job.log`, and all six output files.
- Missing-DLL dialog observation.
- Offline/no-network confirmation.
- Manual quality review of generated outputs.

## Result

Step 13 is blocked and remains pending. The only work performed in this pass
was documentation and logging of the blockers and required Windows acceptance
procedure.

It is acceptable to commit this blocked/preflight record with a message that
clearly says acceptance is blocked. Do not use the completion-style
`Record offline acceptance results` commit message until a real Windows offline
acceptance run passes or fails with actual results.
