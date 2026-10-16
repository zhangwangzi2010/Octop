# OpenSpec Lifecycle

## 阶段映射

| 阶段 | 技能 | OpenSpec 产物 | 门禁 |
|---|---|---|---|
| 需求分析 | `request-analysis` | `proposal.md` | 目标、非目标、验收标准、影响面明确 |
| 方案与拆分 | `solution-design-task-breakdown` | `design.md`、`specs/`、`tasks.md` | `openspec validate <change>` 通过 |
| 实现 | `tdd-implementation` | 勾选 tasks | 每项产物/验证/完成判定齐备，RED→GREEN |
| 验证 | `verification` | 证据记录 | 受影响测试和 `make all` |
| UAT/部署 | `uat-deploy` | UAT/部署记录 | 冒烟、回滚、人工签字 |
| 归档 | `openspec archive` | `openspec/specs/` | 全部任务与 DoD 完成 |

## 变更纪律

1. 触发 Spec 门禁的改动先更新 OpenSpec，再实现。
2. 实现偏离已确认需求时，先更新 proposal/spec/design 并说明原因。
3. `acceptance.md`、`ops.md` 或 UAT 记录不得预填未实测结论。
4. 未归档 change 的任务 checkbox 必须与实际状态一致。

## 当前 change

`add-store-diagnosis` 是首个候选实战 change。当前只完成规格和任务拆分，尚未进入实现；启动实现前需用户明确授权。
