# Migration Rules

Use these rules when slimming `AGENTS.md`, `CLAUDE.md`, or similar startup
files.

## Keep In Startup File

- Project path and baseline map.
- Direct user instruction precedence.
- Protect existing user work.
- Safety boundaries.
- Default branch/worktree policy.
- Required commit/push policy if the project has one.
- Pointers to scripts, hooks, docs, and skills.

## Move To Path-Scoped Rules

- Rules that apply only to one package, plugin, module, template, or legacy
  directory.
- File-type-specific conventions.
- Local naming, styling, or architecture constraints.

## Move To Skills

- Multi-step task classification.
- Design/review workflows.
- Release and packaging workflows.
- Debugging and investigation flows.
- Domain-specific checklists.

## Move To Scripts / Tools

- Syntax checks.
- Formatting checks.
- Dangerous-file detection.
- Staged-file ownership checks.
- Generated-file detection.
- Build/test orchestration.

## Move To Hooks

- Checks that must happen before commit, message acceptance, push, deploy, or
  destructive operation.

Hooks should call scripts. They should not duplicate script logic.

## Move To Reference Docs

- Official links.
- Directory diagrams.
- Long examples.
- API notes.
- Detailed background.

## Delete Or Delay

- One-time debugging notes.
- Unproven preferences.
- Personal thoughts that do not change future behavior.
- Rules that duplicate stronger hooks or scripts.

## Migration Output Format

```text
Item:
Current location:
Recommended layer:
Recommended file:
Reason:
Action:
```
