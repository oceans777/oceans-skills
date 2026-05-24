# PHP, Template, CSS, And JavaScript Norms

Use this reference when a Discuz X5 task touches PHP code structure, plugin modules, template files, CSS, JavaScript, or responsive frontend presentation.

## PHP Structure

- Entry files only bootstrap or dispatch. Put behavior in `admin/*.php`, front module files, `lib/`, or `table/` according to responsibility.
- `admincp.inc.php` should authorize/dispatch/load shared assets, not contain large forms, persistence logic, or page-specific rendering.
- `lib/` contains reusable domain helpers and service-like code. Keep names tied to the plugin domain.
- `table/` contains table gateways and query helpers. Prefer Discuz table conventions and existing project query helpers over scattered SQL.
- Templates should not query the database or parse request payloads.
- Use `DISCUZ_PLUGIN()`, `DISCUZ_TEMPLATE()`, `DISCUZ_DATA`, and `DISCUZ_ROOT_STATIC` where official X5/W compatibility expects path abstraction.
- Keep PHP 8 compatibility in mind: avoid loose assumptions about arrays, nulls, string offsets, and callable signatures.

## Input, Output, And Data

- Normalize request input at the module boundary.
- Use one sanitizer/cleaner per domain concept instead of repeating ad hoc casts in every page.
- Escape output with `dhtmlspecialchars()` by default.
- Render trusted rich HTML only through an explicit allowlist or project-approved renderer.
- Keep object storage credentials, upload signatures, and provider keys server-side.
- Store plugin-owned integration or domain metadata separately from presentation copy when the plugin owns that behavior.

## Admincp UI

- Use Discuz admin helpers for forms, tables, messages, and submissions.
- Keep admin style consistent with Discuz's native backend; use small local CSS only for layout clarity.
- Normalize all `showsetting(..., 'select')` options to two-column rows: `array(array($value, $label))`.
- Preserve `0`, empty-string, and disabled/default sentinel options through shared option helpers.
- Prefer sectioned forms and clear module tabs over one long settings screen.

## Template Files

- Source templates live in the plugin/template source location, not `data/template/`.
- Use templates for structure, loops, conditionals, and display decisions only.
- Keep repeated template fragments in includes/partials if the project pattern supports it.
- Escape variables unless a value has already been sanitized and intentionally marked as trusted.
- Keep touch targets, fixed overlays, dialogs, and responsive states usable across desktop and mobile views.

## CSS

- Put custom CSS in dedicated static files.
- Prefix custom selectors with the plugin/template identifier.
- Avoid broad selectors such as `div`, `a`, `.btn`, `.content`, or global resets that can affect Discuz core/admin pages.
- Do not place large CSS blocks in PHP strings or database settings.
- Use CSS variables or small theme maps for administrator-controlled colors rather than duplicating literal colors.
- Verify desktop and mobile layouts; overlays and fixed controls should avoid text overlap and unreachable controls.

## JavaScript

- Put reusable behavior in static JS files.
- Keep inline scripts small and only for wiring sanitized configuration data.
- Avoid relying on generated DOM IDs when stable data attributes would be clearer.
- Avoid duplicating complex state logic across multiple templates.
- For uploads, expose only safe client parameters; signatures and secrets stay server-side.

## File Size And Splitting

- Around 300-400 lines, reassess responsibility and split before adding unrelated behavior.
- Above roughly 500 lines, require an explicit reason or refactor plan.
- Split by domain responsibility, not by arbitrary line count: admin form, table access, sanitizer, integration logic, template, CSS, and JS are separate axes.
