---
name: experience-triage
description: 'Use when a user wants to preserve a lesson, pitfall, rule, workflow, or agent behavior after real work and asks where it belongs: AGENTS.md/CLAUDE.md, directory rules, a skill, script/MCP tool, hook, memory, or no durable record. Triggers include "这次学到的", "踩坑沉淀", "规则该写到哪", and "新流程放哪".'
---

# Experience Triage

## Overview

Classify a new agent-work lesson into the right persistence layer. Optimize for reliability, low context cost, and future maintainability instead of dumping every rule into the global instruction file.

## Workflow

1. Restate the lesson in one concrete sentence.
2. If the lesson is vague, ask only the minimum clarifying question needed to classify it.
3. Classify both the lesson's scope and its execution mechanism. These are separate decisions and may produce a combined answer.
4. Give a directly usable draft for the recommended layer.
5. Mention when the lesson should later be promoted, demoted, automated, or deleted.

## Decision Tree

Use these questions in order:

**Q0: Is this lesson too private, speculative, one-off, or already obvious?**  
Yes -> Do not persist it. Explain why.  
No -> Q1.

**Q1: What is the scope?**

- Cross-project personal/team preference -> user-level memory or rule.
- Whole repository -> repository guidance or repository skill/tool.
- Directory, file type, module, plugin, or subsystem -> local routing guidance near that path, while keeping detailed workflows or tools in a skill/script.

Scope decides where the entry point lives. It does not decide whether the implementation is prose, a skill, a script, or a hook.

**Q2: Is the behavior mechanically decidable and repeatable?**

Yes -> Recommend a `script`, CLI command, MCP tool, or automation, then continue to Q3 to decide whether a hook should invoke it.

No -> Skip Q3 and continue to Q4.

**Q3: Is it tied to a deterministic lifecycle event and required every time?**

Yes -> Recommend a `hook` that calls the mechanical check. A hook is appropriate only when pass/fail can be determined without subjective judgment.

No -> Q4.

**Q4: Is it a multi-step workflow, checklist, review flow, or branching decision process?**  
Yes -> Recommend a new or updated `skill`. If it is path-scoped, add only a short local routing rule that points to the skill.

No -> Q5.

**Q5: Should every session in this project know it as a default behavior, map, or hard constraint?**  
Yes -> Recommend top-level `AGENTS.md` or `CLAUDE.md`. Keep it concise and judgment-oriented; do not claim a hook can enforce it unless Q2 and Q3 both passed.

No -> Q6.

**Q6: Is it a stable personal or team preference that applies across projects?**  
Yes -> Recommend memory or a user-level rule.  
No -> Do not persist it yet; wait for another real occurrence.

## Layer Guide

- `AGENTS.md` / `CLAUDE.md`: high-frequency project defaults, repository map, safety rules, collaboration rules, verification gates.
- Nested rules: concise local constraints or routing for one directory, module, plugin, template set, or file type. Keep detailed procedures in skills or scripts.
- `skill`: reusable judgment-heavy process with steps, branches, examples, and checks.
- `script` / CLI / MCP tool: deterministic execution, data retrieval, validation, transformation, or repeatable checks.
- `hook`: mechanically decidable pre/post action bound to a lifecycle event; hooks must not make subjective decisions.
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
