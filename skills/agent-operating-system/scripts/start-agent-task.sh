#!/bin/sh
set -eu

PROJECT_ROOT=$(pwd)
TASK_NAME=
BASELINE_BRANCH=
TASK_PREFIX=codex
WORKTREE_DIR=.worktrees
BRANCH_NAME=
VERIFICATION_COMMAND=
NO_FETCH=0
ENSURE_IGNORE=0

usage() {
  cat <<'EOF'
Usage: start-agent-task.sh --task-name <name> [options]

Options:
  --project-root <path>         Repository path. Defaults to current directory.
  --baseline-branch <name>      Task source branch. Defaults to current branch.
  --task-prefix <prefix>        Task branch prefix. Defaults to codex.
  --worktree-dir <path>         Worktree root. Defaults to .worktrees.
  --branch-name <name>          Explicit branch name.
  --verification-command <cmd>  Command to print in the next-step summary.
  --no-fetch                    Use local refs without fetching origin.
  --ensure-ignore               Add a relative worktree root to .gitignore.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --project-root) [ "$#" -ge 2 ] || exit 2; PROJECT_ROOT=$2; shift 2 ;;
    --task-name) [ "$#" -ge 2 ] || exit 2; TASK_NAME=$2; shift 2 ;;
    --baseline-branch) [ "$#" -ge 2 ] || exit 2; BASELINE_BRANCH=$2; shift 2 ;;
    --task-prefix) [ "$#" -ge 2 ] || exit 2; TASK_PREFIX=$2; shift 2 ;;
    --worktree-dir) [ "$#" -ge 2 ] || exit 2; WORKTREE_DIR=$2; shift 2 ;;
    --branch-name) [ "$#" -ge 2 ] || exit 2; BRANCH_NAME=$2; shift 2 ;;
    --verification-command) [ "$#" -ge 2 ] || exit 2; VERIFICATION_COMMAND=$2; shift 2 ;;
    --no-fetch) NO_FETCH=1; shift ;;
    --ensure-ignore) ENSURE_IGNORE=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [ -z "$TASK_NAME" ]; then
  echo '--task-name is required.' >&2
  usage >&2
  exit 2
fi

repo_root=$(git -C "$PROJECT_ROOT" rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "$repo_root" ]; then
  echo "Project root is not inside a git repository: $PROJECT_ROOT" >&2
  exit 1
fi
cd "$repo_root"

if [ -z "$BASELINE_BRANCH" ]; then
  BASELINE_BRANCH=$(git branch --show-current 2>/dev/null || true)
fi
if [ -z "$BASELINE_BRANCH" ]; then
  echo 'Could not detect a task source branch. Pass --baseline-branch.' >&2
  exit 1
fi

slug=$(printf '%s' "$TASK_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9][^a-z0-9]*/-/g; s/^-//; s/-$//' | cut -c1-48 | sed 's/-$//')
if [ -z "$slug" ]; then
  slug=task-$(date +%Y%m%d-%H%M%S)
fi
if [ -z "$BRANCH_NAME" ]; then
  BRANCH_NAME=$TASK_PREFIX/$slug
fi

if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
  echo "Branch already exists: $BRANCH_NAME" >&2
  exit 1
fi

has_origin=0
if git remote | grep -Fxq origin; then
  has_origin=1
fi

baseline_ref=$BASELINE_BRANCH
if [ "$has_origin" -eq 1 ] && [ "$NO_FETCH" -eq 0 ]; then
  printf '[INFO] Fetching origin/%s\n' "$BASELINE_BRANCH"
  if ! git fetch origin "$BASELINE_BRANCH"; then
    echo "Failed to fetch origin/$BASELINE_BRANCH. Fix origin access or pass --no-fetch intentionally." >&2
    exit 1
  fi
  if git ls-remote --exit-code --heads origin "$BRANCH_NAME" >/dev/null 2>&1; then
    echo "Remote branch already exists: origin/$BRANCH_NAME" >&2
    exit 1
  else
    remote_status=$?
    if [ "$remote_status" -ne 2 ]; then
      echo "Could not check whether origin/$BRANCH_NAME already exists." >&2
      exit 1
    fi
  fi
  baseline_ref=$(git rev-parse FETCH_HEAD)
elif ! git rev-parse --verify --quiet "$BASELINE_BRANCH^{commit}" >/dev/null; then
  if [ "$NO_FETCH" -eq 1 ] && git rev-parse --verify --quiet "origin/$BASELINE_BRANCH^{commit}" >/dev/null; then
    baseline_ref=origin/$BASELINE_BRANCH
  else
    echo "Baseline branch not found locally or at origin: $BASELINE_BRANCH" >&2
    exit 1
  fi
fi

case "$WORKTREE_DIR" in
  /*) worktree_root=$WORKTREE_DIR; relative_worktree=0 ;;
  *) worktree_root=$repo_root/$WORKTREE_DIR; relative_worktree=1 ;;
esac

if [ "$ENSURE_IGNORE" -eq 1 ] && [ "$relative_worktree" -eq 1 ]; then
  ignore_line=${WORKTREE_DIR%/}/
  if [ ! -f .gitignore ] || ! grep -Fxq "$ignore_line" .gitignore; then
    printf '%s\n' "$ignore_line" >> .gitignore
  fi
fi

mkdir -p "$worktree_root"
worktree_path=$worktree_root/$slug
if [ -e "$worktree_path" ]; then
  echo "Worktree path already exists: $worktree_path" >&2
  exit 1
fi

printf '[INFO] Creating branch %s from %s\n' "$BRANCH_NAME" "$baseline_ref"
git worktree add -b "$BRANCH_NAME" "$worktree_path" "$baseline_ref"

printf '[READY] Task worktree created\n'
printf 'Task: %s\nBranch: %s\nBaseline: %s\nWorktree: %s\n' "$TASK_NAME" "$BRANCH_NAME" "$baseline_ref" "$worktree_path"
if [ -n "$VERIFICATION_COMMAND" ]; then
  printf 'Verification: %s\n' "$VERIFICATION_COMMAND"
fi
printf '\nNext steps:\n  cd %s\n  implement only this task\n  stage only task-owned files\n  verify, commit, and share only as authorized\n' "$worktree_path"
