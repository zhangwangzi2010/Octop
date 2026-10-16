# Harness Index

## 阅读顺序

| 顺序 | 规则 | 必读时机 |
|---|---|---|
| 1 | [Agent collaboration](01-agent-collaboration.md) | 多 agent 或多人参与同一 change |
| 2 | [Git worktree](02-git-worktree.md) | 创建分支、worktree、并行流或合并模块 |
| 3 | [Testing and TDD](03-testing-tdd.md) | 修改行为、接口、数据、权限、错误处理或 UI |
| 4 | [Quality gates](04-quality-gates.md) | 报告已实现、review-ready、发布-ready |
| 5 | [OpenSpec lifecycle](05-openspec-lifecycle.md) | 从新需求到归档 change 的任一阶段 |
| 6 | [Module boundaries](06-module-boundaries.md) | 新增目录、迁移、API、Dashboard 或跨层调用 |

## 执行基线

1. 先判断意图：问答和评审只读；开发任务必须先有 OpenSpec change 或明确的无行为变化理由。
2. 影响业务行为、接口、数据、权限、架构或部署时，按 `request-analysis` → `solution-design-task-breakdown` → `tdd-implementation` 执行。
3. 每个实现任务必须有产物、验证命令和完成判定；缺陷修复先复现并保留 RED 证据。
4. 声明状态只能使用：已实现、待验证、已知差距。没有最新命令输出不得声称通过。
5. 多智能体任务先定义角色、文件所有权、交接物和禁区；冲突记录到 change 的 `OPEN_QUESTIONS.md` 或 `design.md`。
6. 领域基线只约束事实口径。实现仍以 OpenSpec specs 的 SHALL/MUST 需求为准。

## 当前仓库状态

- OpenSpec change：`openspec/changes/add-store-diagnosis/`，用于店铺诊断 0→1 需求。
- Harness 状态：文档骨架已落地，未启动店铺诊断实现，未创建功能 worktree，未修改测试和功能代码。
- 领域基线：`domains/store-diagnosis-baseline.md` 记录语义层指标、固定 SQL 和 demo 处理逻辑的参考来源。
