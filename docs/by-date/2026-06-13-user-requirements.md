# 2026-06-13 User Requirements

## Requirement 1

```text
我想要写一个软件（运行在windows系统上），可以将一首歌中不同的乐器分别提取出来。如果做不到，至少要能够把最低音的乐器和最高音的乐器的声音提取出来。这个软件应该是自包含的，不需要联网，不需要额外下载数据库或工具。输入应当可以是各种常见的音频文件；但除此之外，很多时候只有视频，甚至是在线视频，这种情况也要能够解决，我的一个可能可行的想法是让用户完整放一遍，然后使用录音功能记录下来再做转换，你如果有更好的方式也可以提出来。引号中的内容放到AGENTS.md中：“所有代码、文档、日志存放在本地，文档（包括项目进展）、日志要分别有两个子目录存放，要根据功能、日期分类存放，并在顶层有索引，结构化组织。AGENTS.md文档应始终保持精简，细节记录在文档目录下，AGENTS中只记录索引。每次任务执行完都要详细记录文档和日志，要详细到任何一个新的agent来都能迅速接手项目。有任何问题先采访我。”
```

## Requirement 2

```text
先把plan存到文档子目录下，把AGENTS.md建好
```

## Requirement 3

```text
AGENTS.md中加一条，每次我的需求都要原文记录到文档子目录中。完成任务后自己用git保存推送，不过在那之前先建立.gitignore文件，确保不要把不必要的文件commit。
```

## Requirement 4

```text
现在把plan整理成一份可以step by step执行得详细方案，详细到任何一个新的agent拿到之后都可以直接执行得程度。
```

## Requirement 5

```text
在 AGENTS.md 中加一条，每一步的任务都要分别用一个单独的子agent executor来执行，然后用一个单独的子agent reviewer来严格审核，审核完之后意见反馈给executor修改，之后再由reviewer审核，知道双方都没有问题了才结束，然后你作为主agent负责组织协调并按要求记录推进项目。
```

## Requirement 6

```text
现在开始执行方案
```

## Requirement 7

```text
可以考虑使用已有的python虚拟环境，如果不行也可以新建一个虚拟环境
```

## Requirement 8

```text
继续执行
```

## Requirement 9

```text
先检查一下除了docs/codex-review/之外有没有其它文件被改动。没有的话继续执行。
```

## Requirement 10

```text
Reviewer returned CHANGES_REQUESTED for Step 3.

Required fix:
- Add explicit missing-FFprobe negative-path coverage in tests/test_media_service.py.
- Test scenario: MUSIC_DECOMP_FFPROBE unset, bundled ffprobe.exe absent, system ffprobe unavailable.
- Assert MissingExecutableError message includes both `ffprobe` and `MUSIC_DECOMP_FFPROBE`.

Constraints:
- Do not touch docs/codex-review/.
- Keep changes scoped to Step 3. Update docs/logs only if needed to reflect the additional check.
- Do not commit or push.

After fixing, run `.venv/bin/python -m pytest`, `.venv/bin/python -m music_decomp --version`, and `git diff --check`. Report files changed and results.
```

## Requirement 11

```text
继续执行
```
