# Record schema — v2.3

`new` and `revise` accept one JSON object. Unknown fields are rejected so schema drift remains visible. New writes require a governing charter and use the current conflict and dependency forms; records created before v2.3 remain readable for migration compatibility.

## Required proposal fields

```json
{
  "title": "Cross-device sync with explicit opt-in",
  "charter": {
    "goal": "Provide cross-device access without weakening the default local-only privacy boundary.",
    "actors": ["Product administrators", "Operators", "Signed-in workspace users"],
    "scope": ["Workspace-level sync opt-in", "Remote-copy deletion"],
    "principles": ["Default off", "No upload before explicit opt-in"],
    "non_goals": ["Collaborative editing"]
  },
  "goal": "Let signed-in users access the same workspace on multiple devices.",
  "decision": "Add encrypted cloud sync, disabled by default, with per-workspace opt-in.",
  "outcome": "Opted-in workspaces converge without uploading local-only workspaces.",
  "scope": ["sync", "storage", "privacy"],
  "acceptance_criteria": [
    "A new workspace uploads no data before explicit opt-in.",
    "Two opted-in devices converge after reconnecting."
  ],
  "conflict": {
    "compatibility": "compatible",
    "reviewed_ids": ["IDEA-0003"],
    "conflicts_with": [],
    "rationale": "IDEA-0003 requires local-only storage by default; this proposal preserves that default and adds an explicit opt-in path.",
    "confidence": "high",
    "disposition": "none",
    "mitigation": null
  }
}
```

Required fields are:

- `title`: single-line title;
- `charter`: the concise, upstream authority confirmed before the AI generates the remaining fields;
- `goal`: problem or objective;
- `decision`: the rule future work must follow;
- `outcome`: expected observable result;
- `scope`: one or more applicability labels;
- `acceptance_criteria`: one or more observable pass/fail conditions;
- `conflict`: structured review result.

Each acceptance criterion must be falsifiable from behavior, a metric, a state transition, or durable evidence. Vague claims such as “works well” are not sufficient without an observable result or threshold.

## Governing charter

The charter is written and aligned first. The AI then generates the detailed `goal`, `decision`, `outcome`, `constraints`, and `acceptance_criteria` from it. It must not create the detailed solution first and reverse-summarize it into a charter.

```json
{
  "charter": {
    "goal": "One sentence, maximum 240 characters.",
    "actors": ["One to five roles"],
    "scope": ["One to five product boundaries"],
    "principles": ["One to five non-negotiable rules"],
    "non_goals": ["Zero to three explicit exclusions"]
  }
}
```

New and revised records require this object. Stored records created before v2.3 may omit it and remain readable without rewriting immutable history.

## Optional proposal fields

```json
{
  "rationale": "Why this decision was selected.",
  "tags": ["security", "multi-device"],
  "constraints": [
    "Encryption in transit and at rest is mandatory.",
    "A user can return a workspace to local-only mode."
  ],
  "alternatives_considered": ["Device-to-device transfer only"],
  "tradeoffs": ["Adds cloud operating cost in exchange for cross-device continuity"],
  "non_goals": ["This decision does not select a cloud vendor"],
  "sources": ["Product review 2026-07-24"],
  "owner": "Product",
  "review_at": "2026-10-01T00:00:00+00:00",
  "supersedes": [],
  "depends_on": [
    {"id": "IDEA-0008", "mode": "lineage"}
  ],
  "notes": ["Legal review is tracked outside this ledger."]
}
```

`owner` and `review_at` are informational fields; the CLI does not authenticate owners or schedule reviews.

## Conflict object

```json
{
  "compatibility": "tension",
  "reviewed_ids": ["IDEA-0003", "IDEA-0007"],
  "conflicts_with": ["IDEA-0003"],
  "rationale": "The proposal adds remote transfer while IDEA-0003 protects a local-only default.",
  "confidence": "high",
  "disposition": "bounded",
  "mitigation": "Remote transfer is disabled by default and can begin only after workspace-level opt-in."
}
```

### Compatibility

| Value | Meaning |
|---|---|
| `compatible` | No material incompatibility found in the reviewed evidence |
| `duplicate` | Substantively covered by an earlier decision |
| `tension` | Can coexist only with an explicit boundary or trade-off |
| `incompatible` | Cannot coexist in the same applicability |
| `unknown` | Evidence is insufficient |

### Disposition

| Value | Meaning |
|---|---|
| `none` | No action required |
| `bounded` | Preserve both decisions behind a concrete boundary or mitigation |
| `supersede` | Replace every conflicting decision |
| `defer` | Do not approve yet |

### Structural combinations

- `compatible` requires `disposition: none`, empty `conflicts_with`, and `mitigation: null`.
- `duplicate` requires non-empty `conflicts_with` and `disposition: defer`.
- `tension` requires non-empty `conflicts_with` and either `bounded` or `defer`; `bounded` requires a non-empty `mitigation`.
- `incompatible` requires non-empty `conflicts_with` and either `supersede` or `defer`; `supersede` requires a non-empty `mitigation`.
- `unknown` requires `disposition: defer`.
- Every `conflicts_with` ID must also appear in `reviewed_ids`.

Direct approval is restricted to:

```text
compatible / none
tension / bounded
incompatible / supersede
```

For `incompatible / supersede`, `supersedes` must equal `conflicts_with` as a set.

The classifier remains a model or human judgment. The CLI validates structure and graph consistency; it does not prove the semantic judgment correct.

## Dependencies

Preferred form:

```json
{
  "depends_on": [
    {"id": "IDEA-0008", "mode": "lineage"},
    {"id": "IDEA-0010", "mode": "exact"}
  ]
}
```

- `lineage`: resolve the referenced record through the unique accepted `supersedes` chain to its current effective successor.
- `exact`: require the referenced record itself to remain currently effective.

A dependency ID cannot also appear in the same record's `supersedes` or `conflicts_with`. The active accepted dependency graph must be acyclic.

Legacy v2.0 strings are accepted and interpreted as `lineage`:

```json
{"depends_on": ["IDEA-0008"]}
```

## Relationship rules

- All referenced IDs must exist before the candidate write is committed.
- A record cannot reference itself.
- Dependency IDs must be disjoint from both `supersedes` and `conflicts_with`; for a `supersede` disposition, `supersedes` and `conflicts_with` must instead match exactly.
- `supersedes` targets must be accepted.
- A target can have at most one accepted direct successor.
- Only currently effective accepted records impose runtime dependency requirements.
- A proposed supersession is rejected before disk mutation when it would break an active `exact` dependency.

## Stored state and metadata

The CLI adds deterministic ledger fields such as:

```json
{
  "schema": 2,
  "id": "IDEA-0001",
  "number": 1,
  "status": "proposed",
  "created_at": "2026-07-24T12:34:56+00:00",
  "updated_at": "2026-07-24T12:34:56+00:00",
  "accepted_at": null,
  "rejected_at": null,
  "rejection_reason": null,
  "approval": null
}
```

Stored states:

- `proposed`: editable only through `revise`; no terminal metadata;
- `accepted`: immutable; approval and `accepted_at` required; `updated_at == accepted_at`;
- `rejected`: immutable; reason and `rejected_at` required; `updated_at == rejected_at`.

`superseded` is a derived effective state and is never written into the old record.

## Approval evidence

`accept` supports two evidence modes. The legacy exact phrase remains valid and is auto-detected:

```text
批准 IDEA-0001
APPROVE IDEA-0001
```

The accepted record stores:

```json
{
  "approval": {
    "method": "explicit_phrase",
    "recorded_phrase": "批准 IDEA-0001",
    "actor_verified": false,
    "recorded_at": "2026-07-24T12:34:56+00:00"
  }
}
```

This is an audit trace only. It does not identify the speaker, prove authorization, or provide non-repudiation.

For natural language, the model must first determine that the current user message unambiguously finalizes exactly one proposal, then pass that message without paraphrasing. The CLI normalizes whitespace for canonical storage.

```bash
python3 idea_ledger.py accept --root . --id IDEA-0001 \
  --mode natural-language-intent \
  --evidence "就按刚才这个方案执行"
```

The accepted record stores:

```json
{
  "approval": {
    "method": "natural_language_intent",
    "recorded_message": "就按刚才这个方案执行",
    "resolved_record": "IDEA-0001",
    "actor_verified": false,
    "recorded_at": "2026-08-03T12:34:56+00:00"
  }
}
```

The message is audit evidence, not deterministic proof of its meaning. The CLI blocks generic confirmations and blocks an unnamed target when multiple proposed records exist. The model must never rewrite or manufacture the recorded message.

## Pre-v2.3 compatibility

v2.3 can read v2.0 `conflict.kind` objects and normalizes them in memory:

- `none` → `compatible / none`;
- `duplicate` → `duplicate / defer`;
- `tension` without resolution → `tension / defer`;
- `tension` with resolution → `tension / bounded`;
- `hard_conflict` → `incompatible / defer`;
- `resolved` with `supersedes` → `incompatible / supersede`;
- `resolved` without `supersedes` → `tension / bounded`;
- `unknown` → `unknown / defer`.

New or revised records are written in the current two-axis form and must contain a governing charter plus acceptance criteria generated from it.
