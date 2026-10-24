# AGENTS.md

This repository stores first-party oceans777 skills.

## Rules

- Place each skill under `skills/<skill-name>/`.
- New and extracted skills live in `https://github.com/oceans777/<skill-name>`. Link them here with a submodule. Do not commit a second full copy.
- `skills/git-upstream-sync-guard/` is a deprecated stub for `fork-skill`. Do not revive the old topology there.
- `skills/prd-blueprint/` is a deprecated stub for `prd-skill`. Do not revive the old skill id there.
- Do not add `skills/audit-ai-generation-site/` back into this tree while the hub catalog status is `pending-review`.
- Use lowercase letters, digits, and hyphens for skill names.
- Each skill must include `SKILL.md`.
- `SKILL.md` frontmatter must include `name` and `description`.
- Keep `SKILL.md` concise.
- Move long reference material into `references/`.
- Put deterministic helper scripts in `scripts/`.
- Put reusable output assets in `assets/`.
- Write reusable examples, templates, and workflow prose in Chinese by default; keep command names, file paths, package names, and required upstream text in their original language.
- Do not commit secrets, tokens, private paths, account details, or machine-specific configuration.
