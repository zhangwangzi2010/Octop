## 1. 基线与规格冻结

- [ ] 1.1 以飞书需求文档 `GTPJdXujnom2WnxgUFVcU2Bonsb` 为验收 SoT，核对环比截图（2026-10-16）与飞书看板黄标五项（库存、推广 roas、流量异常（建议调价未调价）、流量异常SPU数占比、推广 Roas）已写入 design 与 specs。架构 wiki 只作框架参考，与 wiki 的差异不阻塞验收；与需求文档、环比截图或黄标清单冲突时先改 OpenSpec 再实现
- [ ] 1.2 冻结数据契约：Q1~Q5 口径、快照 schema v2。C-S09 / C-S12 / C-S13 的验收常量已是来源 A（≥10% / <90% / <95%），见 `specs/diagnosis-promoted-contracts/spec.md`。非黄标指标从 data_agent 语义层核对指标 ID、表字段、分区、时间窗和量纲，并记录对应 SQL 模板；上述黄标五项只登记 `fetchable=false`，不编造映射值
- [ ] 1.3 固化固定 SQL 构造原则：白名单 + 参数绑定 + 分区裁剪 + 禁止 LLM 生成/改写 SQL；RAG 运行时不进入 Octop 诊断链路。取数失败显式失败或标记数据不足，不用模型补数
- [ ] 1.4 建立 `feature/store-diagnosis` 主干与 WT-1~WT-6 worktree 分支映射（合并顺序：DB → Orchestrator → API → Agent → UI → E2E）
- [ ] 1.5 注（未完成，不要勾选）：取数展示名已写入 `specs/diagnosis-fetch-fields/spec.md`。第一级 27 个展示名、第二级检查单 25 个叶子、需求 6.3 四类下钻用词以该规格为准。已拍板：额外指标名为空；策略切片只用 SPU 概览三列。已拍板：履约 139 列为空 / 无此宽表。该规格不把展示名冻结成 JSON 键、文件路径或比率量纲。本项不代表取数实现完成
- [ ] 1.6 注（未完成，不要勾选）：参考表里已批准的部分写入 `specs/diagnosis-promoted-contracts/spec.md`，文内短语为「已由用户批准从参考升格为契约」。升格范围是一店一文件约定、十项二级指标名、Q4 的 latest / over_peers / next_level，以及评价 / 售后 / 发货 / 到货四类明细。路径是 kickoff §3.4 的 `{data_dir}/{shop_id}.json`。同节快照形状，以及十个指标名和 Q4 短名的快照 JSON 键，已写入该规格。四项原待裁决已有唯一验收常量：内部 0~1 对外 ×100；C-S09 / C-S12 / C-S13 用来源 A；`mall_check_score` 为规范名；明细为默认 Top N + 完整进附件。版本路径已登记为无版本段。一级取数到底表的六条验收常量已写入该规格。症状规则引擎的确定性判定场景已写入该规格，只组合已锁定常量。kickoff §7.1 的二级指标命中线与权重已写入该规格，C-S09 仍是 ≥10%。环比、下滑贡献占比、下滑权重指数已写入「诊断侧派生量」。已拍板：额外指标名为空；策略切片只用 SPU 概览三列。已拍板：履约 139 列为空 / 无此宽表。已拍板：六个售后类名依次是 1-物流履约、2-产品满意度、3-商品价格、4-店铺原因、5-平台原因、6-其他原因；9-未分类只作 SQL ELSE 回退，不进入元组。本项不代表实现，也不勾选 1.2

## 2. DB + 数据层（WT-1）

- [ ] 2.1 [RED] 迁移与版本断言：`tests/unit/db/test_db_pool.py` 的诊断水位一次升到 v21。不预期 v22、v23 或迁移文件 022 / 023
- [ ] 2.2 迁移对 `021_diagnosis_runs`（`.sql` / `.pg.sql`）创建 `diag_runs`、`diag_run_items`、`diag_node_events`。`diag_runs.client_request_id` 有唯一约束。不把本项写成在已有诊断表上加列，也不另开 022
- [ ] 2.3 repo：`repos/diagnosis_runs.py` CRUD + 事件写入 + owner 过滤（单测覆盖 SQLite 与 PG 方言）
- [ ] 2.4 boot `reset_orphan_items` 断点恢复 + 单测（崩溃场景）
- [ ] 2.5 不新增 022。`attempt` 已在 021 的 `diag_run_items`。批次头表、五阶段状态列、取消字段不在已拍板的列里，不新造这些列
- [ ] 2.6 快照存储：一店一文件 schema v2 读写 + 周期解析确定性单测

## 3. 编排器与流程 A（WT-2）

- [ ] 3.1 [RED] 五阶段状态机非法迁移测试 + 节点超时 / 重试表测试
- [ ] 3.2 DiagnosisOrchestrator：状态机、Semaphore 并发、取消、diag_node_events 事件流水
- [ ] 3.3 症状规则引擎属于 WT-1，不属于 WT-2。代码在 `src/octop/infra/diagnosis/symptom_engine.py`。共性 ≥40%、个体分级和影响度使用已锁定公式。健康判定只统计 `fetchable=true` 的范围内指标。命中标注句子仍是「运行时按 thresholds.json 计算」，本项不新造另一套阈值，也不把引擎改派给编排器
- [ ] 3.4 节点实现：ensure_data_ready（30min ×3）、analysis_run（900s ×2）、route 分流、diagnose 段1（60s ×2）、summarize（600s 降级）
- [ ] 3.5 预加载版本与状态门禁：`COMPLETED + row_count > 0` 才进入分析；`RUNNING` 幂等去重，`FAILED` 支持人工重试并记录事件
- [ ] 3.6 流程 A 零 LLM 全链路单测（`tests/unit/diagnosis/test_flow_a.py`）与健康店 SKIPPED。仅黄标指标不可取数、其余可取数指标未越阈时，店铺仍为 SKIPPED
- [ ] 3.7 Cron 每日 13:00 触发挂点 + 幂等（重复触发不产生重复 run）
- [ ] 3.8 [RED] 环比与可取数单测 `tests/unit/diagnosis/test_pop_rules.py` 随 WT-1 的症状引擎落地，不改属 WT-2。覆盖：公式 `(本期-上期)/上期×100%`；等长 7 天累计不做日均；比率 `sum(分子)/sum(分母)`，天数相等或不等都不使用日比率均值；仅累计指标在两侧天数不等时用日均；上期为 0、缺失或比率分母合计为 0 时不产生环比数值；正向指标下降、负向指标上升按轻微 `5%≤w<10%`、一般 `10%≤w≤20%`、严重 `w>20%` 分档，好转方向不入档；库存、推广 roas、流量异常（建议调价未调价）、流量异常SPU数占比、推广 Roas 均为 `fetchable=false` 并 SKIP，不产生数值。验证：`uv run pytest tests/unit/diagnosis/test_pop_rules.py -q`。完成判定：上述场景全部通过，且测试夹具不含这五项黄标指标的伪造数值

## 4. API（WT-3）

- [ ] 4.1 [RED] router 契约测试：幂等创建 / 越权 403 / 取消
- [ ] 4.2 `/api/diagnosis/runs` 系列（创建 / 列表 / 详情 / 取消），薄路由委托 infra
- [ ] 4.3 OpenAPI summary + 类型化 response_model，`/api/docs` 渲染人工检查
- [ ] 4.4 i18n：诊断相关错误码与用户可见文案 en / zh 键同步（`uv run pytest tests/unit/i18n -q`）

## 5. Agent 与流程 B（WT-4）

- [ ] 5.1 [RED] 契约门禁测试：结论 schema 校验失败与 data_refs 数字不一致 → item FAIL
- [ ] 5.2 诊断专家 Agent（SOUL 五步工作流）+ 4 份 Skill 资产（metrics_catalog / analysis_guide / drilldown_playbook / query_tasks）加载。五步是 kickoff §6.1.1 已批准的 SOUL 内联工作流，不是 Skill。四份 Skill 资产仍按名字加载。流程 A 保持零 LLM。标题依次是：
  - ① read_file 读取本 run 的切片（slice.json）
  - ② 只解读 hit=true 的项（个体优先 / 权重降序；共性带过，不展开）
  - ③ 按契约 write_file interpretation.json（headline / overall / findings / actions / risks，含 data_refs）
  - ④ execute 强制校验（scripts/validate_*.py：结构 + data_refs 数值逐条核对；不过 → 必须改，禁止静默降级）
  - ⑤ 一行收尾（结论 + 命中最重项）
- [ ] 5.3 store-perf MCP connector：5 工具注册与配置；入参透传 run_id / store_id
- [ ] 5.4 两段式 diagnose + attempt+1 换会话 + thread 命名 `diag:{run_id}:{store_id}:a{attempt}`
- [ ] 5.5 报告五段合成 summarize + PARTIAL 附录 + 失败降级拼接
- [ ] 5.6 fake agent 全链路集成测试（`tests/integration/test_diagnosis_integration.py`）
- [ ] 5.7 归因不引用 `fetchable=false` 指标的数值，不为库存、推广 roas、流量异常（建议调价未调价）、流量异常SPU数占比、推广 Roas 创建下钻。段1 环比上下文复用症状管线的周期合计结果，不改成日比率均值。验证：归因契约测试断言这五项不出现数值证据

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
- [ ] 7.5 UAT 暂不执行。飞书需求文档状态为待评审，正文没有 UAT / 验收 / Done / U1–U10。本任务不编写这些检查项；需求文档写入条文后再执行，并把证据放到 `docs/diagnosis-design/`。见 design.md Open Questions

## 8. 部署与收尾

- [ ] 8.1 本地部署冒烟：本机直跑 `octop run` + Cron 13:00 定时链路（含时区按服务器配置；不依赖 Docker）
- [ ] 8.2 迁移上线与回滚说明确认（成对 SQL 幂等验证）
- [ ] 8.3 按 WT-1 → WT-6 合并顺序合入 `feature/store-diagnosis`；跨模块冲突经协调仲裁
- [ ] 8.4 实现任务完成后归档 change（openspec archive add-store-diagnosis），更新 CHANGELOG。需求文档尚无验收 / Done 条文，归档说明不补写 U1–U10 或自拟验收清单
