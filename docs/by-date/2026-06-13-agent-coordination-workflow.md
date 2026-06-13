# 2026-06-13 Agent Coordination Workflow

## Summary

Added a project rule requiring each implementation step to use a dedicated executor subagent and a separate reviewer subagent. The main agent coordinates the loop, records progress, commits, and pushes only after executor and reviewer both agree the step is complete.

## Canonical Workflow

- [Agent coordination workflow](../by-feature/agent-coordination-workflow.md)

## Result

- `AGENTS.md` now contains the compact mandatory rule.
- Detailed executor/reviewer loop requirements are documented under `docs/by-feature/`.
- The step-by-step execution plan now references the required subagent review process.

