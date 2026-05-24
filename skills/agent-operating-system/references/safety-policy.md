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

## Hook Scope

Hooks should be deterministic. They may block:

- invalid commit message format
- syntax failures
- dangerous staged files
- direct baseline commits

Hooks should not make subjective architecture decisions.
