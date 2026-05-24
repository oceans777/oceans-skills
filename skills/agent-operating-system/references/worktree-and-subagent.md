# Worktree And Subagent Strategy

## Core Rule

Use this mapping for parallel agentic development:

```text
one task = one branch = one worktree = optional one implementer subagent
```

The baseline checkout should remain clean and on the integration branch
(`dev`, `main`, or the project-defined baseline).

## Worktree Creation Policy

Before creating a worktree:

1. Detect whether the current checkout is already a linked worktree.
2. Prefer platform-native worktree support if available.
3. If falling back to Git, prefer a project-local `.worktrees/` only when it is ignored.
4. Otherwise use a global worktree directory.

Recommended branch names:

```text
codex/<short-task-name>
codex/<area>-<intent>
```

Recommended local paths:

```text
.worktrees/<short-task-name>/
~/.config/superpowers/worktrees/<project>/<short-task-name>/
```

## Task Start Script

Prefer the bundled script when creating a new task lane:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <skill-dir>/scripts/start-agent-task.ps1 -ProjectRoot <repo> -TaskName "<task>" -BaselineBranch dev -TaskPrefix codex -EnsureIgnore
```

The script:

- Creates a safe task slug.
- Creates `codex/<slug>` unless `-BranchName` is provided.
- Creates one worktree at `.worktrees/<slug>` by default.
- Fetches `origin/<baseline>` and starts from the fetched commit when `origin` is available.
- Refuses to continue when fetch fails, unless `-NoFetch` is explicitly used.
- Refuses to overwrite an existing local branch, remote branch, or worktree path.
- Optionally appends `.worktrees/` to `.gitignore` with `-EnsureIgnore`.

## Subagent Use

Use subagents when the user explicitly asks for subagents, delegation, or
parallel work and the tasks are independent.

Good subagent tasks:

- Implement one feature slice in one worktree.
- Review a completed branch.
- Run browser QA while the main agent continues non-overlapping work.
- Investigate a specific codebase question.

Bad subagent tasks:

- Editing the same files as another active agent.
- Solving an unclear root-cause bug before investigation.
- Touching baseline branch directly.
- Reverting unknown changes.

## Subagent Prompt Contract

Every editing subagent should receive:

- Worktree path.
- Branch name.
- Baseline branch.
- Owned files or directories.
- Explicit instruction not to revert unrelated changes.
- Verification command.
- Expected final report with changed files and test results.

Use `references/subagent-prompt-templates.md` for implementer, reviewer,
verifier, and integrator prompt shapes.

## Merge Policy

Before merging a task branch:

1. Fetch baseline.
2. Rebase or merge latest baseline into the task branch.
3. Re-run verification.
4. Push task branch.
5. Merge via project policy: PR, no-ff merge, or fast-forward.
6. Push baseline only when the project rules authorize it.

Conflicts are not mechanical. Stop, explain affected files, and resolve with
the smallest possible edits.
