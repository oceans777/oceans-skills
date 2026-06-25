# Branch Workflow

## Baseline

- Baseline branch: `{{BASE_BRANCH}}`
- Task branch prefix: `{{TASK_PREFIX}}/`
- Worktree directory: `{{WORKTREE_DIR}}`

## Start A Task

```sh
git switch {{BASE_BRANCH}}
git pull --ff-only origin {{BASE_BRANCH}}
git worktree add {{WORKTREE_DIR}}/<task-name> -b {{TASK_PREFIX}}/<task-name>
cd {{WORKTREE_DIR}}/<task-name>
```

## Work

- Keep one worktree focused on one change intent.
- Re-read `AGENTS.md` from the task worktree.
- Run the project worktree/bootstrap script when present, such as `scripts/agent-worktree-init.sh`, `scripts/agent-bootstrap.sh`, or the platform-specific equivalent.
- Stage only task-owned files.
- Run the project verification entrypoint before commit, such as `scripts/agent-verify.sh`, `scripts/agent-verify.ps1`, package scripts, or language test commands.

## Finish

```sh
git add -- <task-files>
git commit -m "<type>: <title>"
git push -u origin {{TASK_PREFIX}}/<task-name>
```

## Merge Back

```sh
git switch {{BASE_BRANCH}}
git pull --ff-only origin {{BASE_BRANCH}}
git merge --no-ff -m "chore: merge <task-name>" {{TASK_PREFIX}}/<task-name>
# Push the baseline branch only when project policy authorizes it.
git push origin {{BASE_BRANCH}}
```
