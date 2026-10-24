# oceans777 First-Party Skills

This repository is the compatibility aggregate for skills created or primarily maintained by oceans777. It is not the install entry. The entry repository remains [oceans777/skills](https://github.com/oceans777/skills). Do not rename this repository to `skills`; that name is already the umbrella.

Each first-party skill now has its own repository. A directory under `skills/<skill-id>/` is a Git submodule pointing at that repository, except for the deprecation stub called out below. History of the old in-tree copies stays in this repository's git history.

| Skill | Canonical repository |
| --- | --- |
| `fork-skill` | https://github.com/oceans777/fork-skill |
| `agent-operating-system` | https://github.com/oceans777/agent-operating-system |
| `audit-ai-generation-site` | https://github.com/oceans777/audit-ai-generation-site |
| `discuz-x5` | https://github.com/oceans777/discuz-x5 |
| `experience-triage` | https://github.com/oceans777/experience-triage |
| `idea-ledger` | https://github.com/oceans777/idea-ledger |
| `prd-skill` | https://github.com/oceans777/prd-skill |

`skills/git-upstream-sync-guard/` is a deprecated stub. That skill was renamed to `fork-skill`. New forks use a fast-forward mirror branch `upstream/<default>`, active work on `dev`, and release on `main` (formerly `release`).

`skills/prd-blueprint/` is a deprecated stub. That skill was renamed to `prd-skill`. The outline-first flow is unchanged.

`audit-ai-generation-site` is not linked as a submodule here. The hub catalog still marks it pending review, and the hub rejects a pending skill that also exists in this package tree. Its source repository is linked above.

Clone this aggregate with its skill pointers:

```sh
git clone --recurse-submodules https://github.com/oceans777/oceans-skills.git
```

Each skill must include `SKILL.md`. Optional supporting folders are `scripts/`, `references/`, `assets/`, and `agents/`. Use lowercase letters, digits, and hyphens for skill names. Add a new skill by creating `oceans777/<skill-id>` and linking it with `git submodule add`, instead of committing another full copy into this tree.

## 需求文档生成技能

`prd-skill`（需求文档生成技能）：明确要求写需求文档时，生成三项总纲和完整详细文档，并逐项核对功能与验收。

[使用说明与验收依据](docs/prd-skill/README.md)。规范副本在 [oceans777/prd-skill](https://github.com/oceans777/prd-skill)。安装通过 [统一入口](https://github.com/oceans777/skills)，生效状态以入口目录为准。
