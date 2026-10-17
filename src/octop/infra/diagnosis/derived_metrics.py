"""Diagnosis-side derived values.

The prior window is the adjacent equal-length window. Recent N days end
yesterday. Contribution and the weight index have no semantic-layer metric.
PoP severity bands stay in ``pop_rules`` and are not retuned here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from octop.infra.diagnosis.l1_semantic import age_bands
from octop.infra.diagnosis.pop_rules import pop_percent

_DERIVED_LABEL = "派生在诊断侧、语义层无同名 metric"
_DERIVED_SLICES: tuple[str, ...] = ("Top", "品类", "售龄")


def derived_value_label(kind: str) -> str:
    """环比、贡献占比、权重指数、影响度 share this label."""
    del kind
    return _DERIVED_LABEL


def is_alias(left: str, right: str) -> bool:
    """``weight`` is not ``over_peers`` and not ``next_level``."""
    del left, right
    return False


def recent_days(today: date, day_count: int) -> tuple[date, ...]:
    """The N days ending yesterday. Today is not included."""
    start = today - timedelta(days=day_count)
    return tuple(start + timedelta(days=offset) for offset in range(day_count))


def prior_window(current: Sequence[date]) -> tuple[date, ...]:
    """The equal-length window immediately before ``current``."""
    days = tuple(current)
    start = days[0] - timedelta(days=len(days))
    return tuple(start + timedelta(days=offset) for offset in range(len(days)))


def period_change(current: float, previous: float) -> float:
    """Current period minus the previous period."""
    return current - previous


def gmv_field() -> str:
    """GMV measure. Quantity uses a different field."""
    return "sales_amount"


def quantity_field() -> str:
    """Quantity measure. GMV uses a different field."""
    return "sales_quantity"


def derived_slices() -> tuple[str, ...]:
    """Slices that share the contribution formula."""
    return _DERIVED_SLICES


def decline_contribution(
    slice_kind: str,
    entity_change: float,
    slice_changes: Sequence[float],
) -> float | None:
    """Entity change divided by the same-sign sum. A zero sum is not a number."""
    del slice_kind
    same_sign_sum = sum(change for change in slice_changes if _sign(change) == _sign(entity_change))
    if same_sign_sum == 0:
        return None
    return entity_change / same_sign_sum


def decline_weight_index(
    contribution: float | None,
    entity_previous: float,
    slice_previous_total: float,
) -> float | None:
    """Absolute contribution times the entity's share of the previous total."""
    if contribution is None:
        return None
    return abs(contribution) * entity_previous / slice_previous_total


@dataclass(frozen=True)
class MeasureWindow:
    """Current and previous values for one GMV or quantity measure."""

    current: float
    previous: float
    slice_changes: tuple[float, ...] = ()
    slice_previous_total: float | None = None


_GAP_DISPLAYS: tuple[str, ...] = (
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
_GAP_MARK = "gap"


def measure_result(kind: str, window: MeasureWindow) -> dict[str, float | None]:
    """Pop, contribution, and weight index. A zero previous pop is not a number."""
    change = period_change(window.current, window.previous)
    contribution = None
    if window.slice_changes:
        contribution = decline_contribution(kind, change, window.slice_changes)
    total = window.slice_previous_total
    weight_index = None
    if isinstance(total, (int, float)) and not isinstance(total, bool) and total != 0:
        weight_index = decline_weight_index(contribution, window.previous, total)
    return {
        "pop": pop_percent(window.current, window.previous),
        "contribution": contribution,
        "weight_index": weight_index,
    }


def live_minimal(
    *,
    overall: Mapping[str, Any] | None = None,
    slices: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Runtime values for the locked formulas. Missing inputs stay empty."""
    overall_windows = overall or {}
    displays = {
        "GMV环比下滑幅度": _display_pop(overall_windows.get(gmv_field())),
        "销量环比下滑幅度": _display_pop(overall_windows.get(quantity_field())),
    }
    return {
        "displays": displays,
        "gaps": _GAP_DISPLAYS,
        "gap_mark": _GAP_MARK,
        "slices": _live_slices(slices or {}),
        "top_x": None,
    }


def _display_pop(window: object) -> float | None:
    if not isinstance(window, MeasureWindow):
        return None
    return pop_percent(window.current, window.previous)


def _live_slices(
    slices: Mapping[str, Any],
) -> dict[str, dict[str, dict[str, float | None]]]:
    computed: dict[str, dict[str, dict[str, float | None]]] = {}
    for kind, measures in slices.items():
        if not _slice_accepted(str(kind)) or not isinstance(measures, Mapping):
            continue
        kind_result: dict[str, dict[str, float | None]] = {}
        for field in (gmv_field(), quantity_field()):
            window = measures.get(field)
            if isinstance(window, MeasureWindow):
                kind_result[field] = measure_result(str(kind), window)
        if kind_result:
            computed[str(kind)] = kind_result
    return computed


def _slice_accepted(kind: str) -> bool:
    return kind in {"Top", "品类"} or kind in age_bands()


def _sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0
