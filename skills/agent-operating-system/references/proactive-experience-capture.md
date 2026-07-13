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

Classify two dimensions:

1. Scope: cross-project, whole repository, or path-scoped. Scope decides where
   the entry point or routing rule lives.
2. Mechanism: mechanically decidable -> script/tool; mechanically decidable and
   tied to a required lifecycle event -> hook; judgment/branching/multiple steps
   -> skill; always-needed project context -> top-level `AGENTS.md`.
3. Combine layers when needed. A path-scoped workflow can use a local routing
   rule plus a skill. A hook should call a script.
4. If temporary, speculative, private, or one-off -> no durable record.

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
