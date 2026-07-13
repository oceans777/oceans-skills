#!/bin/sh
set -eu

SKIP_VERIFY=0

usage() {
  cat <<'EOF'
Usage: sh scripts/agent-bootstrap.sh [--skip-verify]
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --skip-verify) SKIP_VERIFY=1 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

repo_root=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "$repo_root" ]; then
  echo 'Not inside a git repository.' >&2
  exit 1
fi

cd "$repo_root"

for path in .githooks/pre-commit .githooks/commit-msg scripts/agent-verify.sh scripts/agent-standards-hook.sh scripts/dedupe-agent-docs.sh; do
  if [ ! -f "$path" ]; then
    echo "Required agent workflow file not found: $path" >&2
    exit 1
  fi
done

git config core.hooksPath .githooks
hooks_path=$(git config --get core.hooksPath)
if [ "$hooks_path" != '.githooks' ]; then
  echo "Unexpected core.hooksPath after bootstrap: $hooks_path" >&2
  exit 1
fi

printf '[OK] Git hooks path configured: .githooks\n'

if [ "$SKIP_VERIFY" -eq 0 ]; then
  sh scripts/agent-verify.sh
fi

printf '[OK] Agent bootstrap completed\n'
