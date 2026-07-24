# Tests

Run from the package root:

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

The deterministic suite contains **51 tests**. Test subprocesses have bounded timeouts; Git operations inside the optional CI module also use bounded timeouts and disabled interactive prompts.

Coverage includes:

- no unintended Git or global side effects;
- explicit-only plugin metadata;
- configuration path topology and symlink/lock hardening;
- exact approval and terminal immutability;
- candidate global-graph validation before disk mutation;
- two-axis conflict rules;
- `lineage` and `exact` dependencies, cycles, supersession, and legacy v2.0 input;
- strict context budgets, complete audit/JSONL output, deterministic indexes, and PRD digests;
- JSON-safe CLI output and canonical record rendering;
- baseline and per-commit terminal-history CI checks;
- real footer trailers, per-commit accepted-state validation, policy exemptions, and linear history;
- direct runtime installation and self-contained repository layout.

`eval-cases.json` is a separate model-level routing/output evaluation set. Run those prompts in fresh sessions with and without the skill enabled. Unit tests cannot prove model routing precision or semantic conflict accuracy.
