---
name: metrics_catalog
description: 店铺诊断指标清单与已锁定阈值。本资产是唯一事实源。
---

metrics_catalog。唯一事实源。阈值和权重用已锁定常量。
量纲 0~1，展示与判定乘 100。
分值直通 用户评价分、售罄健康分。
绩效分规范名 mall_check_score。
绩效分别名 perf_score 不是同一个字段。
绩效分语义 store_performance_score_average、ecommerce.metric.store_performance_score_average。
共性阈值 40%。
环比方向正号为上升，负号为下降。
影响度等于权重乘以命中率。
≥4.3 优秀，≥4 正常，≥3.5 低危，<3.5 高危
<3.5 高危 / 3.5~4 低危 / 4~4.3 正常 / ≥4.3 优秀。店铺维度用店铺绩效分，主体维度用主体平均分。
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
语义 用户评价分 temu_store_user_review_score
语义 非买家责任退货退款率 temu_store_non_buyer_fault_return_refund_rate
语义 延迟发货率 temu_store_late_shipment_rate
语义 延迟到货率 temu_store_late_delivery_rate
语义 缺货率 temu_store_out_of_stock_rate
语义 24 小时回复率 temu_store_24h_reply_rate
语义 售后准时率 temu_store_after_sales_on_time_rate
语义 爆旺款率 temu_store_hot_product_rate
语义 售罄健康分 temu_store_sellout_health_score
语义 活动报名率 temu_store_campaign_registration_rate
叶名只读别名，JSON 键不改。
叶名 用户评价 → 用户评价分
叶名 48小时发货率 → 延迟发货率
叶名 24小时回复率 → 24 小时回复率
黄标不取数 库存、推广 roas、流量异常（建议调价未调价）、流量异常SPU数占比、推广 Roas。指标及相关明细空缺。
商品策略额外指标名为空。
履约 139 列为空。
售龄四档 0–10、11–29、30–89、≥90。
TOP X 的 X 与无公式一级不在本资产补公式。
