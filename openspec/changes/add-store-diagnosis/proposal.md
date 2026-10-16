## Why

运营数据在 MaxCompute，店铺销量下滑诊断目前依赖人工、口径不一、费时。飞书需求 V1.0 与架构方案（整合版 v1.0）已冻结"双流程"蓝图：需要在不破坏 Octop 模块边界的前提下，把"定时症状管线（零 LLM）+ 归因下钻（LLM 参与）"从 Dify 工作流迁移为 Octop 内生能力，实现"接得进、诊得准、管得住"。

## What Changes

- 新增店铺诊断领域 `infra/diagnosis/`：五阶段 DAG 编排器（run/item 状态机、幂等、断点恢复、取消、并发限速、节点事件流水）
- 新增流程 A 症状管线：Cron 每日 13:00 定时触发，Q1~Q5 取数 → 一店一文件快照（schema v2）→ 阈值症状规则引擎（零 LLM、可重放）→ 落库
- 新增流程 B 归因下钻：症状分流（健康 SKIP / 个体 / 共性）→ 两段式 diagnose（段1 确定性上下文 + 段2 Agent 归因 JSON）→ 报告五段合成；契约校验失败 FAIL，不静默降级
- 新增 DB 迁移 021~023（成对 `.sql` / `.pg.sql`）：`diag_runs` / `diag_run_items` / `diag_node_events`，按三批低冲突落地
- 新增 API `/api/diagnosis/runs` 系列：提交幂等（client_request_id）、owner 隔离、Scalar 文档可读
- 新增 Dashboard 诊断中心：发起 / Run 列表 / 详情（items、阶段、失败原因）/ 报告渲染 / 追问
- 注册 store-perf MCP connector（get_data_latest / submit_preload / run_analysis / drill_metric / get_report）；沉淀 4 份 Skill 资产（metrics_catalog / analysis_guide / drilldown_playbook / query_tasks）与诊断专家 Agent
- 沉淀测试资产：症状引擎手算单测、fake-agent 全链路集成、Playwright 关键路径 E2E、UAT 检查表

## Capabilities

### New Capabilities

- `diagnosis-orchestration`: 诊断 Run/Item 生命周期、五阶段状态机、幂等/恢复/取消/并发/事件审计
- `diagnosis-symptom-pipeline`: 流程 A 零 LLM 症状管线（定时取数、快照、阈值规则引擎、可重放）
- `diagnosis-attribution`: 流程 B 归因下钻（分流、两段式 diagnose、契约门禁、报告五段合成）
- `diagnosis-api`: 店铺诊断 HTTP 面（/api/diagnosis/runs 提交/查询/取消、幂等与权限）
- `diagnosis-dashboard`: 诊断中心界面（发起、Run 列表、详情、报告、追问）

### Modified Capabilities

（当前 `openspec/specs/` 为空，本次全部为新增能力；DB 版本断言等属实现细节，不构成 spec 级需求变更。）

## Impact

- 后端：`src/octop/infra/diagnosis/`（新）、`infra/db/migrations/021~023`（新迁移对）、`infra/db/repos/diagnosis_runs.py`（新）、`api/routers/diagnosis.py`（新）、`infra/cron`（13:00 触发挂点）、`infra/connectors`（store-perf 注册）
- 前端：`dashboard/src/` 新增诊断中心页面/路由/API 封装；构建产物经 `make build-frontend` 生成，不手改 `src/octop/dashboard/`
- 测试：`tests/unit/diagnosis/`、`tests/integration/test_diagnosis_*`、dashboard vitest、Playwright E2E；`tests/unit/db/test_db_pool.py` 版本断言 v20 → v23
- 外部依赖：MaxCompute 数据服务（:8787 MCP）需可达；真实数据联调与 UAT 需外部配合
- 文档：`docs/diagnosis-design/` 既有设计资料为本 change 输入；change 完成后经 archive 沉淀进 `openspec/specs/`
