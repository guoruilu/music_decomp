# Agent Coordination Workflow

Date: 2026-06-13

## Summary

Every implementation step must be coordinated by the main agent and executed through two separate subagents:

- `executor`: performs the step implementation.
- `reviewer`: strictly reviews the executor's work.

The step is not complete until the executor has addressed reviewer feedback and the reviewer confirms that no issues remain.

## Required Loop

1. The main agent reads the current docs, logs, git status, and the relevant step from `docs/by-feature/step-by-step-execution-plan.md`.
2. The main agent starts a dedicated `executor` subagent for exactly one implementation step.
3. The `executor` implements only that step's scope and reports:
   - files changed
   - commands run
   - tests/checks run
   - known risks or incomplete items
4. The main agent starts a separate `reviewer` subagent for the same step.
5. The `reviewer` must inspect the diff and focus on:
   - correctness
   - missed requirements
   - bugs or regressions
   - missing or weak tests
   - documentation/logging gaps
   - accidental tracked/generated files
6. If the reviewer finds issues, the main agent sends the feedback back to the `executor`.
7. The `executor` fixes the issues and reports the changes.
8. The `reviewer` reviews again.
9. Repeat until both are true:
   - the `executor` reports the step is complete
   - the `reviewer` reports no remaining blocking issues
10. The main agent then:
   - updates docs and logs
   - records any new user requirements verbatim
   - verifies git status
   - commits
   - pushes
   - reports the final result to the user

## Main Agent Responsibilities

- Own coordination, scope control, and final project records.
- Ensure executor and reviewer are separate subagents.
- Keep each executor assignment limited to one step from the execution plan.
- Ensure reviewer feedback is actually addressed before closing the step.
- Prevent unrelated refactors from being mixed into the step.
- Maintain `docs/` and `logs/` so a new agent can take over quickly.
- Commit and push only after the executor/reviewer loop is complete.

## Blocking Rule

If the environment does not provide a usable subagent mechanism for an implementation step, the main agent must not silently bypass this workflow. It must record the blocker in `logs/`, tell the user, and ask how to proceed.

