# Subagent Prompt Templates

Use these templates only when the user explicitly asks for subagents,
delegation, or parallel work. Each editing subagent must own one branch and
one worktree.

## Common Contract

Every prompt should include:

- Worktree path.
- Branch name.
- Baseline branch.
- Owned files or directories.
- Out-of-scope files or behaviors.
- Verification command.
- Final report requirements.

Every prompt should also say:

```text
You are not alone in this codebase. Other work may be happening in parallel.
Do not revert, delete, reformat, or "clean up" unrelated changes. If another
change blocks your task, stop and report the exact file and conflict.
```

## Implementer

```text
Use the repository at: <worktree-path>
Branch: <branch>
Baseline: <baseline>
Task: <one concrete task>
Owned files/directories: <paths>
Out of scope: <paths or behaviors>

Implement only this task. Follow the repo AGENTS.md and local rules.
Do not revert unrelated changes. Do not touch files outside the owned scope
unless the task is impossible without it; if that happens, stop and report why.

Verification command: <command>

Final report:
- Files changed
- What changed
- Verification run and result
- Any risks or follow-up needed
```

## Reviewer

```text
Review the task branch in: <worktree-path>
Branch: <branch>
Baseline: <baseline>
Review scope: <paths or diff range>

Act as an independent reviewer. Look for correctness bugs, regressions,
missing verification, unsafe Git behavior, and mismatch with the task intent.
Do not modify files.

Final report:
- Findings first, ordered by severity
- File and line references
- Open questions
- Residual risk if no findings
```

## Verifier

```text
Verify the task branch in: <worktree-path>
Branch: <branch>
Baseline: <baseline>
Verification target: <feature or behavior>

Run the specified checks and any cheap adjacent checks that directly validate
the changed behavior. Do not edit files unless the user explicitly asked for
fixes.

Required command: <command>

Final report:
- Commands run
- Pass/fail result
- Important output summary
- Repro steps for failures
```

## Integrator

```text
Prepare integration for: <worktree-path>
Task branch: <branch>
Baseline branch: <baseline>

Fetch the latest baseline, inspect divergence, and report whether the branch
is ready to merge. Do not force-push. Do not resolve non-trivial conflicts
without reporting them first.

Final report:
- Baseline commit inspected
- Divergence summary
- Conflicts, if any
- Verification required before merge
- Recommended merge action
```
