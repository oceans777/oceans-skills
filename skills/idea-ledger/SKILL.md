---
name: idea-ledger
description: Explicitly review, record, approve, reject, supersede, or audit a material product decision in the current repository. Use only when the user invokes $idea-ledger or /idea-ledger. Do not trigger for ordinary coding, explanation, summarization, translation, bug fixing, generic planning, or a natural-language mention of Idea Ledger without the explicit skill token. Never initialize Git, change Git configuration, commit, stage, reset, restore, clean, or revert user work.
license: MIT. See LICENSE.
compatibility: Requires Python 3.10 or later. Git is optional and is used only by strict CI checks.
disable-model-invocation: true
argument-hint: "[new|review|approve|reject|status|show|audit|prd] [topic or IDEA-id]"
metadata:
  author: oceans777
  version: "2.1.0"
  invocation-policy: explicit-only
---

# Idea Ledger

Manage durable **product decisions**, not every user utterance. Keep semantic judgment in the model and deterministic state, graph, rendering, and CI validation in the bundled scripts.

## Non-negotiable safety boundary

1. Run only after `$idea-ledger` or `/idea-ledger` is explicitly invoked.
2. Make only project-local ledger or PRD writes required by the requested action.
3. Never run `git init`, alter `core.hooksPath`, install hooks, stage, commit, reset, restore, clean, or revert unless the user separately requests that Git action.
4. Never classify pre-existing working-tree changes as yours and never tell the user to discard them.
5. Do not claim lexical retrieval, deterministic checks, or CI prove semantic correctness. Cite clauses, IDs, assumptions, and confidence.
6. `accepted` and `rejected` records are immutable. A changed decision becomes a new proposal linked with `supersedes`.
7. Generic replies such as “可以”, “继续”, “OK”, or “yes” are not approval. Approval must name the record exactly: `批准 IDEA-0001` or `APPROVE IDEA-0001`.
8. Approval metadata is an audit trace, not authentication. The CLI stores `actor_verified: false`; never claim it proves identity or authorization.
9. Do not report a write as successful until `validate` succeeds.

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

### 3. Retrieve candidates

When the user explicitly asked to record and the ledger is absent:

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

Approve only when the current user message contains the exact record-specific phrase:

```bash
python3 "$LEDGER" accept --root . --id IDEA-0001 --evidence "批准 IDEA-0001" --json
```

Do not manufacture approval evidence from context.

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
4. **Next gate** — the exact approval phrase when approval is still required.

State assumptions instead of inventing facts. Ask a question only when missing information would materially change the record or classification.

## References

- `references/record-schema.md` — payload, conflict, dependency, and record fields.
- `references/workflow.md` — materiality, review rubric, and graph semantics.
- `references/strict-mode.md` — optional CI enforcement without hooks.
- `references/migration-v2.0.md` — compatible upgrade notes from v2.0.
- `references/migration-v1.md` — controlled migration from v1.
