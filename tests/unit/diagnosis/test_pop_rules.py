"""RED contracts for period-over-period rules and yellow-metric fetch flags.

``octop.infra.diagnosis`` does not exist yet. These tests fail because that
behavior is absent. They do not add the engine, thresholds, or sample numbers
for the five unfetchable metrics.

Expected surface once the module exists:

- ``cumulative_pop(current_daily, previous_daily) -> float | None``
- ``ratio_pop(current_numerators, current_denominators, previous_numerators, previous_denominators) -> float | None``
- ``worsening_grade(pop_percent, *, polarity) -> str | None``
- ``metric_gate(name) -> fetchable / skipped / value``

Bands follow the symptom-pipeline spec: 5% ≤ w < 10% 轻微下滑,
10% ≤ w ≤ 20% 一般下滑, w > 20% 严重下滑, otherwise no band.
"""

from __future__ import annotations

import importlib
from collections.abc import Mapping
from typing import Any, NoReturn

import pytest

YELLOW_METRICS = (
    "库存",
    "推广 roas",
    "流量异常（建议调价未调价）",
    "流量异常SPU数占比",
    "推广 Roas",
)
NOT_YELLOW_METRICS = (
    "推广花费（关停）",
    "roas环比变化",
    "流量异常",
    "曝光",
)


def test_equal_length_cumulative_pop_uses_period_sums() -> None:
    """曝光两侧都是 7 天：700 对 1000，环比 −30%，不用日均。"""
    pop = _fn("cumulative_pop")
    current = [100.0] * 7
    previous = [1000.0 / 7] * 7
    assert sum(current) == pytest.approx(700)
    assert sum(previous) == pytest.approx(1000)
    assert pop(current, previous) == pytest.approx(-30)


def test_ratio_pop_uses_sum_ratio_not_mean_of_daily_rates() -> None:
    """本期日退货 14/200、上期 10/200。环比 40%，不是各日退货率的平均。"""
    pop = _fn("ratio_pop")
    current_numerators = [0, 0, 0, 0, 0, 4, 10]
    current_denominators = [10, 10, 10, 10, 10, 50, 100]
    previous_numerators = [0, 0, 0, 0, 0, 0, 10]
    previous_denominators = [10, 10, 10, 10, 10, 10, 140]
    assert sum(current_numerators) / sum(current_denominators) == pytest.approx(14 / 200)
    assert sum(previous_numerators) / sum(previous_denominators) == pytest.approx(10 / 200)
    assert pop(
        current_numerators,
        current_denominators,
        previous_numerators,
        previous_denominators,
    ) == pytest.approx(40)


def test_cumulative_pop_uses_daily_average_only_when_lengths_differ() -> None:
    """7 天曝光 700 对 6 天曝光 600：日均都是 100，环比 0%。"""
    pop = _fn("cumulative_pop")
    assert pop([100.0] * 7, [100.0] * 6) == pytest.approx(0)


def test_ratio_pop_keeps_sum_ratio_when_window_lengths_differ() -> None:
    """7 天 14/200 对 6 天 6/120，仍用合计比率，环比 40%。"""
    pop = _fn("ratio_pop")
    current_numerators = [0, 0, 0, 0, 0, 4, 10]
    current_denominators = [10, 10, 10, 10, 10, 50, 100]
    previous_numerators = [1, 1, 1, 1, 1, 1]
    previous_denominators = [10, 10, 10, 10, 10, 70]
    assert sum(current_numerators) == 14
    assert sum(current_denominators) == 200
    assert sum(previous_numerators) == 6
    assert sum(previous_denominators) == 120
    assert pop(
        current_numerators,
        current_denominators,
        previous_numerators,
        previous_denominators,
    ) == pytest.approx(40)


def test_pop_is_absent_when_previous_or_ratio_denominator_is_unusable() -> None:
    cumulative = _fn("cumulative_pop")
    ratio = _fn("ratio_pop")
    assert cumulative([100.0] * 7, [0.0] * 7) is None
    assert cumulative([100.0] * 7, None) is None
    assert ratio([1.0], [0.0], [1.0], [1.0]) is None
    assert ratio([1.0], [1.0], [1.0], [0.0]) is None
    assert ratio([1.0], [1.0], None, None) is None


def test_positive_metric_decline_bands() -> None:
    grade = _fn("worsening_grade")
    assert grade(-7, polarity="positive") == "轻微下滑"
    assert grade(-10, polarity="positive") == "一般下滑"
    assert grade(-20, polarity="positive") == "一般下滑"
    assert grade(-21, polarity="positive") == "严重下滑"
    assert grade(-4, polarity="positive") is None


def test_negative_metric_rises_to_worsen() -> None:
    grade = _fn("worsening_grade")
    assert grade(12, polarity="negative") == "一般下滑"
    assert grade(-12, polarity="negative") is None


def test_yellow_metrics_are_unfetchable_and_skipped_without_numbers() -> None:
    gate = _fn("metric_gate")
    for name in YELLOW_METRICS:
        row = gate(name)
        assert _field(row, "fetchable") is False
        assert _field(row, "skipped") is True
        assert _field(row, "value") is None


def test_named_non_yellow_metrics_stay_fetchable() -> None:
    gate = _fn("metric_gate")
    for name in NOT_YELLOW_METRICS:
        row = gate(name)
        assert _field(row, "fetchable") is True
        assert _field(row, "skipped") is False


def _fn(name: str) -> Any:
    module = _module()
    function = getattr(module, name, None)
    if not callable(function):
        _absent(f"{name} is not implemented")
    return function


def _module() -> Any:
    try:
        return importlib.import_module("octop.infra.diagnosis.pop_rules")
    except ImportError as exc:
        _absent(f"octop.infra.diagnosis.pop_rules is absent ({exc})")


def _field(row: Any, name: str) -> Any:
    if isinstance(row, Mapping):
        return row[name]
    return getattr(row, name)


def _absent(detail: str) -> NoReturn:
    pytest.fail(f"symptom pop rules are absent: {detail}")
