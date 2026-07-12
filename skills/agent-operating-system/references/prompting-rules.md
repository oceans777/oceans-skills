# Prompting Rules

Use these rules when auditing project task prompts, reusable prompt templates, or startup instructions that prescribe how users should request work.

## Outcome First

Start with the observable result. Include the audience only when it changes the deliverable. Describe a process when the process itself is important; otherwise leave the agent room to inspect, compare, and adjust its approach.

## Relevant Context Only

Include files, data, screenshots, reproduction steps, current facts, or connected sources only when they can change the result. Point to what matters in each source instead of enumerating every search step.

## Optional Output And Boundaries

Specify format, length, language, or detail only when the result will be used that way. Keep boundaries to the one to three constraints that prevent real rework or unintended shared effects. Missing information should be flagged rather than guessed.

## Verifiable Final Check

Ask for a final check that matches the work: rerun a reproduction, confirm every action has an owner, verify cited numbers, compare generated files, or report commands and results. A final check is not a substitute for user review.

## Audit Smells

- A role or persona appears before the desired result without changing behavior.
- A general template forces a fixed number of skills, steps, or limitations.
- A tool must be called on every turn instead of under a stated trigger.
- The prompt hides sources even when the user needs to verify current or important claims.
- The same rule is copied across `AGENTS.md`, `CLAUDE.md`, skills, and hooks.
- Commit, push, merge, publish, or send actions are treated as implicit permission.

## Migration

Preserve task-specific constraints and observable acceptance criteria. Replace rigid scaffolding with optional outcome, context, output, boundaries, and final-check sections. Move detailed examples to an on-demand project document and keep the startup file as an index.
