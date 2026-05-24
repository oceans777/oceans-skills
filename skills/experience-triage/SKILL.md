---
name: experience-triage
description: "Use when a user wants to preserve a lesson, pitfall, rule, workflow, or agent behavior after real work and asks where it belongs: AGENTS.md/CLAUDE.md, directory rules, a skill, script/MCP tool, hook, memory, or no durable record. Triggers include \"\u8fd9\u6b21\u5b66\u5230\u7684\", \"\u8e29\u5751\u6c89\u6dc0\", \"\u89c4\u5219\u8be5\u5199\u5230\u54ea\", and \"\u65b0\u6d41\u7a0b\u653e\u54ea\"."
---

# Experience Triage

## Overview

Classify a new agent-work lesson into the right persistence layer. Optimize for reliability, low context cost, and future maintainability instead of dumping every rule into the global instruction file.

## Workflow

1. Restate the lesson in one concrete sentence.
2. If the lesson is vague, ask only the minimum clarifying question needed to classify it.
3. Run the decision tree in order; the first matching layer usually wins.
4. Give a directly usable draft for the recommended layer.
5. Mention when the lesson should later be promoted, demoted, automated, or deleted.

## Decision Tree

Use these questions in order:

**Q0: Is this lesson too private, speculative, one-off, or already obvious?**  
Yes -> Do not persist it. Explain why.  
No -> Q1.

**Q1: Must this happen every time, with zero exceptions and no reliance on model memory?**  
Yes -> Recommend a `hook` or another deterministic guard.  
No -> Q2.

**Q2: Does it require executing commands, querying APIs, inspecting data, or performing repeatable mechanical checks?**  
Yes -> Recommend a `script`, CLI command, MCP tool, or automation, then reference it from the relevant rule or skill.  
No -> Q3.

**Q3: Does it apply only to a directory, file type, module, plugin, template family, or subsystem?**  
Yes -> Recommend a nested `AGENTS.md`/`CLAUDE.md` or path-scoped rule near that code.  
No -> Q4.

**Q4: Is it a multi-step workflow, checklist, review flow, or branching decision process?**  
Yes -> Recommend a new or updated `skill`.  
No -> Q5.

**Q5: Should every session in this project know it as a default behavior, map, or hard constraint?**  
Yes -> Recommend top-level `AGENTS.md` or `CLAUDE.md`. Keep it concise; if the file is already long, suggest moving detailed procedure into a skill.  
No -> Q6.

**Q6: Is it a stable personal or team preference that applies across projects?**  
Yes -> Recommend memory or a user-level rule.  
No -> Do not persist it yet; wait for another real occurrence.

## Layer Guide

- `AGENTS.md` / `CLAUDE.md`: high-frequency project defaults, repository map, safety rules, collaboration rules, verification gates.
- Nested rules: local constraints for one directory, module, plugin, template set, or file type.
- `skill`: reusable judgment-heavy process with steps, branches, examples, and checks.
- `script` / CLI / MCP tool: deterministic execution, data retrieval, validation, transformation, or repeatable checks.
- `hook`: mandatory pre/post action that must run even when the model forgets.
- Memory / user rule: stable cross-project preference, not repository-specific.
- No persistence: one-off discoveries, temporary debugging details, personal notes, or rules that would create noise.

## Output Format

Use this exact shape unless the user asks for another format:

```text
[Triage conclusion] <layer>
[Recommended location] <path or asset>
[Reason] <1-3 concise bullets>
[Draft] <directly usable draft, command, hook sketch, or skill description>
[Follow-up reminder] <promotion/demotion/automation/safety note, if useful>
```

## Current-Repo Hints

When a repository has an `AGENTS.md`, treat it as the canonical project instruction layer. For Discuz X5 template work, classify common lessons like this:

- "Do not maintain compiled template cache as source" -> top-level `AGENTS.md` if not already present.
- "Only this plugin has this static asset convention" -> nested rule near that plugin.
- "After template changes, inspect desktop/mobile/login/navigation/static assets" -> skill or QA checklist.
- "Run `php -l` on changed PHP files before commit" -> verification script or hook if it must be enforced.
- "How to release this repository" -> skill if it branches; script/tool if it is deterministic.

## Writing Rules

- Be specific: include file paths, trigger phrases, examples, and non-examples.
- Prefer moving detailed procedures out of always-loaded files and into skills.
- Prefer automation over instructions when the behavior is mechanical.
- Do not create or edit persistence files unless the user asks to implement the recommendation.
