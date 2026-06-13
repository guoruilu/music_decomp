# Repository Hygiene And Git Workflow

Date: 2026-06-13

## Rules

- Keep `.gitignore` in place before committing project files.
- Do not commit generated media, runtime caches, local virtual environments, build outputs, bundled model files, or vendored binaries unless explicitly approved.
- Record every user requirement verbatim under `docs/`.
- At task completion, update documentation and logs before committing.
- Save completed work with git and push to the configured remote when available.

## Current Git Remote

- `origin`: `git@github.com:guoruilu/music_decomp.git`
- Primary branch: `main`

## Current Ignore Policy

- Python caches and test caches are ignored.
- Virtual environments are ignored.
- PyInstaller and packaging outputs are ignored.
- Generated media and runtime output directories are ignored.
- Large `models/` and `vendor/` directories are ignored by default and should be handled as release artifacts unless explicitly approved for version control.

