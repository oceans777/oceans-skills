---
name: discuz-x5
description: Use when developing, reviewing, debugging, or planning Discuz X5 PHP plugin, template, admincp, table class, hook, CSS, JavaScript, install/upgrade, generated-cache, PHP 8 compatibility, or application packaging changes.
---

# Discuz X5 Development

## Overview

Discuz X5 work is primarily PHP extension work. Preserve Discuz's extension boundaries, keep PHP modules small, keep templates presentational, keep CSS/JS in static assets, and treat generated caches as runtime output.

For official packaging and detailed verification, read [packaging-and-verification.md](references/packaging-and-verification.md). For PHP/template/CSS conventions, read [php-template-css.md](references/php-template-css.md).

## First Decisions

- **Plugin behavior**: use `source/plugin/<identifier>/` for front modules, admincp modules, install/upgrade/uninstall scripts, libraries, table classes, plugin-local templates, and plugin-owned assets.
- **Template presentation**: use `template/<name>/` and related static assets for theme/page presentation. Do not hide plugin business logic in template files.
- **Generated output**: treat `data/template/`, `data/cache/`, and similar runtime artifacts as generated files, not maintainable source, unless the task explicitly targets compiled output.
- **Core source**: treat Discuz core as off-limits by default in this repository. Solve defects through plugin code, source templates, source static assets, lifecycle scripts, extension points, or operational repair steps. Only consider a core change after explicit user authorization, with reason, upgrade impact, and rollback path.

Choose data ownership deliberately:

- Use Discuz native tables only when native forum behavior, permissions, moderation, search, or comments are the canonical owner of the data.
- Use plugin tables when the plugin owns the domain data, configuration, ordering, or integration metadata.
- Prefer a hybrid only when native Discuz records and plugin-owned records each have a clear responsibility.

## PHP Plugin Architecture

- Use Discuz path helpers and constants such as `DISCUZ_PLUGIN()`, `DISCUZ_TEMPLATE()`, `DISCUZ_DATA`, and `DISCUZ_ROOT_STATIC` instead of hardcoded server paths when applicable.
- Guard PHP entry files with `if(!defined('IN_DISCUZ')) exit('Access Denied');`; admin modules also require `IN_ADMINCP`.
- Keep `admincp.inc.php` as a small dispatcher; move page-specific behavior to `admin/*.php`.
- Put shared PHP helpers in `lib/`, table gateways in `table/`, and plugin-local templates in `source/plugin/<identifier>/template/`.
- Split by responsibility before adding code: request handling, validation, persistence, rendering, assets, and tests should not accumulate in one file.
- Prefer Discuz table classes or established project helpers for persistence; avoid raw SQL/string concatenation unless there is a clear local pattern and sanitized input.
- Sanitize request input before persistence and escape output with `dhtmlspecialchars()` unless intentionally rendering trusted HTML.

## Admincp Pages

- Prefer `showformheader`, `showtableheader`, `showsetting`, `showtablerow`, `showsubmit`, `cpmsg`, `submitcheck`, `ADMINSCRIPT`, and native admin styling.
- Use shared admin UI helpers for repeated headers, tabs, buttons, tips, and option normalization.
- For `showsetting(..., 'select')`, pass Discuz-compatible option rows such as `array(array($value, $label))`; do not pass associative maps directly.
- Preserve sentinel/default options such as `0 => 未分配` through shared option helpers so edit forms do not silently rewrite data.
- Keep admin CSS in a dedicated stylesheet; avoid long inline style strings in PHP helpers.

## Templates, CSS, And JavaScript

- Template files should express markup and lightweight presentation flow, not database access, request handling, or business rules.
- Edit source templates and source static files, not compiled `data/template/` output.
- Keep CSS in plugin/template static files, not inside PHP strings. Prefix custom classes with the plugin/template identifier to avoid bleeding into Discuz core/admin styles.
- Keep JavaScript in static files or focused template scripts. Avoid duplicating state logic across templates; expose only sanitized data needed by the UI.
- Frontend templates require responsive checks for desktop and mobile views, especially fixed controls, overlays, dialogs, and interactive states.

## Lifecycle, Storage, And Packaging

- `install.php` should be idempotent where practical and set `$finish = TRUE`.
- `upgrade.php` must migrate existing installs without destroying user data.
- `uninstall.php` is the normal place for destructive drops, limited to plugin-owned tables.
- For plugin metadata, menu, language, or package repair bugs, fix the source of truth inside plugin-owned XML/JSON, `lib/` helpers, and lifecycle/admincp entry points. Do not patch Discuz AdminCP list rendering or generated caches to hide stale database metadata.
- For a suite of related plugins, prefer one idempotent suite-level repair helper in the owning/hub plugin that delegates to each plugin's own repair helper; cover it with a focused test that simulates stale `common_plugin` rows.
- Store Chinese JSON with `JSON_UNESCAPED_UNICODE` when admin content must remain readable.
- Keep upload/provider secrets server-side. Store only safe integration metadata for frontend use; never expose secret keys in templates or JavaScript.
- For official release packaging, keep the installation XML aligned with modules, version, directory, lifecycle scripts, and plugin-owned tables. JSON exports are local/project helper artifacts, not a substitute for the official XML package contract.

## Code Quality Gate

Before implementing or approving a Discuz X5 plugin/template change:

- Do not put all logic into one file. Entry files dispatch; admin modules coordinate; `lib/` owns reusable behavior; `table/` owns persistence; templates own markup; CSS/JS own presentation and interaction.
- Treat long custom files as a design smell. If a file approaches roughly 300-400 lines, or mixes unrelated responsibilities, split it before adding more behavior. Files over roughly 500 lines need a clear reason or a refactor plan.
- Avoid giant `admincp.inc.php`, giant settings pages, inline CSS blocks in PHP, repeated option-building code, duplicated sanitization logic, and copied template snippets that should be shared.
- Prefer small helper functions/classes with names tied to Discuz concepts and the plugin domain; do not introduce broad abstractions that do not match the existing project.
- Add architecture guards or focused tests for fragile conventions such as admin option formats, sentinel defaults, module dispatch, and generated-cache boundaries.

## Two-Pass Review

**Pass 1: Discuz contract**

- Correct plugin/template/core boundary?
- If a core edit seems tempting, has a plugin/template/lifecycle/extension-point alternative been exhausted first?
- Correct guards, admin permissions, module declaration, and lifecycle scripts?
- Generated cache files excluded unless explicitly required?
- Official package metadata checked when preparing a release?

**Pass 2: Maintainability and runtime risk**

- Existing local architecture reused?
- Does the fix address the source of truth instead of masking a stale database/cache/rendering symptom?
- Admin UI split into dispatcher, modules, helpers, and stylesheet?
- No monolithic file, overlong file, or mixed responsibility introduced?
- `showsetting` options normalized for PHP 8?
- Defaults and sentinel values preserved on edit/save?
- Input sanitized, output escaped, secrets not exposed?
- Tests or architecture guards cover fragile behavior?

## Verification

Match verification to the change. Minimum expectations:

- For projects that use the oceans777 agent workflow, the bundled template
  `assets/agent-verify.template.ps1` can be copied to
  `scripts/agent-verify.ps1` as a Discuz X5 project-level verification gate.
  It enforces `.githooks`, `dev` / `codex/<task-name>` branch policy, risky
  staged file checks, generated runtime file boundaries, PHP lint, JavaScript
  syntax checks, related JS behavior tests, staged PHP tests, and commit
  message format.
- Copy `assets/agent-status.template.ps1` to `scripts/agent-status.ps1` when
  using that verification gate. It reports working tree state and can detect or
  restore whitespace-only drift referenced by `agent-verify.ps1`.
- PHP changes: `php -l` on changed PHP files.
- Plugin behavior: run existing focused tests.
- Template/CSS/JS: run available lint/build/test or browser QA with screenshots.
- Packaging/release: read [packaging-and-verification.md](references/packaging-and-verification.md) and inspect official metadata.
- Always run `git diff --check` before committing.

Report any verification that could not be run and the remaining risk.
