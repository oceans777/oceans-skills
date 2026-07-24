# Evaluation Cases

Use these cases to review classification consistency. They are examples, not hardcoded answers for every repository.

| Case | State | Scope | Mechanism | Reason |
| --- | --- | --- | --- | --- |
| A formatter fails on every commit and has a deterministic command | automated | repository | hook calling script | Mechanical and lifecycle-bound |
| Every architecture change needs human review | adopted | repository | startup guidance or skill | Mandatory but judgment-heavy |
| One temporary API outage caused a retry | observe | none | no record | One-off external event |
| A secret was committed once | candidate | repository | script plus hook | Single severe incident justifies immediate review |
| One plugin requires two-column admin select options | adopted | path-scoped | local route to domain skill/test | Domain-specific and repeatable |
| A generated cache was edited repeatedly | automated | repository or path | validator plus hook | Mechanical path boundary |
| Team prefers Chinese commit titles across projects | adopted | cross-project | user/team rule | Stable preference, not repository logic |
| Release steps branch by package type | adopted | repository | skill | Judgment-heavy branching workflow |
| Release is one deterministic command | automated | repository | script/tool | Mechanical execution |
| A rule duplicates a stricter existing rule | retired | existing scope | no new record | New text adds noise |
| Two startup files contradict branch policy | candidate | repository | owner decision | Conflict must be resolved first |
| A directory convention appears once with low impact | observe | path-scoped | no record | Insufficient evidence |
| Browser screenshots were omitted in three UI regressions | adopted | path-scoped or repository | skill/checklist; automate evidence where possible | Repeated judgment-heavy quality gate |
| A local drive path leaked into a public template | automated | repository | validator plus hook | Mechanically detectable portability defect |
| A model repeatedly overwrites unrelated work | adopted | cross-project and repository | safety guidance plus deterministic dirty-tree checks | Combined scope and mechanism |
| An obsolete build system rule remains after migration | retired | repository | remove after verification | No longer valid |
| A high-risk migration lacks rollback evidence | candidate | repository | skill plus required evidence | Consequential and judgment-heavy |
| The same lesson is already enforced by CI | adopted | existing automation | documentation pointer only | Avoid duplicate enforcement |
| A user asks to remember a private token | retired | none | no record | Secret data must not be persisted |
| A task-specific debugging command helped once | observe | none | no record | Temporary detail |
