#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
HOOK_NAME=${1:-pre-commit}
if [ "$#" -gt 0 ]; then
  shift
fi

failures=0

info() { printf '[INFO] %s\n' "$*"; }
pass() { printf '[OK] %s\n' "$*"; }
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

  if [ -n "$value" ]; then printf '%s\n' "$value"; else printf '%s\n' "$default_value"; fi
}

is_enabled() {
  case "$1" in 1|true|yes|on) return 0 ;; *) return 1 ;; esac
}

repo_root=$(git rev-parse --show-toplevel 2>/dev/null || true)
[ -n "$repo_root" ] || exit 0
cd "$repo_root"

config_file=$repo_root/.oceans/agent-standards.conf
require_agents=$(config_value "$config_file" require_agents_md 1)
require_claude=$(config_value "$config_file" require_claude_md 0)
commit_message_policy=$(config_value "$config_file" commit_message conventional)

is_tracked_or_staged() {
  path=$1
  git ls-files --error-unmatch "$path" >/dev/null 2>&1 && return 0
  git diff --cached --name-only -- "$path" | grep -q .
}

check_doc() {
  path=$1
  required=$2

  is_enabled "$required" || return 0

  if [ ! -f "$path" ]; then
    fail "$path 缺失。请显式运行 agent-operating-system bootstrap，审查生成内容后再提交。"
    return
  fi

  if ! is_tracked_or_staged "$path"; then
    fail "$path 已存在，但未被 Git 跟踪或暂存。请加入仓库，或在 .oceans/agent-standards.conf 中关闭该要求。"
  fi
}

check_commit_message() {
  message_file=$1

  case "$commit_message_policy" in off|none) return ;; esac
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
  diff_report=$(mktemp "${TMPDIR:-/tmp}/oceans-agent-diff-check.XXXXXX") || {
    fail '无法创建安全的临时检查文件。'
    return
  }

  if git diff --check --cached >"$diff_report" 2>&1; then
    rm -f "$diff_report"
    pass 'git diff --check'
    return
  fi

  diff_output=$(cat "$diff_report")
  rm -f "$diff_report"
  fail "git diff --check failed:
$diff_output"
}

case "$HOOK_NAME" in
  pre-commit)
    info "Agent 标准守卫：$repo_root"
    check_doc AGENTS.md "$require_agents"
    check_doc CLAUDE.md "$require_claude"
    check_diff_whitespace
    ;;
  commit-msg)
    if [ "$#" -lt 1 ]; then fail 'commit-msg hook requires a message file path.'; else check_commit_message "$1"; fi
    ;;
  pre-push)
    info 'Agent 标准守卫：pre-push 当前没有强制检查。'
    ;;
  *) fail "未知 hook 名称：$HOOK_NAME" ;;
esac

if [ "$failures" -gt 0 ]; then
  cat >&2 <<'EOF'

Agent 标准守卫已拦截本次 Git 操作。

守卫只读取仓库状态并执行确定性检查；它不会创建或修改项目文件，也不会打开编辑器。
请显式运行 agent-operating-system bootstrap 或手动修复上述问题后重试。
EOF
  exit 1
fi

pass 'agent 标准守卫通过'
