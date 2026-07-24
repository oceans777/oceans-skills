# Workflow and review rubric — v2.1

## Purpose

The ledger exists to reduce future decision ambiguity. It is not a transcript, ticket system, universal project manager, identity system, or substitute for PRDs and source control.

A useful record should let a future contributor answer:

1. What rule was selected?
2. Why was it selected?
3. What scope, constraints, trade-offs, and non-goals apply?
4. Which earlier records were reviewed, conflicted with, superseded, or depended on?
5. Which decision is currently effective?

## Materiality test

A candidate is material when a future contributor could reasonably implement the wrong product because the decision was not recorded. Typical examples include:

- user-visible behavior or product scope;
- data handling, security, privacy, permissions, pricing, or operational policy;
- an architectural constraint future work must respect;
- a default, rollout, compatibility, or deprecation rule;
- an explicit exception to or replacement of a prior decision.

Routine refactors, formatting, explanations, summaries, translations, and implementation details normally fail this test.

## Review sequence

1. Restate the candidate as goal, decision, rationale, outcome, scope, non-goals, constraints, trade-offs, and acceptance criteria.
2. Use `context` for a bounded related set.
3. Read every cited record in full with `show`.
4. Compare concrete clauses and applicability, not only keywords.
5. Record all reviewed IDs; put only genuine conflicts in `conflicts_with`.
6. Select compatibility, disposition, mitigation, and confidence independently.
7. Express dependencies as `lineage` or `exact` deliberately.
8. Save only when the user explicitly asked to record the decision.
9. Require record-specific approval before acceptance.
10. Use a new record for any later material change.
11. After every write, run `validate` and report success only when it passes.

## Compatibility versus disposition

Do not use a single label to mix diagnosis and resolution.

- Compatibility answers: **Can these decisions coexist in the same applicability?**
- Disposition answers: **What should happen next?**

Examples:

### Compatible after review

```json
{
  "compatibility": "compatible",
  "reviewed_ids": ["IDEA-0001"],
  "conflicts_with": [],
  "disposition": "none"
}
```

This means IDEA-0001 was actually reviewed, but no conflict was found.

### Bounded tension

```json
{
  "compatibility": "tension",
  "reviewed_ids": ["IDEA-0001"],
  "conflicts_with": ["IDEA-0001"],
  "disposition": "bounded",
  "mitigation": "The new behavior applies only to enterprise workspaces after an administrator opt-in."
}
```

### Supersession

```json
{
  "compatibility": "incompatible",
  "reviewed_ids": ["IDEA-0001"],
  "conflicts_with": ["IDEA-0001"],
  "disposition": "supersede",
  "mitigation": "IDEA-0001 remains historical; all new work follows this replacement decision."
}
```

The proposal must also contain:

```json
{"supersedes": ["IDEA-0001"]}
```

## Adversarial questions

Before claiming compatibility or a successful resolution, ask:

- What existing behavior would become impossible?
- Does a default, permission, storage location, price, lifecycle, or operational responsibility change?
- Can both decisions be true for the same user, object, platform, environment, jurisdiction, and time?
- Is the mitigation a testable boundary, or only reassuring language?
- Does the new decision silently broaden an exception?
- What evidence is missing?
- Would a future implementer know which rule wins?
- Does a dependency need the exact historical decision, or only the continuing lineage?
- Would superseding this target break another currently effective decision?

## Confidence rubric

- `high`: directly comparable clauses, matching applicability, and explicit evidence.
- `medium`: likely comparable, but one or more scope assumptions remain.
- `low`: weak lexical overlap, incomplete records, missing applicability, or uncertain evidence.

Low confidence should normally produce `unknown/defer` or a clearly qualified `tension/defer`, not a confident “no conflict”.

## Dependency selection

Use `lineage` when the dependent decision needs the continuing product rule or capability, regardless of which accepted record currently represents it.

Use `exact` when the dependent decision relies on the exact wording, boundary, implementation contract, legal basis, or historical version of a particular record. Replacing that record should then be blocked until the dependent decision is revised or superseded.

Only active accepted decisions impose runtime dependency constraints. Historical superseded records preserve their original dependency evidence but no longer block the current effective graph.

## Candidate-state transaction model

Every write follows this logical sequence:

```text
load current ledger
→ normalize old and new forms
→ construct candidate record set
→ derive supersession and dependency graph
→ validate all record/state/graph invariants
→ write target record
→ rebuild deterministic index
```

If candidate validation fails, the target record is not written. The filesystem write and index rebuild are serialized with the project ledger lock.

## Retrieval versus audit

`context` is a recall aid with a strict total character budget. It can miss semantically related records and must never be described as exhaustive. If a full record does not fit, it may emit a minimal summary and explicitly mark truncation.

`audit` emits complete normalized records in pages, including effective state, normalized conflicts, normalized/resolved dependencies, dependency errors, and record digest. A full conflict audit requires reading every page and still remains a semantic review, not a mathematical proof.

## Approval and identity boundary

An exact record-specific phrase prevents accidental generic confirmation, but it is not an identity or authorization mechanism. The ledger records `actor_verified: false`; rely on the host platform, repository permissions, code review, and organizational controls for who may approve.
