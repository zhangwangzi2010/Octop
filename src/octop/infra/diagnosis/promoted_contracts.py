"""Promoted display strings for the store-diagnosis fetch contract.

Names and ids only. This module does not define JSON keys, ratio scales,
or metric names under 商品策略结构.
"""

from __future__ import annotations

_SECOND_LEVEL_NAMES: tuple[str, ...] = (
    "用户评价分",
    "非买家责任退货退款率",
    "延迟发货率",
    "延迟到货率",
    "缺货率",
    "24小时回复率",
    "售后准时率",
    "爆旺款率",
    "售罄健康分",
    "活动报名率",
)
_KICKOFF_METRIC_IDS: tuple[tuple[str, str], ...] = (
    ("用户评价分", "temu_store_user_review_score"),
    ("非买家责任退货退款率", "temu_store_non_buyer_fault_return_refund_rate"),
    ("延迟发货率", "temu_store_late_shipment_rate"),
    ("延迟到货率", "temu_store_late_delivery_rate"),
    ("缺货率", "temu_store_out_of_stock_rate"),
    ("24 小时回复率", "temu_store_24h_reply_rate"),
    ("售后准时率", "temu_store_after_sales_on_time_rate"),
    ("爆旺款率", "temu_store_hot_product_rate"),
    ("售罄健康分", "temu_store_sellout_health_score"),
    ("活动报名率", "temu_store_campaign_registration_rate"),
)
_PREFIXED_METRIC_IDS: tuple[str, ...] = (
    "ecommerce.metric.temu_store_user_review_score",
    "ecommerce.metric.temu_store_sellout_health_score",
)
_PERFORMANCE_SCORE_IDS: tuple[str, ...] = (
    "store_performance_score_average",
    "ecommerce.metric.store_performance_score_average",
)
_Q4_OUTPUT_NAMES: tuple[str, ...] = ("latest", "over_peers", "next_level")
_Q4_COLUMN_LABELS: tuple[str, ...] = ("最新值", "超过同行", "下一级标准")
_Q4_PHYSICAL_FIELDS: tuple[tuple[str, str], ...] = (
    ("indicator_data_detail", "指标最新值"),
    ("indicator_data_over_peers_rate", "超过同行水平"),
    ("indicator_data_next_level_threshold", "下一级标准"),
)
_DETAIL_TABLES: tuple[tuple[str, str], ...] = (
    ("评价", "dwd_prd_temu_review_detail_df"),
    ("售后", "dwd_trd_temu_refund_detail_df"),
    ("发货", "dwm_robot_self_order_detail_df"),
    ("到货", "dwm_robot_self_order_detail_df"),
)
_DRILL_TEMPLATES: tuple[tuple[str, str], ...] = (
    ("店铺绩效异常", "评价"),
    ("非买家责任退款退货率", "售后"),
    ("延迟发货（48小时发货）", "发货"),
    ("延迟到货", "到货"),
)


def snapshot_path(data_dir: str, shop_id: str) -> str:
    """One snapshot file per shop. The template has no version segment."""
    return f"{data_dir}/{shop_id}.json"


def second_level_metric_names() -> tuple[str, ...]:
    """Ten whitelist names. The reply-rate spelling here has no space."""
    return _SECOND_LEVEL_NAMES


def kickoff_metric_ids() -> tuple[tuple[str, str], ...]:
    """Kickoff table rows. The reply-rate row keeps the spaced spelling."""
    return _KICKOFF_METRIC_IDS


def prefixed_metric_ids() -> tuple[str, ...]:
    """Only the two ids whose source text already includes the prefix."""
    return _PREFIXED_METRIC_IDS


def performance_score_ids() -> tuple[str, ...]:
    """Score ids that stay outside the ten second-level names."""
    return _PERFORMANCE_SCORE_IDS


def q4_output_names() -> tuple[str, ...]:
    """Q4 output names. These are not the physical field names."""
    return _Q4_OUTPUT_NAMES


def q4_column_labels() -> tuple[str, ...]:
    """Kickoff labels for the three Q4 columns."""
    return _Q4_COLUMN_LABELS


def q4_physical_fields() -> tuple[tuple[str, str], ...]:
    """Physical field names paired with their source purpose text."""
    return _Q4_PHYSICAL_FIELDS


def detail_tables() -> tuple[tuple[str, str], ...]:
    """Four detail templates and the physical tables named for them."""
    return _DETAIL_TABLES


def drill_templates() -> tuple[tuple[str, str], ...]:
    """Section 6.3 trigger wording paired with a detail template."""
    return _DRILL_TEMPLATES
