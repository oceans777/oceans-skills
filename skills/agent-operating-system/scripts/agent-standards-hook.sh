#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
SKILL_DIR=$(CDPATH= cd "$SCRIPT_DIR/.." && pwd)
ASSETS_DIR=$SKILL_DIR/assets

HOOK_NAME=${1:-pre-commit}
if [ "$#" -gt 0 ]; then
  shift
fi

failures=0

info() {
  printf '[INFO] %s\n' "$*"
}

pass() {
  printf '[OK] %s\n' "$*"
}

fail() {
  printf '[FAIL] %s\n' "$*" >&2
  failures=$((failures + 1))
}

config_value() {
  file=$1
  key=$2
  default_value=$3

  if [ ! -f "$file" ]; then
    printf '%s\n' "$default_value"
    return
  fi

  value=$(awk -F= -v key="$key" '
    /^[[:space:]]*#/ { next }
    {
      k = $1
      sub(/^[[:space:]]+/, "", k)
      sub(/[[:space:]]+$/, "", k)
      if (k == key) {
        v = $0
        sub(/^[^=]*=/, "", v)
        sub(/^[[:space:]]+/, "", v)
        sub(/[[:space:]]+$/, "", v)
        print v
        exit
      }
    }
  ' "$file")

  if [ -n "$value" ]; then
    printf '%s\n' "$value"
  else
    printf '%s\n' "$default_value"
  fi
}

is_enabled() {
  case "$1" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

repo_root=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "$repo_root" ]; then
  exit 0
fi

cd "$repo_root"

git_dir=$(git rev-parse --git-dir)
state_file=$(git rev-parse --git-path oceans-agent-standards-state)
config_file=$repo_root/.oceans/agent-standards.conf
if [ ! -f "$ASSETS_DIR/AGENTS.template.md" ] &&
   [ -f "$repo_root/.oceans/templates/AGENTS.template.md" ]; then
  ASSETS_DIR=$repo_root/.oceans/templates
fi

require_agents=$(config_value "$config_file" require_agents_md 1)
require_claude=$(config_value "$config_file" require_claude_md 0)
open_on_first_init=$(config_value "$config_file" open_on_first_init 1)
commit_message_policy=$(config_value "$config_file" commit_message conventional)
baseline_branch=$(config_value "$config_file" baseline_branch main)
task_prefix=$(config_value "$config_file" task_prefix codex)
worktree_dir=$(config_value "$config_file" worktree_dir .worktrees)

reviewed=0
if [ -f "$state_file" ] && grep -q '^agent_docs_reviewed=1$' "$state_file"; then
  reviewed=1
fi

open_doc() {
  path=$1
  if ! is_enabled "$open_on_first_init"; then
    return
  fi

  if command -v cursor >/dev/null 2>&1; then
    cursor "$path" >/dev/null 2>&1 || true
  elif command -v code >/dev/null 2>&1; then
    code "$path" >/dev/null 2>&1 || true
  elif [ "$(uname -s 2>/dev/null || printf unknown)" = "Darwin" ]; then
    open "$path" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$path" >/dev/null 2>&1 || true
  fi
}

render_template() {
  template=$1
  target=$2

  awk \
    -v baseline="$baseline_branch" \
    -v task_prefix="$task_prefix" \
    -v worktree_dir="$worktree_dir" '
      {
        gsub(/\{\{BASE_BRANCH\}\}/, baseline)
        gsub(/\{\{TASK_PREFIX\}\}/, task_prefix)
        gsub(/\{\{WORKTREE_DIR\}\}/, worktree_dir)
        print
      }
    ' "$template" > "$target"
}

is_tracked_or_staged() {
  path=$1
  git ls-files --error-unmatch "$path" >/dev/null 2>&1 && return 0
  git diff --cached --name-only -- "$path" | grep -q .
}

mark_reviewed() {
  state_dir=$(dirname "$state_file")
  mkdir -p "$state_dir"
  {
    echo 'agent_docs_reviewed=1'
    echo "repo=$repo_root"
  } > "$state_file"
}

check_doc() {
  path=$1
  template=$2
  required=$3

  if ! is_enabled "$required"; then
    return
  fi

  if [ ! -f "$path" ]; then
    render_template "$template" "$path"
    info "已从 oceans777 模板创建 ${path}。"
    open_doc "$path"
    fail "${path} 已创建；提交前必须先查看、按项目调整，并加入暂存区。"
    return
  fi

  if [ "$reviewed" -ne 1 ]; then
    open_doc "$path"
    info "${path} 已存在，脚本不会覆盖。"
    info "如需去重报告，运行：$SCRIPT_DIR/dedupe-agent-docs.sh --project \"$repo_root\""
    info "如需 AI 结合项目调整规则，请让 Codex 使用 \$agent-operating-system 审查本仓库的 agent 文档。"
    fail "${path} 在本仓库第一次通过标准守卫提交前，必须先查看确认一次。"
  fi

  if ! is_tracked_or_staged "$path"; then
    fail "${path} 已存在，但未被 Git 跟踪或暂存。请加入仓库，或在 .oceans/agent-standards.conf 中关闭该要求。"
  fi
}

check_commit_message() {
  message_file=$1

  if [ "$commit_message_policy" = "off" ] || [ "$commit_message_policy" = "none" ]; then
    return
  fi

  if [ ! -f "$message_file" ]; then
    fail "找不到提交说明文件：$message_file"
    return
  fi

  first_line=$(sed -n '1p' "$message_file")
  if printf '%s\n' "$first_line" | grep -Eq '^(feat|fix|docs|style|refactor|perf|test|chore)(\([A-Za-z0-9._-]+\))?: .+'; then
    pass '提交说明格式'
  else
    fail "提交说明必须使用 '<type>: <title>' 或 '<type>(scope): <title>'。当前为：$first_line"
  fi
}

check_diff_whitespace() {
  if git diff --check --cached >/tmp/oceans-agent-diff-check.$$ 2>&1; then
    rm -f /tmp/oceans-agent-diff-check.$$
    pass 'git diff --check'
    return
  fi

  fail "git diff --check failed:
$(cat /tmp/oceans-agent-diff-check.$$)"
  rm -f /tmp/oceans-agent-diff-check.$$
}

case "$HOOK_NAME" in
  pre-commit)
    info "Agent 标准守卫：$repo_root"
    check_doc AGENTS.md "$ASSETS_DIR/AGENTS.template.md" "$require_agents"
    check_doc CLAUDE.md "$ASSETS_DIR/CLAUDE.template.md" "$require_claude"
    if [ "$reviewed" -ne 1 ]; then
      mark_reviewed
    fi
    check_diff_whitespace
    ;;
  commit-msg)
    if [ "$#" -lt 1 ]; then
      fail 'commit-msg hook requires a message file path.'
    else
      check_commit_message "$1"
    fi
    ;;
  pre-push)
    info "Agent 标准守卫：pre-push 当前没有强制检查。"
    ;;
  *)
    fail "未知 hook 名称：$HOOK_NAME"
    ;;
esac

if [ "$failures" -gt 0 ]; then
  cat >&2 <<EOF

Agent 标准守卫已拦截本次 Git 操作。

这个守卫只做确定性动作：缺少启动文档时从模板创建，首次检查时打开已有文档供查看，
并且绝不会覆盖项目中已经存在的 AGENTS.md 或 CLAUDE.md。

请查看相关文件，按当前项目调整后，把需要提交的文档加入暂存区，然后重新执行 Git 命令。
如需 AI 结合项目给出调整建议，请让 Codex 使用 \$agent-operating-system。
EOF
  exit 1
fi

pass 'agent 标准守卫通过'
