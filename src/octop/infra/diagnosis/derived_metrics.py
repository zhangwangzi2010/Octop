"""Diagnosis-side derived values.

The prior window is the adjacent equal-length window. Recent N days end
yesterday. Contribution and the weight index have no semantic-layer metric.
PoP severity bands stay in ``pop_rules`` and are not retuned here.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

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


def _sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0
