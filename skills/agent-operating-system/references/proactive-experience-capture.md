# Proactive Experience Capture

## Principle

The user should not need to know whether a moment is a lesson, rule, workflow,
or hook candidate. The agent should notice friction, then run a small
`experience-triage` style classification before proposing any durable change.

## Trigger Signals

Run a light triage pass when any of these appear:

- The user corrects the agent and the mistake could recur.
- The same class of issue appears twice.
- The user says a flow is unreasonable, confusing, too heavy, or should be restored.
- The user says "next time", "from now on", "do not do this again", or "make this standard".
- A missing verification, commit, branch, merge, or push step caused rework.
- A rule is becoming too long for `AGENTS.md`.
- A repeated command or check can be scripted or enforced by a hook.
- Parallel work caused branch, worktree, or file ownership confusion.

## Classification

Use this order:

1. Must happen every time with no exception -> hook.
2. Can be mechanically checked or generated -> script/tool.
3. Applies only to one path, module, plugin, template, or file type -> local rule.
4. Requires judgment, branching, or multiple steps -> skill.
5. Every session in this repository must know it -> top-level `AGENTS.md`.
6. Applies across projects as a stable preference -> memory or user-level rule.
7. Is temporary, speculative, private, or one-off -> no durable record.

## Output Shape

Keep the proposal small:

```text
I noticed a possible durable lesson:
<one sentence>

Suggested layer:
<hook | script | local rule | skill | AGENTS.md | memory | no durable record>

Draft:
<one short rule, command, hook idea, or skill update>

Why:
<1-2 bullets>
```

## Guardrails

- Do not interrupt urgent implementation for a long process discussion.
- Do not modify persistence files unless the user asks to apply the draft.
- Prefer automation over prose for deterministic checks.
- Prefer skills over `AGENTS.md` for long workflows.
- Prefer no durable record when the lesson is not likely to repeat.
