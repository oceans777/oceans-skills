# Verification

The repository-native v2.3.0 package is verified with:

```bash
python3 -m py_compile scripts/*.py
python3 -m unittest discover -s tests -p "test_*.py" -v
```

Expected result: 60 tests pass.

The suite verifies:

- no unintended Git or global side effects;
- implicit material-decision routing metadata with read-only discovery boundaries;
- path, symlink, lock, and configuration hardening;
- charter-first generation order, required acceptance criteria, natural-language approval evidence, generic-reply rejection, and multi-proposal disambiguation;
- terminal immutability and supersession-derived state;
- candidate graph validation before writes;
- `lineage` and `exact` dependency behavior and cycle rejection;
- bounded context and complete paginated audit output;
- deterministic indexes and PRD decision digests;
- strict base/history checks and real footer trailers;
- direct runtime installation and self-contained package layout.

The tests prove deterministic implementation properties. They do not prove semantic conflict classifications or user identity.
