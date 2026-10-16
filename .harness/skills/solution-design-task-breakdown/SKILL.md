---
name: solution-design-task-breakdown
description: Convert an approved proposal into OpenSpec design, capability specs, and small verifiable tasks.
---

# Solution Design and Task Breakdown

## 触发

proposal 已确认，需要技术设计、能力规格或任务拆分。

## 步骤

1. 以当前代码和测试为准核定事实基线，记录 HEAD 与文档冲突。
2. 设计边界、状态机、数据契约、错误处理、并发、恢复、安全和回滚。
3. 按能力拆 `specs/*/spec.md`，每个需求含可测场景。
4. 把 `tasks.md` 拆到一次会话可完成；每项写产物、验证命令、完成判定和依赖。
5. 行为变更任务显式安排 RED 测试；多模块任务定义 worktree 与合并顺序。
6. 运行 `openspec validate <change>`。

## 输出

`design.md`、`specs/**/spec.md`、`tasks.md`，以及必要的开放问题记录。

## 禁止

不得在设计和拆分未完成时进入实现；不得把未实测方案写成“已验证”。
