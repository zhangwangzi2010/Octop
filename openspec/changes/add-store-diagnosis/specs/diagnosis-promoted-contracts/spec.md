## ADDED Requirements

### Requirement: 一店一文件约定
已由用户批准从参考升格为契约。

快照落库 MUST 遵循一店一文件（schema v2）。症状规格「快照与可重放」与 `proposal.md` 写的是「一店一文件快照（schema v2）」。kickoff §7.5 写的是「一店一文件 schema v2」。`.harness/domains/store-diagnosis-baseline.md` 把这次写入称为「版本化快照」。

本契约的路径约定停在上述原文：每家店铺一份 schema v2 快照。kickoff §3.4 已写出的快照文件路径是 `{data_dir}/{shop_id}.json`。已由用户批准从参考升格为契约。该句不带版本路径段。

#### Scenario: 每店一份快照
- **WHEN** 两家店铺各自完成取数落库
- **THEN** 每家店铺各有一份 schema v2 快照

#### Scenario: 快照路径使用已写出的模板
- **WHEN** 核对一店一文件的路径约定
- **THEN** 路径是 `{data_dir}/{shop_id}.json`，并且没有版本路径段

### Requirement: 十项二级指标名
已由用户批准从参考升格为契约。

二级指标名 MUST 使用 `.harness/domains/store-diagnosis-baseline.md` 指标白名单的下列 10 个写法，顺序如下。`performance_indicator` 是 kickoff §7.1 写出的「二级指标名（行转列的键）」。这些名字是指标名，本契约不把它们声明为 JSON 键。

1. 用户评价分
2. 非买家责任退货退款率
3. 延迟发货率
4. 延迟到货率
5. 缺货率
6. 24小时回复率
7. 售后准时率
8. 爆旺款率
9. 售罄健康分
10. 活动报名率

承载这 10 个名字的主表，按同一基线原文是 `ai_nlsql.dwd_sto_temu_store_performance_df`，分区 `ds=max_pt`，业务时间 `business_date`。绩效侧键是 `store_id` / `store_name`。

kickoff §7.1 表格把第 6 项写作「24 小时回复率」，并给出下列语义层 metric id。两种写法都按原文保留。metric id 用表格里的短 id，不给其余八项追加来源没有逐项写出的前缀。

| 二级指标名（kickoff 表格原文） | 语义层 metric id |
|---|---|
| 用户评价分 | `temu_store_user_review_score` |
| 非买家责任退货退款率 | `temu_store_non_buyer_fault_return_refund_rate` |
| 延迟发货率 | `temu_store_late_shipment_rate` |
| 延迟到货率 | `temu_store_late_delivery_rate` |
| 缺货率 | `temu_store_out_of_stock_rate` |
| 24 小时回复率 | `temu_store_24h_reply_rate` |
| 售后准时率 | `temu_store_after_sales_on_time_rate` |
| 爆旺款率 | `temu_store_hot_product_rate` |
| 售罄健康分 | `temu_store_sellout_health_score` |
| 活动报名率 | `temu_store_campaign_registration_rate` |

kickoff 另把其中两项写成带前缀的 id：`ecommerce.metric.temu_store_user_review_score`、`ecommerce.metric.temu_store_sellout_health_score`。

店铺绩效分不在这 10 个名字里。kickoff §7.1 的 C-S06 把它写成可下钻到这 10 项的绩效分，表格中的语义层 metric id 是 `store_performance_score_average`。同节指标定义另有 `ecommerce.metric.store_performance_score_average`，说明是「店铺绩效分均值」。

本条只升格名字、主表、分区、业务时间和上表 metric id。同表里的权重与阈值百分数不在本条。

#### Scenario: 十个名字按白名单核对
- **WHEN** 核对二级指标名
- **THEN** 名单依次是用户评价分、非买家责任退货退款率、延迟发货率、延迟到货率、缺货率、24小时回复率、售后准时率、爆旺款率、售罄健康分、活动报名率

#### Scenario: 回复率的两种写法都保留
- **WHEN** 对照白名单「24小时回复率」与 kickoff 表格「24 小时回复率」
- **THEN** 两处字符串都在契约中；`temu_store_24h_reply_rate` 写在 kickoff 表格那一行旁边，契约不另声明两处共用一个 JSON 键

#### Scenario: 名字落在绩效主表的指标名键上
- **WHEN** 读取这 10 个二级指标名
- **THEN** 行键字段是 `performance_indicator`，主表是 `ai_nlsql.dwd_sto_temu_store_performance_df`

### Requirement: Q4 的 latest、over_peers、next_level
已由用户批准从参考升格为契约。

Q4 在症状规格中的名称是「Q4 二级指标快照」。kickoff §7.3 把同一查询写作 `Q4_level2_snapshot`。其粒度是主体 × 店铺。核心输出 MUST 覆盖 10 项二级指标 × {最新值, 超过同行, 下一级标准}，共 30 列。时间口径是每店铺每指标最近一天有值。展示形态是表格。`.harness` 的 Q4 输出名 MUST 保留 `latest`、`over_peers`、`next_level`。

`.harness/domains/store-diagnosis-baseline.md` 把 Q4 指标快照写成：每店铺每指标各自最近有值记录，输出 `latest` / `over_peers` / `next_level`。

同一基线写出的指标值字段是：

| 字段 | 用途 |
|---|---|
| `indicator_data_detail` | 指标最新值 |
| `indicator_data_over_peers_rate` | 超过同行水平 |
| `indicator_data_next_level_threshold` | 下一级标准 |

每项二级指标还有同构语义 metric：`{id}`、`{id}_over_peers`、`{id}_next_level`。`{id}` 是来源里的占位写法。

上述字符串按出处保留。`latest` 与 `indicator_data_detail`、`over_peers` 与 `indicator_data_over_peers_rate`、`next_level` 与 `indicator_data_next_level_threshold` 是不同出处的不同字符串。`最新值` 与 `指标最新值`、`超过同行` 与 `超过同行水平` 也按原文分别保留。

#### Scenario: Q4 输出三个英文名
- **WHEN** 核对 Q4 指标快照的输出
- **THEN** 输出名是 `latest`、`over_peers`、`next_level`

#### Scenario: Q4 同时保留中文三元组
- **WHEN** 核对 `Q4_level2_snapshot`
- **THEN** 每个二级指标带有最新值、超过同行、下一级标准，10 项合计 30 列

#### Scenario: 三个物理字段按原文核对
- **WHEN** 核对语义层指标值字段
- **THEN** 字段是 `indicator_data_detail`、`indicator_data_over_peers_rate`、`indicator_data_next_level_threshold`，用途依次是指标最新值、超过同行水平、下一级标准

### Requirement: 评价、售后、发货、到货四类明细
已由用户批准从参考升格为契约。

明细模板 MUST 使用 kickoff §7.3 写出的 4 类：评价、售后、发货、到货。

物理表按来源原文如下。发货与到货没有各自独立的第二张表名。

| 模板 | 物理表 | 来源挂接 |
|---|---|---|
| 评价 | `dwd_prd_temu_review_detail_df` | kickoff §7.2「C-S07 评价分」；harness 下钻表「评价」；粒度「商品评价一行」；时间字段 `business_date` |
| 售后 | `dwd_trd_temu_refund_detail_df` | kickoff §7.2「C-S08 退款率」；可下钻项「非买家责任退货退款率」对应售后明细；harness 下钻表「售后」；粒度「售后单 × SKU 一行」；时间字段 `business_date` |
| 发货 | `dwm_robot_self_order_detail_df` | kickoff §7.2 将 C-S09 与 C-S10 都挂在这张履约表；harness 称该表为「履约」 |
| 到货 | `dwm_robot_self_order_detail_df` | 与发货同一张履约表 |

需求 §6.3 的四个触发项用词不改，与四类模板的对照是：

| 需求 §6.3 触发项 | 明细模板 |
|---|---|
| 店铺绩效异常 | 评价。其范围包含商品评价、物流履约、客户服务、店铺运营等 10 项二级子指标；评价模板对应该范围中的评价类 |
| 非买家责任退款退货率 | 售后 |
| 延迟发货（48小时发货） | 发货 |
| 延迟到货 | 到货 |

这张对照保留两边的原文。需求用词、检查单叶子和十项指标名仍然是不同字符串。

履约表侧键是 `shop_id` / `shop_name`。该表无 `business_date`。kickoff §7.2 的时间字段是 `order_time` / `pay_time`。harness 写的是订单、支付、签收字段。kickoff 写明该表有 139 列，列名清单不在来源中。

延迟发货率口径：分母为已发货且 `ship_time IS NOT NULL`，分子为 `parent_shipping_time > expect_ship_latest_time`。延迟到货率口径：分母为 `parent_receipt_time IS NOT NULL`，分子为 `parent_receipt_time > latest_delivery_time`。kickoff 另写 `ship_time IS NOT NULL` 与 `sub_order_status_name = '已发货'` 实测等价。

kickoff §7.3 写出不可下钻、因而没有这四类明细的 6 项：缺货率、24 小时回复率、售后准时率、爆旺款率、售罄健康分、活动报名率。同一 kickoff 的 §7.1 又对活动报名率标注「报名 SPU」。两处原文都保留。四类模板仍是评价、售后、发货、到货。

#### Scenario: 四类模板名
- **WHEN** 核对明细模板
- **THEN** 四个名字是评价、售后、发货、到货

#### Scenario: 发货与到货共用履约表
- **WHEN** 核对发货和到货的物理表
- **THEN** 两者都是 `dwm_robot_self_order_detail_df`

#### Scenario: 需求 6.3 用词保持原样
- **WHEN** 把四类模板对照需求 §6.3
- **THEN** 触发项仍是店铺绩效异常、非买家责任退款退货率、延迟发货（48小时发货）、延迟到货

#### Scenario: 履约口径使用已写出的字段
- **WHEN** 计算延迟发货率或延迟到货率
- **THEN** 延迟发货率使用 `ship_time IS NOT NULL` 与 `parent_shipping_time > expect_ship_latest_time`，延迟到货率使用 `parent_receipt_time IS NOT NULL` 与 `parent_receipt_time > latest_delivery_time`
