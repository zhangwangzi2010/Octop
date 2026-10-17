"""RED contracts for the ten metric weights and the seven new hit lines.

``octop.infra.diagnosis.hit_weights`` does not exist yet. These tests fail
because that API is absent. They do not invent strategy metric names,
fulfillment column names, after-sales class names, or slice D formulas.

Expected surface once the module exists:

- ``metric_ids() -> Sequence[str]``
- ``metric_name(metric_id) -> str``
- ``metric_weight_percent(metric_id) -> float``
- ``hit_rule(metric_id) -> str``
- ``multiplies_by_100(metric_id) -> bool``
- ``score_hits(metric_id, value) -> bool``
- ``stored_ratio_hits(metric_id, stored) -> bool``
- ``percent_hits(metric_id, percent) -> bool``
- ``pop_direction_hits(metric_id, direction) -> bool``
- ``pop_magnitude_percent(metric_id) -> None``
- ``judgment_basis(metric_id) -> str``
- ``document_numerator(metric_id) -> str | None``
- ``document_denominator(metric_id) -> str | None``
- ``reply_rate_judgment_name() -> str``
- ``reply_rate_contrast_spelling() -> str``
- ``common_hit_rate(hit_store_count, eligible_store_count) -> float``
- ``common_mark_percent() -> int``
- ``counts_toward_common_denominator(has_value, yellow_gap) -> bool``
- ``yellow_gap_mark() -> str``
- ``entity_avg_field() -> str``
- ``entity_avg_mall_check_score(scores) -> float``
- ``store_score_field() -> str``
- ``strategy_metric_names() -> Sequence[str]``
- ``fulfillment_column_names() -> Sequence[str]``
- ``after_sales_class_names() -> Sequence[str]``
"""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from typing import Any, NoReturn

import pytest

METRIC_IDS = (
    "C-S07",
    "C-S08",
    "C-S09",
    "C-S10",
    "C-S11",
    "C-S12",
    "C-S13",
    "C-S14",
    "C-S15",
    "C-S16",
)
METRIC_NAMES = {
    "C-S07": "用户评价分",
    "C-S08": "非买家责任退货退款率",
    "C-S09": "延迟发货率",
    "C-S10": "延迟到货率",
    "C-S11": "缺货率",
    "C-S12": "24 小时回复率",
    "C-S13": "售后准时率",
    "C-S14": "爆旺款率",
    "C-S15": "售罄健康分",
    "C-S16": "活动报名率",
}
WEIGHTS = {
    "C-S07": 10,
    "C-S08": 10,
    "C-S09": 5,
    "C-S10": 10,
    "C-S11": 10,
    "C-S12": 5,
    "C-S13": 5,
    "C-S14": 10,
    "C-S15": 20,
    "C-S16": 15,
}
HIT_RULES = {
    "C-S07": "< 4",
    "C-S08": "×100 后 ≥ 5%",
    "C-S09": "≥10%",
    "C-S10": "×100 后 ≥ 3%",
    "C-S11": "环比上升",
    "C-S12": "<90%",
    "C-S13": "<95%",
    "C-S14": "环比下降",
    "C-S15": "< 95",
    "C-S16": "×100 后 < 90%",
}
LATE_SHIP_NUMERATOR = "parent_shipping_time > expect_ship_latest_time"
LATE_SHIP_DENOMINATOR = "已发货且 ship_time IS NOT NULL"
LATE_ARRIVAL_NUMERATOR = "parent_receipt_time > latest_delivery_time"
LATE_ARRIVAL_DENOMINATOR = "parent_receipt_time IS NOT NULL"
LATEST_VS_THRESHOLD = ("C-S08", "C-S12", "C-S13", "C-S16")
POP_DIRECTION_ONLY = ("C-S11", "C-S14")
YELLOW_GAP_MARK = "指标及相关明细空缺"


def test_all_ten_weights_and_hit_rules() -> None:
    """十个权重和命中规则按目录登记。C-S09 仍是 ≥10%，不是 ≥2%。"""
    assert _texts("metric_ids") == METRIC_IDS
    weight = _fn("metric_weight_percent")
    name = _fn("metric_name")
    rule = _fn("hit_rule")
    for metric_id in METRIC_IDS:
        assert name(metric_id) == METRIC_NAMES[metric_id]
        assert weight(metric_id) == WEIGHTS[metric_id]
        assert rule(metric_id) == HIT_RULES[metric_id]
    assert sum(WEIGHTS.values()) == 100
    assert "≥2%" not in rule("C-S09")


def test_review_score_hits_below_four_without_scaling() -> None:
    """用户评价分低于 4 命中。等于 4 不命中。分值不乘 100。"""
    assert _fn("multiplies_by_100")("C-S07") is False
    assert _fn("judgment_basis")("C-S07") == "score_passthrough"
    hits = _fn("score_hits")
    assert hits("C-S07", 3.9) is True
    assert hits("C-S07", 4) is False


def test_refund_rate_hits_at_five_percent() -> None:
    """非买家责任退货退款率 ×100 后 ≥5% 命中，含等于 5%。"""
    assert _fn("multiplies_by_100")("C-S08") is True
    assert _fn("judgment_basis")("C-S08") == "latest_vs_threshold"
    assert _fn("document_numerator")("C-S08") is None
    hits = _fn("stored_ratio_hits")
    assert hits("C-S08", 0.05) is True
    assert hits("C-S08", 0.049) is False


def test_late_shipment_keeps_ten_percent_and_document_fields() -> None:
    """C-S09 权重 5%。命中线仍是 ≥10%。分子分母用已写出的字段。"""
    assert _fn("metric_weight_percent")("C-S09") == 5
    assert _fn("hit_rule")("C-S09") == "≥10%"
    assert _fn("percent_hits")("C-S09", 10) is True
    assert _fn("percent_hits")("C-S09", 2) is False
    assert _fn("stored_ratio_hits")("C-S09", 0.1) is True
    assert _fn("stored_ratio_hits")("C-S09", 0.02) is False
    assert _fn("document_numerator")("C-S09") == LATE_SHIP_NUMERATOR
    assert _fn("document_denominator")("C-S09") == LATE_SHIP_DENOMINATOR
    assert _fn("judgment_basis")("C-S09") == "document_ratio"


def test_late_arrival_hits_at_three_percent() -> None:
    """延迟到货率 ×100 后 ≥3% 命中。分子分母用已写出的字段。"""
    assert _fn("metric_weight_percent")("C-S10") == 10
    assert _fn("multiplies_by_100")("C-S10") is True
    hits = _fn("stored_ratio_hits")
    assert hits("C-S10", 0.03) is True
    assert hits("C-S10", 0.029) is False
    assert _fn("document_numerator")("C-S10") == LATE_ARRIVAL_NUMERATOR
    assert _fn("document_denominator")("C-S10") == LATE_ARRIVAL_DENOMINATOR


def test_stockout_hits_only_when_pop_rises() -> None:
    """缺货率环比上升才命中。没有上升幅度百分数。"""
    assert _fn("metric_weight_percent")("C-S11") == 10
    assert _fn("judgment_basis")("C-S11") == "pop_direction"
    assert _fn("pop_magnitude_percent")("C-S11") is None
    assert _fn("document_numerator")("C-S11") is None
    hits = _fn("pop_direction_hits")
    assert hits("C-S11", "上升") is True
    assert hits("C-S11", "下降") is False


def test_reply_and_after_sales_weights_stay_five() -> None:
    """C-S12 与 C-S13 权重都是 5%。命中线仍是 <90% 与 <95%。"""
    assert _fn("metric_weight_percent")("C-S12") == 5
    assert _fn("metric_weight_percent")("C-S13") == 5
    assert _fn("reply_rate_judgment_name")() == "24 小时回复率"
    assert _fn("reply_rate_contrast_spelling")() == "24小时回复率"
    assert _fn("percent_hits")("C-S12", 89.9) is True
    assert _fn("percent_hits")("C-S12", 90) is False
    assert _fn("percent_hits")("C-S13", 94.9) is True
    assert _fn("percent_hits")("C-S13", 95) is False
    assert _fn("judgment_basis")("C-S12") == "latest_vs_threshold"
    assert _fn("judgment_basis")("C-S13") == "latest_vs_threshold"


def test_hot_product_hits_only_when_pop_falls() -> None:
    """爆旺款率环比下降才命中。没有下降幅度百分数。"""
    assert _fn("metric_weight_percent")("C-S14") == 10
    assert _fn("judgment_basis")("C-S14") == "pop_direction"
    assert _fn("pop_magnitude_percent")("C-S14") is None
    assert _fn("document_numerator")("C-S14") is None
    hits = _fn("pop_direction_hits")
    assert hits("C-S14", "下降") is True
    assert hits("C-S14", "上升") is False


def test_sellout_score_hits_below_ninety_five_without_scaling() -> None:
    """售罄健康分低于 95 命中。等于 95 不命中。分值不乘 100。"""
    assert _fn("metric_weight_percent")("C-S15") == 20
    assert _fn("multiplies_by_100")("C-S15") is False
    assert _fn("judgment_basis")("C-S15") == "score_passthrough"
    hits = _fn("score_hits")
    assert hits("C-S15", 94.9) is True
    assert hits("C-S15", 95) is False


def test_campaign_rate_hits_below_ninety() -> None:
    """活动报名率 ×100 后低于 90% 命中。等于 90% 不命中。"""
    assert _fn("metric_weight_percent")("C-S16") == 15
    assert _fn("multiplies_by_100")("C-S16") is True
    assert _fn("judgment_basis")("C-S16") == "latest_vs_threshold"
    assert _fn("document_numerator")("C-S16") is None
    hits = _fn("stored_ratio_hits")
    assert hits("C-S16", 0.899) is True
    assert hits("C-S16", 0.9) is False


def test_ratios_without_document_numerator_do_not_invent_columns() -> None:
    """没有单据级分子的比率只用最新值对阈值，或只用环比方向。"""
    basis = _fn("judgment_basis")
    numerator = _fn("document_numerator")
    for metric_id in LATEST_VS_THRESHOLD:
        assert basis(metric_id) == "latest_vs_threshold"
        assert numerator(metric_id) is None
    for metric_id in POP_DIRECTION_ONLY:
        assert basis(metric_id) == "pop_direction"
        assert numerator(metric_id) is None
    assert _texts("fulfillment_column_names") == ()
    assert _texts("strategy_metric_names") == ()
    assert _texts("after_sales_class_names") == (
        "1-物流履约",
        "2-产品满意度",
        "3-商品价格",
        "4-店铺原因",
        "5-平台原因",
        "6-其他原因",
    )


def test_common_hit_rate_excludes_yellow_gaps() -> None:
    """共性命中率 = 命中店铺数 / 有可取数值且不是黄标空缺的店铺数。"""
    counts = _fn("counts_toward_common_denominator")
    assert counts(True, False) is True
    assert counts(True, True) is False
    assert counts(False, False) is False
    assert _fn("yellow_gap_mark")() == YELLOW_GAP_MARK
    assert _fn("common_hit_rate")(2, 5) == 0.4
    assert _fn("common_mark_percent")() == 40


def test_entity_average_is_mean_of_store_scores() -> None:
    """主体平均分字段是 entity_avg_mall_check_score，等于各店 mall_check_score 的平均。"""
    assert _fn("entity_avg_field")() == "entity_avg_mall_check_score"
    assert _fn("store_score_field")() == "mall_check_score"
    average = _fn("entity_avg_mall_check_score")
    assert average((3.0, 4.0, 5.0)) == 4.0
    assert average((3.5, 4.5)) == 4.0


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
        return importlib.import_module("octop.infra.diagnosis.hit_weights")
    except ImportError as exc:
        _absent(f"octop.infra.diagnosis.hit_weights is absent ({exc})")


def _absent(detail: str) -> NoReturn:
    pytest.fail(f"hit weights are absent: {detail}")
