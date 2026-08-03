# Migration from v1 to v2.3

Do not run v2.3 directly over a v1 `.idea-ledger/config.json`; v2.3 deliberately rejects schema 1.

## Why migration is not in-place

V1 combines records, automatic lifecycle hooks, Git hook installation, prompt snapshots, and enforcement state. V2.1 separates durable decision data from those mechanisms. An automatic in-place rewrite could silently preserve incorrect conflict claims, invent dependency semantics, or delete user-specific Git configuration.

## Safe migration

1. Create a branch or filesystem backup.
2. Disable and remove the v1 user/plugin lifecycle hooks through the platform that installed them.
3. Restore the repository's previous `core.hooksPath` deliberately. Verify all original hook types, not only `pre-commit` and `commit-msg`.
4. Keep `docs/idea-ledger/ideas/` as a read-only archive.
5. Move the v1 `.idea-ledger/` directory aside, for example to `.idea-ledger-v1-archive/`.
6. Run v2.3 `init`.
7. For each v1 record worth retaining, first align a governing charter, then create a v2.3 proposal with:
   - `charter` containing goal, actors, scope, principles, and non-goals;
   - `goal` from 目标;
   - `decision` from 方案;
   - `outcome` from 落点;
   - an explicit `rationale` reviewed by a human;
   - explicit scope, constraints, trade-offs, non-goals, and acceptance criteria where available;
   - a new `compatibility/disposition` assessment, not a blind copy of the v1 conflict label;
   - dependencies classified as `lineage` or `exact`;
   - `notes: ["Migrated from v1 IDEA-…"]`.
8. Accept only migrated records that still represent current decisions.
9. Run `validate`, then review the generated index and every audit page.
10. If enabling strict CI, establish the baseline only after terminal records and policy paths have been reviewed.

## Important

Do not delete the v1 archive until the team confirms that Git hooks, active decisions, record relationships, and any historical approval evidence were migrated correctly. V2.3 intentionally has no command that resets, restores, or deletes v1 files.
