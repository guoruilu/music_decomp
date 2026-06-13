# Project Agent Index

## Rules

所有代码、文档、日志存放在本地，文档（包括项目进展）、日志要分别有两个子目录存放，要根据功能、日期分类存放，并在顶层有索引，结构化组织。AGENTS.md文档应始终保持精简，细节记录在文档目录下，AGENTS中只记录索引。每次任务执行完都要详细记录文档和日志，要详细到任何一个新的agent来都能迅速接手项目。有任何问题先采访我。

每次用户需求都要原文记录到文档子目录中。

每一步实施任务都必须由主agent组织一个单独的executor子agent执行，并由一个单独的reviewer子agent严格审核；reviewer意见反馈给executor修改后再复审，直到executor和reviewer都确认没有问题，主agent才能结束该步并按要求记录推进项目。

## Index

- Documentation index: [docs/INDEX.md](docs/INDEX.md)
- Log index: [logs/INDEX.md](logs/INDEX.md)
- Current product plan: [docs/by-feature/windows-offline-stem-separation-plan.md](docs/by-feature/windows-offline-stem-separation-plan.md)
- Step-by-step execution plan: [docs/by-feature/step-by-step-execution-plan.md](docs/by-feature/step-by-step-execution-plan.md)
- Agent coordination workflow: [docs/by-feature/agent-coordination-workflow.md](docs/by-feature/agent-coordination-workflow.md)
- User requirement records: [docs/by-date/2026-06-13-user-requirements.md](docs/by-date/2026-06-13-user-requirements.md)
