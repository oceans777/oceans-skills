---
name: idea-ledger
description: Establish a concise governing charter for a material product decision, then use that charter to generate, review, and manage the detailed solution and acceptance criteria in the current repository. Use when a user proposes, changes, compares, records, approves, rejects, supersedes, or audits a decision affecting user-visible behavior, product scope, data, security, privacy, permissions, pricing, operational policy, or architecture. Implicit use may align and analyze without persistence; write or finalize only when the user's natural-language intent is unambiguous. Do not trigger for ordinary coding, explanation, summarization, translation, routine bug fixing, formatting, or generic planning.
---

# Idea Ledger

Manage durable **product decisions**, not every user utterance. Let the model perform materiality and intent judgment while the bundled scripts enforce deterministic state, graph, rendering, evidence, and CI invariants.

## Non-negotiable safety boundary

1. Invoke automatically when the request matches the materiality boundary; `$idea-ledger` and `/idea-ledger` remain optional manual routes.
2. Keep implicit discovery read-only. Analyze, retrieve, compare, and draft in chat without initializing a ledger or writing files.
3. Create or revise a proposal only when the user clearly asks to record, save, preserve, or update the decision. Natural language is sufficient; never require a command token.
4. Accept or reject only when the current user message unambiguously finalizes exactly one identified proposal. Pass that message without paraphrasing as evidence; never synthesize approval language. The CLI may normalize whitespace for canonical storage.
5. Treat generic replies such as “可以”, “继续”, “OK”, “yes”, or “同意” as ambiguous. If several proposals are active and the message does not identify one, ask for disambiguation.
6. Require a confirmed governing charter before generating a new or changed detailed decision. Then derive at least one observable, falsifiable acceptance criterion from that charter before creating, revising, or accepting a proposal.
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

## Governing charter first

For a new or changed decision, first create and align a short formal `总纲领`. Skip this step only for direct status, show, list, audit, accept, or reject requests.

The charter is the upstream product authority for administrators, operators, and the AI. It is not a summary extracted from an already-written solution. The AI must generate the detailed solution and acceptance criteria from the confirmed charter, and every downstream section must remain traceable to it.

Return the charter before drafting detailed content:

- **Goal**: one sentence describing the result to achieve;
- **Actors**: no more than five administrator, operator, or user roles;
- **Scope**: no more than five items;
- **Principles**: no more than five non-negotiable rules;
- **Non-goals**: no more than three items.

Keep the charter and final question within 10 non-empty lines. End with `总纲领是否正确？` Do not include a detailed solution or acceptance criteria at this stage; those are downstream products of the charter.

After the user confirms the charter, generate the complete decision in this order: detailed goal and scenarios, concrete solution, constraints and trade-offs, observable acceptance criteria, dependencies, and conflict assessment. Do not reverse the flow by drafting those fields first and summarizing them into a charter afterward.

A generic reply such as `对`, `可以`, or `OK` may confirm the displayed charter when only one charter is active, but it is not Ledger approval. After charter confirmation, create or revise a proposal only if the conversation already contains an unambiguous request to record, save, preserve, or update it. Accept a proposed record only under the approval rules below.

## Review workflow

### 1. Read status without side effects

Read-only commands never initialize a missing ledger:

```bash
python3 "$LEDGER" status --root .
python3 "$LEDGER" show --root . --id IDEA-0001
python3 "$LEDGER" audit --root . --page 1 --page-size 25 --format jsonl
```

For a full audit, read every page. A normal decision review should use bounded retrieval first.

### 2. Generate the detailed decision from the charter

Only after charter alignment, generate the proposal as:

- goal;
- decision;
- rationale;
- expected outcome;
- scope and non-goals;
- constraints and trade-offs;
- acceptance criteria;
- dependencies and supersession intent.

Treat the charter as a hard upstream constraint. If a proposed detail or acceptance criterion cannot be traced to the charter, revise the detail or explicitly request a charter change. Show the complete draft when the user asks to expand, compare, or audit, or when a material conflict cannot be explained safely in compact form.

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

### 9. Create and complete a detailed PRD only when requested

```bash
python3 "$LEDGER" prd-template --root . --id IDEA-0001 --json
```

The command works only for a currently effective accepted decision, uses exclusive creation, never overwrites, and records a decision digest so later supersession or baseline drift can be detected.

After creating the skeleton, complete the PRD with the detailed plan required by the decision. Include, when applicable: background and current facts, users and scenarios, full functional scope, capability or workflow decomposition, inputs and outputs, data ownership and storage, permissions and security, failure and retry semantics, implementation phases, observable acceptance criteria, risks, compatibility, rollback or forward migration, and open questions. Do not leave placeholder sections when the available evidence can fill them, and do not invent missing facts.

Place the confirmed charter at the top of the PRD, before the detailed plan and acceptance criteria. After creating a PRD skeleton, do not print or restate the full PRD in chat. Return the charter reference, file path, Ledger action, and next gate. Show PRD content only when the user explicitly asks to read or expand it.

## Response contract

For a new or changed decision, return the governing charter defined above and nothing else before alignment. Keep it within 10 non-empty lines.

Do not generate the detailed solution or acceptance criteria until the charter is aligned. After alignment, generate and validate the complete decision and detailed PRD required by the workflow.

After alignment or a Ledger action, keep the normal response within 12 non-empty lines and include only:

1. the concise charter or a one-line reference to the unchanged charter;
2. **Conflict** — one line for `compatible / none`, including reviewed IDs and confidence;
3. **Ledger** — `not written`, `proposed IDEA-…`, `accepted`, or `rejected`;
4. **Next** — the unresolved evidence, decision, or natural-language confirmation needed before the next state change.

Expand beyond the compact response only when:

- the user asks to expand, compare, or audit;
- compatibility is `duplicate`, `tension`, `incompatible`, or `unknown`;
- disposition is not `none`;
- missing information would materially change the decision or classification.

In an expanded response, include the complete decision draft, conflict assessment, Ledger action, and next gate. Always preserve reviewed IDs, conflicting clauses, scope assumptions, disposition, mitigation, and confidence in the record; compact display must not weaken persistence or validation requirements.

State assumptions instead of inventing facts. Ask a question only when missing information would materially change the record or classification.

## References

- `references/record-schema.md` — payload, conflict, dependency, and record fields.
- `references/workflow.md` — materiality, review rubric, and graph semantics.
- `references/strict-mode.md` — optional CI enforcement without hooks.
- `references/migration-v2.0.md` — compatible upgrade notes from v2.0.
- `references/migration-v1.md` — controlled migration from v1.
