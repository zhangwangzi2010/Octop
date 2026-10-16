# Store Diagnosis Domain Baseline

## 权威顺序

1. 飞书需求文档 `GTPJdXujnom2WnxgUFVcU2Bonsb`。
2. 飞书架构 wiki `UGlmwS7rsiqRs2kKpcEcLwuInbU`。
3. OpenSpec change `add-store-diagnosis`。
4. data_agent 语义层与店铺绩效 demo 的实测口径。

本文件只提供实现前事实参考。若与 OpenSpec 需求冲突，先更新 OpenSpec，再实现。

## 固定链路原则

- Octop 店铺诊断使用固定 Query/SQL 构造链路，不引入 RAG 检索、向量召回或自然语言自由生成 SQL。
- 语义层 YAML 是指标、物理表、维度、时间语义和公式的口径来源；Octop 只蒸馏店铺诊断需要的白名单子集。
- SQL 只能由受控模板、字段白名单、参数绑定和固定指标选择构造；LLM 不生成 SQL。
- RAG 相关实现可读取为语义资产设计参考，不移植 embedding、rerank、Chroma 或动态检索运行时。

## 参考来源

| 来源 | 用途 |
|---|---|
| `data_agent_total_zhilong/backend/app/plugins/rag_retrieval/resources/semantic_layer/` | 指标、表、维度、时间语义 |
| `backend/app/plugins/sql_generator/sql_generator.py` | 分区裁剪、时间语义、白名单和 SQL 组装的纪律参考 |
| `backend/app/skills_analysis/store_performance_analysis/` | 固定 Q1~Q5、下钻、预加载、分析、报告逻辑 |
| `Octop_grokbot/skill-verify/store-diagnosis-0to1-launch-prompt.md` | 已提炼的启动契约 |

## 语义层要点

- 主表：`ai_nlsql.dwd_sto_temu_store_performance_df`，分区 `ds=max_pt`，业务时间 `business_date`。
- 主维度：主体、店铺、业务日期、指标名；绩效侧键为 `store_id`/`store_name`。
- 指标值：`indicator_data_detail`、`indicator_data_over_peers_rate`、`indicator_data_next_level_threshold`；绩效分与等级用 `mall_check_score`、`score_level`。
- 指标白名单：用户评价分、非买家责任退货退款率、延迟发货率、延迟到货率、缺货率、24小时回复率、售后准时率、爆旺款率、售罄健康分、活动报名率。
- 每项二级指标有 `{id}`、`{id}_over_peers`、`{id}_next_level` 同构语义 metric。
- 比率类源值通常为 0~1，展示与判定统一换算为百分比；只有延迟发货率在语义层显式标注 scale 时也要全指标统一应用实测口径。

## 查询与计算

| 查询 | 口径 |
|---|---|
| Q1 主体汇总 | 最新分区 + 最新业务日期，主体等级由有分店铺平均分套阈值 |
| Q2 店铺快照 | 每店铺最近有评分记录，`ROW_NUMBER` 按 `business_date DESC` |
| Q3 分数趋势 | 最近 60 天，不含今天 |
| Q4 指标快照 | 每店铺每指标各自最近有值记录，输出 latest/over_peers/next_level |
| Q5 指标趋势 | 最近 3 个月，不含今天 |

等级：≥4.3 优秀，≥4 正常，≥3.5 低危，<3.5 高危。共性命中占比 ≥40%；个体 P0 为个体权重 ≥30% 或绩效分 <3.5，P1 为 15%~30%，P2 为 <15%；影响度 = 权重 × 命中率。

延迟发货率：分母已发货且 `ship_time IS NOT NULL`，分子 `parent_shipping_time > expect_ship_latest_time`。延迟到货率：分母 `parent_receipt_time IS NOT NULL`，分子 `parent_receipt_time > latest_delivery_time`。

## 预加载与分析

demo 的可靠边界值得保留：定时任务只幂等发起 preload 并立即返回 job；后台任务从 MaxCompute 读取固定数据集，写入版本化快照并记录 row counts 与终态；分析只消费 `COMPLETED` 且行数大于 0 的 data version。`RUNNING` 禁止重复提交补数，`FAILED` 允许人工重试；HTTP 异常输出固定错误，不让 LLM 编造状态。

Octop 落地仍按飞书 wiki：流程 A 由 `DiagnosisOrchestrator` 驱动 ensure data ready、analysis、snapshot 与状态事件；流程 B 只对异常项做两段式归因。demo 的 PG/Redis 进程形态不直接移植。

## SQL 构造参考

- 绩效快照使用固定 SELECT、CTE `max_ds`、`ROW_NUMBER` 和指标 CASE/IN 白名单。
- 下钻表：评价 `dwd_prd_temu_review_detail_df`，售后 `dwd_trd_temu_refund_detail_df`，履约 `dwm_robot_self_order_detail_df`。
- 订单履约侧键为 `shop_id`/`shop_name`，无 `business_date`，时间用订单/支付/签收字段。
- 售后原因先按英文逗号拆分，再归并为固定 6 大类；映射表必须作为受控资产，不能由模型推断。
- 明细默认 Top N，完整单据只进 Excel/附件，不进入 LLM 上下文。
