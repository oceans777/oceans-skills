# Optional strict mode — v2.1

The default skill is advisory and project-local. Teams that need merge-time policy can run the deterministic CLI in CI. Do not install global lifecycle hooks and do not treat agent tool hooks as a security boundary.

## Structural validation

```bash
python3 path/to/idea_ledger.py validate --root .
```

This checks canonical record rendering, schema, terminal state rules, full relationship graph, active dependency resolution, generated index content, and PRD decision baselines.

`ci-check` without a base ref runs the same structural validation:

```bash
python3 path/to/idea_ledger.py ci-check --root .
```

## Compare with the target branch

```bash
python3 path/to/idea_ledger.py ci-check \
  --root . \
  --base-ref origin/main
```

The check:

- resolves the target to a commit and computes a merge-base;
- reads critical governance policy from the base commit;
- rejects changing `schema`, `records_dir`, `index_file`, `prd_dir`, or `policy_exempt_prefixes` in the same change set;
- rejects modification, deletion, or renaming of records that were accepted or rejected at the base;
- traverses every commit-to-parent edge in `merge-base..HEAD` and rejects any later mutation of a record once it has entered accepted or rejected state;
- therefore also detects a terminal record that was illegally changed in one commit and restored in a later commit;
- performs an additional NUL-safe diff parse as defense in depth.

New proposed records and the first valid transition of a proposed record to a terminal state remain allowed. Once terminal in branch history, later commits cannot modify it.

## Optional commit traceability

```bash
python3 path/to/idea_ledger.py ci-check \
  --root . \
  --base-ref origin/main \
  --require-trailer
```

Trailer mode requires a **linear** `merge-base..HEAD` history. Merge commits fail the check and should be rebased or squashed.

For each commit that changes a non-exempt path, the commit message must contain a true Git footer trailer separated from the message body by a blank line:

```text
feat: implement encrypted workspace sync

Idea: IDEA-0002
```

A subject line such as this is not sufficient:

```text
Idea: IDEA-0002
```

The checker uses `git interpret-trailers --parse`; it does not accept an arbitrary matching line in the subject or body.

The referenced record must be a currently effective accepted decision **in that commit's snapshot**. A commit cannot cite a proposal that is accepted only in a later commit.

## Exempt paths

`policy_exempt_prefixes` in `.idea-ledger/config.json` identifies paths that do not need a trailer. Defaults are:

```json
[
  ".idea-ledger/",
  "docs/idea-ledger/",
  "docs/prd/",
  ".github/"
]
```

Matching preserves leading dots and path-component boundaries. For example, `.github/workflows/check.yml` matches `.github/`, while `github/workflows/check.yml` does not.

The CI module sets `GIT_LITERAL_PATHSPECS=1`, so configured record paths are treated literally rather than as Git pathspec magic.

## GitHub Actions example

Use a checkout depth sufficient to compute the merge-base. A robust example is:

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0

- name: Validate Idea Ledger
  run: |
    python3 path/to/pinned/idea_ledger.py ci-check \
      --root . \
      --base-ref origin/main \
      --require-trailer
```

If your checkout does not expose `origin/main`, fetch it explicitly before running the check.

## Trust model and limits

- Pin or vendor the reviewed CLI version in the repository.
- Protect the workflow and checker paths through repository controls.
- Run the check from a trusted revision when the hosting platform supports that model.
- The checker invokes read-only Git commands with disabled prompts and pagers, but it still executes inside the repository's CI trust context.
- It proves structural and history properties, not that the model's semantic conflict classification is correct.
- Trailer attribution is repository traceability, not human identity authentication.
- A maintainer who can change code, workflow, policy, and checker together remains outside this tool's security boundary.
