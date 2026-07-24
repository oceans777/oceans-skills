# Changelog

## 2.1.0 — 2026-07-24

- Preserves explicit-only invocation metadata and adds repository-native runtime metadata.
- Adds the two-axis `compatibility` and `disposition` conflict model.
- Adds `lineage` and `exact` dependency modes with full candidate-graph validation.
- Protects accepted and rejected records as immutable terminal states.
- Adds deterministic context, paginated audit, JSONL output, PRD decision digests, and strict CI history validation.
- Keeps v2.0 schema-2 records readable without rewriting terminal files.
- Packages licenses, tests, references, examples, and plugin manifests inside the skill directory.
- Splits the deterministic core by responsibility while preserving the public `idea_ledger_core` API.
