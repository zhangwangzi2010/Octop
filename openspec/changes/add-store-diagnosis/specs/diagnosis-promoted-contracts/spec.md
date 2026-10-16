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

二级指标名 MUST 使用 `.harness/domains/store-diagnosis-baseline.md` 指标白名单的下列 10 个写法，顺序如下。`performance_indicator` 是 kickoff §7.1 写出的「二级指标名（行转列的键）」。这些名字是指标名。快照 JSON 键的写法见「快照 JSON 键」；本条仍只登记名字与 metric id。

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

### Requirement: 快照 JSON 形状
已由用户批准从参考升格为契约。

kickoff §3.4 快照文件的形状 MUST 按原文登记：店铺/主体/负责人 + `store_performance{perf_score, score_level, metrics[10]}`。

嵌套是：店铺、主体、负责人与对象 `store_performance` 同级；`store_performance` 含 `perf_score`、`score_level`、`metrics`；`metrics` 的写法是 `metrics[10]`。这些是该形状写出的字段。

`score_level` 只作为 `store_performance` 里的形状字段。本条不登记 `mall_check_score`，也不把等级取值、比率量纲或 `thresholds.json` 写成单独契约。同一句后半的「比率 0~100」和「命中标注运行时按 thresholds.json 计算」不在本条。

#### Scenario: 形状按原文核对
- **WHEN** 读取快照 JSON 形状
- **THEN** 字段是店铺、主体、负责人，以及 `store_performance` 下的 `perf_score`、`score_level`、`metrics[10]`

#### Scenario: score_level 只留在形状内
- **WHEN** 核对 `score_level`
- **THEN** 它只出现在 `store_performance` 的形状字段中

### Requirement: 快照 JSON 键
已由用户批准从参考升格为契约。

`metrics[10]` 的十个条目 MUST 使用 kickoff §7.1 表格中的指标名作为 JSON 键。kickoff 写法与白名单不同时，JSON 键用 kickoff 写法，另一处写法只作对照，不并成同一个键。

| JSON 键（kickoff 表格） | 对照 |
|---|---|
| 用户评价分 | 与白名单相同 |
| 非买家责任退货退款率 | 需求 §6.3 写作「非买家责任退款退货率」 |
| 延迟发货率 | 与白名单相同 |
| 延迟到货率 | 与白名单相同 |
| 缺货率 | 与白名单相同 |
| 24 小时回复率 | 白名单写作「24小时回复率」 |
| 售后准时率 | 与白名单相同 |
| 爆旺款率 | 与白名单相同 |
| 售罄健康分 | 与白名单相同 |
| 活动报名率 | 与白名单相同 |

每个指标键下面的 Q4 短名 MUST 保留为 JSON 键：`latest`、`over_peers`、`next_level`。这三个短名来自 harness 的 Q4 输出和本规格「Q4 的 latest、over_peers、next_level」。

对照按原文另列，不互相改写：

- kickoff §3.4 的 data_refs 路径是 `metrics.<指标名|key>.<latest|prev|weight>`。`latest` 与上面的 JSON 键同字。`prev` 与 `weight` 是该路径里的另外两个词。
- Q4 中文仍是最新值、超过同行、下一级标准。
- 物理列仍是 `indicator_data_detail`、`indicator_data_over_peers_rate`、`indicator_data_next_level_threshold`。

#### Scenario: 十个指标键用 kickoff 写法
- **WHEN** 核对 `metrics[10]` 的 JSON 键
- **THEN** 键是用户评价分、非买家责任退货退款率、延迟发货率、延迟到货率、缺货率、24 小时回复率、售后准时率、爆旺款率、售罄健康分、活动报名率

#### Scenario: 回复率两种写法不并成一个键
- **WHEN** 对照 JSON 键「24 小时回复率」与白名单「24小时回复率」
- **THEN** 快照键用「24 小时回复率」，白名单写法留在对照中

#### Scenario: 退款用词不并成一个键
- **WHEN** 对照 JSON 键「非买家责任退货退款率」与需求 §6.3「非买家责任退款退货率」
- **THEN** 快照键用「非买家责任退货退款率」，需求用词留在对照中

#### Scenario: Q4 短名是指标键下的 JSON 键
- **WHEN** 读取一个二级指标键下的字段
- **THEN** 其中有 `latest`、`over_peers`、`next_level`，并且这三项不改写成 `indicator_data_detail`、`indicator_data_over_peers_rate`、`indicator_data_next_level_threshold`

### Requirement: 比率量纲
已由用户批准从参考升格为契约。唯一验收常量是：内部保存 0~1，对外展示与判定统一 ×100 换成百分比。

比率指标 MUST 按这一条执行。用户评价分与售罄健康分是分值直通，不做比率换算。`over_peers_rate` 与 `next_level_threshold` 跟随同一指标的量纲。

§3.4「比率 0~100」与 §7.1 / §7.3「0~1 再 ×100」折成这一条，不再两套并存。§3.4 的「0~100」只作参照，不是第二套存储量纲。

#### Scenario: 比率内部 0~1、对外乘 100
- **WHEN** 保存一项比率，或展示、判定这项比率
- **THEN** 内部值是 0~1，展示和判定使用该值 ×100 的百分比

#### Scenario: 两个分值不按比率换算
- **WHEN** 处理用户评价分或售罄健康分
- **THEN** 按分值直通，不套用 0~1 到百分比的换算

### Requirement: 命中标注使用 thresholds.json
已由用户批准从参考升格为契约。

kickoff §3.4 写明：命中标注运行时按 thresholds.json 计算。

#### Scenario: 命中标注不改写这句
- **WHEN** 核对快照上的命中标注
- **THEN** 契约写的是运行时按 thresholds.json 计算

### Requirement: C-S09、C-S12、C-S13 阈值
已由用户批准从参考升格为契约。唯一验收常量是来源 A：C-S09 ≥10%，C-S12 <90%，C-S13 <95%。

来源 B 与症状规格里的另一列只作参照，不是验收常量：C-S09 ≥2%（超同行 70%）、C-S12 <100%、C-S13 <100%，以及症状规格原先的「C-S09 ≥2%、C-S12 <90%、C-S13 <95%」。kickoff 的「以 B 为主 / 以 A 为主」同样只作参照。

#### Scenario: 验收只用来源 A
- **WHEN** 核对这三项阈值
- **THEN** 验收常量是 C-S09 ≥10%、C-S12 <90%、C-S13 <95%，来源 B 的 ≥2% 与 <100% 不是验收常量

### Requirement: 等级取值
已由用户批准从参考升格为契约。

两处原文都登记：

- harness：≥4.3 优秀，≥4 正常，≥3.5 低危，<3.5 高危。
- kickoff §7.3：<3.5 高危 / 3.5~4 低危 / 4~4.3 正常 / ≥4.3 优秀。店铺维度用店铺绩效分，主体维度用主体平均分。

#### Scenario: 四档名称和切分数字都在
- **WHEN** 核对等级取值
- **THEN** 契约有高危、低危、正常、优秀，以及 3.5、4、4.3

### Requirement: mall_check_score 与 perf_score
已由用户批准从参考升格为契约。店铺绩效分的规范字段是 `mall_check_score`。形状字段 `perf_score` 是同一含义的别名，也是旧键。

`mall_check_score` MUST 作为规范名。`perf_score` 仍出现在已登记的快照形状里，只表示这个别名，不再与规范名并列为未裁决的两个字段。

#### Scenario: 规范名是 mall_check_score
- **WHEN** 核对店铺绩效分的字段名
- **THEN** 规范名是 `mall_check_score`，`perf_score` 是它的别名 / 旧键

### Requirement: 无版本段
已由用户批准从参考升格为契约。

来源没有写出快照路径的版本段。路径保持 `{data_dir}/{shop_id}.json`。本需求登记为无版本段。

#### Scenario: 路径没有版本段
- **WHEN** 核对快照路径是否带版本段
- **THEN** 契约写明无版本段，路径仍是 `{data_dir}/{shop_id}.json`

### Requirement: 商品策略指标名
来源写明商品策略指标名待补，没有给出指标名清单。本项阻断。不编造指标名。

#### Scenario: 没有指标名清单
- **WHEN** 核对商品策略指标名
- **THEN** 契约写明阻断，并且没有商品策略指标名清单

### Requirement: 履约表列名清单
kickoff §7.2 写明 `dwm_robot_self_order_detail_df`（139 列）。来源没有这 139 个列名。本项登记为列名待完整清单，不编造列名。本项阻断。

#### Scenario: 只有列数没有列名
- **WHEN** 核对履约表列名
- **THEN** 契约有「139 列」和「列名待完整清单」，并且没有逐列名单

### Requirement: 售后六大类
已由用户批准从参考升格为契约。升格的是来源已经写出的归并规则，不是六个类名。

- harness：售后原因先按英文逗号拆分，再归并为固定 6 大类；映射表必须作为受控资产，不能由模型推断。
- kickoff §7.3：售后 26 原因 → 6 大类。

六个类名在来源中没有列出。类名清单阻断，不编造类名。

#### Scenario: 归并规则按原文核对
- **WHEN** 核对售后原因归并
- **THEN** 契约有英文逗号拆分、固定 6 大类、26 原因 → 6 大类，以及映射表必须作为受控资产

#### Scenario: 六个类名没有清单
- **WHEN** 核对六个类名
- **THEN** 契约写明类名清单阻断，并且没有六个类名

### Requirement: 明细条数
已由用户批准从参考升格为契约。唯一验收常量是「默认 Top N + 完整进附件」。

明细 MUST 默认 Top N。完整单据只进入 Excel 或附件，不进入 LLM 上下文。报告正文只写结论与占比。

kickoff「每店铺每类 Top 10」和「4 区块 × Top 10」是参照默认 N=10，并且可配置，不是写死的 Top 10。

#### Scenario: 验收是默认 Top N 加完整进附件
- **WHEN** 核对明细条数
- **THEN** 验收常量是默认 Top N，完整单据只进 Excel 或附件；Top 10 只是可配置的参照默认值

### Requirement: §3.4 的 run 切片、interpretation 与批次报告
已由用户批准从参考升格为契约。

kickoff §3.4 的三份形状按原文登记：

1. run 切片（`workspace diagnosis/<item_id>/checklists/<checklist>.json`）：单店单检查单；追加 grade / individual_* / common_issues / metrics[].hit|is_common。
2. interpretation 契约：headline / overall / findings[{title,severity,analysis,evidence[],data_refs[]}] / actions[{title,detail,priority?,owner_hint?}] / risks[]；data_refs 支持 `perf_score`、`metrics.<指标名|key>.<latest|prev|weight>`（label 与英文 key 双匹配）；value 必须与切片一致。
3. 批次报告：mode(single|multi) + coverage + common_issues[]（影响度降序）+ priority[]（P0→P1→P2→共性）+ stores[] 分店章节；五段结构（概览/共性问题/店铺明细=症状+归因/行动建议/附录 FAIL·SKIPPED）。

#### Scenario: 三份形状按原文核对
- **WHEN** 核对这三份形状
- **THEN** 契约含 run 切片路径、interpretation 的 headline / overall / findings / actions / risks，以及批次报告的 mode、coverage、common_issues、priority、stores 和五段结构

### Requirement: prev、weight 与 over_peers、next_level
已由用户批准从参考升格为契约。

来源没有把 `prev` 写成 `over_peers` 的别名，也没有把 `weight` 写成 `next_level` 的别名。data_refs 路径中的 `latest|prev|weight` 与 Q4 短名 `latest` / `over_peers` / `next_level` 保持为两套词。本需求不合并这些键。

#### Scenario: 两套词不合并
- **WHEN** 对照 `prev` 与 `over_peers`，以及 `weight` 与 `next_level`
- **THEN** 契约写明它们不是别名，并且没有把两边收成同一个键

### Requirement: 一级取数到语义层的底表映射
已由用户批准从参考升格为契约。下面六条是唯一验收常量。

1. 整体下滑（GMV / 销量 / 订单）读取订单明细的 `sales_amount` / `sales_quantity` / `order_count`。
2. 品类、售龄、策略、Top 切片读取 SPU 概览的 `spu_sold_amount` / `spu_sold_quantity` / `spu_order_count`，以及该切片对应的切片度量。
3. 动销 SPU 是 `active_spu_count`。在售是 `on_sale_spu_count`。品类维度是 `spu_category`。
4. 售龄是 `ads_bi_temu_spu_overview_self_df.min_first_join_time` 与当前时间的差。四档是 0–10 / 11–29 / 30–89 / ≥90 天。第 30 天属于 30–90 档。
5. 售龄的动销率是 `ecommerce.metric.active_spu_rate`，并按售龄档过滤。
6. 五条黄标不查询、不替代。症状判定和归因把它们标为「指标及相关明细空缺」。这五条仍是库存、推广 roas、流量异常（建议调价未调价）、流量异常SPU数占比、推广 Roas。

环比、贡献、权重一类展示值是派生在诊断侧、语义层无同名 metric。本需求不冻结环比、贡献或权重的计算公式。策略切片没有写出独立指标名，不编造商品策略指标名。

#### Scenario: 整体下滑读取订单明细
- **WHEN** 取整体下滑的 GMV、销量或订单
- **THEN** 读取的字段是 `sales_amount`、`sales_quantity`、`order_count`

#### Scenario: 切片读取 SPU 概览
- **WHEN** 取品类、售龄、策略或 Top 切片
- **THEN** 读取 `spu_sold_amount`、`spu_sold_quantity`、`spu_order_count`

#### Scenario: 动销、在售和品类维度
- **WHEN** 核对动销 SPU、在售和品类维度
- **THEN** 它们分别是 `active_spu_count`、`on_sale_spu_count`、`spu_category`

#### Scenario: 售龄按加入时间分四档
- **WHEN** 计算售龄
- **THEN** 用 `ads_bi_temu_spu_overview_self_df.min_first_join_time` 与当前时间的差，四档是 0–10、11–29、30–89、≥90 天，并且第 30 天属于 30–90 档

#### Scenario: 售龄动销率按档过滤
- **WHEN** 取售龄下的动销率
- **THEN** 度量是 `ecommerce.metric.active_spu_rate`，并按售龄档过滤

#### Scenario: 黄标不查询也不替代
- **WHEN** 症状判定或归因遇到五条黄标之一
- **THEN** 不查询、不替代，并标为「指标及相关明细空缺」

#### Scenario: 环比贡献权重不冻结公式
- **WHEN** 展示值是环比、贡献或权重
- **THEN** 该值标为派生在诊断侧、语义层无同名 metric，并且契约没有环比、贡献或权重的计算公式

### Requirement: 症状规则引擎的确定性判定
已由用户批准从参考升格为契约。本条只把已经锁定的常量收成可测判定。不新增阈值百分数、公式或指标名。黄标的 `fetchable`、环比分档、ABCD 常量和一级取数映射都不改。

判定 MUST 由确定性代码完成。AI 只写摘要，MUST NOT 出现在判定路径上，也 MUST NOT 改写命中、共性、分级或影响度。

引擎只组合下列已锁定常量。

- C-S09、C-S12、C-S13 只用来源 A：≥10% / <90% / <95%。判定对象用已登记的名字：C-S09 是延迟发货率，C-S12 是「24 小时回复率」，C-S13 是售后准时率。白名单「24小时回复率」仍只是对照写法。来源 B 与旧列仍不是验收常量。
- 这三项是比率。判定使用内部值 ×100 后的百分比。用户评价分与售罄健康分仍是分值直通。
- 共性标记是命中率 ≥40%。共性命中率的分子和分母见「二级指标命中线与权重」。≥40% 这条不改。
- 个体分级：P0 是个体权重 ≥30%，或绩效分 <3.5。绩效分的规范字段是 `mall_check_score`。P2 是个体权重 <15%，且绩效分不满足 <3.5。P1 是「15%~30%」与这两条相邻不等式的组合：个体权重不满足 <15%，也不满足 ≥30%，且绩效分不满足 <3.5。这里没有新的百分数。各指标权重见「二级指标命中线与权重」。P0、P1、P2 的切分不改。
- 影响度 = 权重 × 命中率。已算出的影响度按降序排列，顺序与手算一致。
- 等级沿用已登记切分：<3.5 高危，≥3.5 低危，≥4 正常，≥4.3 优秀。端点归入更高一档，因此 3.5 是低危，4 是正常，4.3 是优秀。店铺维度用店铺绩效分，主体维度用主体平均分。
- 五条黄标沿用「黄标不查询也不替代」：不查询、不替代，判定和归因标「指标及相关明细空缺」。

没有锁定常量的规则列为未覆盖。引擎 MUST NOT 为它们写出占位百分数，也 MUST NOT 编造名字。未覆盖的是：商品策略指标名、履约表 139 个列名、六个售后类名。C-S07 到 C-S16 的命中线与权重见「二级指标命中线与权重」，不再列在这里。环比公式与下滑分档沿用已有场景，本条不改。

#### Scenario: AI 不在判定路径上
- **WHEN** 症状引擎判定命中、共性、分级或影响度
- **THEN** 判定由确定性代码完成；AI 只写摘要，并且摘要不改变这些判定

#### Scenario: 延迟发货率达到 10% 命中
- **WHEN** 延迟发货率的判定百分比满足 ≥10%，包括等于 10%
- **THEN** C-S09 命中

#### Scenario: 延迟发货率未达到 10% 不命中
- **WHEN** 延迟发货率的判定百分比不满足 ≥10%
- **THEN** C-S09 不命中

#### Scenario: 内部 0.1 按 10% 判定
- **WHEN** 延迟发货率的内部值是 0.1
- **THEN** 判定使用 0.1 × 100 得到的 10%，并且 C-S09 命中

#### Scenario: 回复率低于 90% 命中
- **WHEN** 「24 小时回复率」的判定百分比满足 <90%
- **THEN** C-S12 命中

#### Scenario: 回复率不低于 90% 不命中
- **WHEN** 「24 小时回复率」的判定百分比不满足 <90%，包括等于 90%
- **THEN** C-S12 不命中

#### Scenario: 售后准时率低于 95% 命中
- **WHEN** 售后准时率的判定百分比满足 <95%
- **THEN** C-S13 命中

#### Scenario: 售后准时率不低于 95% 不命中
- **WHEN** 售后准时率的判定百分比不满足 <95%，包括等于 95%
- **THEN** C-S13 不命中

#### Scenario: 命中率达到 40% 标为共性
- **WHEN** 命中率满足 ≥40%，包括等于 40%
- **THEN** 标为共性

#### Scenario: 命中率未达到 40% 不标共性
- **WHEN** 命中率不满足 ≥40%
- **THEN** 不标为共性

#### Scenario: 权重达到 30% 为 P0
- **WHEN** 个体权重满足 ≥30%
- **THEN** 个体分级是 P0

#### Scenario: 绩效分低于 3.5 为 P0
- **WHEN** `mall_check_score` 满足 <3.5
- **THEN** 个体分级是 P0，即使个体权重不满足 ≥30%

#### Scenario: 权重落在 P1
- **WHEN** 个体权重不满足 <15%，也不满足 ≥30%，且 `mall_check_score` 不满足 <3.5
- **THEN** 个体分级是 P1

#### Scenario: 权重低于 15% 为 P2
- **WHEN** 个体权重满足 <15%，且 `mall_check_score` 不满足 <3.5
- **THEN** 个体分级是 P2

#### Scenario: 影响度等于权重乘命中率
- **WHEN** 计算影响度
- **THEN** 影响度等于权重乘以命中率。权重取「二级指标命中线与权重」，公式仍是权重 × 命中率

#### Scenario: 影响度按降序排列
- **WHEN** 对已经算出的影响度排序
- **THEN** 按影响度降序，顺序与手算一致

#### Scenario: 绩效分套用四档
- **WHEN** 用 `mall_check_score` 套等级
- **THEN** <3.5 为高危，满足 ≥3.5 且不满足 ≥4 为低危，满足 ≥4 且不满足 ≥4.3 为正常，满足 ≥4.3 为优秀

#### Scenario: 店铺与主体用各自的分
- **WHEN** 店铺维度或主体维度套用同一套四档
- **THEN** 店铺维度用店铺绩效分，主体维度用主体平均分

#### Scenario: 未覆盖规则不写占位百分数
- **WHEN** 规则属于未覆盖清单
- **THEN** 引擎不输出占位百分数，也不编造商品策略指标名、履约 139 个列名或六个售后类名

### Requirement: 二级指标命中线与权重
已由用户批准从参考升格为契约。来源是 kickoff §7.1 的 metrics_catalog。与已经锁定的 ABCD 常量冲突时，以 ABCD 为准。

C-S09、C-S12、C-S13 的命中线不改：仍是 ≥10% / <90% / <95%。目录里 C-S09 的 ≥2% 不是命中线。≥40% 的共性比较、P0 / P1 / P2、影响度 = 权重 × 命中率、黄标空缺、ABCD 常量和一级取数映射都不改。

下表是验收常量。比率先按内部 0~1 ×100 再比较。用户评价分与售罄健康分是分值直通，不乘 100。

| 编号 | 指标 | 权重 | 命中 |
|---|---|---|---|
| C-S07 | 用户评价分 | 10% | < 4 |
| C-S08 | 非买家责任退货退款率 | 10% | ×100 后 ≥ 5% |
| C-S09 | 延迟发货率 | 5% | ≥10% |
| C-S10 | 延迟到货率 | 10% | ×100 后 ≥ 3% |
| C-S11 | 缺货率 | 10% | 环比上升 |
| C-S12 | 「24 小时回复率」 | 5% | <90% |
| C-S13 | 售后准时率 | 5% | <95% |
| C-S14 | 爆旺款率 | 10% | 环比下降 |
| C-S15 | 售罄健康分 | 20% | < 95 |
| C-S16 | 活动报名率 | 15% | ×100 后 < 90% |

C-S09 的比率沿用已写出的字段：分子是 `parent_shipping_time > expect_ship_latest_time`，分母是已发货且 `ship_time IS NOT NULL`。C-S10 的比率沿用已写出的字段：分子是 `parent_receipt_time > latest_delivery_time`，分母是 `parent_receipt_time IS NOT NULL`。

没有单据级分子的比率不新写履约列。C-S08、C-S12、C-S13、C-S16 用最新值对上表阈值。C-S11、C-S14 只用环比方向。白名单「24小时回复率」仍只是对照写法。

共性命中率 MUST 等于该指标命中的店铺数，除以有可取数值且不是黄标空缺的店铺数。黄标空缺仍标「指标及相关明细空缺」，不进入分母。

主体平均分的字段 MUST 是 `entity_avg_mall_check_score`，等于各店 `mall_check_score` 的算术平均。店铺侧仍是 `mall_check_score`。

商品策略指标名、履约表 139 个列名、六个售后类名仍不编造。

#### Scenario: 评价分低于 4 命中
- **WHEN** 用户评价分满足 < 4
- **THEN** C-S07 命中，权重是 10%，并且不把分值乘 100

#### Scenario: 评价分等于 4 不命中
- **WHEN** 用户评价分等于 4
- **THEN** C-S07 不命中

#### Scenario: 退货退款率达到 5% 命中
- **WHEN** 非买家责任退货退款率的内部值经 ×100 后满足 ≥ 5%，包括等于 5%
- **THEN** C-S08 命中，权重是 10%

#### Scenario: 退货退款率未达到 5% 不命中
- **WHEN** 非买家责任退货退款率的判定百分比不满足 ≥ 5%
- **THEN** C-S08 不命中

#### Scenario: 延迟发货率的权重是 5%
- **WHEN** 核对 C-S09 的权重和比率字段
- **THEN** 权重是 5%，分子是 `parent_shipping_time > expect_ship_latest_time`，分母是已发货且 `ship_time IS NOT NULL`，命中线仍是 ≥10%，不是 ≥2%

#### Scenario: 延迟到货率达到 3% 命中
- **WHEN** 延迟到货率的内部值经 ×100 后满足 ≥ 3%，包括等于 3%
- **THEN** C-S10 命中，权重是 10%，分子是 `parent_receipt_time > latest_delivery_time`，分母是 `parent_receipt_time IS NOT NULL`

#### Scenario: 延迟到货率未达到 3% 不命中
- **WHEN** 延迟到货率的判定百分比不满足 ≥ 3%
- **THEN** C-S10 不命中

#### Scenario: 缺货率环比上升命中
- **WHEN** 缺货率的环比是上升
- **THEN** C-S11 命中，权重是 10%

#### Scenario: 缺货率环比不是上升不命中
- **WHEN** 缺货率的环比不是上升
- **THEN** C-S11 不命中，并且没有另写一个上升幅度百分数

#### Scenario: 回复率与售后准时率的权重是 5%
- **WHEN** 核对 C-S12 和 C-S13 的权重
- **THEN** 两者权重都是 5%，命中线仍是「24 小时回复率」<90% 与售后准时率 <95%

#### Scenario: 爆旺款率环比下降命中
- **WHEN** 爆旺款率的环比是下降
- **THEN** C-S14 命中，权重是 10%

#### Scenario: 爆旺款率环比不是下降不命中
- **WHEN** 爆旺款率的环比不是下降
- **THEN** C-S14 不命中，并且没有另写一个下降幅度百分数

#### Scenario: 售罄健康分低于 95 命中
- **WHEN** 售罄健康分满足 < 95
- **THEN** C-S15 命中，权重是 20%，并且不把分值乘 100

#### Scenario: 售罄健康分等于 95 不命中
- **WHEN** 售罄健康分等于 95
- **THEN** C-S15 不命中

#### Scenario: 活动报名率低于 90% 命中
- **WHEN** 活动报名率的内部值经 ×100 后满足 < 90%
- **THEN** C-S16 命中，权重是 15%

#### Scenario: 活动报名率不低于 90% 不命中
- **WHEN** 活动报名率的判定百分比不满足 < 90%，包括等于 90%
- **THEN** C-S16 不命中

#### Scenario: 没有单据级分子就不编造列
- **WHEN** 比率没有写出单据级分子
- **THEN** 用最新值对阈值，或只用环比方向，并且不新增履约列名

#### Scenario: 共性命中率只用可取数店铺
- **WHEN** 计算某指标的共性命中率
- **THEN** 分子是该指标命中的店铺数，分母是有可取数值且不是黄标空缺的店铺数

#### Scenario: 主体平均分是各店绩效分的平均
- **WHEN** 计算主体平均分
- **THEN** 字段是 `entity_avg_mall_check_score`，等于各店 `mall_check_score` 的算术平均；店铺侧仍是 `mall_check_score`
