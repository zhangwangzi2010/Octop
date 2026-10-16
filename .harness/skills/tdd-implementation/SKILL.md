---
name: tdd-implementation
description: Implement OpenSpec tasks with test-first evidence and Octop module boundaries.
---

# TDD Implementation

## 触发

OpenSpec `tasks.md` 已确认，用户已授权开始实现。

## 步骤

1. 读取任务、对应 spec 场景、领域基线和相关代码。
2. 先写失败测试，运行并确认失败原因正确。
3. 实现最小变更，遵守 `AGENTS.md` 模块边界和迁移规范。
4. 复跑目标测试转绿，再逐步扩大到受影响门禁。
5. 勾选 tasks，记录命令、退出状态和已知差距。

## 店铺诊断提示

先实现确定性规则和状态机；Agent 与 MCP 只在流程 B 归因阶段接入。语义层参考 `.harness/domains/store-diagnosis-baseline.md`，但需求以 OpenSpec specs 为准。

## 完成定义

当前任务有 RED/GREEN 证据，相关文档同步，未引入无关重构。
