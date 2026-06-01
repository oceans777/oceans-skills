#!/bin/sh
set -eu

COMMIT_MESSAGE_FILE=
ALLOW_BASELINE_BRANCH=0
ALLOW_RISKY_FILES=0
BASELINE_BRANCH='{{BASE_BRANCH}}'
TASK_PREFIX='{{TASK_PREFIX}}'
failures=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --commit-msg)
      [ "$#" -ge 2 ] || { echo '--commit-msg 需要一个文件路径。' >&2; exit 2; }
      COMMIT_MESSAGE_FILE=$2
      shift 2
      ;;
    --allow-baseline-branch)
      ALLOW_BASELINE_BRANCH=1
      shift
      ;;
    --allow-dev-branch)
      ALLOW_BASELINE_BRANCH=1
      shift
      ;;
    --allow-risky-files)
      ALLOW_RISKY_FILES=1
      shift
      ;;
    *)
      echo "未知选项：$1" >&2
      exit 2
      ;;
  esac
done

fail() {
  printf '[FAIL] %s\n' "$*" >&2
  failures=$((failures + 1))
}

pass() {
  printf '[OK] %s\n' "$*"
}

info() {
  printf '[INFO] %s\n' "$*"
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

is_tracked_or_staged() {
  path=$1
  git ls-files --error-unmatch "$path" >/dev/null 2>&1 && return 0
  git diff --cached --name-only -- "$path" | grep -q . && return 0
  return 1
}

check_required_doc() {
  path=$1
  required=$2

  if ! is_enabled "$required"; then
    return
  fi

  if [ ! -f "$path" ]; then
    fail "缺少 ${path}。请运行 agent-operating-system bootstrap，或安装 agent 标准 hook。"
  elif ! is_tracked_or_staged "$path"; then
    fail "${path} 已存在，但未被 Git 跟踪或暂存。"
  else
    pass "${path} 存在"
  fi
}

repo_root=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "$repo_root" ]; then
  echo '当前目录不在 Git 仓库中。' >&2
  exit 1
fi
cd "$repo_root"

config_file=.oceans/agent-standards.conf
BASELINE_BRANCH=$(config_value "$config_file" baseline_branch "$BASELINE_BRANCH")
TASK_PREFIX=$(config_value "$config_file" task_prefix "$TASK_PREFIX")
REQUIRE_AGENTS=$(config_value "$config_file" require_agents_md 1)
REQUIRE_CLAUDE=$(config_value "$config_file" require_claude_md 0)
COMMIT_MESSAGE_POLICY=$(config_value "$config_file" commit_message conventional)

info "仓库：$repo_root"

branch=$(git branch --show-current)
git_dir=$(git rev-parse --git-dir)
if [ -f "$git_dir/MERGE_HEAD" ]; then
  merge_in_progress=1
else
  merge_in_progress=0
fi

if [ -z "$branch" ]; then
  fail '常规 agent 工作不允许处于 detached HEAD 状态。'
elif [ "$branch" = "$BASELINE_BRANCH" ] && [ "$ALLOW_BASELINE_BRANCH" -ne 1 ] && [ "$merge_in_progress" -ne 1 ]; then
  fail "当前位于 $BASELINE_BRANCH。请使用 $TASK_PREFIX/<task-name> 分支，或在明确合并时传入 --allow-dev-branch。"
elif [ "$branch" != "$BASELINE_BRANCH" ]; then
  case "$branch" in
    "$TASK_PREFIX"/*) pass "分支规则：$branch" ;;
    *) fail "分支 '$branch' 不符合预期。应为 $TASK_PREFIX/<task-name> 或 $BASELINE_BRANCH。" ;;
  esac
else
  pass "分支规则：$branch"
fi

staged_files=$(git diff --cached --name-only --diff-filter=ACMRD)
if [ -z "$staged_files" ]; then
  info '没有暂存文件。将对工作区 diff 运行空白字符检查。'
  if git diff --check; then
    pass 'git diff --check'
  else
    fail 'git diff --check failed.'
  fi
else
  count=$(printf '%s\n' "$staged_files" | sed '/^$/d' | wc -l | tr -d ' ')
  pass "暂存文件数量：$count"
  if git diff --check --cached; then
    pass 'git diff --check --cached'
  else
    fail 'git diff --check --cached failed.'
  fi
fi

if [ "$ALLOW_RISKY_FILES" -ne 1 ] && [ -n "$staged_files" ]; then
  risky=$(printf '%s\n' "$staged_files" | grep -E '(^|/)\.env($|[./])|\.(pem|key|p12|pfx)$|\.(zip|7z|rar)$|(^|/)data/(cache|template|attachment)/|\.log$' || true)
  if [ -n "$risky" ]; then
    fail "暂存区存在高风险文件，需要明确审查：
$risky"
  else
    pass '没有高风险暂存文件'
  fi
fi

check_required_doc AGENTS.md "$REQUIRE_AGENTS"
check_required_doc CLAUDE.md "$REQUIRE_CLAUDE"

if [ -n "$COMMIT_MESSAGE_FILE" ] &&
   [ "$COMMIT_MESSAGE_POLICY" != off ] &&
   [ "$COMMIT_MESSAGE_POLICY" != none ]; then
  if [ ! -f "$COMMIT_MESSAGE_FILE" ]; then
    fail "找不到提交说明文件：$COMMIT_MESSAGE_FILE"
  else
    first_line=$(sed -n '1p' "$COMMIT_MESSAGE_FILE")
    if printf '%s\n' "$first_line" | grep -Eq '^(feat|fix|docs|style|refactor|perf|test|chore)(\([A-Za-z0-9._-]+\))?: .+'; then
      pass '提交说明格式'
    else
      fail "提交说明必须使用 '<type>: <title>' 或 '<type>(scope): <title>'。当前为：$first_line"
    fi
  fi
fi

if [ "$failures" -gt 0 ]; then
  exit 1
fi

pass 'agent 验证通过'
