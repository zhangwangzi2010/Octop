"""RED contracts for diagnosis-side derived values.

``octop.infra.diagnosis.derived_metrics`` does not exist yet. These tests
fail because that API is absent. They do not retune the locked PoP severity
bands, and they do not invent strategy metric names, fulfillment column
names, or after-sales class names.

Expected surface once the module exists:

- ``derived_value_label(kind) -> str``
- ``is_alias(left, right) -> bool``
- ``recent_days(today, day_count) -> Sequence[date]``
- ``prior_window(current) -> Sequence[date]``
- ``period_change(current, previous) -> float``
- ``gmv_field() -> str``
- ``quantity_field() -> str``
- ``derived_slices() -> Sequence[str]``
- ``decline_contribution(slice_kind, entity_change, slice_changes) -> float | None``
- ``decline_weight_index(contribution, entity_previous, slice_previous_total) -> float | None``
"""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from datetime import date
from typing import Any, NoReturn

import pytest

DERIVED_LABEL = "派生在诊断侧、语义层无同名 metric"
DERIVED_KINDS = ("环比", "下滑贡献占比", "下滑权重指数", "影响度")
DERIVED_SLICES = ("Top", "品类", "售龄")
TODAY = date(2026, 10, 16)


def test_derived_values_keep_the_diagnosis_side_label() -> None:
    """环比、下滑贡献占比、下滑权重指数和影响度都标为派生。"""
    label = _fn("derived_value_label")
    for kind in DERIVED_KINDS:
        assert label(kind) == DERIVED_LABEL


def test_weight_is_not_an_alias_of_q4_short_names() -> None:
    """weight 不是 over_peers 的别名，也不是 next_level 的别名。"""
    alias = _fn("is_alias")
    assert alias("weight", "over_peers") is False
    assert alias("weight", "next_level") is False


def test_prior_window_is_the_adjacent_equal_length() -> None:
    """上期是紧邻本期的等长窗口。"""
    current = tuple(date(2026, 10, day) for day in range(9, 16))
    prior = tuple(_fn("prior_window")(current))
    assert prior == tuple(date(2026, 10, day) for day in range(2, 9))
    assert len(prior) == len(current)
    assert prior[-1] == date(2026, 10, 8)
    assert set(prior).isdisjoint(current)


def test_recent_n_days_exclude_today_and_end_yesterday() -> None:
    """「最近 N 天」不含今天，截止到昨天。"""
    recent = _fn("recent_days")
    assert tuple(recent(TODAY, 7)) == tuple(date(2026, 10, day) for day in range(9, 16))
    assert TODAY not in recent(TODAY, 7)
    assert tuple(recent(TODAY, 1)) == (date(2026, 10, 15),)
    assert tuple(_fn("prior_window")(recent(TODAY, 3))) == (
        date(2026, 10, 10),
        date(2026, 10, 11),
        date(2026, 10, 12),
    )


def test_decline_contribution_uses_same_sign_changes() -> None:
    """贡献占比等于本期减上期，再除以切片内同号变动之和。"""
    change = _fn("period_change")
    assert change(80, 100) == -20
    assert change(50, 40) == 10
    contribute = _fn("decline_contribution")
    slice_changes = (-20.0, 10.0, -20.0)
    assert contribute("Top", -20.0, slice_changes) == pytest.approx(0.5)
    assert contribute("Top", 10.0, slice_changes) == pytest.approx(1)


def test_decline_contribution_is_absent_when_same_sign_sum_is_zero() -> None:
    """同号变动之和为 0 时不产生贡献占比，权重指数也不补一个数。"""
    assert _fn("decline_contribution")("品类", 0.0, (0.0, 0.0)) is None
    assert _fn("decline_weight_index")(None, 10.0, 30.0) is None


def test_gmv_and_quantity_stay_on_separate_fields() -> None:
    """GMV 用 sales_amount，销量用 sales_quantity。两条序列不混算。"""
    assert _fn("gmv_field")() == "sales_amount"
    assert _fn("quantity_field")() == "sales_quantity"
    contribute = _fn("decline_contribution")
    gmv = contribute("Top", -20.0, (-20.0, 10.0))
    quantity = contribute("Top", -5.0, (-5.0, -5.0))
    assert gmv == pytest.approx(1)
    assert quantity == pytest.approx(0.5)
    assert gmv != quantity


def test_decline_weight_index_uses_absolute_contribution_and_previous_share() -> None:
    """权重指数是贡献占比的绝对值乘以上期值占切片上期合计的比重。"""
    index = _fn("decline_weight_index")
    assert index(0.5, 100, 200) == pytest.approx(0.25)
    assert index(-0.5, 100, 200) == pytest.approx(0.25)
    gmv_index = index(0.5, 100, 190)
    quantity_index = index(0.5, 40, 80)
    assert gmv_index == pytest.approx(0.5 * 100 / 190)
    assert quantity_index == pytest.approx(0.25)
    assert gmv_index != quantity_index


def test_derived_slices_are_top_category_and_age() -> None:
    """同一条贡献公式用于 Top、品类、售龄。"""
    assert _texts("derived_slices") == DERIVED_SLICES
    contribute = _fn("decline_contribution")
    for slice_kind in DERIVED_SLICES:
        assert contribute(slice_kind, -20.0, (-20.0, -20.0)) == pytest.approx(0.5)


def _texts(name: str, *args: object) -> tuple[str, ...]:
    value = _fn(name)(*args)
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        _absent(f"{name} did not return the recorded names")
    return tuple(str(item) for item in value)


def _fn(name: str) -> Any:
    function = getattr(_module(), name, None)
    if not callable(function):
        _absent(f"{name} is not implemented")
    return function


def _module() -> Any:
    try:
        return importlib.import_module("octop.infra.diagnosis.derived_metrics")
    except ImportError as exc:
        _absent(f"octop.infra.diagnosis.derived_metrics is absent ({exc})")


def _absent(detail: str) -> NoReturn:
    pytest.fail(f"derived metrics are absent: {detail}")
