---
name: agent-operating-system
description: 'Use only when a user wants to design or change repository-wide agent workflow architecture: audit/bootstrap/migrate/dedupe AGENTS.md or CLAUDE.md, govern reusable prompts, install deterministic agent guards, or explicitly manage an isolated worktree/subagent task lifecycle. Do not invoke for ordinary code changes, commits, merges, or one-off worktree operations unless the user explicitly requests this skill or workflow architecture changes.'
---

# Agent Operating System

## Overview

Turn a project into an eight-layer agent operating system: thin startup rules, scoped local rules, reusable skills, executable checks, deterministic hooks, isolated worktrees, subagent orchestration, and post-task evaluation. Keep task prompts outcome-led and require explicit authorization for shared side effects.

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
| `prompt-governance` | "improve our task prompts", "replace rigid prompt templates" | Outcome/context/output/boundary/final-check rules and project template |
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

## Prompt Governance Flow

Use `prompt-governance` when a repository's startup rules or reusable task templates prescribe long roles, fixed step counts, or unconditional tool use.

1. Start with the observable result and audience.
2. Add only context that can change the result.
3. Specify output shape only when it affects usability.
4. Keep one to three critical boundaries, especially shared side effects.
5. Add a final check that can be verified.

All five parts are optional. Do not replace one rigid formula with another. Read `references/prompting-rules.md` for audit criteria and migration guidance.

## Audit Flow

1. Read `AGENTS.md`, `CLAUDE.md`, `.githooks/`, `scripts/`, `docs/agent/`, existing skill mentions, and worktree configuration.
2. Classify each item on two separate axes:
   - **Scope** decides where its entry point lives: cross-project preference, repository startup guidance, or path-scoped routing.
   - **Mechanism** decides how it works: judgment-heavy workflow -> skill; mechanically decidable operation -> script/tool; mechanically decidable lifecycle enforcement -> hook; long reference -> `docs/agent/`.
   - A path-scoped workflow may need both a short local routing rule and a reusable skill. Do not force the whole procedure into the local rule.
   - A mandatory but judgment-based rule belongs in startup/local guidance, not a hook. Hooks are only for deterministic pass/fail checks.
   - One-off or unproven lessons should not persist.
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

Generated examples are written in Chinese by default. Branches are detected from the repository when possible: the remote default branch becomes the baseline and the current branch becomes the integration branch. Override with `--baseline-branch`, `--dev-branch`, or `--task-prefix` when project policy differs.

Created scaffold:

- `AGENTS.md`
- Optional `CLAUDE.md` with `--require-claude` / `-RequireClaude`
- `.oceans/agent-standards.conf`
- `.oceans/templates/AGENTS.template.md`
- `.oceans/templates/CLAUDE.template.md`
- `docs/agent/branch-workflow.md`
- `docs/agent/prompting-workflow.md`
- `docs/agent/project-reference.md`
- `scripts/agent-bootstrap.ps1`
- `scripts/agent-bootstrap.sh`
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

The global guard calls `scripts/agent-standards-hook.sh`. It is deliberately
read-only: it checks whether required agent documents exist and are tracked,
checks staged whitespace, and validates commit-message format. It never creates
project files, writes review markers, launches an editor, or calls an LLM.
Missing documents are repaired only through an explicit `bootstrap` invocation,
where the generated files can be reviewed before they enter the repository.

Hook checks must stay deterministic. Do not call an LLM from a Git hook. For
AI-assisted tailoring, inspect the repository and edit `AGENTS.md` /
`CLAUDE.md` explicitly in response to the user request.

`install-global-hooks.sh` installs a self-contained copy of the guard under the
user's Git hook config directory, so commits do not depend on the current clone
path remaining unchanged. The installer prepares a complete replacement first
and rolls back the previous hook directory if activation fails.

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
powershell -NoProfile -ExecutionPolicy Bypass -File <skill-dir>/scripts/start-agent-task.ps1 -ProjectRoot <repo> -TaskName "<task>" -TaskPrefix codex -EnsureIgnore
```

```sh
sh <skill-dir>/scripts/start-agent-task.sh --project-root <repo> --task-name "<task>" --task-prefix codex --ensure-ignore
```

The task-start scripts use the current branch as the source by default. Pass `-BaselineBranch` or `--baseline-branch` explicitly when the current checkout is not the branch that should receive the task. They refuse to reuse an existing branch or worktree path.

Use subagents only when tasks are independent and the user has asked for subagent or parallel work. Give each subagent a distinct worktree, branch, file ownership, verification command, and merge target. Tell each subagent that other work may exist and it must not revert unrelated changes.

For detailed policy, read `references/worktree-and-subagent.md`. For delegation wording, read `references/subagent-prompt-templates.md`.

## Finish Flow

Before finishing a task branch:

1. Stage only task-owned files.
2. Run project verification, including `scripts/agent-verify.ps1` if present.
3. Commit with the project's required message format.
4. Push the task branch only when the current request authorizes a remote update.
5. Merge or open a PR only when authorized by the user and project policy.
6. Push the development integration branch only when the current request authorizes that shared side effect.
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
- Hand-writing task setup every time: use the platform-appropriate `start-agent-task` script when branch/worktree setup matters.
- Waiting for the user to name a "rule" or "lesson": infer durable lessons from friction signals and offer a triage draft.
