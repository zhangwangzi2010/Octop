---
name: drilldown_playbook
description: 店铺诊断下钻手册。分流以 analysis_guide 为准，不另写命中线。
---

drilldown_playbook。下钻分流以 analysis_guide 为准，不另写命中线。
不内嵌查询语句，不写外部服务地址。
默认 Top N + 完整进附件。
可下钻 绩效分 路由 ai_nlsql.dwd_sto_temu_store_performance_df
可下钻 C-S07 路由 评价
可下钻 C-S08 路由 售后
可下钻 C-S09 路由 发货
可下钻 C-S10 路由 到货
不可下钻 C-S11 无明细下钻能力
不可下钻 C-S12 无明细下钻能力
不可下钻 C-S13 无明细下钻能力
不可下钻 C-S14 无明细下钻能力
不可下钻 C-S15 无明细下钻能力
不可下钻 C-S16 无明细下钻能力
明细 评价 dwd_prd_temu_review_detail_df
明细 售后 dwd_trd_temu_refund_detail_df
明细 发货 dwm_robot_self_order_detail_df
明细 到货 dwm_robot_self_order_detail_df
触发 店铺绩效异常 → 评价
触发 非买家责任退款退货率 → 售后
触发 延迟发货（48小时发货） → 发货
触发 延迟到货 → 到货
售后类名 1-物流履约、2-产品满意度、3-商品价格、4-店铺原因、5-平台原因、6-其他原因。
9-未分类不进入类名。
C-S09 单据分子 parent_shipping_time > expect_ship_latest_time 分母 已发货且 ship_time IS NOT NULL
C-S10 单据分子 parent_receipt_time > latest_delivery_time 分母 parent_receipt_time IS NOT NULL
履约侧键 shop_id、shop_name。
履约时间 order_time、pay_time。
履约表没有 business_date。
履约 139 列为空。
商品策略额外指标名为空。
分流表复用 analysis_guide：
下钻分流。阈值和权重用已锁定命中线。
可下钻：绩效分、用户评价分（C-S07）、非买家责任退货退款率（C-S08）、延迟发货率（C-S09）、延迟到货率（C-S10）。
不可下钻：缺货率（C-S11）、24 小时回复率（C-S12）、售后准时率（C-S13）、爆旺款率（C-S14）、售罄健康分（C-S15）、活动报名率（C-S16）。无明细下钻能力。
C-S07 用户评价分 权重 10% 命中 < 4
C-S08 非买家责任退货退款率 权重 10% 命中 ×100 后 ≥ 5%
C-S09 延迟发货率 权重 5% 命中 ≥10%
C-S10 延迟到货率 权重 10% 命中 ×100 后 ≥ 3%
C-S11 缺货率 权重 10% 命中 环比上升
C-S12 24 小时回复率 权重 5% 命中 <90%
C-S13 售后准时率 权重 5% 命中 <95%
C-S14 爆旺款率 权重 10% 命中 环比下降
C-S15 售罄健康分 权重 20% 命中 < 95
C-S16 活动报名率 权重 15% 命中 ×100 后 < 90%
