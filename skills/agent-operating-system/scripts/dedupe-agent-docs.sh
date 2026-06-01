#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
SKILL_DIR=$(CDPATH= cd "$SCRIPT_DIR/.." && pwd)
ASSETS_DIR=$SKILL_DIR/assets
PROJECT_ROOT=
GLOBAL_DOC=
APPLY=0

usage() {
  cat <<EOF
Usage: dedupe-agent-docs.sh [--project <repo>] [--global <file>] [--apply]

Reports duplicate bullet rules between a global/template agent doc and the
project AGENTS.md / CLAUDE.md. By default this script reports only; --apply is
reserved and currently refuses to edit so rules are not deleted blindly.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --project)
      [ "$#" -ge 2 ] || { echo '--project needs a path.' >&2; exit 2; }
      PROJECT_ROOT=$2
      shift 2
      ;;
    --global)
      [ "$#" -ge 2 ] || { echo '--global needs a file.' >&2; exit 2; }
      GLOBAL_DOC=$2
      shift 2
      ;;
    --apply)
      APPLY=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ "$APPLY" -eq 1 ]; then
  echo '--apply is intentionally not implemented. Review the report and edit manually or with Codex.' >&2
  exit 2
fi

if [ -z "$PROJECT_ROOT" ]; then
  PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
fi

PROJECT_ROOT=$(CDPATH= cd "$PROJECT_ROOT" && pwd)
DEFAULT_TEMPLATE=$ASSETS_DIR/AGENTS.template.md
if [ ! -f "$DEFAULT_TEMPLATE" ] && [ -f "$PROJECT_ROOT/.oceans/templates/AGENTS.template.md" ]; then
  DEFAULT_TEMPLATE=$PROJECT_ROOT/.oceans/templates/AGENTS.template.md
fi

if [ -z "$GLOBAL_DOC" ]; then
  if [ -n "${CODEX_HOME:-}" ] && [ -f "$CODEX_HOME/AGENTS.md" ]; then
    GLOBAL_DOC=$CODEX_HOME/AGENTS.md
  elif [ -f "$HOME/.codex/AGENTS.md" ]; then
    GLOBAL_DOC=$HOME/.codex/AGENTS.md
  else
    GLOBAL_DOC=$DEFAULT_TEMPLATE
  fi
fi

if [ ! -f "$GLOBAL_DOC" ]; then
  echo "Global/template doc not found: $GLOBAL_DOC" >&2
  exit 1
fi

tmp_global=$(mktemp "${TMPDIR:-/tmp}/oceans-global-rules.XXXXXX")
tmp_project=$(mktemp "${TMPDIR:-/tmp}/oceans-project-rules.XXXXXX")
trap 'rm -f "$tmp_global" "$tmp_project"' EXIT

extract_rules() {
  file=$1
  label=$2
  awk -v label="$label" '
    /^[[:space:]]*[-*][[:space:]]+/ {
      line = $0
      sub(/^[[:space:]]*[-*][[:space:]]+/, "", line)
      gsub(/`/, "", line)
      gsub(/[[:space:]]+/, " ", line)
      sub(/^[[:space:]]+/, "", line)
      sub(/[[:space:]]+$/, "", line)
      normalized = tolower(line)
      if (length(normalized) >= 20) {
        print normalized "\t" label "\t" line
      }
    }
  ' "$file"
}

extract_rules "$GLOBAL_DOC" "global:$GLOBAL_DOC" > "$tmp_global"

for doc in AGENTS.md CLAUDE.md; do
  if [ -f "$PROJECT_ROOT/$doc" ]; then
    extract_rules "$PROJECT_ROOT/$doc" "project:$doc" >> "$tmp_project"
  fi
done

echo "Agent doc dedupe report"
echo
echo "Project: $PROJECT_ROOT"
echo "Global/template source: $GLOBAL_DOC"
echo

if [ ! -s "$tmp_project" ]; then
  echo 'No project AGENTS.md or CLAUDE.md bullet rules found.'
  exit 0
fi

duplicates=$(awk -F '\t' '
  NR == FNR {
    global[$1] = $3
    next
  }
  $1 in global {
    print "- " $3 "\n  Project: " $2 "\n  Also in global/template: " global[$1]
  }
' "$tmp_global" "$tmp_project")

if [ -z "$duplicates" ]; then
  echo 'No exact duplicate bullet rules found.'
  echo
  echo 'Note: semantic duplicates are not removed automatically. Ask Codex to use'
  echo '$agent-operating-system for a judgment-based dedupe review.'
  exit 0
fi

echo 'Exact duplicate bullet rules:'
printf '%s\n' "$duplicates"
echo
echo 'Recommendation: remove duplicates from project docs only when the project'
echo 'line does not add commands, paths, scopes, exceptions, or stricter behavior.'
