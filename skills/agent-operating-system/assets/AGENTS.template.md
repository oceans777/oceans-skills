# AGENTS.md

## Startup Rules

- This file is the project startup layer. Keep it thin: hard rules, project map, and pointers to deeper layers.
- Direct user instructions override this file.
- Protect existing user work. Do not overwrite, delete, or revert unrelated changes.
- Work on one change intent at a time.

## Project Map

- Baseline branch: `{{BASE_BRANCH}}`
- Agent reference docs: `docs/agent/`
- Verification script: `scripts/agent-verify.ps1`
- Hooks directory: `.githooks/`

## Layering Rules

- Global hard rules stay here.
- Path-specific rules belong near the path or in `docs/agent/`.
- Multi-step judgment workflows belong in skills.
- Mechanical checks belong in scripts.
- Mandatory checks belong in hooks.
- Long references belong in `docs/agent/`.

## Git Workflow

- Start independent work from latest `{{BASE_BRANCH}}`.
- Use `{{TASK_PREFIX}}/<task-name>` task branches.
- Prefer one task branch per worktree for parallel work.
- Verify before commit and before merge.
- Stage only files owned by the current task.

See `docs/agent/branch-workflow.md`.
