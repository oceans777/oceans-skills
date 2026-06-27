# AGENTS.md

This repository stores first-party oceans777 skills.

## Rules

- Place each skill under `skills/<skill-name>/`.
- Use lowercase letters, digits, and hyphens for skill names.
- Each skill must include `SKILL.md`.
- `SKILL.md` frontmatter must include `name` and `description`.
- Keep `SKILL.md` concise.
- Move long reference material into `references/`.
- Put deterministic helper scripts in `scripts/`.
- Put reusable output assets in `assets/`.
- Write reusable examples, templates, and workflow prose in Chinese by default; keep command names, file paths, package names, and required upstream text in their original language.
- Do not commit secrets, tokens, private paths, account details, or machine-specific configuration.
