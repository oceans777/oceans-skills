# Migration from v2.0 to v2.1

v2.1 keeps record `schema: 2` and is designed to read existing v2.0 ledgers without rewriting accepted or rejected files.

## Before upgrading

1. Create a branch or filesystem backup.
2. Record the current `VERSION`, `.idea-ledger/config.json`, record directory, index, and PRD directory.
3. Confirm no Idea Ledger command is currently running.
4. Replace the v2.0 skill/plugin files with the v2.1 package. Do not overwrite project records with package examples.

## First run

From the project root:

```bash
python3 path/to/v2.1/idea_ledger.py status --root .
python3 path/to/v2.1/idea_ledger.py refresh-index --root .
python3 path/to/v2.1/idea_ledger.py validate --root .
```

The v2.0 index format differs from v2.1, so `validate` may initially report a stale index. Running `refresh-index` is the expected migration step.

## Compatibility behavior

v2.1 reads:

- existing schema-2 record metadata;
- v2.0 `conflict.kind` objects;
- v2.0 string `depends_on` entries.

In memory:

- legacy conflicts are mapped to the new compatibility/disposition model;
- string dependencies are treated as `lineage`.

Existing terminal record files are not automatically rewritten. New records and revised proposed records use the v2.1 canonical forms.

## New invariants that may expose an old problem

`validate` may report a ledger that v2.0 accepted but v2.1 considers globally inconsistent, for example:

- the same ID appears in `supersedes` and `depends_on`;
- two accepted records supersede the same target;
- an active exact-style requirement cannot remain effective after supersession;
- active accepted dependencies form a cycle;
- a terminal record has inconsistent terminal timestamps or a non-approvable conflict state;
- configured records/index/PRD paths collide or nest;
- a generated PRD references a superseded or changed decision baseline.

Do not repair an accepted or rejected record in place merely to silence validation. Preserve the original file and choose one of these controlled responses:

1. If the record was never actually terminal in trusted history, restore it from the trusted source and re-run validation.
2. If a current decision must change, create a new proposed record with explicit supersession and reviewed dependencies.
3. If historical corruption must be repaired, perform a separately reviewed repository migration, document the byte-level change and reason outside the ledger, and update CI baselines deliberately.

## Adopting explicit dependency modes

You do not need to rewrite old strings immediately. For a proposed record you are already revising, convert:

```json
{"depends_on": ["IDEA-0008"]}
```

to:

```json
{"depends_on": [{"id": "IDEA-0008", "mode": "lineage"}]}
```

Use `exact` only when replacement of IDEA-0008 must be blocked until the dependent decision changes.

## Adopting the two-axis conflict model

For any new or revised proposal, replace a legacy object such as:

```json
{
  "kind": "resolved",
  "related_ids": ["IDEA-0003"],
  "rationale": "The default remains local-only.",
  "confidence": "high",
  "resolution": "Cloud transfer requires explicit workspace opt-in."
}
```

with an explicit diagnosis and response:

```json
{
  "compatibility": "tension",
  "reviewed_ids": ["IDEA-0003"],
  "conflicts_with": ["IDEA-0003"],
  "rationale": "Remote transfer creates tension with the local-only boundary.",
  "confidence": "high",
  "disposition": "bounded",
  "mitigation": "Cloud transfer requires explicit workspace opt-in."
}
```

If comparison shows no actual incompatibility, use `compatible/none`, retain the reviewed ID in `reviewed_ids`, and leave `conflicts_with` empty.

## Strict CI migration

v2.1 strict mode is stronger than v2.0:

- rejected records are protected in addition to accepted records;
- branch-local terminal history is checked commit by commit;
- trailer lines must be true Git footers;
- trailers are validated against the decision state at that commit;
- point-directory exemptions and literal paths are handled correctly.

Before making the new check required, run it on representative branches and repair commit-message/history practices through rebase or squash where repository policy allows.

## Completion checklist

- `refresh-index` completed;
- `validate` returns success;
- `audit --format jsonl` can read every page;
- existing PRDs either validate or are intentionally marked for regeneration/review;
- strict CI passes on a representative branch;
- team documentation uses `compatibility/disposition` and `{id, mode}` examples.
