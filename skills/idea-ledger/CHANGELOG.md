# Changelog

## 2.3.0 — 2026-08-03

- Adds a formal governing charter before any detailed solution or acceptance-criteria generation.
- Limits the charter to Goal, Actors, Scope, Principles, Non-goals, and one confirmation question within 10 non-empty lines.
- Makes the confirmed charter the upstream constraint from which the AI generates the complete decision and observable acceptance criteria.
- Persists the charter at the top of new decision records and PRDs for administrators and operators.
- Distinguishes charter confirmation from Ledger approval; generic confirmation never accepts a record.
- Keeps legacy v2.2 records without a charter readable and canonically stable.

## 2.2.0 — 2026-08-03

- Enables automatic routing for material product decisions while keeping implicit analysis read-only.
- Accepts unambiguous natural-language approval without requiring users to know a command token or fixed phrase.
- Preserves the original approval message and resolved record ID as audit evidence; legacy exact phrases remain readable and valid.
- Rejects generic confirmations and unnamed approval when multiple proposals are active.
- Requires at least one observable acceptance criterion for every new or revised proposal and before acceptance.
- Keeps schema-2 records and existing explicit approval evidence readable without rewriting terminal files.

## 2.1.0 — 2026-07-24

- Preserves explicit-only invocation metadata and adds repository-native runtime metadata.
- Adds the two-axis `compatibility` and `disposition` conflict model.
- Adds `lineage` and `exact` dependency modes with full candidate-graph validation.
- Protects accepted and rejected records as immutable terminal states.
- Adds deterministic context, paginated audit, JSONL output, PRD decision digests, and strict CI history validation.
- Keeps v2.0 schema-2 records readable without rewriting terminal files.
- Packages licenses, tests, references, examples, and plugin manifests inside the skill directory.
- Splits the deterministic core by responsibility while preserving the public `idea_ledger_core` API.
