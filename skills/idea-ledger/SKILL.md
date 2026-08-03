---
name: idea-ledger
description: Automatically review and manage material product decisions in the current repository. Use when a user proposes, changes, compares, records, approves, rejects, supersedes, or audits a decision affecting user-visible behavior, product scope, data, security, privacy, permissions, pricing, operational policy, or architecture. Implicit use may analyze and draft without persistence; write or finalize only when the user's natural-language intent is unambiguous. Do not trigger for ordinary coding, explanation, summarization, translation, routine bug fixing, formatting, or generic planning.
---

# Idea Ledger

Manage durable **product decisions**, not every user utterance. Let the model perform materiality and intent judgment while the bundled scripts enforce deterministic state, graph, rendering, evidence, and CI invariants.

## Non-negotiable safety boundary

1. Invoke automatically when the request matches the materiality boundary; `$idea-ledger` and `/idea-ledger` remain optional manual routes.
2. Keep implicit discovery read-only. Analyze, retrieve, compare, and draft in chat without initializing a ledger or writing files.
3. Create or revise a proposal only when the user clearly asks to record, save, preserve, or update the decision. Natural language is sufficient; never require a command token.
4. Accept or reject only when the current user message unambiguously finalizes exactly one identified proposal. Pass that message without paraphrasing as evidence; never synthesize approval language. The CLI may normalize whitespace for canonical storage.
5. Treat generic replies such as “可以”, “继续”, “OK”, “yes”, or “同意” as ambiguous. If several proposals are active and the message does not identify one, ask for disambiguation.
6. Require at least one observable, falsifiable acceptance criterion before creating, revising, or accepting a proposal.
7. Make only project-local ledger or PRD writes required by the requested action.
8. Never run `git init`, alter `core.hooksPath`, install hooks, stage, commit, reset, restore, clean, or revert unless the user separately requests that Git action.
9. Never classify pre-existing working-tree changes as yours and never tell the user to discard them.
10. Do not claim lexical retrieval, deterministic checks, or CI prove semantic correctness. Cite clauses, IDs, assumptions, and confidence.
11. `accepted` and `rejected` records are immutable. A changed decision becomes a new proposal linked with `supersedes`.
12. Approval metadata is an audit trace, not authentication. The CLI stores `actor_verified: false`; never claim it proves identity or authorization.
13. Do not report a write as successful until `validate` succeeds.

## Locate the script

Use the bundled `scripts/idea_ledger.py` next to this `SKILL.md`. Prefer the runtime-provided absolute skill directory. Supported resolution order:

1. A runtime-provided absolute path to this skill directory.
2. `${CLAUDE_SKILL_DIR}/scripts/idea_ledger.py` when Claude Code provides it.
3. A directly installed runtime path such as `~/.codex/skills/idea-ledger/scripts/idea_ledger.py`, `~/.agents/skills/idea-ledger/scripts/idea_ledger.py`, or `~/.claude/skills/idea-ledger/scripts/idea_ledger.py`.
4. Plugin compatibility paths `${PLUGIN_ROOT}/skills/idea-ledger/scripts/idea_ledger.py` or `${CLAUDE_PLUGIN_ROOT}/skills/idea-ledger/scripts/idea_ledger.py`.

Do not guess a project-relative script path. If the runtime does not expose the skill directory and no known path exists, report that the installed skill entrypoint cannot be located. In examples, `$LEDGER` means the resolved absolute path.

## Decide whether a record is warranted

Create a record only when the proposal materially changes at least one of:

- user-visible behavior or product scope;
- data, security, privacy, permissions, pricing, or operational policy;
- an architectural constraint future work must respect;
- an earlier accepted decision through bounded tension or supersession.

Do not create records for explanations, summaries, translations, formatting, routine implementation details, or a bug fix that does not change intended behavior.

## Review workflow

### 1. Read status without side effects

Read-only commands never initialize a missing ledger:

```bash
python3 "$LEDGER" status --root .
python3 "$LEDGER" show --root . --id IDEA-0001
python3 "$LEDGER" audit --root . --page 1 --page-size 25 --format jsonl
```

For a full audit, read every page. A normal decision review should use bounded retrieval first.

### 2. Draft the decision

Restate the proposal as:

- goal;
- decision;
- rationale;
- expected outcome;
- scope and non-goals;
- constraints and trade-offs;
- acceptance criteria;
- dependencies and supersession intent.

If the user asked only for a review, do not initialize or write files.

Every proposal must include at least one acceptance criterion. Write each criterion so a future reviewer can observe pass or fail from behavior, a metric, a state transition, or durable evidence. Prefer a trigger/action/outcome shape. Reject vague criteria such as “works well”, “is user friendly”, or “improves performance” without a threshold or observable result.

### 3. Retrieve candidates

When the user's natural-language request clearly asks to persist the decision and the ledger is absent:

```bash
python3 "$LEDGER" init --root .
```

Retrieve a bounded candidate set:

```bash
python3 "$LEDGER" context --root . --query "the proposed decision" --limit 8
```

Read every cited record in full with `show`. Use `audit` only for an explicit full-history review or when bounded retrieval is demonstrably insufficient.

### 4. Assess compatibility and disposition

Use two independent dimensions.

`compatibility`:

- `compatible`: no material incompatibility in reviewed evidence;
- `duplicate`: already covered by an earlier decision;
- `tension`: can coexist only with an explicit boundary or trade-off;
- `incompatible`: cannot coexist in the same applicability;
- `unknown`: evidence is insufficient.

`disposition`:

- `none`: no action required;
- `bounded`: preserve both decisions behind a concrete boundary or mitigation;
- `supersede`: replace every conflicting decision listed in `conflicts_with`;
- `defer`: do not approve until evidence or resolution changes.

Directly approvable combinations are only:

- `compatible / none`;
- `tension / bounded` with a concrete `mitigation`;
- `incompatible / supersede` with `supersedes == conflicts_with` and a concrete `mitigation`.

`duplicate`, `unknown`, and any `defer` disposition are not directly approvable.

Always report reviewed IDs, conflicting clauses, scope assumptions, disposition, mitigation, and confidence.

### 5. Express dependencies deliberately

Use dependency objects:

```json
{
  "id": "IDEA-0008",
  "mode": "lineage"
}
```

- `lineage`: follow the unique accepted `supersedes` chain to the current effective successor;
- `exact`: require that exact record to remain currently effective; a supersession that would break it is rejected before writing.

Legacy string dependencies remain readable and are interpreted as `lineage`.

A dependency cannot also be in `supersedes` or `conflicts_with`. The CLI checks the active dependency graph for cycles before any terminal write.

### 6. Create or revise a proposal

Create a payload matching `references/record-schema.md`, then:

```bash
python3 "$LEDGER" new --root . --input /path/to/proposal.json --json
```

Only `proposed` records may be revised:

```bash
python3 "$LEDGER" revise --root . --id IDEA-0001 --input /path/to/revised.json --json
```

The CLI constructs the full candidate ledger state, validates relationships and active dependencies, and writes only if the candidate graph is valid.

### 7. Approve or reject

The exact legacy phrase remains valid:

```bash
python3 "$LEDGER" accept --root . --id IDEA-0001 --evidence "批准 IDEA-0001" --json
```

For an unambiguous natural-language approval of exactly one proposal, pass the current user message without paraphrasing:

```bash
python3 "$LEDGER" accept --root . --id IDEA-0001 \
  --mode natural-language-intent \
  --evidence "就按刚才这个方案执行" --json
```

Do not paraphrase, concatenate, or manufacture approval evidence. The CLI rejects generic confirmations and rejects an unnamed target when multiple proposals exist.

Reject only on an explicit rejection instruction:

```bash
python3 "$LEDGER" reject --root . --id IDEA-0001 --reason "reason" --json
```

### 8. Validate

After every write:

```bash
python3 "$LEDGER" validate --root .
```

Validation covers canonical rendering, terminal state rules, the full relationship graph, active dependency resolution, deterministic index content, and generated PRD baseline metadata.

### 9. Create a PRD skeleton only when requested

```bash
python3 "$LEDGER" prd-template --root . --id IDEA-0001 --json
```

The command works only for a currently effective accepted decision, uses exclusive creation, never overwrites, and records a decision digest so later supersession or baseline drift can be detected.

## Response contract

For a decision review, return four sections:

1. **Decision draft** — goal, decision, rationale, expected outcome, scope, non-goals, constraints, and acceptance criteria.
2. **Conflict assessment** — compatibility, disposition, reviewed/conflicting IDs, clause evidence, mitigation, and confidence.
3. **Ledger action** — `not written`, `proposed IDEA-…`, `accepted`, or `rejected`.
4. **Next gate** — the unresolved evidence, decision, or natural-language confirmation needed before the next state change.

State assumptions instead of inventing facts. Ask a question only when missing information would materially change the record or classification.

## References

- `references/record-schema.md` — payload, conflict, dependency, and record fields.
- `references/workflow.md` — materiality, review rubric, and graph semantics.
- `references/strict-mode.md` — optional CI enforcement without hooks.
- `references/migration-v2.0.md` — compatible upgrade notes from v2.0.
- `references/migration-v1.md` — controlled migration from v1.
