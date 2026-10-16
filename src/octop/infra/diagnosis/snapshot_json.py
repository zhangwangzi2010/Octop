"""Promoted snapshot JSON shape and key names.

Field names only. Reply-rate and refund-rate spellings stay separate.
Q4 short names are not rewritten as physical columns.
"""

from __future__ import annotations

from octop.infra.diagnosis.promoted_contracts import q4_output_names

_SHAPE_FIELDS: tuple[str, ...] = ("店铺", "主体", "负责人", "store_performance")
_STORE_PERFORMANCE_FIELDS: tuple[str, ...] = ("perf_score", "score_level", "metrics")
_METRIC_JSON_KEYS: tuple[str, ...] = (
    "用户评价分",
    "非买家责任退货退款率",
    "延迟发货率",
    "延迟到货率",
    "缺货率",
    "24 小时回复率",
    "售后准时率",
    "爆旺款率",
    "售罄健康分",
    "活动报名率",
)


def snapshot_shape_fields() -> tuple[str, ...]:
    """Siblings of the snapshot object. ``score_level`` is not one of them."""
    return _SHAPE_FIELDS


def store_performance_fields() -> tuple[str, ...]:
    """Fields inside ``store_performance``. ``metrics`` holds the ten keys."""
    return _STORE_PERFORMANCE_FIELDS


def metric_json_keys() -> tuple[str, ...]:
    """Ten kickoff spellings. The reply-rate key keeps its space."""
    return _METRIC_JSON_KEYS


def metric_value_keys() -> tuple[str, ...]:
    """Q4 short names under each metric key, not the physical columns."""
    return q4_output_names()
