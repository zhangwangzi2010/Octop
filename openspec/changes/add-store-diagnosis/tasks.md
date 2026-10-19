## 1. 基线与规格冻结

- [ ] 1.1 以飞书需求文档 `GTPJdXujnom2WnxgUFVcU2Bonsb` 为验收 SoT，核对环比截图（2026-10-16）与飞书看板黄标五项（库存、推广 roas、流量异常（建议调价未调价）、流量异常SPU数占比、推广 Roas）已写入 design 与 specs。架构 wiki 只作框架参考，与 wiki 的差异不阻塞验收；与需求文档、环比截图或黄标清单冲突时先改 OpenSpec 再实现。缺：对照表有 `tests/unit/diagnosis/test_pop_rules.py` 与 `test_fetch_catalog.py`，没有点名提交。
- [ ] 1.2 冻结数据契约：Q1~Q5 口径、快照 schema v2。C-S09 / C-S12 / C-S13 的验收常量已是来源 A（≥10% / <90% / <95%），见 `specs/diagnosis-promoted-contracts/spec.md`。非黄标指标从 data_agent 语义层核对指标 ID、表字段、分区、时间窗和量纲，并记录对应 SQL 模板；上述黄标五项只登记 `fetchable=false`，不编造映射值。缺：对照表有 `test_remaining_contracts.py` 与 `test_hit_weights.py`，没有点名提交。语义层逐项 ID 和 SQL 模板仍未记录。
- [ ] 1.3 固化固定 SQL 构造原则：白名单 + 参数绑定 + 分区裁剪 + 禁止 LLM 生成/改写 SQL；RAG 运行时不进入 Octop 诊断链路。取数失败显式失败或标记数据不足，不用模型补数。缺：没有诊断 SQL 模板的提交和测试。
- [ ] 1.4 建立 `feature/store-diagnosis` 主干与 WT-1~WT-6 worktree 分支映射（合并顺序：DB → Orchestrator → API → Agent → UI → E2E）。缺：没有 `feature/store-diagnosis` 主干，也没有这份 worktree 映射的提交和测试。
- [ ] 1.5 注（未完成，不要勾选）：取数展示名已写入 `specs/diagnosis-fetch-fields/spec.md`。第一级 27 个展示名、第二级检查单 25 个叶子、需求 6.3 四类下钻用词以该规格为准。已拍板：额外指标名为空；策略切片只用 SPU 概览三列。已拍板：履约 139 列为空 / 无此宽表。该规格不把展示名冻结成 JSON 键、文件路径或比率量纲。本项不代表取数实现完成。缺：条文写明不要勾选。对照表没有点名提交。
- [ ] 1.6 注（未完成，不要勾选）：参考表里已批准的部分写入 `specs/diagnosis-promoted-contracts/spec.md`，文内短语为「已由用户批准从参考升格为契约」。升格范围是一店一文件约定、十项二级指标名、Q4 的 latest / over_peers / next_level，以及评价 / 售后 / 发货 / 到货四类明细。路径是 kickoff §3.4 的 `{data_dir}/{shop_id}.json`。同节快照形状，以及十个指标名和 Q4 短名的快照 JSON 键，已写入该规格。四项原待裁决已有唯一验收常量：内部 0~1 对外 ×100；C-S09 / C-S12 / C-S13 用来源 A；`mall_check_score` 为规范名；明细为默认 Top N + 完整进附件。版本路径已登记为无版本段。一级取数到底表的六条验收常量已写入该规格。症状规则引擎的确定性判定场景已写入该规格，只组合已锁定常量。kickoff §7.1 的二级指标命中线与权重已写入该规格，C-S09 仍是 ≥10%。环比、下滑贡献占比、下滑权重指数已写入「诊断侧派生量」。已拍板：额外指标名为空；策略切片只用 SPU 概览三列。已拍板：履约 139 列为空 / 无此宽表。已拍板：六个售后类名依次是 1-物流履约、2-产品满意度、3-商品价格、4-店铺原因、5-平台原因、6-其他原因；9-未分类只作 SQL ELSE 回退，不进入元组。本项不代表实现，也不勾选 1.2。缺：条文写明本项不代表实现。

## 2. DB + 数据层（WT-1）

- [ ] 2.1 [RED] 迁移与版本断言：`tests/unit/db/test_db_pool.py` 的诊断水位一次升到 v21。不预期 v22、v23 或迁移文件 022 / 023。缺：对照表有 `tests/unit/db/test_db_pool.py`，没有点名提交。
- [ ] 2.2 迁移对 `021_diagnosis_runs`（`.sql` / `.pg.sql`）创建 `diag_runs`、`diag_run_items`、`diag_node_events`。`diag_runs.client_request_id` 有唯一约束。不把本项写成在已有诊断表上加列，也不另开 022。缺：对照表只有迁移文件，没有点名测试。
- [ ] 2.3 repo：`repos/diagnosis_runs.py` CRUD + 事件写入 + owner 过滤（单测覆盖 SQLite 与 PG 方言）。缺：对照表没有点名提交，也没有点名测试文件。
- [x] 2.4 boot `reset_orphan_items` 断点恢复 + 单测（崩溃场景）。证据：提交 `ec8d3b1e`；测试 `tests/unit/diagnosis/test_orchestrator.py::test_startup_resumes_a_diagnosing_crash`。
- [ ] 2.5 不新增 022。`attempt` 已在 021 的 `diag_run_items`。批次头表、五阶段状态列、取消字段不在已拍板的列里，不新造这些列。缺：022 没有落地，这不是完成项。
- [x] 2.6 快照存储：一店一文件 schema v2 读写 + 周期解析确定性单测。证据：提交 `50918268`；测试 `tests/unit/diagnosis/test_snapshot_v2_fetch.py`、`tests/unit/diagnosis/test_snapshot_json.py`。一级派生现算仍缺，不在本项里。

## 3. 编排器与流程 A（WT-2）

- [ ] 3.1 [RED] 五阶段状态机非法迁移测试 + 节点超时 / 重试表测试。缺：对照表有 `tests/unit/diagnosis/test_orchestrator.py`，没有点名提交。
- [ ] 3.2 DiagnosisOrchestrator：状态机、Semaphore 并发、取消、diag_node_events 事件流水。缺：对照表有提交 `ec8d3b1e`，没有点名测试。
- [x] 3.3 症状规则引擎属于 WT-1，不属于 WT-2。代码在 `src/octop/infra/diagnosis/symptom_engine.py`。共性 ≥40%、个体分级和影响度使用已锁定公式。健康判定只统计 `fetchable=true` 的范围内指标。命中标注句子仍是「运行时按 thresholds.json 计算」，本项不新造另一套阈值，也不把引擎改派给编排器。证据：提交 `16ab91af`；测试 `tests/unit/diagnosis/test_symptom_engine.py`。总权重汇总仍没有函数，不在本项里。
- [ ] 3.4 节点实现：ensure_data_ready（30min ×3）、analysis_run（900s ×2）、route 分流、diagnose 段1（60s ×2）、summarize（600s 降级）。缺：这些节点没有独立实现提交。分流表正文没有。
- [ ] 3.5 预加载版本与状态门禁：`COMPLETED + row_count > 0` 才进入分析；`RUNNING` 幂等去重，`FAILED` 支持人工重试并记录事件。缺：对照表只写了快照结构单测，没有点名提交。
- [ ] 3.6 流程 A 零 LLM 全链路单测（`tests/unit/diagnosis/test_flow_a.py`）与健康店 SKIPPED。仅黄标指标不可取数、其余可取数指标未越阈时，店铺仍为 SKIPPED。缺：没有 `tests/unit/diagnosis/test_flow_a.py`。
- [ ] 3.7 Cron 每日 13:00 触发挂点 + 幂等（重复触发不产生重复 run）。缺：没有诊断定时挂点，也没有幂等测试。
- [x] 3.8 [RED] 环比与可取数单测 `tests/unit/diagnosis/test_pop_rules.py` 随 WT-1 的症状引擎落地，不改属 WT-2。覆盖：公式 `(本期-上期)/上期×100%`；等长 7 天累计不做日均；比率 `sum(分子)/sum(分母)`，天数相等或不等都不使用日比率均值；仅累计指标在两侧天数不等时用日均；上期为 0、缺失或比率分母合计为 0 时不产生环比数值；正向指标下降、负向指标上升按轻微 `5%≤w<10%`、一般 `10%≤w≤20%`、严重 `w>20%` 分档，好转方向不入档；库存、推广 roas、流量异常（建议调价未调价）、流量异常SPU数占比、推广 Roas 均为 `fetchable=false` 并 SKIP，不产生数值。验证：`uv run pytest tests/unit/diagnosis/test_pop_rules.py -q`。完成判定：上述场景全部通过，且测试夹具不含这五项黄标指标的伪造数值。证据：提交 `c51876f1`；测试 `tests/unit/diagnosis/test_pop_rules.py`。环比方向仍缺：快照没有 C-S11 / C-S14 的升降，不在本项里。

## 4. API（WT-3）

- [x] 4.1 [RED] router 契约测试：幂等创建 / 越权 403 / 取消。证据：提交 `f420d4a2`；测试 `tests/unit/api/test_diagnosis_runs.py::test_create_is_idempotent_and_reaches_flow_a`、`test_other_owner_cannot_reuse_client_request_id`、`test_list_detail_and_cancel_are_owner_scoped`。
- [x] 4.2 `/api/diagnosis/runs` 系列（创建 / 列表 / 详情 / 取消），薄路由委托 infra。证据：提交 `f420d4a2`；测试 `tests/unit/api/test_diagnosis_runs.py::test_create_is_idempotent_and_reaches_flow_a`、`test_list_detail_and_cancel_are_owner_scoped`。
- [x] 4.3 OpenAPI summary + 类型化 response_model，`/api/docs` 渲染人工检查。证据：提交 `f420d4a2`；测试 `tests/unit/api/test_diagnosis_runs.py::test_openapi_routes_are_typed_and_have_no_retry`。
- [ ] 4.4 i18n：诊断相关错误码与用户可见文案 en / zh 键同步（`uv run pytest tests/unit/i18n -q`）。缺：`src/octop/i18n` 没有诊断文案键，也没有对应测试。

## 5. Agent 与流程 B（WT-4）

- [ ] 5.1 [RED] 契约门禁测试：结论 schema 校验失败与 data_refs 数字不一致 → item FAIL。缺：对照表有 `test_flow_b.py` 和夹具换会话，没有点名提交。
- [x] 5.2 诊断专家 Agent（SOUL 五步工作流）+ 4 份 Skill 资产（metrics_catalog / analysis_guide / drilldown_playbook / query_tasks）加载。五步是 kickoff §6.1.1 已批准的 SOUL 内联工作流，不是 Skill。四份 Skill 资产仍按名字加载。流程 A 保持零 LLM。标题依次是：
  - ① read_file 读取本 run 的切片（slice.json）
  - ② 只解读 hit=true 的项（个体优先 / 权重降序；共性带过，不展开）
  - ③ 按契约 write_file interpretation.json（headline / overall / findings / actions / risks，含 data_refs）
  - ④ execute 强制校验（scripts/validate_*.py：结构 + data_refs 数值逐条核对；不过 → 必须改，禁止静默降级）
  - ⑤ 一行收尾（结论 + 命中最重项）
  证据：SOUL `src/octop/infra/agents/experts/library/store-diagnosis/SOUL.md`；Skill 同目录 `skills/metrics_catalog`、`analysis_guide`、`drilldown_playbook`、`query_tasks` 的 `SKILL.md`；尖端 `20cdc132`；测试 `tests/unit/diagnosis/test_skill_bodies.py`。架构门禁与代码门禁均接受。
- [ ] 5.3 store-perf MCP connector：5 工具注册与配置；入参透传 run_id / store_id。缺：目录字段有测试，阶段仍是 `coming_soon`。真实数仓 / :8787 没有实现，入参透传没有点名测试。
- [ ] 5.4 两段式 diagnose + attempt+1 换会话 + thread 命名 `diag:{run_id}:{store_id}:a{attempt}`。缺：对照表有 `test_flow_b.py` 与 `test_fixture_run.py`，没有点名提交。
- [x] 5.5 报告五段合成 summarize + PARTIAL 附录 + 失败降级拼接。证据：提交 `d705907e`；测试 `tests/unit/diagnosis/test_fixture_run.py::test_three_store_fixture_reaches_partial_from_snapshot_files`。
- [ ] 5.6 fake agent 全链路集成测试（`tests/integration/test_diagnosis_integration.py`）。缺：对照表有这个测试文件，没有点名提交。
- [ ] 5.7 归因不引用 `fetchable=false` 指标的数值，不为库存、推广 roas、流量异常（建议调价未调价）、流量异常SPU数占比、推广 Roas 创建下钻。段1 环比上下文复用症状管线的周期合计结果，不改成日比率均值。验证：归因契约测试断言这五项不出现数值证据。缺：对照表没有点名提交。环比方向仍缺。

## 6. Dashboard（WT-5）

- [ ] 6.1 [RED] vitest 组件测试：创建入口 / Run 列表 / PARTIAL 标注。缺：没有诊断 vitest。
- [ ] 6.2 `dashboard/src/api/` diagnosis 封装 + 诊断中心页面与路由。缺：`dashboard/src` 没有诊断 API 封装和页面。
- [ ] 6.3 报告 markdown 渲染 + 追问入口 + i18n（zh / en）。缺：没有报告页面，也没有诊断 i18n。
- [ ] 6.4 `cd dashboard && npx tsc -b` 通过 + `make build-frontend` 更新构建产物。缺：没有诊断前端的类型检查和构建产物。

## 7. 集成 / E2E / UAT（WT-6）

- [ ] 7.1 Playwright 前后端关键路径：本机直跑后端 `octop run` + Dashboard 构建产物/开发服务，覆盖登录 → 诊断中心 → 创建 → 终态 / 报告（样例数据夹具；不依赖 Docker）。缺：没有 Playwright 诊断路径。
- [ ] 7.2 集成演练：断点恢复 / 提交幂等 / 取消 / PARTIAL 附录。缺：没有集成演练记录。单测不能代替这次演练。
- [x] 7.3 真实数据联调：MaxCompute 样例店铺集小批次流程 B（外部依赖就绪后）。证据：仓内 `docs/store-perf-local-uat-20261018.md`。来源是本机 zhangbo-office 四店 HTTP 200（health / data/latest / preload / analysis/run / drill×4，storeCount=4，abnormalStoreCount=3）。空 Key 单测 `tests/unit/diagnosis/test_store_perf_client.py::test_empty_api_key_builds_client_when_base_url_is_set`。架构门禁与代码门禁均接受。
- [ ] 7.4 终验门禁：`make all` 全绿。缺：`make all` 在 `88163b5e` 上是绿的，但终验还覆盖没有证据的任务。对照表没有把它当作可勾选项。
- [ ] 7.5 UAT 暂不执行。飞书需求文档状态为待评审，正文没有 UAT / 验收 / Done / U1–U10。本任务不编写这些检查项；需求文档写入条文后再执行，并把证据放到 `docs/diagnosis-design/`。见 design.md Open Questions。缺：需求文档没有 UAT 条文。

## 8. 部署与收尾

- [ ] 8.1 本地部署冒烟：本机直跑 `octop run` + Cron 13:00 定时链路（含时区按服务器配置；不依赖 Docker）。缺：没有本机冒烟，也没有 13:00 定时链路。
- [ ] 8.2 迁移上线与回滚说明确认（成对 SQL 幂等验证）。缺：没有上线与回滚确认记录。
- [ ] 8.3 按 WT-1 → WT-6 合并顺序合入 `feature/store-diagnosis`；跨模块冲突经协调仲裁。缺：没有合入 `feature/store-diagnosis`。
- [ ] 8.4 实现任务完成后归档 change（openspec archive add-store-diagnosis），更新 CHANGELOG。需求文档尚无验收 / Done 条文，归档说明不补写 U1–U10 或自拟验收清单。缺：没有归档，也没有 CHANGELOG 更新。

## 已知缺口

- [x] 分流表正文。证据：绿灯 `c015c010`；测试 `tests/unit/diagnosis/test_analysis_guide.py::test_analysis_guide_body_uses_locked_lines`、`test_drill_routes_cover_five_and_mark_six`、`test_fixture_hangs_the_drill_route`。
- [x] 总权重汇总。证据：绿灯 `7925473a`；测试 `tests/unit/diagnosis/test_weight_and_direction.py::test_individual_weight_drops_common_hits_and_total_keeps_them`、`test_multi_hit_fixture_sorts_top5_and_grades_direction_hits`。
- [x] 一级派生现算（最小集）。证据：绿灯 `f33cad8f`；测试 `tests/unit/diagnosis/test_l1_live.py::test_live_minimal_computes_pop_contribution_and_weight_index`、`test_two_level_fetch_applies_windows_and_marks_gaps`。调用方给出窗口时按已锁公式现算。TOP X 的 X 和无公式项不在本项里。快照文件仍没有一级底字段，夹具缺口句「一级派生展示值不从快照现算」仍在。
- [ ] TOP X 的 X。缺：没有把 X 定成某个数的提交。凡是「Top x …」展示名保持空并标 gap。`tests/unit/diagnosis/test_l1_live.py::test_formula_gaps_and_unknown_age_spellings_stay_empty` 只锁定 `top_x` 为空。
- [ ] 无公式的一级展示名。缺：订单量下滑占比、下滑SPU数占比、动销SPU下滑占比、在售SPU下滑占比没有已锁公式，保持空并标 gap。没有为它们补公式的提交。`tests/unit/diagnosis/test_l1_live.py::test_formula_gaps_and_unknown_age_spellings_stay_empty` 只锁定这些名字留在 gaps 里。
- [x] 清单叶子名和锁定指标名不一致。证据：绿灯 `acca0f58`；测试 `tests/unit/diagnosis/test_leaf_aliases.py::test_leaf_aliases_do_not_change_json_keys`、`test_level2_reads_aliased_leaves_from_locked_keys`。
- [x] 环比方向。证据：绿灯 `c28dd964`；测试 `tests/unit/diagnosis/test_weight_and_direction.py::test_direction_is_the_sign_and_ignores_five_percent_bands`、`test_multi_hit_fixture_sorts_top5_and_grades_direction_hits`。
- [ ] 真实数仓 / :8787。缺：没有数仓连接，也没有 :8787 服务。
