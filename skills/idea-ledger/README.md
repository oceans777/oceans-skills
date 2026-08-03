# Idea Ledger v2.3.0

Idea Ledger first establishes a governing charter of at most 10 lines, then uses that confirmed charter to generate the detailed solution and acceptance criteria as project-local, structured, auditable files. Implicit use is read-only; persistence and terminal state changes require unambiguous natural-language intent. `$idea-ledger` and `/idea-ledger` remain optional manual routes.

## Safety boundary

- Never initializes Git, changes Git configuration, installs hooks, stages, commits, resets, restores, cleans, or reverts user work.
- Read-only commands never initialize a missing ledger.
- Accepted and rejected records are immutable.
- Every new or revised proposal requires a governing charter and at least one observable acceptance criterion derived after charter alignment.
- New or changed decisions show the concise charter before detailed solution or acceptance work begins.
- A generic confirmation may confirm one active charter, but never approves a Ledger record.
- Generic confirmations such as “可以”, “继续”, “同意”, or “OK” never approve a record.
- Natural-language approval preserves the user's original message and resolved record ID.
- An unnamed natural-language approval is rejected when more than one proposal is active.
- Every write validates the complete candidate relationship and dependency graph before disk mutation.
- Approval metadata is an audit trace with `actor_verified: false`, not identity authentication.

## Default response

The first chat response contains only Goal, Actors, Scope, Principles, Non-goals, and `总纲领是否正确？` within 10 non-empty lines. After confirmation, the AI generates the detailed solution and observable acceptance criteria from that charter.

When a PRD is requested, the confirmed charter appears first and the skeleton is completed as a detailed implementation and acceptance plan; chat returns only the charter reference, file path, Ledger action, and next gate unless the user asks to read it.

## Requirements

Python 3.10 or later. Git is optional and used only by strict CI checks.

## Direct use

```bash
python3 scripts/idea_ledger.py --version
python3 scripts/idea_ledger.py init --root .
python3 scripts/idea_ledger.py new --root . --input examples/proposal-0001-local-first.json --json
python3 scripts/idea_ledger.py accept --root . --id IDEA-0001 \
  --mode natural-language-intent --evidence "就按刚才这个方案执行" --json
python3 scripts/idea_ledger.py validate --root .
```

## Commands

`init`, `new`, `revise`, `accept`, `reject`, `show`, `list`, `status`, `context`, `audit`, `validate`, `refresh-index`, `prd-template`, and `ci-check`.

## Tests

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

The deterministic suite contains 60 tests covering side effects, charter-first generation, acceptance-criteria gates, approval evidence, state transitions, graph validation, dependencies, retrieval budgets, audits, PRD baselines, and strict Git history checks.

See `SKILL.md` for the agent workflow and `references/` for the record schema, review rubric, strict mode, and migration guides.
