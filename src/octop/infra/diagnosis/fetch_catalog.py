"""Frozen fetch display-name registry.

Strings only. This module does not define JSON keys, SQL columns, file paths,
or a ratio scale. Product-strategy metric names stay empty.
"""

from __future__ import annotations

from dataclasses import dataclass

_L1_DISPLAY_NAMES: tuple[str, ...] = (
    "GMV环比下滑幅度",
    "销量环比下滑幅度",
    "订单量下滑占比",
    "下滑SPU数占比",
    "动销SPU下滑占比",
    "在售SPU下滑占比",
    "Top x 下滑款清单",
    "Top x GMV环比下滑幅度",
    "Top x 销量环比下滑幅度",
    "Top x 上期GMV占比",
    "Top x 上期销量占比",
    "Top x 本期GMV占比",
    "Top x 本期销量占比",
    "Top x GMV 下滑贡献占比",
    "Top x 销量下滑贡献占比",
    "GMV下滑权重指数",
    "销量下滑权重指数",
    "品类下滑幅度",
    "品类下滑贡献占比",
)
_AGE_BANDS: tuple[str, ...] = ("0-10天", "11-30天", "30-90天", "90天以上")
_AGE_METRICS: tuple[str, ...] = ("动销率", "下滑贡献占比")
_L1_AGE_DISPLAYS: tuple[tuple[str, str], ...] = tuple(
    (band, metric) for band in _AGE_BANDS for metric in _AGE_METRICS
)
_PRODUCT_STRATEGY_DIMENSIONS: tuple[str, ...] = ("原创款", "跟卖款", "裂变款")
_L2_LEAVES: tuple[tuple[str, str], ...] = (
    ("商品检查单", "违规"),
    ("商品检查单", "库存"),
    ("商品检查单", "商品评分"),
    ("商品检查单", "超预算(关停)"),
    ("商品检查单", "roas环比变化"),
    ("商品检查单", "在售时长"),
    ("商品检查单", "加价率"),
    ("商品检查单", "价格"),
    ("商品检查单", "流量异常（建议调价未调价）"),
    ("商品检查单", "件单价"),
    ("平台风控", "流量异常SPU数/占比"),
    ("平台风控", "违规SPU数/占比"),
    ("店铺运营", "活动覆盖率"),
    ("店铺运营", "流量加速覆盖率"),
    ("店铺绩效", "用户评价"),
    ("店铺绩效", "非买家责任退货退款率"),
    ("店铺绩效", "48小时发货率"),
    ("店铺绩效", "延迟到货率"),
    ("店铺绩效", "24小时回复率"),
    ("店铺绩效", "售后准时率"),
    ("店铺绩效", "爆旺款率"),
    ("店铺绩效", "售罄健康分"),
    ("商品运营", "推广Roas"),
    ("商品运营", "上新SPU数"),
    ("商品运营", "件单价"),
)
_DRILL_TRIGGERS: tuple[str, ...] = (
    "店铺绩效异常",
    "非买家责任退款退货率",
    "延迟发货（48小时发货）",
    "延迟到货",
)
_YELLOW_LABELS: tuple[str, ...] = (
    "库存",
    "推广 roas",
    "流量异常（建议调价未调价）",
    "流量异常SPU数占比",
    "推广 Roas",
)


def l1_display_names() -> tuple[str, ...]:
    """19 first-level names: overall, TOP X, and category. Age pairs are separate."""
    return _L1_DISPLAY_NAMES


def l1_age_displays() -> tuple[tuple[str, str], ...]:
    """Eight ``(age band, metric)`` pairs. Bands are not concatenated into new names."""
    return _L1_AGE_DISPLAYS


def product_strategy_dimensions() -> tuple[str, ...]:
    """Frozen strategy dimension values."""
    return _PRODUCT_STRATEGY_DIMENSIONS


def product_strategy_metric_names() -> tuple[str, ...]:
    """Decided empty. Strategy slices use the three SPU overview columns."""
    return ()


def l2_leaves() -> tuple[tuple[str, str], ...]:
    """25 ``(checklist, leaf)`` pairs. The 推广roas parent is not a leaf."""
    return _L2_LEAVES


def drill_triggers() -> tuple[str, ...]:
    """Four §6.3 triggers in requirement wording, not checklist wording."""
    return _DRILL_TRIGGERS


def yellow_labels() -> tuple[str, ...]:
    """The five unfetchable labels, exact spelling, nothing added or removed."""
    return _YELLOW_LABELS


@dataclass(frozen=True)
class MetricGate:
    fetchable: bool
    skipped: bool
    value: float | None


def metric_gate(name: str) -> MetricGate:
    """Skip only the five yellow labels. Every other display name stays fetchable."""
    if name in _YELLOW_LABELS:
        return MetricGate(fetchable=False, skipped=True, value=None)
    return MetricGate(fetchable=True, skipped=False, value=None)
