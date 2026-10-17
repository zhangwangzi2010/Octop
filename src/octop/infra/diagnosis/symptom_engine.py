"""Deterministic symptom judgment.

AI writes summaries only. This module does not invent hit lines, weight
percents, hit-rate numerators, strategy metric names, fulfillment columns,
or after-sales class names.
"""

from __future__ import annotations

from collections.abc import Sequence

_ACCEPTANCE_THRESHOLDS: tuple[str, ...] = (
    "C-S09 ≥10%",
    "C-S12 <90%",
    "C-S13 <95%",
)
_HIT_LINES: dict[str, float] = {
    "延迟发货率": 10,
    "24 小时回复率": 90,
    "售后准时率": 95,
}
_YELLOW_METRICS: tuple[str, ...] = (
    "库存",
    "推广 roas",
    "流量异常（建议调价未调价）",
    "流量异常SPU数占比",
    "推广 Roas",
)
_SCORE_LABELS: dict[str, str] = {
    "店铺": "店铺绩效分",
    "主体": "主体平均分",
}


def judgment_executor() -> str:
    """Judgment is code. AI is not on this path."""
    return "确定性代码"


def ai_on_judgment_path() -> bool:
    """AI does not hit, grade, or rank."""
    return False


def ai_role() -> str:
    """The only AI role next to a finished judgment."""
    return "摘要"


def summary_changes_judgment(judgment: str, summary: str) -> bool:
    """A summary cannot rewrite the judgment."""
    del judgment, summary
    return False


def late_shipment_hits(percent: float) -> bool:
    """C-S09 hits when the judged percent is at least 10."""
    return percent >= 10


def stored_ratio_percent(stored: float) -> float:
    """Display and judgment percent for a stored 0~1 ratio."""
    return stored * 100


def late_shipment_hits_stored(stored: float) -> bool:
    """Judge C-S09 from the stored ratio after multiplying by 100."""
    return late_shipment_hits(stored_ratio_percent(stored))


def reply_rate_hits(percent: float) -> bool:
    """C-S12 hits when the judged percent is below 90."""
    return percent < 90


def reply_rate_judgment_name() -> str:
    """Judgment name. The unspaced whitelist spelling is only a contrast."""
    return "24 小时回复率"


def reply_rate_contrast_spelling() -> str:
    """Whitelist spelling. It is not a second judgment name."""
    return "24小时回复率"


def after_sales_on_time_hits(percent: float) -> bool:
    """C-S13 hits when the judged percent is below 95."""
    return percent < 95


def acceptance_thresholds() -> tuple[str, ...]:
    """Source A only."""
    return _ACCEPTANCE_THRESHOLDS


def is_common(hit_rate_percent: float) -> bool:
    """Common when the given hit rate is at least 40. No numerator is stored."""
    return hit_rate_percent >= 40


def individual_priority(weight_percent: float, mall_check_score: float) -> str:
    """P0, P1, or P2 from the given weight and mall_check_score."""
    if weight_percent >= 30 or mall_check_score < 3.5:
        return "P0"
    if weight_percent < 15:
        return "P2"
    return "P1"


def impact(weight: float, hit_rate: float) -> float:
    """Impact is the caller-supplied weight times the caller-supplied hit rate."""
    return weight * hit_rate


def metric_weight_percent(metric: str) -> None:
    """No per-metric weight table is locked."""
    del metric
    return None


def sort_impacts(values: Sequence[float]) -> tuple[float, ...]:
    """Already computed impacts, highest first."""
    return tuple(sorted(values, reverse=True))


def score_band(mall_check_score: float) -> str:
    """Endpoints belong to the higher band."""
    if mall_check_score < 3.5:
        return "高危"
    if mall_check_score < 4:
        return "低危"
    if mall_check_score < 4.3:
        return "正常"
    return "优秀"


def dimension_score_label(dimension: str) -> str:
    """Store uses the store score. Subject uses the subject average."""
    return _SCORE_LABELS[dimension]


def store_score_field() -> str:
    """Canonical store-performance field."""
    return "mall_check_score"


def subject_score_field() -> None:
    """The subject average has no canonical field name."""
    return None


def hit_line_percent(metric: str) -> float | None:
    """Source A hit lines only. Uncovered metrics have no placeholder."""
    return _HIT_LINES.get(metric)


def strategy_metric_names() -> tuple[str, ...]:
    """Decided empty. Extra strategy metric names are not a pending gap."""
    return ()


def fulfillment_column_names() -> tuple[str, ...]:
    """Decided empty. There is no fulfillment wide table."""
    return ()


def after_sales_class_names() -> tuple[str, ...]:
    """Empty. The six after-sales class names are not invented."""
    return ()


def yellow_metric_names() -> tuple[str, ...]:
    """The five yellow metrics. Nothing is added or substituted."""
    return _YELLOW_METRICS


def yellow_is_queried(name: str) -> bool:
    """Yellow metrics are not queried."""
    del name
    return False


def yellow_is_substituted(name: str) -> bool:
    """Yellow metrics are not replaced."""
    del name
    return False


def yellow_gap_mark() -> str:
    """Mark used when a yellow metric is judged or attributed."""
    return "指标及相关明细空缺"
