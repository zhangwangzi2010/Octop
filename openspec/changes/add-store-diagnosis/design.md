## Context

- 宿主：Octop（Python 3.12 + FastAPI + React/Vite + uv），模块边界与迁移规范见根目录 `AGENTS.md`；DB 当前 schema v20，迁移必须成对（`.sql` + `.pg.sql`）。
- 输入：飞书需求 V1.0 与架构方案（整合版 v1.0，权威）；本地参照 `docs/diagnosis-design/`（精简版 v2）与 `skill-verify/shop-diagnosis-kickoff-prompt.md`。
- 数据事实参考：`data_agent_total_zhilong/backend/app/plugins/rag_retrieval/resources/semantic_layer/` 的店铺绩效指标/表/时间口径，以及 `backend/app/skills_analysis/store_performance_analysis/` 的固定 Q1~Q5、下钻、预加载与分析逻辑。该参考只提供口径，不改变飞书需求边界。
- 既有能力：诊断数据服务（:8787，MCP 5 工具）已存在不动；Agent 运行时为 octop-harness；编排需进程内直调 Agent（Route-D）。

## Goals / Non-Goals

**Goals:**

- 流程 A：零 LLM、定时、可重放的症状管线（快照为唯一事实源）。
- 流程 B：白名单收敛的归因下钻（两段式 diagnose + 契约门禁 + 报告五段合成）。
- 企业级：多用户隔离、多店铺并发、幂等 / 断点恢复 / 取消 / 事件审计、单店失败不阻塞（PARTIAL）。

**Non-Goals:**

- 不引入 Plan-and-Execute / 外部队列 / 新消息中间件；不改动 :8787 数据服务本体。
- 不做行动执行（运营系统工作流对接），仅预留挂点。
- 不修改既有聊天 / Agent 主路径行为。
- 本地部署、集成验证与 GUI UAT 不依赖 Docker：后端以本机 `octop run` 启动，前端使用 Dashboard 构建产物或既有开发服务，Playwright 驱动真实 HTTP/UI 链路。
- 不移植 RAG 运行时（embedding、向量库、rerank、自然语言生成 SQL）；店铺诊断取数使用固定查询模板与白名单。

## Decisions

1. **Route-D 进程内编排**：DiagnosisOrchestrator 放在 `infra/diagnosis/`，经 `SharedServices` 直调 Agent 与 repos，不建独立编排服务。备选（独立编排进程）被否：跨进程状态同步与部署复杂度不匹配当前规模。
2. **代码 DAG + 五阶段状态机**：调度与可靠性由编排层兜底（节点超时重试、条件更新认领、boot 恢复、Semaphore 并发），不依赖模型自觉；归因空间用 ≤5 项白名单收敛，ReAct 足够。
3. **迁移三批低冲突落地（021~023）**：第一批零冲突（node_events 表 + runs 加列 + client_request_id 幂等查重 + boot 恢复 + owner 过滤）；第二批独立迁移回归（attempt 多行化 + 批次头表 + 五阶段状态列 + 取消）；第三批承载流程 A / B 完整链路。资源表遵循 `id` 整数 PK + 公共字符串 ID 唯一、子表存字符串 ID 的项目规范。
4. **两段式 diagnose + 契约门禁**：段1 确定性上下文与 LLM 解读分离；结论 JSON schema 校验 + data_refs 逐条核对，失败判 FAIL 并 attempt+1 换会话，不静默降级。
5. **MCP connector + Skill 资产**：store-perf 5 工具经 connector 注册；归因思路沉淀在 4 份 Skill 资产（metrics_catalog 为唯一事实源，阈值冲突按影响文档拍板）。
6. **固定数据链路**：SQL 由受控模板、指标白名单、字段白名单、参数绑定和分区裁剪构造；LLM 不生成或改写 SQL。语义层 YAML 仅作为指标、表、维度和时间语义的口径资产，不引入其 RAG 检索运行时。
7. **版本化预加载**：定时触发只幂等发起 preload 并立即返回 job；后台任务读取 MaxCompute 固定数据集，写入版本化快照并记录 row counts 与终态。分析只消费 `COMPLETED` 且行数大于 0 的版本；`RUNNING` 禁止重复补数，`FAILED` 允许人工重试。
8. **thread 命名与并发**：归因会话命名 `diag:{run_id}:{store_id}:a{attempt}`；全局 Semaphore（默认 3~5，配置化）限制并发，纯数据节点不占槽。
9. **报告确定性合成**：summarize 只拼装快照数字与已校验结论；失败降级为列表拼接并在附录标注。
10. **前端走既有分层**：`dashboard/src/api/` 封装 + 页面组件 + i18n 双语键；构建产物由 `make build-frontend` 生成。

## Risks / Trade-offs

- [MaxCompute / 数据服务不可达] → ensure_data_ready 超时策略 + 联调前置检查 + UAT 备样例数据集。
- [attempt 多行化迁移回归风险] → 第二批独立迁移 + db 回归测试 + 版本断言逐批递增。
- [LLM 编造数字] → schema 校验 + data_refs 核对 + FAIL 重试；禁止静默降级。
- [订单表 shop_id 与绩效表 store_id 口径不一致] → 下钻 SQL 测试同时覆盖两套键名。
- [demo 语义层与飞书需求漂移] → 以飞书 wiki 和 OpenSpec specs 为需求权威；data_agent 只作为表、指标、SQL 和处理逻辑事实参考。
- [真实 LLM E2E 成本与时长] → 限 3 店小批次（分钟级），并可用 fake agent 集成测试兜底回归。

## Migration Plan

1. 按 021 → 022 → 023 顺序落迁移，每批更新 `tests/unit/db/test_db_pool.py` 版本断言并跑 db 回归。
2. 编排 / API / Agent / UI 按模块分支合入 `feature/store-diagnosis`，合并顺序：DB+Data → Orchestrator → API → Agent → UI → E2E。
3. 上线先本机直跑部署冒烟（`octop run` + Cron 13:00 链路，不引入 Docker/compose 作为验证前置），再真实数据小批次联调，最后 Playwright + 人工 UAT 签字。
4. 回滚：迁移成对且幂等，失败回退上一版本断言；Cron 挂点可配置关闭，不影响既有主路径。

## Open Questions

- :8787 数据服务的生产部署归属（运维边界）待拍板；connector 抽象先隔离影响。
- UAT 样例店铺集与健康 / 异常组合由谁提供待确认。
- 真实 LLM E2E 的 provider 限额与预算（3 店 ≤1 分钟级）待确认。
