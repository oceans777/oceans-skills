#!/bin/sh
set -eu

CONFIG_FILE=.discuz-x5-skill.conf
ALLOW_RISKY=0

usage() {
  cat <<'USAGE'
Usage: agent-verify.sh [--config <path>] [--allow-risky-files]
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --config) [ "$#" -ge 2 ] || exit 2; CONFIG_FILE=$2; shift 2 ;;
    --allow-risky-files) ALLOW_RISKY=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

failures=0
info() { printf '[INFO] %s\n' "$*"; }
pass() { printf '[OK] %s\n' "$*"; }
fail() { printf '[FAIL] %s\n' "$*" >&2; failures=$((failures + 1)); }

repo_root=$(git rev-parse --show-toplevel 2>/dev/null || true)
[ -n "$repo_root" ] || { echo 'Not inside a git repository.' >&2; exit 1; }
cd "$repo_root"

config_value() {
  key=$1
  default_value=$2
  if [ ! -f "$CONFIG_FILE" ]; then printf '%s\n' "$default_value"; return; fi
  value=$(awk -F= -v key="$key" '
    /^[[:space:]]*#/ { next }
    {
      k=$1; sub(/^[[:space:]]+/,"",k); sub(/[[:space:]]+$/,"",k)
      if (k==key) { v=$0; sub(/^[^=]*=/,"",v); sub(/^[[:space:]]+/,"",v); sub(/[[:space:]]+$/,"",v); print v; exit }
    }
  ' "$CONFIG_FILE")
  if [ -n "$value" ]; then printf '%s\n' "$value"; else printf '%s\n' "$default_value"; fi
}

schema_version=$(config_value schema_version 1)
[ "$schema_version" = 1 ] || { echo "Unsupported schema_version: $schema_version" >&2; exit 1; }
discuz_root=$(config_value discuz_root .)
[ "$discuz_root" = . ] && discuz_root=
plugin_roots=$(config_value plugin_roots source/plugin)
template_roots=$(config_value template_roots template)
generated_roots=$(config_value generated_roots data/cache,data/template,data/attachment)
php_command=$(config_value php_command php)
node_command=$(config_value node_command node)
run_related_tests=$(config_value run_related_tests 1)

case "$discuz_root" in /*|*../*|../*|*/..) echo 'discuz_root must be repository-relative and contained in the repository.' >&2; exit 1 ;; esac
info "Discuz root: ${discuz_root:-.}"

status_file=$(mktemp "${TMPDIR:-/tmp}/discuz-x5-status.XXXXXX")
files_file=$(mktemp "${TMPDIR:-/tmp}/discuz-x5-files.XXXXXX")
tests_file=$(mktemp "${TMPDIR:-/tmp}/discuz-x5-tests.XXXXXX")
cleanup() { rm -f "$status_file" "$files_file" "$tests_file"; }
trap cleanup EXIT INT TERM

if git diff --cached --quiet --; then
  git status --porcelain=v1 -uall > "$status_file"
  awk 'length($0)>=4 { status=substr($0,1,2); path=substr($0,4); if (index(path," -> ")) { n=split(path,a," -> "); path=a[n] } print status "\t" path }' "$status_file" > "$files_file"
  diff_args=''
else
  git diff --cached --name-status --diff-filter=ACMRD > "$files_file"
  diff_args='--cached'
fi

if [ -n "$diff_args" ]; then
  if git diff --check --cached; then pass 'git diff --check'; else fail 'git diff --check failed.'; fi
else
  if git diff --check; then pass 'git diff --check'; else fail 'git diff --check failed.'; fi
fi

command_exists() { command -v "$1" >/dev/null 2>&1 || [ -x "$1" ]; }
path_under_list() {
  path=$1
  list=$2
  old_ifs=$IFS; IFS=,
  for item in $list; do
    item=$(printf '%s' "$item" | sed 's#^\./##; s#/$##')
    [ -n "$item" ] || continue
    prefixed=${discuz_root:+$discuz_root/}$item
    case "$path" in "$prefixed"|"$prefixed"/*) IFS=$old_ifs; return 0 ;; esac
  done
  IFS=$old_ifs
  return 1
}

collect_related_tests() {
  path=$1
  old_ifs=$IFS; IFS=,
  for root in $plugin_roots; do
    root=$(printf '%s' "$root" | sed 's#^\./##; s#/$##')
    prefix=${discuz_root:+$discuz_root/}$root/
    case "$path" in
      "$prefix"*)
        rest=${path#"$prefix"}
        plugin=${rest%%/*}
        test_dir=$prefix$plugin/tests
        if [ -d "$test_dir" ]; then
          find "$test_dir" -maxdepth 1 -type f \( -name '*_test.php' -o -name '*_js_behavior_test.js' \) -print >> "$tests_file"
        fi
        ;;
    esac
  done
  IFS=$old_ifs
}

while IFS="$(printf '\t')" read -r status path; do
  [ -n "$path" ] || continue
  normalized=$(printf '%s' "$path" | sed 's#\\#/#g; s#^\./##')
  short_status=$(printf '%s' "$status" | tr -d ' ')

  if path_under_list "$normalized" "$generated_roots" && [ "$short_status" != D ]; then
    fail "Generated runtime path must not be maintained as source: $normalized"
  fi

  if [ "$ALLOW_RISKY" -ne 1 ]; then
    case "$normalized" in
      .env|.env.*|*/.env|*/.env.*|*.pem|*.key|*.p12|*.pfx|*.zip|*.7z|*.rar|*.log)
        fail "Risky file requires explicit review: $normalized" ;;
    esac
  fi

  [ "$short_status" = D ] && continue
  [ -f "$normalized" ] || continue
  case "$normalized" in
    *.php)
      if ! command_exists "$php_command"; then fail "PHP command not found: $php_command"; else "$php_command" -l "$normalized" >/dev/null || fail "PHP syntax failed: $normalized"; fi
      collect_related_tests "$normalized"
      ;;
    *.js)
      if ! command_exists "$node_command"; then fail "Node command not found: $node_command"; else "$node_command" --check "$normalized" >/dev/null || fail "JavaScript syntax failed: $normalized"; fi
      collect_related_tests "$normalized"
      ;;
  esac
done < "$files_file"

if [ "$run_related_tests" = 1 ] && [ -s "$tests_file" ]; then
  sort -u "$tests_file" | while IFS= read -r test_file; do
    case "$test_file" in
      *.php) "$php_command" "$test_file" || exit 91 ;;
      *.js) "$node_command" "$test_file" || exit 92 ;;
    esac
  done || fail 'A related behavior test failed.'
fi

[ "$failures" -eq 0 ] || exit 1
pass 'Discuz X5 verification passed'
