"""Ten second-level weights and the locked hit lines.

C-S09 stays at ≥10%. Strategy names, fulfillment columns, after-sales class
names, and slice D formulas are not listed.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

_LATE_SHIP_NUMERATOR = "parent_shipping_time > expect_ship_latest_time"
_LATE_SHIP_DENOMINATOR = "已发货且 ship_time IS NOT NULL"
_LATE_ARRIVAL_NUMERATOR = "parent_receipt_time > latest_delivery_time"
_LATE_ARRIVAL_DENOMINATOR = "parent_receipt_time IS NOT NULL"


@dataclass(frozen=True)
class _Metric:
    name: str
    weight: float
    hit_rule: str
    multiplies_by_100: bool
    basis: str


_METRICS: dict[str, _Metric] = {
    "C-S07": _Metric("用户评价分", 10, "< 4", False, "score_passthrough"),
    "C-S08": _Metric("非买家责任退货退款率", 10, "×100 后 ≥ 5%", True, "latest_vs_threshold"),
    "C-S09": _Metric("延迟发货率", 5, "≥10%", True, "document_ratio"),
    "C-S10": _Metric("延迟到货率", 10, "×100 后 ≥ 3%", True, "document_ratio"),
    "C-S11": _Metric("缺货率", 10, "环比上升", False, "pop_direction"),
    "C-S12": _Metric("24 小时回复率", 5, "<90%", True, "latest_vs_threshold"),
    "C-S13": _Metric("售后准时率", 5, "<95%", True, "latest_vs_threshold"),
    "C-S14": _Metric("爆旺款率", 10, "环比下降", False, "pop_direction"),
    "C-S15": _Metric("售罄健康分", 20, "< 95", False, "score_passthrough"),
    "C-S16": _Metric("活动报名率", 15, "×100 后 < 90%", True, "latest_vs_threshold"),
}
_NUMERATORS: dict[str, str] = {
    "C-S09": _LATE_SHIP_NUMERATOR,
    "C-S10": _LATE_ARRIVAL_NUMERATOR,
}
_DENOMINATORS: dict[str, str] = {
    "C-S09": _LATE_SHIP_DENOMINATOR,
    "C-S10": _LATE_ARRIVAL_DENOMINATOR,
}


def metric_ids() -> tuple[str, ...]:
    """The ten catalog ids, in order."""
    return tuple(_METRICS)


def metric_name(metric_id: str) -> str:
    """Display name for one catalog id."""
    return _METRICS[metric_id].name


def metric_weight_percent(metric_id: str) -> float:
    """Weight in percent points. There is no separate weight table."""
    return _METRICS[metric_id].weight


def hit_rule(metric_id: str) -> str:
    """Locked hit rule. C-S09 remains ≥10%."""
    return _METRICS[metric_id].hit_rule


def multiplies_by_100(metric_id: str) -> bool:
    """Ratio metrics scale a stored 0~1 value. Scores do not."""
    return _METRICS[metric_id].multiplies_by_100


def judgment_basis(metric_id: str) -> str:
    """How the metric is judged. No extra fulfillment columns are implied."""
    return _METRICS[metric_id].basis


def score_hits(metric_id: str, value: float) -> bool:
    """Passthrough scores. The value is not multiplied by 100."""
    if metric_id == "C-S07":
        return value < 4
    if metric_id == "C-S15":
        return value < 95
    return False


def stored_ratio_hits(metric_id: str, stored: float) -> bool:
    """Judge a stored 0~1 ratio after multiplying by 100."""
    return percent_hits(metric_id, stored * 100)


def percent_hits(metric_id: str, percent: float) -> bool:
    """Judge an already scaled percent. C-S09 hits at 10, not at 2."""
    if metric_id == "C-S08":
        return percent >= 5
    if metric_id == "C-S09":
        return percent >= 10
    if metric_id == "C-S10":
        return percent >= 3
    if metric_id == "C-S12":
        return percent < 90
    if metric_id == "C-S13":
        return percent < 95
    if metric_id == "C-S16":
        return percent < 90
    return False


def pop_direction_hits(metric_id: str, direction: str) -> bool:
    """Direction only. No rise or fall magnitude is stored."""
    if metric_id == "C-S11":
        return direction == "上升"
    if metric_id == "C-S14":
        return direction == "下降"
    return False


def pop_magnitude_percent(metric_id: str) -> None:
    """No rise or fall percent is locked."""
    del metric_id
    return None


def document_numerator(metric_id: str) -> str | None:
    """Document-level numerator for C-S09 and C-S10 only."""
    return _NUMERATORS.get(metric_id)


def document_denominator(metric_id: str) -> str | None:
    """Document-level denominator for C-S09 and C-S10 only."""
    return _DENOMINATORS.get(metric_id)


def reply_rate_judgment_name() -> str:
    """Judgment name. The unspaced spelling is only a contrast."""
    return "24 小时回复率"


def reply_rate_contrast_spelling() -> str:
    """Whitelist spelling. It is not a second judgment name."""
    return "24小时回复率"


def common_hit_rate(hit_store_count: int, eligible_store_count: int) -> float:
    """Hit stores divided by stores that have a value and are not a yellow gap."""
    return hit_store_count / eligible_store_count


def common_mark_percent() -> int:
    """The common-issue comparison stays at 40."""
    return 40


def counts_toward_common_denominator(has_value: bool, yellow_gap: bool) -> bool:
    """Yellow gaps stay out of the denominator."""
    return has_value and not yellow_gap


def yellow_gap_mark() -> str:
    """Mark used when a yellow metric is judged or attributed."""
    return "指标及相关明细空缺"


def entity_avg_field() -> str:
    """Canonical field for the subject average."""
    return "entity_avg_mall_check_score"


def entity_avg_mall_check_score(scores: Sequence[float]) -> float:
    """Arithmetic mean of store mall_check_score values."""
    return sum(scores) / len(scores)


def store_score_field() -> str:
    """Canonical store-performance field."""
    return "mall_check_score"


def strategy_metric_names() -> tuple[str, ...]:
    """Empty. Strategy metric names are not invented."""
    return ()


def fulfillment_column_names() -> tuple[str, ...]:
    """Empty. The 139 fulfillment columns are not invented."""
    return ()


def after_sales_class_names() -> tuple[str, ...]:
    """Empty. The six after-sales class names are not invented."""
    return ()
