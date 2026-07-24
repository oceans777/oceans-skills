#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd "$(dirname "$0")/.." && pwd)
SKILL_ROOT=$REPO_ROOT/skills/discuz-x5
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/oceans-discuz-test.XXXXXX")
cleanup() { rm -rf "$TEST_ROOT"; }
trap cleanup EXIT INT TERM

PROJECT=$TEST_ROOT/project
git init -b main "$PROJECT" >/dev/null
git -C "$PROJECT" config user.name 'Discuz Test'
git -C "$PROJECT" config user.email 'discuz-test@example.invalid'
mkdir -p "$PROJECT/source/plugin/demo/tests" "$PROJECT/scripts" "$PROJECT/tools"
printf '%s\n' '# test' > "$PROJECT/README.md"
cp "$SKILL_ROOT/assets/agent-verify.template.sh" "$PROJECT/scripts/discuz-x5-verify.sh"
chmod +x "$PROJECT/scripts/discuz-x5-verify.sh"

cat > "$PROJECT/tools/fake-php" <<'FAKE'
#!/bin/sh
if [ "${1:-}" = -l ]; then
  grep -q BROKEN "$2" && exit 1
  exit 0
fi
case "${1:-}" in *_test.php) : > "${TEST_MARKER:?}" ;; esac
FAKE
chmod +x "$PROJECT/tools/fake-php"
cat > "$PROJECT/tools/fake-node" <<'FAKE'
#!/bin/sh
[ "${1:-}" = --check ] || exit 0
grep -q BROKEN "$2" && exit 1
FAKE
chmod +x "$PROJECT/tools/fake-node"

cat > "$PROJECT/.discuz-x5-skill.conf" <<EOF2
schema_version=1
discuz_root=.
plugin_roots=source/plugin
template_roots=template
generated_roots=data/cache,data/template,data/attachment
php_command=$PROJECT/tools/fake-php
node_command=$PROJECT/tools/fake-node
run_related_tests=1
EOF2

printf '%s\n' '<?php echo "BROKEN";' > "$PROJECT/source/plugin/demo/example.php"
printf '%s\n' '<?php exit(0);' > "$PROJECT/source/plugin/demo/tests/demo_test.php"
if (cd "$PROJECT" && TEST_MARKER="$PROJECT/test-marker" sh scripts/discuz-x5-verify.sh >/dev/null 2>&1); then
  echo 'Expected unstaged invalid PHP to fail.' >&2
  exit 1
fi

printf '%s\n' '<?php echo "ok";' > "$PROJECT/source/plugin/demo/example.php"
(cd "$PROJECT" && TEST_MARKER="$PROJECT/test-marker" sh scripts/discuz-x5-verify.sh >/dev/null)
test -f "$PROJECT/test-marker"

mkdir -p "$PROJECT/data/cache"
printf '%s\n' generated > "$PROJECT/data/cache/cache_demo.php"
if (cd "$PROJECT" && TEST_MARKER="$PROJECT/test-marker" sh scripts/discuz-x5-verify.sh >/dev/null 2>&1); then
  echo 'Expected generated runtime file to fail.' >&2
  exit 1
fi

grep -q 'discuz_root' "$SKILL_ROOT/assets/discuz-x5.conf.template"
! grep -Eqi 'phpstudy|Discuz_X5\.0_|codex/|branch --show-current' "$SKILL_ROOT/assets/agent-verify.template.sh"
printf 'Discuz X5 Shell tests passed.\n'
