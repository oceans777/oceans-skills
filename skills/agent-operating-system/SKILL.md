---
name: agent-operating-system
description: 'Use only when the user wants to design or change repository-wide agent workflow architecture: audit/bootstrap/migrate/dedupe AGENTS.md or CLAUDE.md, govern reusable prompts, install deterministic agent guards, or explicitly manage an isolated worktree/subagent task lifecycle. Do not invoke for ordinary code changes, commits, merges, or one-off worktree operations unless the user explicitly requests this skill or workflow architecture changes.'
---

# Agent Operating System

## Purpose

Build and operate a repository-level agent workflow without turning every task into a heavyweight ceremony. Keep startup rules thin, move mechanical checks into scripts, keep hooks deterministic, isolate parallel edits, and require explicit authorization for shared side effects.

## Boundary

This skill owns repository-wide agent workflow architecture only.

- It does not replace domain skills such as `discuz-x5`.
- It does not contain a second experience-classification decision tree. When durable learning must be classified, invoke `experience-triage` and use its result.
- It does not run for ordinary implementation, review, commit, merge, or worktree operations unless the user explicitly asks for this skill or for workflow architecture changes.
- It never treats push, merge, release, deployment, message sending, or shared-branch mutation as implicitly authorized.

## Modes

Choose exactly one primary mode.

| Mode | Use when | Main result |
| --- | --- | --- |
| `audit` | Existing agent rules or workflow need review | Layer report; no edits unless requested |
| `bootstrap` | Missing repository workflow files must be created | Missing scaffold only |
| `migrate` | Large startup files need splitting | Content moved to the correct layers |
| `install-global-guard` | Deterministic global Git checks are requested | Non-overwriting hook installation |
| `dedupe` | Global and project rules repeat | Review report; no automatic deletion |
| `prompt-governance` | Reusable task prompts are rigid or noisy | Outcome-led prompt rules |
| `start-task` | An isolated task branch/worktree is explicitly requested | One branch and one worktree |
| `parallel-work` | Independent tasks and subagents are explicitly requested | Ownership and worktree matrix |
| `finish-task` | The user asks to finish or deliver a task branch | Verification and authorized delivery |

Do not combine modes merely because the skill supports them. Escalate only when the requested outcome requires it.

## Eight Layers

1. Cross-project memory or preference.
2. Repository startup file: `AGENTS.md` or `CLAUDE.md`.
3. Path-scoped local routing rules.
4. Judgment-heavy reusable skills.
5. Deterministic scripts or tools.
6. Deterministic lifecycle hooks.
7. Isolated worktrees and optional subagents.
8. Evaluation and durable-learning triage.

Scope and mechanism are separate axes. A path-scoped workflow may need a short local routing rule plus a reusable skill or script.

## Audit

Inspect startup files, local rules, `.githooks/`, scripts, agent documentation, skill references, branch policy, worktrees, and existing verification entry points.

Classify each item:

- Every session must know it -> startup file.
- Path-specific routing or constraint -> local rule.
- Multi-step judgment -> skill.
- Mechanically decidable operation -> script or tool.
- Mechanically decidable lifecycle enforcement -> hook.
- Long reference -> `docs/agent/`.
- One-off or unproven lesson -> do not persist.

Report `Keep`, `Move`, `Create`, `Risk`, and exact target path.

## Bootstrap And Upgrade Safety

Use the bundled platform script only after inspecting the repository and resolving branch policy.

```sh
sh <skill-dir>/scripts/bootstrap-agent-os.sh --project-root <repo> --baseline-branch <baseline> --dev-branch <integration>
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <skill-dir>/scripts/bootstrap-agent-os.ps1 -ProjectRoot <repo> -BaselineBranch <baseline> -DevBranch <integration>
```

The scripts create missing files only and do not overwrite existing project files. Treat the current branch as temporary unless repository evidence proves it is the long-lived integration branch. When the current branch differs from the remote default, pass the integration branch explicitly rather than persisting a guess.

Generated configuration records `schema_version` and `generator_version`. Read `references/versioning-and-upgrades.md` before changing generated templates or adding an upgrade path.

## Deterministic Guard

Global and repository hooks must remain read-only and deterministic. They may check required tracked documents, staged whitespace, and commit-message format. They must not call an LLM, create project files, open an editor, or write review markers.

```sh
sh <skill-dir>/scripts/install-global-hooks.sh
```

If a global `core.hooksPath` already exists, do not replace it silently. Chain or replace it only with explicit user authorization.

## Worktree And Subagent Rules

Default isolation model:

```text
one task = one branch = one worktree = optional one editing subagent
```

Use worktrees only when isolation has real value: parallel tasks, subagent editing, long-running work, or a checkout switch that would disturb user work. Give every editing subagent distinct file ownership, a distinct worktree, a verification command, and a merge target.

```sh
sh <skill-dir>/scripts/start-agent-task.sh --project-root <repo> --task-name <task> --baseline-branch <integration> --ensure-ignore
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <skill-dir>/scripts/start-agent-task.ps1 -ProjectRoot <repo> -TaskName <task> -BaselineBranch <integration> -EnsureIgnore
```

## Finish

1. Stage only task-owned files.
2. Run verification that matches the change.
3. Commit atomically using repository policy.
4. Push, open a PR, merge, or update a shared branch only when the current request authorizes it.
5. When the task produced a durable lesson, invoke `experience-triage`; do not classify it here.

## Common Failures

- Invoking the full workflow for a small ordinary code task.
- Inferring a long-lived integration branch from a temporary current branch.
- Moving all rules out of the startup file or putting all details into it.
- Putting judgment in hooks or mechanical checks in prose.
- Sharing one checkout between editing subagents.
- Duplicating the `experience-triage` decision model inside this skill.
- Treating completion as authorization to push, merge, release, or deploy.
