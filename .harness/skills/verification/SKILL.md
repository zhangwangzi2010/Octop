---
name: verification
description: Produce honest command-based evidence before reporting implementation or readiness.
---

# Verification

## 触发

报告已实现、已修复、review-ready 或发布-ready 前；源码或配置在验证后发生变化时重新执行。

## 步骤

1. 确认当前目录、分支和变更清单是目标 worktree。
2. 先跑最低受影响测试，再跑更广门禁。
3. 记录完整命令和退出状态，区分真实依赖与 mock。
4. 对不可用门禁标注已知差距，不推断通过。

## 输出模板

```markdown
## Verification

| Command | Scope | Result | Evidence |
|---|---|---|---|

## Known gaps
```
