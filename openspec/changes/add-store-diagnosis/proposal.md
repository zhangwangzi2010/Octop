## Why

运营数据在 MaxCompute，店铺销量下滑诊断目前依赖人工、口径不一、费时。飞书需求 V1.0 给出双流程验收边界；架构 wiki 只作可能不完整的框架参考，不阻塞验收。需要在不破坏 Octop 模块边界的前提下，把"定时症状管线（零 LLM）+ 归因下钻（LLM 参与）"从 Dify 工作流迁移为 Octop 内生能力，实现"接得进、诊得准、管得住"。

## What Changes

- 新增店铺诊断领域 `infra/diagnosis/`：五阶段 DAG 编排器（run/item 状态机、幂等、断点恢复、取消、并发限速、节点事件流水）
- 新增流程 A 症状管线：Cron 每日 13:00 定时触发，Q1~Q5 取数 → 一店一文件快照（schema v2）→ 阈值症状规则引擎（零 LLM、可重放）→ 落库
- 新增流程 B 归因下钻：症状分流（健康 SKIP / 个体 / 共性）→ 两段式 diagnose（段1 确定性上下文 + 段2 Agent 归因 JSON）→ 报告五段合成；契约校验失败 FAIL，不静默降级
- 新增 DB 迁移 021~023（成对 `.sql` / `.pg.sql`）：`diag_runs` / `diag_run_items` / `diag_node_events`，按三批低冲突落地
- 新增 API `/api/diagnosis/runs` 系列：提交幂等（client_request_id）、owner 隔离、Scalar 文档可读
- 新增 Dashboard 诊断中心：发起 / Run 列表 / 详情（items、阶段、失败原因）/ 报告渲染 / 追问
- 注册 store-perf MCP connector（get_data_latest / submit_preload / run_analysis / drill_metric / get_report）；沉淀 4 份 Skill 资产（metrics_catalog / analysis_guide / drilldown_playbook / query_tasks）与诊断专家 Agent
- 沉淀测试资产：症状引擎手算单测、fake-agent 全链路集成、Playwright 关键路径 E2E。需求文档当前状态为待评审，正文没有 UAT / 验收 / Done / U1–U10，本 change 不编写该检查表
- 飞书看板黄格暂不可取数（`fetchable=false`）：库存、推广 roas、流量异常（建议调价未调价）、流量异常SPU数占比、推广 Roas。其余诊断范围内指标按 data_agent 语义层与受控 SQL 模板取数，不移植 RAG 运行时

## Capabilities

### New Capabilities

- `diagnosis-orchestration`: 诊断 Run/Item 生命周期、五阶段状态机、幂等/恢复/取消/并发/事件审计
- `diagnosis-symptom-pipeline`: 流程 A 零 LLM 症状管线（定时取数、快照、阈值规则引擎、可重放）
- `diagnosis-attribution`: 流程 B 归因下钻（分流、两段式 diagnose、契约门禁、报告五段合成）
- `diagnosis-api`: 店铺诊断 HTTP 面（/api/diagnosis/runs 提交/查询/取消、幂等与权限）
- `diagnosis-dashboard`: 诊断中心界面（发起、Run 列表、详情、报告、追问）
- `diagnosis-fetch-fields`: 两级取数展示名与需求 6.3 四类下钻名称。展示名本身不含 JSON 键、文件路径、比率量纲
- `diagnosis-promoted-contracts`: 已由用户批准从参考升格为契约的一店一文件约定、十项二级指标名、Q4 的 latest / over_peers / next_level，以及评价 / 售后 / 发货 / 到货四类明细。路径是 kickoff §3.4 的 `{data_dir}/{shop_id}.json`。同节快照形状是店铺/主体/负责人 + `store_performance{perf_score, score_level, metrics[10]}`，十个指标名与 Q4 短名 `latest` / `over_peers` / `next_level` 是快照 JSON 键。比率验收是内部 0~1、对外 ×100。C-S09 / C-S12 / C-S13 的验收常量是来源 A：≥10% / <90% / <95%。店铺绩效分规范名是 `mall_check_score`，`perf_score` 是别名。明细验收是默认 Top N + 完整进附件。版本路径登记为无版本段。一级取数到底表的六条验收常量已写入该规格。症状规则引擎只组合这些已锁定常量做确定性判定，AI 只写摘要。kickoff §7.1 的二级指标命中线与权重已升格，C-S09 仍是 ≥10%。环比、下滑贡献占比、下滑权重指数标为诊断侧派生量。已拍板：额外指标名为空；策略切片只用 SPU 概览三列。已拍板：履约 139 列为空 / 无此宽表。六个售后类名仍阻断

### Modified Capabilities

（当前 `openspec/specs/` 为空，本次全部为新增能力；DB 版本断言等属实现细节，不构成 spec 级需求变更。）

## Impact

- 后端：`src/octop/infra/diagnosis/`（新）、`infra/db/migrations/021~023`（新迁移对）、`infra/db/repos/diagnosis_runs.py`（新）、`api/routers/diagnosis.py`（新）、`infra/cron`（13:00 触发挂点）、`infra/connectors`（store-perf 注册）
- 前端：`dashboard/src/` 新增诊断中心页面/路由/API 封装；构建产物经 `make build-frontend` 生成，不手改 `src/octop/dashboard/`
- 测试：`tests/unit/diagnosis/`、`tests/integration/test_diagnosis_*`、dashboard vitest、Playwright E2E；`tests/unit/db/test_db_pool.py` 版本断言 v20 → v23
- 外部依赖：MaxCompute 数据服务（:8787 MCP）需可达；真实数据联调与 UAT 需外部配合
- 文档：`docs/diagnosis-design/` 既有设计资料为本 change 输入；change 完成后经 archive 沉淀进 `openspec/specs/`
