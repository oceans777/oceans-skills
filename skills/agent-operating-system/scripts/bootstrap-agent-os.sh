#!/bin/sh
set -eu

PROJECT_ROOT=$(pwd)
BASELINE_BRANCH=dev
TASK_PREFIX=codex
WORKTREE_DIR=.worktrees
ENABLE_HOOKS=0
USE_LOCAL_WORKTREES=0
REQUIRE_CLAUDE=0

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
SKILL_DIR=$(CDPATH= cd "$SCRIPT_DIR/.." && pwd)
ASSETS_DIR=$SKILL_DIR/assets

usage() {
  cat <<EOF
Usage: bootstrap-agent-os.sh [options]

Options:
  --project-root <path>       Repository path. Defaults to current directory.
  --baseline-branch <name>    Baseline branch. Defaults to dev.
  --task-prefix <prefix>      Task branch prefix. Defaults to codex.
  --worktree-dir <path>       Local worktree directory. Defaults to .worktrees.
  --enable-hooks              Set git core.hooksPath=.githooks.
  --use-local-worktrees       Create and ignore the worktree directory.
  --require-claude            Create and require CLAUDE.md.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --project-root)
      [ "$#" -ge 2 ] || { echo '--project-root needs a path.' >&2; exit 2; }
      PROJECT_ROOT=$2
      shift 2
      ;;
    --baseline-branch)
      [ "$#" -ge 2 ] || { echo '--baseline-branch needs a value.' >&2; exit 2; }
      BASELINE_BRANCH=$2
      shift 2
      ;;
    --task-prefix)
      [ "$#" -ge 2 ] || { echo '--task-prefix needs a value.' >&2; exit 2; }
      TASK_PREFIX=$2
      shift 2
      ;;
    --worktree-dir)
      [ "$#" -ge 2 ] || { echo '--worktree-dir needs a path.' >&2; exit 2; }
      WORKTREE_DIR=$2
      shift 2
      ;;
    --enable-hooks)
      ENABLE_HOOKS=1
      shift
      ;;
    --use-local-worktrees)
      USE_LOCAL_WORKTREES=1
      shift
      ;;
    --require-claude)
      REQUIRE_CLAUDE=1
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

created() {
  printf '[CREATE] %s\n' "$*"
}

exists() {
  printf '[EXISTS] %s\n' "$*"
}

info() {
  printf '[INFO] %s\n' "$*"
}

repo_root=$(git -C "$PROJECT_ROOT" rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "$repo_root" ]; then
  echo "Project root is not inside a git repository: $PROJECT_ROOT" >&2
  exit 1
fi

cd "$repo_root"
info "Bootstrapping agent OS in $repo_root"

ensure_dir() {
  path=$1
  if [ -d "$path" ]; then
    exists "$path"
  else
    mkdir -p "$path"
    created "$path"
  fi
}

render_template() {
  template=$1
  target=$2
  awk \
    -v baseline="$BASELINE_BRANCH" \
    -v task_prefix="$TASK_PREFIX" \
    -v worktree_dir="$WORKTREE_DIR" \
    -v require_claude="$REQUIRE_CLAUDE" '
      {
        gsub(/\{\{BASE_BRANCH\}\}/, baseline)
        gsub(/\{\{TASK_PREFIX\}\}/, task_prefix)
        gsub(/\{\{WORKTREE_DIR\}\}/, worktree_dir)
        gsub(/\{\{REQUIRE_CLAUDE_MD\}\}/, require_claude)
        print
      }
    ' "$template" > "$target"
}

copy_template_if_missing() {
  template_name=$1
  target=$2
  template=$ASSETS_DIR/$template_name

  if [ ! -f "$template" ]; then
    echo "Template missing: $template" >&2
    exit 1
  fi

  if [ -e "$target" ]; then
    exists "$target"
    return
  fi

  parent=$(dirname "$target")
  ensure_dir "$parent"
  render_template "$template" "$target"
  created "$target"
}

copy_file_if_missing() {
  source=$1
  target=$2

  if [ ! -f "$source" ]; then
    echo "Source file missing: $source" >&2
    exit 1
  fi

  if [ -e "$target" ]; then
    exists "$target"
    return
  fi

  parent=$(dirname "$target")
  ensure_dir "$parent"
  cp "$source" "$target"
  created "$target"
}

append_line_if_missing() {
  path=$1
  line=$2
  if [ -f "$path" ] && grep -Fxq "$line" "$path"; then
    exists "$path contains '$line'"
    return
  fi
  printf '%s\n' "$line" >> "$path"
  info "Appended '$line' to $path"
}

ensure_dir docs
ensure_dir docs/agent
ensure_dir scripts
ensure_dir .githooks
ensure_dir .oceans
ensure_dir .oceans/templates

copy_template_if_missing AGENTS.template.md AGENTS.md
if [ "$REQUIRE_CLAUDE" -eq 1 ]; then
  copy_template_if_missing CLAUDE.template.md CLAUDE.md
fi
copy_template_if_missing AGENTS.template.md .oceans/templates/AGENTS.template.md
copy_template_if_missing CLAUDE.template.md .oceans/templates/CLAUDE.template.md
copy_template_if_missing branch-workflow.template.md docs/agent/branch-workflow.md
copy_template_if_missing project-reference.template.md docs/agent/project-reference.md
copy_template_if_missing agent-bootstrap.template.ps1 scripts/agent-bootstrap.ps1
copy_template_if_missing agent-verify.template.ps1 scripts/agent-verify.ps1
copy_template_if_missing agent-verify.template.sh scripts/agent-verify.sh
copy_file_if_missing "$SCRIPT_DIR/agent-standards-hook.sh" scripts/agent-standards-hook.sh
copy_file_if_missing "$SCRIPT_DIR/dedupe-agent-docs.sh" scripts/dedupe-agent-docs.sh
copy_template_if_missing agent-standards.conf.template .oceans/agent-standards.conf
copy_template_if_missing pre-commit.template .githooks/pre-commit
copy_template_if_missing commit-msg.template .githooks/commit-msg

chmod +x scripts/agent-verify.sh scripts/agent-standards-hook.sh scripts/dedupe-agent-docs.sh .githooks/pre-commit .githooks/commit-msg
append_line_if_missing .gitattributes '.githooks/* text eol=lf'
append_line_if_missing .gitattributes 'scripts/*.sh text eol=lf'

if [ "$USE_LOCAL_WORKTREES" -eq 1 ]; then
  append_line_if_missing .gitignore "$WORKTREE_DIR/"
  ensure_dir "$WORKTREE_DIR"
fi

if [ "$ENABLE_HOOKS" -eq 1 ]; then
  git config core.hooksPath .githooks
  info 'Configured git core.hooksPath=.githooks'
else
  info 'Hooks scaffolded but not enabled. Run: git config core.hooksPath .githooks'
fi

info 'Bootstrap complete. Review existing files before migrating content.'
