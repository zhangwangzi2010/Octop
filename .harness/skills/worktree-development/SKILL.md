---
name: worktree-development
description: Isolate parallel Octop modules in git worktrees with explicit ownership and merge order.
---

# Worktree Development

## 触发

用户授权并行开发，且模块边界能拆分为独立分支和文件所有权。

## 步骤

1. 读取 `.harness/rules/02-git-worktree.md`，记录基线与用户已有修改。
2. 为每个模块创建唯一 worktree、分支和 ownership 清单。
3. 隔离依赖、端口、环境文件、`OCTOP_HOME` 和测试数据。
4. 共享契约先行；每个 worktree 只提交本模块验证过的变更。
5. 合并前运行模块测试，集成流再跑集成测试。

## 当前限制

`add-store-diagnosis` 尚未启动实现，因此尚未创建功能 worktree。骨架确认后按 OpenSpec tasks 的 WT 分组启动。
