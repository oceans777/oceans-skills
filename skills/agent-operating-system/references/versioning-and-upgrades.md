# Versioning And Upgrades

Generated project files are user-owned after creation. A newer skill release must not silently overwrite them.

## Metadata

`.oceans/agent-standards.conf` records:

- `schema_version`: configuration contract version.
- `generator_version`: skill version that created the scaffold.

## Upgrade Contract

1. Read the current configuration and generated files.
2. Compare the recorded schema with the supported schema.
3. Produce a change plan that separates untouched generated files, user-modified files, new files, and obsolete files.
4. Never overwrite a user-modified file automatically.
5. Apply changes through sibling staging files and atomic replacement where the platform supports it.
6. Keep a rollback copy until post-write verification succeeds.
7. Update `generator_version` only after the full upgrade succeeds.

## Compatibility

- A schema increase requires migration notes and tests.
- Removing a generated file requires an explicit deprecation period.
- Hook behavior changes require a negative test proving that hooks do not create files, launch editors, or call an LLM.
- Branch-policy defaults must come from repository evidence or explicit arguments, not from a temporary task branch.
