# 分支工作流

## 基线

- 基线分支：`{{BASE_BRANCH}}`
- 开发分支：`{{DEV_BRANCH}}`
- 任务分支前缀：`{{TASK_PREFIX}}/`
- linked worktree 目录：`{{WORKTREE_DIR}}`
- 默认远程推送目标：`origin/{{DEV_BRANCH}}`

## 开始任务

```sh
git switch {{DEV_BRANCH}}
git pull --ff-only origin {{DEV_BRANCH}}
git worktree add {{WORKTREE_DIR}}/<task-name> -b {{TASK_PREFIX}}/<task-name> {{DEV_BRANCH}}
cd {{WORKTREE_DIR}}/<task-name>
```

进入 worktree 后，重新读取该 worktree 内的 `AGENTS.md`，再运行项目 worktree/bootstrap 初始化脚本。

## 工作中

- 保持一个 worktree 只处理一个变更意图。
- 只暂存当前任务拥有的文件。
- 提交前运行匹配验证命令，例如 `scripts/agent-verify.sh`、`scripts/agent-verify.ps1`、包管理器脚本或语言测试命令。
- 如果发现无关问题，记录并说明，不顺手扩散重构。

## 完成任务

```sh
<运行匹配验证命令>
git add -- <task-files>
git commit -m "fix(scope): 中文提交说明"
git push -u origin {{TASK_PREFIX}}/<task-name>
```

## 合回开发分支

```sh
git switch {{DEV_BRANCH}}
git pull --ff-only origin {{DEV_BRANCH}}
git merge --no-ff -m "chore: 合并 <task-name>" {{TASK_PREFIX}}/<task-name>
git push origin {{DEV_BRANCH}}
```

## 禁止事项

- 不直接向 `{{BASE_BRANCH}}` 提交开发改动。
- 不强制推送。
- 不夹带无关文件。
- 不覆盖用户已有未提交改动。
- 不在未验证时声称完成。
