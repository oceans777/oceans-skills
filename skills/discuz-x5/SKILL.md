---
name: discuz-x5
description: Use when developing, reviewing, debugging, securing, testing, or packaging Discuz X5 PHP plugins, templates, admincp modules, table classes, hooks, CSS, JavaScript, and install/upgrade/uninstall changes.
---

# Discuz X5 Development

## Purpose

Apply Discuz X5 domain rules without importing one repository's branch names, machine paths, or directory snapshots into a reusable skill. Preserve extension boundaries, source-of-truth ownership, lifecycle safety, PHP 8 compatibility, frontend isolation, and official packaging contracts.

## Boundary

This skill owns Discuz engineering rules and domain verification.

- Repository-wide branch, worktree, hook, commit, and delivery policy belongs to `agent-operating-system` or the project itself.
- The reusable verifier must be configured through `.discuz-x5-skill.conf`; it must not contain a project name, dated source directory, local drive, or fixed branch prefix.
- Generated caches are runtime output, not maintainable source.
- Core edits are off-limits by default. Exhaust plugin, template, lifecycle, and extension-point solutions first.

## First Decisions

1. Identify the real Discuz root and application type.
2. Decide whether Discuz native data or plugin-owned data is canonical.
3. Separate request handling, validation, persistence, rendering, assets, and tests.
4. Identify install, upgrade, uninstall, packaging, permission, and rollback impact before editing.

## Architecture

- Plugin code lives under `source/plugin/<identifier>/`.
- Theme/template applications live under `template/<identifier>/`.
- Entry files authorize and dispatch; they do not accumulate page rendering and persistence.
- Put reusable domain behavior in `lib/`, table access in `table/`, page-specific admin behavior in `admin/`, markup in templates, and presentation in static CSS/JavaScript files.
- Prefer Discuz path helpers and constants over machine-specific paths.
- Prefer table classes or established query helpers over scattered SQL.

## Input, Output, And Security

- Guard PHP entry files with `IN_DISCUZ`; admin modules also require `IN_ADMINCP`.
- Normalize request input at the module boundary.
- Use parameterized queries or established table helpers.
- Escape output with `dhtmlspecialchars()` unless an explicit allowlisted renderer owns trusted rich HTML.
- Keep credentials, signatures, provider keys, and storage secrets server-side.
- Review CSRF, permission escalation, upload handling, path traversal, SSRF, stored XSS, lifecycle SQL, and administrative auditability. Read `references/security-review.md`.

## Admincp And Presentation

- Use Discuz admin helpers for forms, tables, messages, and submissions.
- Normalize `showsetting(..., 'select')` options to two-column rows.
- Preserve `0`, empty-string, disabled, and default sentinel values through shared helpers.
- Keep CSS in dedicated static files and prefix selectors with the plugin or template identifier.
- Keep reusable JavaScript in static files; inline scripts may only wire sanitized configuration.
- Verify desktop and mobile states, especially overlays, dialogs, fixed controls, and touch targets.

## Lifecycle And Packaging

- `install.php` should be repeatable where practical and set `$finish = TRUE`.
- `upgrade.php` must preserve existing user data and support real upgrade paths.
- `uninstall.php` may remove only plugin-owned data and must make destructive behavior explicit.
- Repair metadata at the owning XML/JSON/lifecycle source, not by patching generated caches or core list rendering.
- Official packages must align identifier, version, modules, lifecycle scripts, owned tables, files, and installation XML.
- Do not ship caches, attachments, local reports, secrets, debug output, archives, or machine-specific paths.

## Verification

Copy the configuration and platform verifier into the target repository, then tailor only the configuration file.

```text
assets/discuz-x5.conf.template       -> .discuz-x5-skill.conf
assets/agent-verify.template.sh      -> scripts/discuz-x5-verify.sh
assets/agent-verify.template.ps1     -> scripts/discuz-x5-verify.ps1
assets/agent-status.template.ps1     -> scripts/discuz-x5-status.ps1
```

The verifier:

- checks staged files, or all current working-tree changes when nothing is staged;
- blocks generated runtime paths and risky files;
- runs PHP and JavaScript syntax checks;
- runs related plugin behavior tests when discoverable;
- restores the caller's PowerShell working directory;
- contains no branch policy or machine-specific executable discovery.

Also run browser QA with screenshots for UI changes and inspect official package metadata for releases.

## Two-Pass Review

### Pass 1: Discuz Contract

- Correct application type and source directory?
- Core edit avoided or explicitly authorized?
- Correct guards, permissions, module declaration, and lifecycle behavior?
- Generated output excluded?
- Official packaging contract satisfied?

### Pass 2: Runtime And Maintainability

- Source-of-truth defect fixed rather than masked?
- Responsibilities split cleanly?
- Input sanitized, output escaped, and secrets protected?
- Defaults and sentinel values preserved?
- Upgrade and rollback paths safe?
- Matching automated tests and browser evidence present?

## Common Failures

- Copying one project's dated directory layout into a reusable verifier.
- Hardcoding `dev`, a task-branch prefix, a drive letter, or a local PHP installation.
- Passing verification because broken files are unstaged.
- Editing `data/template/` or `data/cache/` as source.
- Turning `admincp.inc.php` into a monolith.
- Shipping frontend changes without real desktop/mobile evidence.
