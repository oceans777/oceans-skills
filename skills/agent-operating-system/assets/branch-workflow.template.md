# Branch Workflow

## Baseline

- Baseline branch: `{{BASE_BRANCH}}`
- Task branch prefix: `{{TASK_PREFIX}}/`
- Worktree directory: `{{WORKTREE_DIR}}`

## Start A Task

```powershell
git switch {{BASE_BRANCH}}
git pull --ff-only origin {{BASE_BRANCH}}
git worktree add {{WORKTREE_DIR}}/<task-name> -b {{TASK_PREFIX}}/<task-name>
```

## Work

- Keep one worktree focused on one change intent.
- Stage only task-owned files.
- Run `scripts/agent-verify.ps1` before commit.

## Finish

```powershell
git add -- <task-files>
git commit -m "<type>: <title>"
git push -u origin {{TASK_PREFIX}}/<task-name>
```

## Merge Back

```powershell
git switch {{BASE_BRANCH}}
git pull --ff-only origin {{BASE_BRANCH}}
git merge --no-ff -m "chore: merge <task-name>" {{TASK_PREFIX}}/<task-name>
git push origin {{BASE_BRANCH}}
```
