# Safety Policy

## Never Overwrite Existing Workflow Files

Bootstrap scripts and agents may create missing files. They must not overwrite
existing project files. Existing content requires audit and patching.

## Protect User Work

Before edits:

- Check `git status`.
- Identify unrelated modified/untracked files.
- Stage only task-owned files.
- Do not delete generated or untracked files unless the user explicitly asks.

## Destructive Operations

Require explicit user confirmation for:

- `git reset --hard`
- force push
- recursive delete
- database destructive operations
- deploy/release
- deleting worktrees with unmerged work

## Shared Side Effects

Treat external messages, publishing, remote pushes, shared-branch merges, and changes to information other people depend on as shared side effects. Execute them only when the current user request explicitly authorizes the action. A repository may define the target branch and validation policy, but it should not convert an implementation request into permanent blanket permission to affect shared state.

## Hook Scope

Hooks should be deterministic. They may block:

- invalid commit message format
- syntax failures
- dangerous staged files
- direct baseline commits

Hooks should not make subjective architecture decisions.
