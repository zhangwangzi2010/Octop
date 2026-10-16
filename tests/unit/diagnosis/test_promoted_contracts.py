"""RED contracts for names promoted in diagnosis-promoted-contracts.

``octop.infra.diagnosis.promoted_contracts`` does not exist yet. These tests
fail because that module is absent. They do not assert JSON keys, ratio
scales, strategy metric names, or threshold percents.

Expected surface once the module exists:

- ``snapshot_path(data_dir, shop_id) -> str``
- ``second_level_metric_names() -> Sequence[str]``
- ``kickoff_metric_ids() -> Sequence[tuple[str, str]]``
- ``prefixed_metric_ids() -> Sequence[str]``
- ``performance_score_ids() -> Sequence[str]``
- ``q4_output_names() -> Sequence[str]``
- ``q4_column_labels() -> Sequence[str]``
- ``q4_physical_fields() -> Sequence[tuple[str, str]]``
- ``detail_tables() -> Sequence[tuple[str, str]]``
- ``drill_templates() -> Sequence[tuple[str, str]]``
"""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from typing import Any, NoReturn

import pytest

SECOND_LEVEL_NAMES = (
    "用户评价分",
    "非买家责任退货退款率",
    "延迟发货率",
    "延迟到货率",
    "缺货率",
    "24小时回复率",
    "售后准时率",
    "爆旺款率",
    "售罄健康分",
    "活动报名率",
)
KICKOFF_METRIC_IDS = (
    ("用户评价分", "temu_store_user_review_score"),
    ("非买家责任退货退款率", "temu_store_non_buyer_fault_return_refund_rate"),
    ("延迟发货率", "temu_store_late_shipment_rate"),
    ("延迟到货率", "temu_store_late_delivery_rate"),
    ("缺货率", "temu_store_out_of_stock_rate"),
    ("24 小时回复率", "temu_store_24h_reply_rate"),
    ("售后准时率", "temu_store_after_sales_on_time_rate"),
    ("爆旺款率", "temu_store_hot_product_rate"),
    ("售罄健康分", "temu_store_sellout_health_score"),
    ("活动报名率", "temu_store_campaign_registration_rate"),
)
PREFIXED_METRIC_IDS = (
    "ecommerce.metric.temu_store_user_review_score",
    "ecommerce.metric.temu_store_sellout_health_score",
)
UNPREFIXED_SHORT_IDS = tuple(
    metric_id
    for _name, metric_id in KICKOFF_METRIC_IDS
    if metric_id
    not in {
        "temu_store_user_review_score",
        "temu_store_sellout_health_score",
    }
)
PERFORMANCE_SCORE_IDS = (
    "store_performance_score_average",
    "ecommerce.metric.store_performance_score_average",
)
Q4_OUTPUT_NAMES = ("latest", "over_peers", "next_level")
Q4_COLUMN_LABELS = ("最新值", "超过同行", "下一级标准")
Q4_PHYSICAL_FIELDS = (
    ("indicator_data_detail", "指标最新值"),
    ("indicator_data_over_peers_rate", "超过同行水平"),
    ("indicator_data_next_level_threshold", "下一级标准"),
)
DETAIL_TABLES = (
    ("评价", "dwd_prd_temu_review_detail_df"),
    ("售后", "dwd_trd_temu_refund_detail_df"),
    ("发货", "dwm_robot_self_order_detail_df"),
    ("到货", "dwm_robot_self_order_detail_df"),
)
DRILL_TEMPLATES = (
    ("店铺绩效异常", "评价"),
    ("非买家责任退款退货率", "售后"),
    ("延迟发货（48小时发货）", "发货"),
    ("延迟到货", "到货"),
)


def test_snapshot_path_is_one_file_per_shop_without_version_segment() -> None:
    """路径是 {data_dir}/{shop_id}.json。两家店铺各一份，中间没有版本段。"""
    path = _fn("snapshot_path")
    left = path("data_dir", "shop-a")
    right = path("data_dir", "shop-b")
    assert left == "data_dir/shop-a.json"
    assert right == "data_dir/shop-b.json"
    assert left != right
    assert left.split("/") == ["data_dir", "shop-a.json"]
    assert right.split("/") == ["data_dir", "shop-b.json"]


def test_second_level_names_and_ids_match_the_promoted_list() -> None:
    """十个白名单名字，以及 kickoff 表格里的短 metric id。"""
    assert _texts("second_level_metric_names") == SECOND_LEVEL_NAMES
    assert _pairs("kickoff_metric_ids") == KICKOFF_METRIC_IDS
    assert len(SECOND_LEVEL_NAMES) == 10


def test_reply_rate_keeps_both_spellings() -> None:
    """24小时回复率与 24 小时回复率都保留，id 跟在表格那一行。"""
    names = _texts("second_level_metric_names")
    rows = _pairs("kickoff_metric_ids")
    assert "24小时回复率" in names
    assert "24 小时回复率" in {name for name, _metric_id in rows}
    assert "24小时回复率" != "24 小时回复率"
    reply_ids = [metric_id for name, metric_id in rows if name == "24 小时回复率"]
    assert reply_ids == ["temu_store_24h_reply_rate"]


def test_prefixed_ids_cover_only_the_two_written_metrics() -> None:
    """只保留规格逐项写出的两个带前缀 id，不给其余八项补前缀。"""
    prefixed = _texts("prefixed_metric_ids")
    assert prefixed == PREFIXED_METRIC_IDS
    for short_id in UNPREFIXED_SHORT_IDS:
        assert f"ecommerce.metric.{short_id}" not in prefixed


def test_performance_score_ids_stay_outside_the_ten() -> None:
    """店铺绩效分不在十个名字里。两个绩效分 id 单独保留。"""
    names = _texts("second_level_metric_names")
    short_ids = {metric_id for _name, metric_id in _pairs("kickoff_metric_ids")}
    score_ids = _texts("performance_score_ids")
    assert "店铺绩效分" not in names
    assert "店铺绩效分均值" not in names
    assert score_ids == PERFORMANCE_SCORE_IDS
    assert set(score_ids).isdisjoint(short_ids)


def test_q4_names_are_not_the_physical_columns() -> None:
    """latest / over_peers / next_level 不并成物理字段名。"""
    outputs = _texts("q4_output_names")
    labels = _texts("q4_column_labels")
    fields = _pairs("q4_physical_fields")
    assert outputs == Q4_OUTPUT_NAMES
    assert labels == Q4_COLUMN_LABELS
    assert fields == Q4_PHYSICAL_FIELDS
    assert len(SECOND_LEVEL_NAMES) * len(outputs) == 30
    physical_names = [name for name, _purpose in fields]
    assert list(outputs) != physical_names
    assert "latest" != "indicator_data_detail"
    assert "over_peers" != "indicator_data_over_peers_rate"
    assert "next_level" != "indicator_data_next_level_threshold"
    assert "最新值" != "指标最新值"
    assert "超过同行" != "超过同行水平"


def test_detail_templates_use_the_promoted_physical_tables() -> None:
    """评价、售后、发货、到货使用规格给出的物理表。发货与到货同一张表。"""
    tables = _pairs("detail_tables")
    assert tables == DETAIL_TABLES
    by_template = dict(tables)
    assert by_template["发货"] == by_template["到货"] == "dwm_robot_self_order_detail_df"
    assert by_template["评价"] != by_template["发货"]
    assert by_template["售后"] != by_template["发货"]


def test_section_63_wording_is_not_rewritten_to_the_ten_names() -> None:
    """需求触发项保持原词，不并进十项指标名。"""
    drills = _pairs("drill_templates")
    names = _texts("second_level_metric_names")
    assert drills == DRILL_TEMPLATES
    assert "非买家责任退款退货率" != "非买家责任退货退款率"
    assert "非买家责任退货退款率" in names
    assert "非买家责任退款退货率" not in names
    triggers = [trigger for trigger, _template in drills]
    assert "非买家责任退款退货率" in triggers
    assert "非买家责任退货退款率" not in triggers


def _texts(name: str) -> tuple[str, ...]:
    value = _fn(name)()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        _absent(f"{name} did not return display strings")
    return tuple(str(item) for item in value)


def _pairs(name: str) -> tuple[tuple[str, str], ...]:
    rows = _fn(name)()
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
        _absent(f"{name} did not return string pairs")
    pairs: list[tuple[str, str]] = []
    for row in rows:
        if isinstance(row, (str, bytes)) or not isinstance(row, Sequence) or len(row) != 2:
            _absent(f"{name} did not return string pairs")
        pairs.append((str(row[0]), str(row[1])))
    return tuple(pairs)


def _fn(name: str) -> Any:
    function = getattr(_module(), name, None)
    if not callable(function):
        _absent(f"{name} is not implemented")
    return function


def _module() -> Any:
    try:
        return importlib.import_module("octop.infra.diagnosis.promoted_contracts")
    except ImportError as exc:
        _absent(f"octop.infra.diagnosis.promoted_contracts is absent ({exc})")


def _absent(detail: str) -> NoReturn:
    pytest.fail(f"promoted contracts are absent: {detail}")
