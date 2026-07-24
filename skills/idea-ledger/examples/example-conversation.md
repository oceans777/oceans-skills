# Example conversation

**User**

```text
$idea-ledger new 我们希望加入云同步，但默认仍然只保存在本地。
```

**Assistant**

```markdown
## Decision draft
- Goal: support cross-device access without weakening the default local-only boundary.
- Decision: encrypted sync is opt-in per workspace; no upload occurs before opt-in.
- Rationale: workspace-level opt-in preserves the existing default while enabling a requested capability.
- Outcome: opted-in devices converge; other workspaces remain local-only.

## Conflict assessment
- Compatibility: compatible
- Disposition: none
- Reviewed record: IDEA-0001
- Conflicts with: none
- Evidence: IDEA-0001 requires local-only by default and explicit authorization for remote transfer; this proposal preserves both clauses.
- Confidence: high

## Ledger action
- Saved as proposed IDEA-0002.

## Next gate
Reply exactly: `批准 IDEA-0002`
```

**User**

```text
可以，不过先把删除远端副本也写进约束。
```

The assistant revises `IDEA-0002`; it does not accept it because “可以” is not record-specific approval. The candidate graph is validated before the revised record is written.

**User**

```text
批准 IDEA-0002
```

The assistant runs `accept` with that exact evidence, validates the full ledger, and reports `accepted`. It does not stage or commit files unless the user separately requests a Git action.
