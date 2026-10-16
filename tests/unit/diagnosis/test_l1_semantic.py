"""RED contracts for the six L1 semantic acceptance constants.

``octop.infra.diagnosis.l1_semantic`` does not exist yet. These tests fail
because that API is absent. They do not invent strategy metric names,
fulfillment column names, after-sales class names, or a frozen derived formula.

Expected surface once the module exists:

- ``overall_decline_source() -> str`` — ``订单明细``
- ``overall_decline_fields() -> Sequence[str]`` — ``sales_amount`` / ``sales_quantity`` / ``order_count``
- ``slice_kinds() -> Sequence[str]`` — 品类、售龄、策略、Top
- ``slice_overview_fields() -> Sequence[str]`` — ``spu_sold_amount`` / ``spu_sold_quantity`` / ``spu_order_count``
- ``strategy_metric_names() -> Sequence[str]`` — empty
- ``top_slice_extra_metric_ids() -> Sequence[str]`` — empty
- ``active_spu_metric() -> str`` — ``active_spu_count``
- ``on_sale_spu_metric() -> str`` — ``on_sale_spu_count``
- ``category_dimension() -> str`` — ``spu_category``
- ``age_clock_field() -> str`` — ``ads_bi_temu_spu_overview_self_df.min_first_join_time``
- ``age_is_difference_from_now() -> bool``
- ``age_bands() -> Sequence[str]`` — ``0–10`` / ``11–29`` / ``30–89`` / ``≥90``
- ``day_30_age_band() -> str`` — ``30–90``
- ``age_active_rate_metric() -> str`` — ``ecommerce.metric.active_spu_rate``
- ``age_active_rate_filters_by_band() -> bool``
- ``yellow_metric_names() -> Sequence[str]``
- ``yellow_is_queried(name) -> bool``
- ``yellow_is_substituted(name) -> bool``
- ``yellow_gap_mark() -> str`` — ``指标及相关明细空缺``
- ``derived_value_label(kind) -> str`` — ``派生在诊断侧、语义层无同名 metric``
- ``derived_formula(kind) -> None``
"""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from typing import Any, NoReturn

import pytest

OVERALL_DECLINE_SOURCE = "订单明细"
OVERALL_DECLINE_FIELDS = ("sales_amount", "sales_quantity", "order_count")
SLICE_KINDS = ("品类", "售龄", "策略", "Top")
SLICE_OVERVIEW_FIELDS = ("spu_sold_amount", "spu_sold_quantity", "spu_order_count")
ACTIVE_SPU_METRIC = "active_spu_count"
ON_SALE_SPU_METRIC = "on_sale_spu_count"
CATEGORY_DIMENSION = "spu_category"
AGE_CLOCK_FIELD = "ads_bi_temu_spu_overview_self_df.min_first_join_time"
AGE_BANDS = ("0–10", "11–29", "30–89", "≥90")
DAY_30_AGE_BAND = "30–90"
AGE_ACTIVE_RATE_METRIC = "ecommerce.metric.active_spu_rate"
YELLOW_METRICS = (
    "库存",
    "推广 roas",
    "流量异常（建议调价未调价）",
    "流量异常SPU数占比",
    "推广 Roas",
)
YELLOW_GAP_MARK = "指标及相关明细空缺"
DERIVED_KINDS = ("环比", "贡献", "权重")
DERIVED_LABEL = "派生在诊断侧、语义层无同名 metric"


def test_overall_decline_reads_order_detail_fields() -> None:
    """整体下滑读取订单明细的 sales_amount / sales_quantity / order_count。"""
    assert _fn("overall_decline_source")() == OVERALL_DECLINE_SOURCE
    assert _texts("overall_decline_fields") == OVERALL_DECLINE_FIELDS
    assert _texts("overall_decline_fields") != SLICE_OVERVIEW_FIELDS


def test_slices_read_spu_overview_fields() -> None:
    """品类、售龄、策略、Top 读取 SPU 概览三列。策略和 Top 不另造指标名。"""
    assert _texts("slice_kinds") == SLICE_KINDS
    assert _texts("slice_overview_fields") == SLICE_OVERVIEW_FIELDS
    assert _texts("slice_overview_fields") != OVERALL_DECLINE_FIELDS
    assert _texts("strategy_metric_names") == ()
    assert _texts("top_slice_extra_metric_ids") == ()


def test_active_on_sale_and_category_dimension() -> None:
    """动销 SPU、在售、品类维度分别是三个已写出的名字。"""
    assert _fn("active_spu_metric")() == ACTIVE_SPU_METRIC
    assert _fn("on_sale_spu_metric")() == ON_SALE_SPU_METRIC
    assert _fn("category_dimension")() == CATEGORY_DIMENSION
    assert ACTIVE_SPU_METRIC != ON_SALE_SPU_METRIC


def test_age_bands_use_first_join_time() -> None:
    """售龄是 min_first_join_time 与当前时间的差。第 30 天属于 30–90 档。"""
    assert _fn("age_clock_field")() == AGE_CLOCK_FIELD
    assert _fn("age_is_difference_from_now")() is True
    assert _texts("age_bands") == AGE_BANDS
    assert _fn("day_30_age_band")() == DAY_30_AGE_BAND
    assert DAY_30_AGE_BAND not in AGE_BANDS
    assert "11-30" not in _texts("age_bands")


def test_age_active_rate_is_filtered_by_band() -> None:
    """售龄动销率是 ecommerce.metric.active_spu_rate，并按售龄档过滤。"""
    assert _fn("age_active_rate_metric")() == AGE_ACTIVE_RATE_METRIC
    assert _fn("age_active_rate_filters_by_band")() is True
    assert _fn("age_active_rate_metric")() != ACTIVE_SPU_METRIC


def test_yellow_metrics_are_not_queried_or_substituted() -> None:
    """五条黄标不查询、不替代，并标为指标及相关明细空缺。"""
    names = _texts("yellow_metric_names")
    assert names == YELLOW_METRICS
    queried = _fn("yellow_is_queried")
    substituted = _fn("yellow_is_substituted")
    for name in YELLOW_METRICS:
        assert queried(name) is False
        assert substituted(name) is False
    assert _fn("yellow_gap_mark")() == YELLOW_GAP_MARK


def test_derived_values_keep_the_diagnosis_side_label() -> None:
    """环比、贡献、权重只标派生标签。不冻结计算公式。"""
    label = _fn("derived_value_label")
    formula = _fn("derived_formula")
    for kind in DERIVED_KINDS:
        assert label(kind) == DERIVED_LABEL
        assert formula(kind) is None


def _texts(name: str) -> tuple[str, ...]:
    value = _fn(name)()
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
        return importlib.import_module("octop.infra.diagnosis.l1_semantic")
    except ImportError as exc:
        _absent(f"octop.infra.diagnosis.l1_semantic is absent ({exc})")


def _absent(detail: str) -> NoReturn:
    pytest.fail(f"l1 semantic mapping is absent: {detail}")
