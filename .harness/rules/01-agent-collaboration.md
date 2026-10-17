# Agent Collaboration

## 角色泳道

使用能推进当前任务的最小团队；一个 agent 可以在小任务中兼任多个角色，但行为变更的实现者不能是唯一验证者。

| 角色 | 职责 | 主要产物 | 禁区 |
|---|---|---|---|
| Coordinator | 管依赖、合并顺序、冲突和状态 | worktree 映射、执行记录 | 不写业务实现 |
| Requirements/QA | 验收标准、测试矩阵、RED 用例 | spec 场景、测试清单 | 不改架构边界 |
| Platform | 编排、状态机、可靠性 | `infra/` 编排实现 | 不写 UI 或 MCP SQL |
| Data/MCP | 固定查询、下钻、connector | 数据契约与工具适配 | 不写 Dashboard |
| Skill | 分析思路、schema、禁编规则 | Skill 资产 | 不挂不可靠工具 |
| Dashboard | 页面、API 封装、i18n | `dashboard/` 源码 | 不改 `infra/` 规则 |
| Docs/Rules | 工程规则与交付文档 | 规则、runbook | 不扩需求 |

## 任务契约

委派任务必须写明六项：owned files、是否允许修改、必要输入、期望输出、完成前验证、不得修改范围。缺少任何一项时，受托 agent 先请求补齐，不猜测。

## 协作纪律

1. Agent 间通过文件、PR 或 thread 交接；口头摘要不能替代 OpenSpec artifact。
2. 冲突不得通过回滚他人修改解决；先适配现状，再提交 Coordinator 仲裁。
3. 共享契约先合入，消费者后合入；跨模块改动先提 RFC。
4. 长会话或压缩恢复后输出 checkpoint：change、阶段、最新证据、blockers、授权状态、worktree ownership。
5. 外部依赖、真实数据、部署和 UAT 未实测时只能标注待验证或已知差距。
