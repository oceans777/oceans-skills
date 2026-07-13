#!/bin/sh
set -eu

REPO_ROOT=$(CDPATH= cd "$(dirname "$0")/.." && pwd)
AOS_ROOT=$REPO_ROOT/skills/agent-operating-system
TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/oceans-aos-test.XXXXXX")
cleanup() { rm -rf "$TEST_ROOT"; }
trap cleanup EXIT INT TERM

PROJECT=$TEST_ROOT/project
git init -b main "$PROJECT" >/dev/null
git -C "$PROJECT" config user.name 'AOS Test'
git -C "$PROJECT" config user.email 'aos-test@example.invalid'
printf '%s\n' '# test' > "$PROJECT/README.md"
git -C "$PROJECT" add README.md
git -C "$PROJECT" commit -m 'test: initialize' >/dev/null

if (cd "$PROJECT" && sh "$AOS_ROOT/scripts/agent-standards-hook.sh" pre-commit >/dev/null 2>&1); then
  echo 'Expected missing AGENTS.md to fail.' >&2
  exit 1
fi
test ! -e "$PROJECT/AGENTS.md"

sh "$AOS_ROOT/scripts/bootstrap-agent-os.sh" --project-root "$PROJECT" >/dev/null
git -C "$PROJECT" add AGENTS.md
(cd "$PROJECT" && sh "$AOS_ROOT/scripts/agent-standards-hook.sh" pre-commit >/dev/null)

if sh "$AOS_ROOT/scripts/start-agent-task.sh" --project-root "$PROJECT" --task-name invalid \
  --branch-name 'bad..branch' --ensure-ignore --no-fetch >/dev/null 2>&1; then
  echo 'Expected invalid branch to fail.' >&2
  exit 1
fi
test ! -e "$PROJECT/.gitignore"

if sh "$AOS_ROOT/scripts/start-agent-task.sh" --project-root "$PROJECT" --task-name escaped \
  --branch-name codex/escaped --worktree-dir ../escaped --ensure-ignore --no-fetch >/dev/null 2>&1; then
  echo 'Expected escaped ignore path to fail.' >&2
  exit 1
fi
test ! -e "$PROJECT/.gitignore"

sh "$AOS_ROOT/scripts/start-agent-task.sh" --project-root "$PROJECT" --task-name valid \
  --branch-name codex/valid --worktree-dir .worktrees --ensure-ignore --no-fetch >/dev/null
test -d "$PROJECT/.worktrees/valid"
grep -Fxq '.worktrees/' "$PROJECT/.gitignore"

GLOBAL_HOME=$TEST_ROOT/global-home
mkdir -p "$GLOBAL_HOME"
HOME=$GLOBAL_HOME XDG_CONFIG_HOME=$GLOBAL_HOME/config GIT_CONFIG_GLOBAL=$GLOBAL_HOME/gitconfig \
  sh "$AOS_ROOT/scripts/install-global-hooks.sh" >/dev/null
test -x "$GLOBAL_HOME/config/oceans777/agent-hooks/pre-commit"
test "$(HOME=$GLOBAL_HOME GIT_CONFIG_GLOBAL=$GLOBAL_HOME/gitconfig git config --global --get core.hooksPath)" = \
  "$GLOBAL_HOME/config/oceans777/agent-hooks"

HOOK_PARENT=$GLOBAL_HOME/config/oceans777
mv "$HOOK_PARENT/agent-hooks" "$HOOK_PARENT/.agent-hooks.oceans-backup"
mkdir "$HOOK_PARENT/.agent-hooks.oceans-lock"
printf '%s\n' 99999999 > "$HOOK_PARENT/.agent-hooks.oceans-lock/pid"
HOME=$GLOBAL_HOME XDG_CONFIG_HOME=$GLOBAL_HOME/config GIT_CONFIG_GLOBAL=$GLOBAL_HOME/gitconfig \
  sh "$AOS_ROOT/scripts/install-global-hooks.sh" >/dev/null
test -x "$HOOK_PARENT/agent-hooks/pre-commit"
test ! -e "$HOOK_PARENT/.agent-hooks.oceans-backup"
test ! -e "$HOOK_PARENT/.agent-hooks.oceans-lock"

printf 'Agent operating system Shell tests passed.\n'
