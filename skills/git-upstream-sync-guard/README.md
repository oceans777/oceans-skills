# git-upstream-sync-guard

一个面向“Fork 后长期二开并持续同步官方上游”的个人 Skill 包。

核心策略：官方上游远端只读语义；镜像分支只允许快进；自定义开发进入 dev；生产发布进入 release；同步前检查工作区；升级前建立回退分支；冲突不自动覆盖；测试失败不进入 release。

安装或导入时，以 `SKILL.md` 为技能入口。