# CLAUDE.md

<!-- oceans777-agent-standards:start version=1 -->

## 常驻规则

- 当 `AGENTS.md` 和本文件同时存在时，优先遵守仓库的 `AGENTS.md`。
- 用户当前明确提出的要求优先级高于本文件。
- 保护用户已有工作。不得删除、覆盖、回滚或随意重排与当前任务无关的改动。
- 项目专属细节写入 `project-local` 区块，避免重复全局规则。

## 工作方式

- 修改文件前先检查仓库结构和工作区状态。
- 优先沿用项目已有模式，不轻易引入新的抽象。
- 运行能够证明改动正确性的最小相关验证。
- 只暂存当前任务拥有的文件，避免夹带无关改动。

<!-- oceans777-agent-standards:end -->

<!-- project-local:start -->

## 项目专属规则

- 只有当 Claude 需要不同于 `AGENTS.md` 的项目规则时，才在这里补充。
- 优先写准确命令、路径和例外条件，少写泛泛描述。

<!-- project-local:end -->
