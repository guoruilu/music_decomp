# 2026-06-13 Repository Hygiene Log

## Task

User requested:

```text
AGENTS.md中加一条，每次我的需求都要原文记录到文档子目录中。完成任务后自己用git保存推送，不过在那之前先建立.gitignore文件，确保不要把不必要的文件commit。
```

## Actions

- Added `.gitignore` with Python, packaging, editor, generated media, runtime artifact, model, and vendor dependency ignore rules.
- Updated `AGENTS.md` with the new requirement-recording rule.
- Added the user's requirements verbatim to `docs/by-date/2026-06-13-user-requirements.md`.
- Updated `docs/INDEX.md` and `logs/INDEX.md`.

## Git Status

- Repository initialized successfully after elevated `git init`.
- Remote configured: `git@github.com:guoruilu/music_decomp.git`.
- Initial commit created: `554c298 Initialize project documentation`.
- Initial push completed: `main -> origin/main`.
