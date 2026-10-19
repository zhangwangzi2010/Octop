---
name: query_tasks
description: 店铺诊断 Q1 到 Q5 查询任务。不写 SQL。
---

query_tasks。Q1 到 Q5 用已锁定名称。不写 SQL。
Q1 主体汇总
Q2 店铺快照
Q3 近 60 天评分趋势
Q4 二级指标快照
Q5 三个月指标趋势
Q3 窗口天数 60。不含今天。
Q4 输出 latest、over_peers、next_level。
Q4 列 最新值、超过同行、下一级标准。
Q4 字段 indicator_data_detail 指标最新值
Q4 字段 indicator_data_over_peers_rate 超过同行水平
Q4 字段 indicator_data_next_level_threshold 下一级标准
快照 {data_dir}/{shop_id}.json。无版本段。
预加载在 COMPLETED 且 row_count > 0 时消费。RUNNING 不重复灌数。FAILED 可以重试。
