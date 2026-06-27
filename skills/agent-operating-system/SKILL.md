---
name: agent-operating-system
description: 'Use when a user wants to audit, bootstrap, migrate, dedupe, or operate a project using an eight-layer agent workflow with AGENTS.md, CLAUDE.md, local rules, skills, scripts, Git hooks, first-commit standards guards, worktrees, subagents, verification, commits, merges, and post-task learning capture.'
---

# Agent Operating System

## Overview

Turn a project into an eight-layer agent operating system: thin startup rules, scoped local rules, reusable skills, executable checks, deterministic hooks, isolated worktrees, subagent orchestration, and post-task evaluation.

## When To Use

Use this skill when the user asks to:

- Standardize agent workflow across projects.
- Slim or migrate a large `AGENTS.md` / `CLAUDE.md`.
- Install a local or global Git hook that checks agent docs and commit messages.
- Initialize missing `AGENTS.md` / `CLAUDE.md` from reusable templates without overwriting existing files.
- Dedupe global and project-level agent rules to reduce repeated context.
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
| `install-global-guard` | "make every git commit check AGENTS", "install global hooks" | Install non-overwriting global Git hooks |
| `dedupe` | "global and project AGENTS duplicate", "reduce token usage" | Duplicate report, no automatic deletion |
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

```sh
sh <skill-dir>/scripts/bootstrap-agent-os.sh --project-root <repo>
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <skill-dir>/scripts/bootstrap-agent-os.ps1 -ProjectRoot <repo>
```

The script creates missing files only. It must not overwrite existing project files. If files exist, inspect and migrate manually.

By default, generated examples are written in Chinese, protect `main` as the baseline branch, use `dev` as the development integration branch, and use `codex/` for task branches. Override with `--baseline-branch`, `--dev-branch`, or `--task-prefix` only when the project has a different policy.

Created scaffold:

- `AGENTS.md`
- Optional `CLAUDE.md` with `--require-claude` / `-RequireClaude`
- `.oceans/agent-standards.conf`
- `.oceans/templates/AGENTS.template.md`
- `.oceans/templates/CLAUDE.template.md`
- `docs/agent/branch-workflow.md`
- `docs/agent/project-reference.md`
- `scripts/agent-bootstrap.ps1`
- `scripts/agent-verify.ps1`
- `scripts/agent-verify.sh`
- `scripts/agent-standards-hook.sh`
- `scripts/dedupe-agent-docs.sh`
- `.githooks/pre-commit`
- `.githooks/commit-msg`
- `.gitattributes` hook and shell-script line-ending rules
- `.gitignore` entry for `.worktrees/`

Templates live in `assets/`. Read or copy them only when bootstrapping or explaining the scaffold.

## Agent Standards Guard

Use the guard when the user wants agent standards to be checked automatically
during normal Git use.

For global hooks across repositories:

```sh
sh <skill-dir>/scripts/install-global-hooks.sh
```

If `git config --global core.hooksPath` already exists, do not overwrite it
silently. Use `--chain-existing` only when the user wants oceans777 checks to
run before the existing global hooks, or `--force` when they explicitly accept
replacement.

The global guard calls `scripts/agent-standards-hook.sh`. On the first guarded
commit per repository it:

1. Creates missing `AGENTS.md` from `assets/AGENTS.template.md`.
2. Creates missing `CLAUDE.md` only when `.oceans/agent-standards.conf` sets
   `require_claude_md=1`.
3. Never overwrites existing `AGENTS.md` or `CLAUDE.md`.
4. Opens existing or newly created docs with Cursor, VS Code, macOS `open`, or
   `xdg-open` when available.
5. Blocks once so the user reviews and stages required docs.
6. Stores the local reviewed marker inside Git's private state via
   `git rev-parse --git-path oceans-agent-standards-state`, not in the working
   tree.

Hook checks must stay deterministic. Do not call an LLM from a Git hook. For
AI-assisted tailoring, inspect the repository and edit `AGENTS.md` /
`CLAUDE.md` explicitly in response to the user request.

`install-global-hooks.sh` installs a self-contained copy of the guard and its
templates under the user's Git hook config directory, so commits do not depend
on the current clone path remaining unchanged.

## Dedupe Flow

Use dedupe when project startup docs repeat global or template rules and the
user wants to reduce duplicated context:

```sh
sh <skill-dir>/scripts/dedupe-agent-docs.sh --project <repo>
```

The script reports exact duplicate bullet rules only. It does not edit files.
Treat output as a review queue:

- Remove project-level duplicates only when they add no path, command, scope,
  exception, or stricter behavior.
- Keep project rules that specialize global rules.
- Keep repository-specific commands and constraints in the project startup doc
  or path-scoped local docs instead of duplicating broad global rules.
- Use AI judgment only through an explicit review task, not from a hook.

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

The task-start script keeps its `-BaselineBranch` parameter for compatibility; pass the project's development integration branch, usually `dev`, so the task worktree starts from the branch that will receive the merge. It refuses to reuse an existing branch or worktree path.

Use subagents only when tasks are independent and the user has asked for subagent or parallel work. Give each subagent a distinct worktree, branch, file ownership, verification command, and merge target. Tell each subagent that other work may exist and it must not revert unrelated changes.

For detailed policy, read `references/worktree-and-subagent.md`. For delegation wording, read `references/subagent-prompt-templates.md`.

## Finish Flow

Before finishing a task branch:

1. Stage only task-owned files.
2. Run project verification, including `scripts/agent-verify.ps1` if present.
3. Commit with the project's required message format.
4. Push the task branch.
5. Merge or open PR according to project policy.
6. Push the development integration branch only when authorized by project rules.
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
