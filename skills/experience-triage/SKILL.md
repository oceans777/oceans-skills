---
name: experience-triage
description: 'Use when a user wants to preserve a lesson, pitfall, rule, workflow, or agent behavior after real work and asks whether it should be observed, adopted, automated, or discarded, and where it belongs: startup guidance, local rules, a skill, script/tool, hook, memory, or no durable record.'
---

# Experience Triage

## Purpose

Turn real work evidence into the smallest durable improvement that prevents recurrence without bloating startup context or encoding one-off reactions as permanent policy.

## Boundary

This skill classifies and drafts durable learning. It does not execute repository workflow, install hooks, edit persistence files, or copy domain-specific rules unless the user explicitly asks for implementation.

Before proposing a new rule, inspect the intended target and nearby layers for duplicates, stricter existing rules, contradictions, deprecated guidance, and an existing mechanical check.

## Required Evidence

Capture only facts that affect the decision:

- what happened;
- observable impact or rework;
- whether it has happened before;
- affected scope;
- whether pass/fail is mechanically decidable;
- lifecycle event, if any;
- existing rule or automation that should already cover it;
- conflict, owner, review condition, and retirement condition.

A severe security, data-loss, or shared-side-effect incident may become a candidate after one occurrence. Low-impact preferences normally require repetition before adoption.

## Lifecycle

Use one state:

1. `observe`: plausible but insufficient evidence; record no permanent rule.
2. `candidate`: evidence exists, but duplicate/conflict/owner review is incomplete.
3. `adopted`: approved durable guidance or workflow.
4. `automated`: a deterministic tool or hook enforces the adopted behavior.
5. `retired`: obsolete, superseded, harmful, or no longer worth its context cost.

Do not jump directly from a vague complaint to `adopted`.

## Classification

Classify two independent axes.

### Scope Axis

- Cross-project personal or team preference -> user-level memory or rule.
- Whole repository -> repository startup guidance, repository skill, or repository tool.
- Directory, file type, module, plugin, or subsystem -> short local routing guidance near that path.

### Mechanism Axis

- Mechanically decidable and repeatable -> script, command, tool, or automation.
- Mechanically decidable, tied to a lifecycle event, and mandatory -> hook invoking the mechanical check.
- Judgment-heavy multi-step process -> skill.
- High-frequency project default, map, or hard constraint -> concise startup guidance.
- Long explanation or evidence -> reference documentation.
- One-off, private, speculative, obvious, or already covered -> no new durable record.

A result may combine layers. Example: a path-scoped rule routes users to a reusable skill, while a hook invokes a deterministic validator.

## Decision Flow

1. Restate the lesson as a falsifiable sentence.
2. Gather the minimum evidence.
3. Search existing target layers for duplicate, conflict, and stronger coverage.
4. Assign lifecycle state.
5. Classify scope and mechanism separately.
6. Recommend the smallest durable change.
7. Draft the exact text, command, test, or hook contract only when adoption is justified.
8. Define promotion, review, automation, and retirement conditions.

## Output

Use a compact response for simple cases and the full form for consequential cases.

```text
[State] observe | candidate | adopted | automated | retired
[Lesson] one falsifiable sentence
[Evidence] occurrence, impact, and existing coverage
[Conflict check] duplicate, contradiction, or none
[Scope] cross-project | repository | path-scoped
[Mechanism] guidance | skill | script/tool | hook | no record
[Target] exact path or system
[Draft] directly usable content, when justified
[Review/retire] condition and owner
```

## Guardrails

- Do not recommend a hook merely because something should happen every time; hooks require deterministic pass/fail logic.
- Do not create a new rule when an existing stricter rule or test already covers the case.
- Do not place detailed procedures in always-loaded startup files.
- Do not preserve blame, temporary debugging facts, secrets, personal data, or machine-specific paths.
- Do not claim that a model judgment can be enforced deterministically.
- Do not silently resolve contradictory rules; surface the conflict and stop adoption until an owner decides.

Read `references/evaluation-cases.md` for representative classification cases.
