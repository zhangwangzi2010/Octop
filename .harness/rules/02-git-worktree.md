# Git Worktree

## 使用条件

当多个功能、模块或实验需要并行推进，且互相覆盖工作区的风险高于管理成本时，使用 worktree。小改动直接在当前分支完成。

## 布局

```text
../octop-worktrees/<change>/<module>/
```

每个 worktree 只承载一个模块所有权。路径必须位于源仓库之外，并避免使用 `node_modules`、`.venv`、构建产物或用户数据目录。

## 创建前检查

1. 记录基线分支和 commit，运行 `git status --short`，标记用户已有修改。
2. 校验目标绝对路径不存在或为空，且父目录可写。
3. 从同一 OpenSpec change 的集成分支创建模块分支。
4. 明确本 worktree 的测试、端口、`OCTOP_HOME`、环境文件和数据目录隔离方式。

## 合并顺序

共享契约和数据层先合入，编排次之，传输层和 UI 后合入，端到端验收最后合入。店铺诊断建议顺序为 DB+Data → Orchestrator → API → Agent/Skill/MCP → Dashboard → E2E/UAT。

## 红线

- 删除、迁移 worktree、提交、推送、创建 PR、历史重写必须获得用户明确授权。
- 不把一个 worktree 的格式化扩展到其他模块。
- 合并前必须运行该模块的最小受影响测试；集成流合入前必须运行对应集成验证。
