# Migration Rules

Use these rules when slimming `AGENTS.md`, `CLAUDE.md`, or similar startup
files.

## Keep In Startup File

- Project path and baseline map.
- Direct user instruction precedence.
- Protect existing user work.
- Safety boundaries.
- Default branch/worktree policy.
- Required commit policy and explicit authorization boundary for shared effects such as pushes, merges, publishing, and external messages.
- Pointers to scripts, hooks, docs, and skills.

## Move To Path-Scoped Rules

- Rules that apply only to one package, plugin, module, template, or legacy
  directory.
- File-type-specific conventions.
- Local naming, styling, or architecture constraints.
- Short routing pointers to path-specific skills or scripts. Do not move an
  entire multi-step procedure into a nested startup file.

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
  another lifecycle event and whose pass/fail result is mechanically decidable.

Hooks should call scripts. They should not duplicate script logic.
Mandatory judgment-based rules stay in startup guidance; a hook cannot enforce
them safely.

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
- Fixed prompt sections, step counts, or role descriptions that do not change the result.

## Migration Output Format

```text
Item:
Current location:
Recommended layer:
Recommended file:
Reason:
Action:
```
