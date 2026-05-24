# Discuz X5 Packaging And Verification

Use this reference when preparing an application package, touching install/upgrade/uninstall behavior, auditing official directory boundaries, or deciding which verification evidence is required.

## Official Application Boundaries

Discuz's open platform defines these application baselines:

- Plugin applications use `/source/plugin/` and include files under `/source/plugin/<plugin-identifier>/`.
- Template applications use `/template/` and include files under `/template/<template-identifier>/`.
- Extension applications use `/` as the baseline and must not include other application-type baseline directories.

Discuz X5 can read application configuration in XML/JSON form, and X5-compatible metadata should use the documented version value such as `X5.0` for X5.0+ compatibility. For plugin application-center submission, the open-platform package contract still expects an installation XML: provide simplified GBK or UTF-8 Simplified Chinese installation XML, and the platform can generate other encoding installation XML files. A JSON export can be useful for local scaffolding, tests, or migration review, but it is not a replacement for the official plugin installation XML submission artifact.

Official entry points:

- X5 docs: https://open.dismall.com/?ac=document&page=dev_x5_index
- Directory structure: https://open.dismall.com/?ac=document&page=x5_1_dir_index
- Application development: https://open.dismall.com/?ac=document&page=dev_dzw_index
- Open platform app types: https://open.dismall.com/index.php
- X5 sample app: https://gitee.com/Discuz/DiscuzXDevSample

## Packaging Checklist

- Plugin identifier, directory, title, version, description, and module declarations match real files.
- Compatibility metadata uses the right target value, such as `X5.0` for X5.0+ branches or the documented Discuz! W value when preparing a W-only branch.
- Front modules, admincp modules, and lifecycle script names resolve from `source/plugin/<identifier>/`.
- `install.php`, `upgrade.php`, and `uninstall.php` are guarded by `IN_DISCUZ`.
- Plugin-owned tables are listed consistently in metadata and lifecycle SQL.
- Official release packages include the expected installation XML. JSON exports are labeled as local helper artifacts only.
- No generated cache, local report, `.env`, secret key, debug output, or machine-specific path is included in the package.

## Verification Checklist

- PHP: run `php -l` on changed PHP files. If `php` is not on `PATH`, locate and invoke the local PHP executable directly.
- Architecture: inspect changed custom files for responsibility boundaries and length. A file approaching 300-400 lines or mixing routing, validation, persistence, rendering, and styling should be split before approval; a file over roughly 500 lines needs an explicit reason or refactor plan.
- Admin pages: test form loading, submission, validation, select/radio options, success/error `cpmsg`, and permission guards.
- `showsetting(..., 'select')`: verify options are two-column rows, not associative maps, to avoid PHP 8 `array_key_exists()` type failures in Discuz admin helpers.
- Templates: verify source templates, cache impact, and rendered pages. Do not treat `data/template/` edits as source fixes.
- CSS/JS: run available lint/build/test. If no automation exists, perform browser QA on target desktop/mobile views.
- Media/storage: confirm provider credentials stay server-side and frontend receives only safe URLs or signed/limited metadata.
- Database lifecycle: install is repeatable where practical, upgrade preserves existing rows, and uninstall only drops plugin-owned tables.
- Git hygiene: run `git diff --check`; stage only files belonging to the current change intent.

## Common Mistakes

- Editing `data/template/` instead of the source template.
- Letting `admincp.inc.php` become a giant page renderer instead of a dispatcher.
- Putting routing, form handling, data access, rendering, CSS, and JavaScript into one long plugin file.
- Passing associative arrays to Discuz admin `select` fields.
- Losing `0` sentinel values such as "未分配" because edit forms rebuild option lists by hand.
- Hiding plugin business rules in theme templates.
- Shipping UI changes without a real browser screenshot.
- Publishing local JSON metadata as if it were the official application-center plugin installation XML.
- Exposing storage bucket credentials or upload secrets in frontend code.
