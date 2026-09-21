---
name: git-upstream-sync-guard
description: Safely initialize and maintain a forked or secondarily-developed Git repository that must continuously receive upstream updates without mixing custom code into the upstream mirror branch. Use when the user asks to clone/fork/pull a repository for secondary development, set up origin/upstream remotes, create isolated dev/release branches, sync official updates, upgrade from upstream, or diagnose divergence/conflicts between upstream code and local customizations.
---

# Git 上游同步与二开隔离技能

## 目标

在持续二开一个高频更新仓库时，同时满足四件事：

1. 官方上游代码始终有一个可验证的纯净镜像分支。
2. 用户自己的定制代码与上游镜像隔离。
3. 每次同步都可回退、可审计、可停止，不用破坏性命令掩盖问题。
4. 上游更新先进入开发分支并通过项目门禁，再进入生产发布分支。

## 触发场景

在用户表达以下意图时使用本技能：

- “克隆某个仓库到本地，后面还要二开。”
- “Fork 一个项目并持续跟官方更新。”
- “给这个仓库配置 upstream。”
- “同步上游 / 更新官方代码 / 升级上游版本。”
- “官方仓库更新很多，怎么保留自己的改动。”
- “检查我的 main/dev/release 分支是否符合上游同步规范。”

只要用户已经给出仓库地址、本地目录或目标分支，就直接使用已有信息，不重复询问。

## 第一性原则

Git 提交图里必须明确区分两类事实：

- **上游事实**：官方仓库真实存在的提交。
- **本地定制事实**：用户自己的二开提交。

不要为了“看起来已经同步”而把两类事实混进同一个镜像分支。镜像分支只能快进到上游提交；一旦镜像分支出现用户独有提交，就先停止并诊断，不自动强推或重置。

## 标准拓扑

优先使用以下结构：

- `upstream`：官方仓库远端，只读语义。
- `origin`：用户自己的 Fork 或私有镜像远端。
- **镜像分支**：默认使用上游仓库的默认分支名称。上游默认分支为 `main` 时，本地镜像分支就是 `main`。
- `dev`：所有二开、自定义、汉化、集成和功能修改。
- `release`：经过测试并允许上线的生产分支。

逻辑关系：

`upstream/<默认分支>` → 本地镜像分支 → `dev` → 验证 → `release`

不要为了符合固定命名而擅自重命名上游默认分支。若上游默认分支不是 `main`，明确报告实际名称并沿用它作为镜像分支。

## 安全硬规则

这些规则优先级高于“尽快完成同步”：

1. 镜像分支禁止提交任何用户自定义代码。
2. 镜像分支同步只能使用快进方式；禁止在镜像分支制造 merge commit。
3. 工作区或暂存区不干净时停止，不自动 stash、不自动丢弃、不自动 reset。
4. 不使用 `git reset --hard`、`git clean -fd`、`git push --force` 或 `git push --force-with-lease` 来“修好”同步，除非用户明确要求并且已解释影响。
5. 不自动解决代码冲突；冲突出现后先列出文件和双方来源，再处理。
6. 公共协作分支默认不用 rebase 改写历史。只有确认是个人私有分支且用户接受历史改写时才可选 rebase。
7. 上游默认分支变化、远端 URL 变化、历史被重写、镜像分支出现独有提交时必须停止并报告。
8. `release` 不直接吸收上游；它只接收已经在 `dev` 完成验证的结果。
9. 任何项目已有自己的分支保护、测试、合并请求或发布规则时，以项目规则为准，本技能不能绕过。

## 初始化流程

### A. 用户有自己的 Fork 地址 + 官方上游地址

1. 克隆用户自己的仓库作为 `origin`。
2. 添加官方仓库为 `upstream`。
3. `fetch upstream --prune --tags`。
4. 读取 `upstream/HEAD`，确认官方默认分支。
5. 让本地镜像分支只跟随 `upstream/<默认分支>`。
6. 验证镜像分支与上游提交关系。
7. 从镜像分支创建 `dev`；需要生产分支时再创建 `release`。
8. 把 `dev` 和需要的镜像分支推送到 `origin`。

### B. 用户只给官方仓库地址

优先判断当前环境是否能安全创建 Fork：

- 如果已有 GitHub 类仓库工具并且用户授权创建 Fork，则先创建用户 Fork，再按 A 流程执行。
- 如果不能创建 Fork，则可以先克隆官方仓库并配置 `upstream`，但不得声称已经建立了可推送的 `origin` 二开仓库；明确指出在推送自定义代码前仍需设置用户自己的 `origin`。

### C. 用户已经有本地仓库

先做预检，不重新克隆：

```bash
git status --short
git remote -v
git branch -vv
git fetch --all --prune --tags
```

然后确认：

- `origin` 指向谁。
- `upstream` 是否存在并指向官方仓库。
- 上游默认分支是什么。
- 当前镜像分支是否含有上游不存在的提交。
- `dev` / `release` 是否已经存在。

任何事实不一致时先修拓扑，不直接同步。

## 镜像分支判定

同步前读取上游默认分支：

```bash
git remote set-head upstream -a
git symbolic-ref --short refs/remotes/upstream/HEAD
```

返回值通常类似：

```text
upstream/main
```

把最后一段作为镜像分支名。

## 定期同步上游流程

### 第 0 步：预检

必须确认工作区干净：

```bash
git status --porcelain
```

输出非空则停止。

检查远端：

```bash
git remote -v
git fetch upstream --prune --tags
```

### 第 1 步：更新纯净镜像分支

切到镜像分支后，只允许快进：

```bash
git checkout <mirror-branch>
git merge --ff-only upstream/<upstream-default-branch>
```

如果 `--ff-only` 失败，不改历史，立即停止并检查分叉来源。

镜像分支更新成功后，可以把纯净镜像推到用户自己的远端：

```bash
git push origin <mirror-branch>
```

### 第 2 步：给二开分支建立回退点

在把新上游引入 `dev` 之前，创建有时间戳的安全备份分支：

```bash
git branch backup/dev-before-upstream-<timestamp> dev
```

不要在没有回退点的情况下进行大版本升级。

### 第 3 步：把镜像分支合入 dev

默认使用 merge：

```bash
git checkout dev
git merge <mirror-branch>
```

如果冲突：

1. 输出冲突文件列表。
2. 标明哪些属于上游改动、哪些属于本地定制。
3. 优先保留双方意图，而不是机械选择 ours/theirs。
4. 解决后运行专项测试和全量门禁。
5. 验证通过后再提交冲突解决结果。

### 第 4 步：验证

优先读取项目自己的贡献文档、测试脚本和持续集成配置，运行项目原生门禁。至少包含：

- 构建或类型检查。
- 与本地定制直接相关的专项测试。
- 能运行时执行完整自动化测试。
- 对前端项目，若环境支持浏览器验证，真实打开关键页面检查运行错误和核心交互。

测试失败时不更新 `release`。

### 第 5 步：进入 release

仅当 `dev` 验证通过，并且用户当前任务允许发布时，才把 `dev` 合入 `release`。有合并请求流程的仓库优先创建合并请求，不直接绕过审查。

## 冲突处理原则

按以下顺序判断，不盲目“保我们的”或“保官方的”：

1. 先弄清上游为什么改这个文件。
2. 再弄清本地定制修改的业务目标。
3. 如果本地改动可以迁移到扩展点、配置、语言包、插件或独立模块，优先迁移，减少以后重复冲突。
4. 如果必须侵入核心源码，保持改动最小并单独提交。
5. 对删除/重命名/目录重构冲突，先跟随上游新结构，再把本地能力移植过去，不把旧文件硬塞回来。

## 二开编码约束

为了降低长期维护成本：

- 能新增文件解决的，不直接改上游核心文件。
- 能用配置、扩展点、插件、语言包解决的，不侵入核心业务逻辑。
- 每个独立定制尽量单独提交，提交信息清楚写明目的。
- 不把多个不相关定制揉成一个大提交。
- 上游同步提交与业务功能提交分开。
- 大版本升级先读官方发行说明和破坏性变更，再开始合并。

## cherry-pick 使用条件

默认仍然完整同步上游。只有用户明确不想升级整版、只需要某个安全修复或缺陷修复时，才考虑 cherry-pick。

使用前必须说明：选择性拿提交会让当前二开分支与完整上游版本产生版本差异，后续升级仍需重新评估依赖关系。

## rebase 使用条件

只在以下条件同时满足时提供：

- 二开提交很少；
- 分支没有被多人共同基于它开发；
- 用户明确接受改写提交哈希；
- 已有安全备份。

否则默认 merge。

## 自动执行时的输出格式

执行任务时，用简短状态报告让用户知道：

1. 当前识别到的 `origin` / `upstream`。
2. 上游默认分支与当前镜像分支。
3. 工作区是否干净、镜像分支是否纯净。
4. 本轮上游新增了多少提交，是否存在破坏性变化迹象。
5. 合入 `dev` 是否冲突、测试是否通过。
6. 是否已经推送、是否已经进入 `release`。
7. 尚未完成的真实阻塞项。

不要只说“同步成功”；给出可核对的分支和提交事实。

## 失败与停止条件

出现下列任一情况都停止自动推进：

- 工作区有未提交修改。
- 镜像分支不是上游祖先关系或含用户独有提交。
- `upstream` 指向不明或疑似错误仓库。
- 上游历史被强制重写。
- 快进同步失败。
- 合并冲突未解决。
- 项目门禁失败。
- 用户要求的生产发布需要额外确认或仓库保护规则阻止。

停止时给出事实、风险和下一步，不用破坏性命令掩盖问题。

## 支持脚本

本技能包附带两个可选 PowerShell 脚本和两个 Bash 脚本：

- `scripts/init-upstream.ps1`
- `scripts/sync-upstream.ps1`
- `scripts/init-upstream.sh`
- `scripts/sync-upstream.sh`

它们用于标准仓库的初始化和同步，但项目已有更严格流程时，以项目流程为准。

详细契约见 `references/operating-contract.md`。
