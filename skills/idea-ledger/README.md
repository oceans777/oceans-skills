# Idea Ledger v2.1.0

Idea Ledger records material product decisions as project-local, structured, auditable files. It is explicit-only: use `$idea-ledger` or `/idea-ledger`; ordinary coding, explanation, summarization, translation, bug fixing, or generic planning must not trigger it.

## Safety boundary

- Never initializes Git, changes Git configuration, installs hooks, stages, commits, resets, restores, cleans, or reverts user work.
- Read-only commands never initialize a missing ledger.
- Accepted and rejected records are immutable.
- Generic confirmations such as “可以”, “继续”, or “OK” never approve a record.
- Every write validates the complete candidate relationship and dependency graph before disk mutation.
- Approval metadata is an audit trace with `actor_verified: false`, not identity authentication.

## Requirements

Python 3.10 or later. Git is optional and used only by strict CI checks.

## Direct use

```bash
python3 scripts/idea_ledger.py --version
python3 scripts/idea_ledger.py init --root .
python3 scripts/idea_ledger.py new --root . --input examples/proposal-0001-local-first.json --json
python3 scripts/idea_ledger.py validate --root .
```

## Commands

`init`, `new`, `revise`, `accept`, `reject`, `show`, `list`, `status`, `context`, `audit`, `validate`, `refresh-index`, `prd-template`, and `ci-check`.

## Tests

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

The deterministic suite contains 51 tests covering side effects, explicit invocation metadata, state transitions, graph validation, dependencies, retrieval budgets, audits, PRD baselines, and strict Git history checks.

See `SKILL.md` for the agent workflow and `references/` for the record schema, review rubric, strict mode, and migration guides.
