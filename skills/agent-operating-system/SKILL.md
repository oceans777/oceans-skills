---
name: agent-operating-system
description: 'Use when a user wants to audit, bootstrap, migrate, or operate a project using an eight-layer agent workflow with AGENTS.md, local rules, skills, scripts, hooks, worktrees, subagents, verification, commits, merges, and post-task learning capture.'
---

# Agent Operating System

## Overview

Turn a project into an eight-layer agent operating system: thin startup rules, scoped local rules, reusable skills, executable checks, deterministic hooks, isolated worktrees, subagent orchestration, and post-task evaluation.

## When To Use

Use this skill when the user asks to:

- Standardize agent workflow across projects.
- Slim or migrate a large `AGENTS.md` / `CLAUDE.md`.
- Initialize missing agent workflow files in a repository.
- Run many parallel feature tasks without branch pollution.
- Use worktrees and subagents safely.
- Make validation, commits, pushes, and merges less error-prone.

Do not use it for a one-off code change unless the user asks to change workflow architecture.

## Modes

Choose exactly one primary mode from the user's request:

| Mode | Trigger | Output |
| --- | --- | --- |
| `audit` | "review our AGENTS", "how should this be layered" | Layer report, no edits unless asked |
| `bootstrap` | "initialize this project", "create the missing files" | Create missing scaffold only |
| `migrate` | "split this AGENTS", "lower the context load" | Move content into correct layers |
| `start-task` | "start feature X", "new task branch" | Isolated worktree + branch plan |
| `parallel-work` | "six features at once", "use subagents" | Worktree/subagent assignment matrix |
| `finish-task` | "finish/merge/ship this task branch" | Verify, commit, push, merge, post-task triage |

## Eight Layers

1. **Memory / preference**: user or team defaults that apply across projects.
2. **Startup file**: `AGENTS.md` / `CLAUDE.md`; only hard rules, project map, and indexes.
3. **Path-scoped rules**: local constraints for directories, file types, modules, or packages.
4. **Skills**: multi-step judgment workflows, checklists, review flows, and reusable methods.
5. **Scripts / tools**: deterministic commands for validation, inspection, generation, or packaging.
6. **Hooks**: mandatory pre/post actions that cannot rely on model memory.
7. **Worktrees / subagents**: isolated execution lanes for parallel work and independent review.
8. **Evaluation / learning**: post-task triage that decides what should be promoted, automated, or deleted.

## Audit Flow

1. Read `AGENTS.md`, `CLAUDE.md`, `.githooks/`, `scripts/`, `docs/agent/`, existing skill mentions, and worktree configuration.
2. Classify each rule with this order:
   - Must always execute, zero exceptions -> hook.
   - Can be mechanically checked -> script/tool.
   - Applies only to a path -> local rule.
   - Multi-step judgment -> skill.
   - Long reference -> `docs/agent/`.
   - Every session must know it -> startup file.
   - One-off or unproven -> do not persist.
3. Report findings as:

```text
Layer:
Keep:
Move:
Create:
Risk:
Exact suggested file:
```

## Bootstrap Flow

When the user asks to create files, prefer the bundled script:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <skill-dir>/scripts/bootstrap-agent-os.ps1 -ProjectRoot <repo>
```

The script creates missing files only. It must not overwrite existing project files. If files exist, inspect and migrate manually.

Created scaffold:

- `AGENTS.md`
- `docs/agent/branch-workflow.md`
- `docs/agent/project-reference.md`
- `scripts/agent-verify.ps1`
- `.githooks/pre-commit`
- `.githooks/commit-msg`
- `.gitattributes` hook line-ending rule
- `.gitignore` entry for `.worktrees/`

Templates live in `assets/`. Read or copy them only when bootstrapping or explaining the scaffold.

## Worktree And Subagent Flow

Default model for parallel development:

```text
one task = one branch = one worktree = optional one implementer subagent
```

Use worktrees when:

- The user may open multiple windows.
- Multiple features are active.
- Switching the main checkout would disturb other work.
- A subagent will edit code.

When starting a task branch, prefer the bundled script:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <skill-dir>/scripts/start-agent-task.ps1 -ProjectRoot <repo> -TaskName "<task>" -BaselineBranch dev -TaskPrefix codex -EnsureIgnore
```

The script creates one task branch and one worktree from the baseline branch. It refuses to reuse an existing branch or worktree path.

Use subagents only when tasks are independent and the user has asked for subagent or parallel work. Give each subagent a distinct worktree, branch, file ownership, verification command, and merge target. Tell each subagent that other work may exist and it must not revert unrelated changes.

For detailed policy, read `references/worktree-and-subagent.md`. For delegation wording, read `references/subagent-prompt-templates.md`.

## Finish Flow

Before finishing a task branch:

1. Stage only task-owned files.
2. Run project verification, including `scripts/agent-verify.ps1` if present.
3. Commit with the project's required message format.
4. Push the task branch.
5. Merge or open PR according to project policy.
6. Push the baseline branch only when authorized by project rules.
7. Run proactive experience capture. The user does not need to know whether something is a "lesson" or "rule"; infer it from friction signals and use `experience-triage` logic only when there is a durable lesson.

For detailed capture signals and output shape, read `references/proactive-experience-capture.md`.

## Proactive Experience Capture

Do a light triage pass when the user says things like "this is unreasonable",
"why did this happen again", "restore the old way", "do not do this next time",
"should this be fixed as a process", or when a preventable workflow mistake
causes rework.

Do not force every correction into documentation. First decide whether it is
recurring, mechanical, path-scoped, workflow-shaped, project-critical, or
cross-project. If yes, propose the right layer and a small draft. If no, say
that no durable record is needed.

## Common Mistakes

- Moving everything out of `AGENTS.md`: hard rules still belong there.
- Putting mechanical checks in prose: automate them.
- Using hooks for judgment: hooks should enforce deterministic checks only.
- Letting multiple tasks share one worktree: this causes branch pollution.
- Dispatching subagents into the same checkout: give each editing subagent a separate branch/worktree.
- Overwriting an existing project workflow: audit first, patch narrowly.
- Hand-writing task setup every time: use `start-agent-task.ps1` when branch/worktree setup matters.
- Waiting for the user to name a "rule" or "lesson": infer durable lessons from friction signals and offer a triage draft.
