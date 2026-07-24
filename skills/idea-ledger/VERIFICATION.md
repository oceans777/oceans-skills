# Verification

The repository-native v2.1.0 package was verified with:

```bash
python3 -m py_compile scripts/*.py
python3 -m unittest discover -s tests -p "test_*.py" -v
```

Expected result: 51 tests pass.

The suite verifies:

- no unintended Git or global side effects;
- explicit-only invocation metadata;
- path, symlink, lock, and configuration hardening;
- exact record-specific approval;
- terminal immutability and supersession-derived state;
- candidate graph validation before writes;
- `lineage` and `exact` dependency behavior and cycle rejection;
- bounded context and complete paginated audit output;
- deterministic indexes and PRD decision digests;
- strict base/history checks and real footer trailers;
- direct runtime installation and self-contained package layout.

The tests prove deterministic implementation properties. They do not prove semantic conflict classifications or user identity.
