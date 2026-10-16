"""Structural snapshot rules that the specs already state.

File identity is opaque. Period labels that are not a frozen window stay
labels. This module does not define JSON keys, SQL columns, paths, or scales.
"""

from __future__ import annotations

from datetime import date, timedelta

_QUERY_NAMES: tuple[str, ...] = (
    "Q1 主体汇总",
    "Q2 店铺快照",
    "Q3 近 60 天评分趋势",
    "Q4 二级指标快照",
    "Q5 三个月指标趋势",
)
_Q3_DAYS = 60
_Q3_LABEL = "最近 60 天（不含今天）"


def snapshot_file_for_store(store_id: str) -> str:
    """Return one stable identity for a store. The value is not a file path."""
    return store_id


def parse_period(label: str, *, today: date) -> tuple[date, ...] | str:
    """Parse a named period. Only the frozen Q3 window becomes dates."""
    if label == _Q3_LABEL:
        return q3_window(today)
    return label


def q3_window(today: date) -> tuple[date, ...]:
    """Sixty daily dates ending yesterday. Today is not included."""
    return tuple(today - timedelta(days=delta) for delta in range(_Q3_DAYS, 0, -1))


def symptom_conclusion(snapshot_text: str) -> str:
    """Repeat the supplied snapshot text so the conclusion adds no numbers."""
    return snapshot_text


def query_names() -> tuple[str, ...]:
    """Q1 through Q5 display names from the symptom-pipeline spec."""
    return _QUERY_NAMES


def preload_consumable(status: str, row_count: int) -> bool:
    """Consume a preload only when it completed with at least one row."""
    return status == "COMPLETED" and row_count > 0


def preload_refill_allowed(status: str) -> bool:
    """RUNNING must not be filled again. Other statuses are not specified."""
    if status == "RUNNING":
        return False
    raise ValueError("refill is only specified for RUNNING")


def preload_retry_allowed(status: str) -> bool:
    """FAILED may be retried. Other statuses are not specified."""
    if status == "FAILED":
        return True
    raise ValueError("retry is only specified for FAILED")
