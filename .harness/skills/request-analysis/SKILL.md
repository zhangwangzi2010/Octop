---
name: request-analysis
description: Clarify new Octop requirements, bugs, architecture or data-impacting requests into an OpenSpec-ready proposal before implementation.
---

# Request Analysis

## 触发

收到新功能、缺陷、行为变化、接口/数据/权限/架构/部署影响，或目标与验收标准不清的请求。

## 步骤

1. 记录 `git status --short` 和相关代码事实，区分事实、假设和待确认问题。
2. 识别用户要解决的问题、期望收益、非目标和更短路径。
3. 把可观察结果转为验收标准；标记外部依赖和人工闸门。
4. 定位影响模块、契约、数据、测试和文档。
5. 触发 Spec 门禁时创建 `openspec/changes/<name>/proposal.md`。

## 输出模板

```markdown
> 🎯 第一性原理：[问题本质与最短路径]

## Outcome
## Acceptance criteria
## Assumptions
## Impact
## Non-goals
## Open questions
```

## 完成定义

proposal 已落盘，能支撑方案设计和任务拆分；无行为实现被启动。
