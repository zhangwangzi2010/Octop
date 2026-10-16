"""Period-over-period math and yellow-metric fetch flags.

Yellow metrics stay unfetchable. This module does not invent values for them.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

_YELLOW_METRICS = frozenset(
    {
        "库存",
        "推广 roas",
        "流量异常（建议调价未调价）",
        "流量异常SPU数占比",
        "推广 Roas",
    }
)


def cumulative_pop(
    current_daily: Sequence[float],
    previous_daily: Sequence[float] | None,
) -> float | None:
    """Pop of a cumulative series.

    Equal-length windows compare period sums. Unequal lengths compare daily
    averages (sum / day count). A missing or zero previous total is not a number.
    """
    if previous_daily is None:
        return None
    if len(current_daily) == len(previous_daily):
        current = float(sum(current_daily))
        previous = float(sum(previous_daily))
    else:
        current = float(sum(current_daily)) / len(current_daily)
        previous = float(sum(previous_daily)) / len(previous_daily)
    return _percent_change(current, previous)


def ratio_pop(
    current_numerators: Sequence[float],
    current_denominators: Sequence[float],
    previous_numerators: Sequence[float] | None,
    previous_denominators: Sequence[float] | None,
) -> float | None:
    """Pop of two window ratios, each ``sum(numerator) / sum(denominator)``.

    Window length does not switch this to an average of daily rates. A missing
    previous window or a zero denominator sum is not a number.
    """
    if previous_numerators is None or previous_denominators is None:
        return None
    current_denominator = float(sum(current_denominators))
    previous_denominator = float(sum(previous_denominators))
    if current_denominator == 0 or previous_denominator == 0:
        return None
    current = float(sum(current_numerators)) / current_denominator
    previous = float(sum(previous_numerators)) / previous_denominator
    return _percent_change(current, previous)


def worsening_grade(
    pop_percent: float,
    *,
    polarity: Literal["positive", "negative"],
) -> str | None:
    """Grade worsening only. Improvement and changes under 5% have no band."""
    worsening = -pop_percent if polarity == "positive" else pop_percent
    if 5 <= worsening < 10:
        return "轻微下滑"
    if 10 <= worsening <= 20:
        return "一般下滑"
    if worsening > 20:
        return "严重下滑"
    return None


@dataclass(frozen=True)
class MetricGate:
    fetchable: bool
    skipped: bool
    value: float | None


def metric_gate(name: str) -> MetricGate:
    """Mark the five yellow metrics skipped. Every other name stays fetchable."""
    if name in _YELLOW_METRICS:
        return MetricGate(fetchable=False, skipped=True, value=None)
    return MetricGate(fetchable=True, skipped=False, value=None)


def _percent_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return (current - previous) / previous * 100
