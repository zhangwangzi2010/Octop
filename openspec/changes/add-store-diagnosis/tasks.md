## 1. 基线与规格冻结

- [ ] 1.1 核对飞书 wiki 整合版 v1.0 与本 change 无冲突；冲突记入 design.md Open Questions，由人拍板
- [ ] 1.2 冻结数据契约：Q1~Q5 口径、快照 schema v2、metrics_catalog 阈值拍板值（C-S09 2% / C-S12 90% / C-S13 95%），并从 data_agent 语义层核对指标 ID、表字段、分区、时间窗和量纲
- [ ] 1.3 固化固定 SQL 构造原则：白名单 + 参数绑定 + 分区裁剪 + 禁止 LLM 生成/改写 SQL；RAG 运行时不进入 Octop 诊断链路
- [ ] 1.4 建立 `feature/store-diagnosis` 主干与 WT-1~WT-6 worktree 分支映射（合并顺序：DB → Orchestrator → API → Agent → UI → E2E）

## 2. DB + 数据层（WT-1）

- [ ] 2.1 [RED] 迁移与版本断言失败测试：`tests/unit/db/test_db_pool.py` v21 起逐批递增
- [ ] 2.2 第一批 021 迁移对：diag_node_events + diag_runs 加列 + client_request_id 幂等查重
- [ ] 2.3 repo：`repos/diagnosis_runs.py` CRUD + 事件写入 + owner 过滤（单测覆盖 SQLite 与 PG 方言）
- [ ] 2.4 boot `reset_orphan_items` 断点恢复 + 单测（崩溃场景）
- [ ] 2.5 第二批 022 迁移对：attempt 多行化 + 批次头表 + 五阶段状态列 + 取消字段；db 回归
- [ ] 2.6 快照存储：一店一文件 schema v2 读写 + 周期解析确定性单测

## 3. 编排器与流程 A（WT-2）

- [ ] 3.1 [RED] 五阶段状态机非法迁移测试 + 节点超时 / 重试表测试
- [ ] 3.2 DiagnosisOrchestrator：状态机、Semaphore 并发、取消、diag_node_events 事件流水
- [ ] 3.3 症状规则引擎：阈值 / 环比 / 共性 ≥40% / 分级 / 影响度排序手算一致单测；thresholds.json 配置化
- [ ] 3.4 节点实现：ensure_data_ready（30min ×3）、analysis_run（900s ×2）、route 分流、diagnose 段1（60s ×2）、summarize（600s 降级）
- [ ] 3.5 预加载版本与状态门禁：`COMPLETED + row_count > 0` 才进入分析；`RUNNING` 幂等去重，`FAILED` 支持人工重试并记录事件
- [ ] 3.6 流程 A 零 LLM 全链路单测（`tests/unit/diagnosis/test_flow_a.py`）与健康店 SKIPPED
- [ ] 3.7 Cron 每日 13:00 触发挂点 + 幂等（重复触发不产生重复 run）

## 4. API（WT-3）

- [ ] 4.1 [RED] router 契约测试：幂等创建 / 越权 403 / 取消
- [ ] 4.2 `/api/diagnosis/runs` 系列（创建 / 列表 / 详情 / 取消），薄路由委托 infra
- [ ] 4.3 OpenAPI summary + 类型化 response_model，`/api/docs` 渲染人工检查
- [ ] 4.4 i18n：诊断相关错误码与用户可见文案 en / zh 键同步（`uv run pytest tests/unit/i18n -q`）

## 5. Agent 与流程 B（WT-4）

- [ ] 5.1 [RED] 契约门禁测试：结论 schema 校验失败与 data_refs 数字不一致 → item FAIL
- [ ] 5.2 诊断专家 Agent（SOUL 五步工作流）+ 4 份 Skill 资产（metrics_catalog / analysis_guide / drilldown_playbook / query_tasks）加载
- [ ] 5.3 store-perf MCP connector：5 工具注册与配置；入参透传 run_id / store_id
- [ ] 5.4 两段式 diagnose + attempt+1 换会话 + thread 命名 `diag:{run_id}:{store_id}:a{attempt}`
- [ ] 5.5 报告五段合成 summarize + PARTIAL 附录 + 失败降级拼接
- [ ] 5.6 fake agent 全链路集成测试（`tests/integration/test_diagnosis_integration.py`）

## 6. Dashboard（WT-5）

- [ ] 6.1 [RED] vitest 组件测试：创建入口 / Run 列表 / PARTIAL 标注
- [ ] 6.2 `dashboard/src/api/` diagnosis 封装 + 诊断中心页面与路由
- [ ] 6.3 报告 markdown 渲染 + 追问入口 + i18n（zh / en）
- [ ] 6.4 `cd dashboard && npx tsc -b` 通过 + `make build-frontend` 更新构建产物

## 7. 集成 / E2E / UAT（WT-6）

- [ ] 7.1 Playwright 前后端关键路径：本机直跑后端 `octop run` + Dashboard 构建产物/开发服务，覆盖登录 → 诊断中心 → 创建 → 终态 / 报告（样例数据夹具；不依赖 Docker）
- [ ] 7.2 集成演练：断点恢复 / 提交幂等 / 取消 / PARTIAL 附录
- [ ] 7.3 真实数据联调：MaxCompute 样例店铺集小批次流程 B（外部依赖就绪后）
- [ ] 7.4 终验门禁：`make all` 全绿
- [ ] 7.5 UAT：执行 U1~U10 检查表，证据写入 `docs/diagnosis-design/UAT-YYYYMMDD.md` 并签字

## 8. 部署与收尾

- [ ] 8.1 本地部署冒烟：本机直跑 `octop run` + Cron 13:00 定时链路（含时区按服务器配置；不依赖 Docker）
- [ ] 8.2 迁移上线与回滚说明确认（成对 SQL 幂等验证）
- [ ] 8.3 按 WT-1 → WT-6 合并顺序合入 `feature/store-diagnosis`；跨模块冲突经协调仲裁
- [ ] 8.4 DoD 核对后归档 change（openspec archive add-store-diagnosis），更新 CHANGELOG
