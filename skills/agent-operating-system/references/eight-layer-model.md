# Eight-Layer Agent Model

Use these layers to decide where agent knowledge and behavior belongs.

## 1. Memory / Preference

Stable cross-project preferences. Examples: preferred language, commit style,
review strictness, default branch naming. Do not put project-specific facts here.

## 2. Startup File

`AGENTS.md`, `CLAUDE.md`, or equivalent. This is the resident startup layer.
It should contain:

- Project map.
- Non-negotiable safety rules.
- Default collaboration rules.
- Pointers to deeper layers.

It should not contain long procedures, full reference docs, or commands that can
be automated.

## 3. Path-Scoped Rules

Rules that apply only to a folder, module, package, file type, template family,
or legacy area. Put them close to the files they govern when the agent harness
supports local instruction files. Otherwise keep them in `docs/agent/` and link
from the startup file.

## 4. Skills

Reusable judgment-heavy workflows:

- Multi-step development flows.
- Review checklists.
- Release procedures.
- Migration decision trees.
- Domain-specific planning.

Skills should explain when and how to act. They should call scripts/tools for
mechanical operations.

## 5. Scripts / Tools

Deterministic executable operations:

- Syntax checks.
- Diff checks.
- File ownership checks.
- Dangerous-file detection.
- Build/test commands.
- Packaging checks.

If a rule can be checked mechanically, implement it here before writing more
prose.

## 6. Hooks

Mandatory, deterministic guardrails:

- `pre-commit`: validate staged files.
- `commit-msg`: validate message format.
- `pre-push`: optional remote/baseline checks.

Hooks must be small and call scripts. Do not put complex judgment in hooks.

## 7. Worktrees / Subagents

Isolation and parallelism:

- One task branch per independent change.
- One worktree per task branch.
- One editing subagent per worktree when parallel execution is requested.

The main checkout should stay on the baseline branch whenever practical.

## 8. Evaluation / Learning

Post-task improvement loop:

- What failed or nearly failed?
- Which layer should catch it next time?
- Should a skill be promoted into startup rules?
- Should a prose rule become a script or hook?
- Should the lesson be discarded as one-off?

Use the `experience-triage` decision tree when available.
