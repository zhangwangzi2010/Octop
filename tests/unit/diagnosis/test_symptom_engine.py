"""RED contracts for the deterministic symptom engine.

``octop.infra.diagnosis.symptom_engine`` does not exist yet. These tests fail
because that API is absent. They do not invent strategy metric names,
fulfillment column names, after-sales class names, hit lines, weight percents,
or hit-rate numerators.

Expected surface once the module exists:

- ``judgment_executor() -> str`` — ``确定性代码``
- ``ai_on_judgment_path() -> bool``
- ``ai_role() -> str`` — ``摘要``
- ``summary_changes_judgment(judgment, summary) -> bool``
- ``late_shipment_hits(percent) -> bool``
- ``stored_ratio_percent(stored) -> float``
- ``late_shipment_hits_stored(stored) -> bool``
- ``reply_rate_hits(percent) -> bool``
- ``reply_rate_judgment_name() -> str``
- ``reply_rate_contrast_spelling() -> str``
- ``after_sales_on_time_hits(percent) -> bool``
- ``acceptance_thresholds() -> Sequence[str]``
- ``is_common(hit_rate_percent) -> bool``
- ``individual_priority(weight_percent, mall_check_score) -> str``
- ``impact(weight, hit_rate) -> float``
- ``metric_weight_percent(metric) -> None``
- ``sort_impacts(values) -> Sequence[float]``
- ``score_band(mall_check_score) -> str``
- ``dimension_score_label(dimension) -> str``
- ``store_score_field() -> str``
- ``subject_score_field() -> None``
- ``hit_line_percent(metric) -> float | None``
- ``strategy_metric_names() -> Sequence[str]``
- ``fulfillment_column_names() -> Sequence[str]``
- ``after_sales_class_names() -> Sequence[str]``
- ``yellow_metric_names() -> Sequence[str]``
- ``yellow_is_queried(name) -> bool``
- ``yellow_is_substituted(name) -> bool``
- ``yellow_gap_mark() -> str``
"""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from typing import Any, NoReturn

import pytest

ACCEPTANCE_THRESHOLDS = ("C-S09 ≥10%", "C-S12 <90%", "C-S13 <95%")
REPLY_JUDGMENT_NAME = "24 小时回复率"
REPLY_CONTRAST_SPELLING = "24小时回复率"
UNCOVERED_HIT_METRICS = (
    "用户评价分",
    "非买家责任退货退款率",
    "延迟到货率",
    "缺货率",
    "爆旺款率",
    "售罄健康分",
    "活动报名率",
)
YELLOW_METRICS = (
    "库存",
    "推广 roas",
    "流量异常（建议调价未调价）",
    "流量异常SPU数占比",
    "推广 Roas",
)
YELLOW_GAP_MARK = "指标及相关明细空缺"


def test_judgment_is_deterministic_and_ai_only_writes_summary() -> None:
    """判定由确定性代码完成。AI 只写摘要，不改命中、共性、分级或影响度。"""
    assert _fn("judgment_executor")() == "确定性代码"
    assert _fn("ai_on_judgment_path")() is False
    assert _fn("ai_role")() == "摘要"
    assert _fn("summary_changes_judgment")("命中", "改成不命中") is False
    hit = _fn("late_shipment_hits")
    assert hit(12.5) is hit(12.5)


def test_cs09_uses_source_a_and_the_stored_ratio_scale() -> None:
    """≥10% 命中，未达到不命中。内部 0.1 判成 10%。来源 B 的 2% 不命中。"""
    assert _texts("acceptance_thresholds") == ACCEPTANCE_THRESHOLDS
    hit = _fn("late_shipment_hits")
    assert hit(12.5) is True
    assert hit(10) is True
    assert hit(9.9) is False
    assert hit(2) is False
    assert _fn("stored_ratio_percent")(0.1) == 10
    assert _fn("late_shipment_hits_stored")(0.1) is True


def test_cs12_hits_only_below_ninety() -> None:
    """「24 小时回复率」低于 90% 命中。等于 90% 不命中。无空格写法只是对照。"""
    assert _fn("reply_rate_judgment_name")() == REPLY_JUDGMENT_NAME
    assert _fn("reply_rate_contrast_spelling")() == REPLY_CONTRAST_SPELLING
    assert REPLY_JUDGMENT_NAME != REPLY_CONTRAST_SPELLING
    hit = _fn("reply_rate_hits")
    assert hit(89.9) is True
    assert hit(90) is False
    assert hit(99) is False


def test_cs13_hits_only_below_ninety_five() -> None:
    """售后准时率低于 95% 命中。等于 95% 和来源 B 的 99% 不命中。"""
    hit = _fn("after_sales_on_time_hits")
    assert hit(94.9) is True
    assert hit(95) is False
    assert hit(99) is False


def test_common_mark_compares_the_given_hit_rate() -> None:
    """命中率 ≥40% 标共性。等于 40% 命中。不提供分子或分母。"""
    mark = _fn("is_common")
    assert mark(40) is True
    assert mark(39.9) is False
    assert not hasattr(_module(), "hit_rate_numerator")
    assert not hasattr(_module(), "hit_rate_denominator")


def test_individual_priority_combines_weight_and_mall_check_score() -> None:
    """P0 是权重 ≥30% 或绩效分 <3.5。P1 是中间档。P2 是权重 <15% 且分不低于 3.5。"""
    grade = _fn("individual_priority")
    assert grade(30, 4.0) == "P0"
    assert grade(10, 3.4) == "P0"
    assert grade(15, 3.5) == "P1"
    assert grade(29.9, 4.3) == "P1"
    assert grade(14.9, 4.0) == "P2"
    assert grade(10, 3.5) == "P2"


def test_impact_multiplies_the_given_weight_and_sorts_descending() -> None:
    """影响度等于调用方给出的权重乘命中率。引擎不填权重表。"""
    assert _fn("metric_weight_percent")("延迟发货率") is None
    assert _fn("metric_weight_percent")("用户评价分") is None
    assert _fn("impact")(3, 4) == 12
    assert _fn("impact")(2, 0.4) == 0.8
    assert _fn("sort_impacts")((0.2, 0.8, 0.5)) == (0.8, 0.5, 0.2)


def test_score_bands_put_endpoints_in_the_higher_band() -> None:
    """<3.5 高危，3.5 低危，4 正常，4.3 优秀。"""
    band = _fn("score_band")
    assert band(3.4) == "高危"
    assert band(3.5) == "低危"
    assert band(3.9) == "低危"
    assert band(4) == "正常"
    assert band(4.2) == "正常"
    assert band(4.3) == "优秀"
    assert band(5) == "优秀"


def test_store_and_subject_use_their_own_scores() -> None:
    """店铺用 mall_check_score。主体用主体平均分，没有另写字段名。"""
    assert _fn("dimension_score_label")("店铺") == "店铺绩效分"
    assert _fn("dimension_score_label")("主体") == "主体平均分"
    assert _fn("store_score_field")() == "mall_check_score"
    assert _fn("store_score_field")() != "perf_score"
    assert _fn("subject_score_field")() is None


def test_uncovered_rules_have_no_placeholder_percents() -> None:
    """未覆盖规则不输出占位百分数，也不编造六个售后类名。"""
    hit_line = _fn("hit_line_percent")
    assert hit_line("延迟发货率") == 10
    assert hit_line("24 小时回复率") == 90
    assert hit_line("售后准时率") == 95
    for name in UNCOVERED_HIT_METRICS:
        assert hit_line(name) is None
    assert _texts("strategy_metric_names") == ()
    assert _texts("fulfillment_column_names") == ()
    assert _texts("after_sales_class_names") == ()


def test_yellow_metrics_stay_unqueried_on_the_judgment_path() -> None:
    """五条黄标不查询、不替代，判定标为指标及相关明细空缺。"""
    assert _texts("yellow_metric_names") == YELLOW_METRICS
    queried = _fn("yellow_is_queried")
    substituted = _fn("yellow_is_substituted")
    for name in YELLOW_METRICS:
        assert queried(name) is False
        assert substituted(name) is False
    assert _fn("yellow_gap_mark")() == YELLOW_GAP_MARK


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
        return importlib.import_module("octop.infra.diagnosis.symptom_engine")
    except ImportError as exc:
        _absent(f"octop.infra.diagnosis.symptom_engine is absent ({exc})")


def _absent(detail: str) -> NoReturn:
    pytest.fail(f"symptom engine is absent: {detail}")
