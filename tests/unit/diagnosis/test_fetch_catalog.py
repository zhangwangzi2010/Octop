"""RED contracts for the frozen fetch display-name catalog.

``octop.infra.diagnosis.fetch_catalog`` does not exist yet. These tests fail
because that catalog is absent. They do not add SQL, JSON keys, file paths,
or a ratio scale.

Expected surface once the module exists. Values are display strings only:

- ``l1_display_names() -> Sequence[str]`` — 19 names (6 overall + 11 TOP X + 2 品类)
- ``l1_age_displays() -> Sequence[tuple[str, str]]`` — 8 ``(band, metric)`` pairs
- ``product_strategy_dimensions() -> Sequence[str]``
- ``product_strategy_metric_names() -> Sequence[str]`` — decided empty
- ``l2_leaves() -> Sequence[tuple[str, str]]`` — 25 ``(checklist, leaf)`` pairs
- ``drill_triggers() -> Sequence[str]`` — four §6.3 trigger strings
- ``yellow_labels() -> Sequence[str]`` — the five yellow labels, exact spelling
- ``metric_gate(name) -> fetchable / skipped / value``
"""

from __future__ import annotations

import importlib
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn

import pytest

OVERALL = (
    "GMV环比下滑幅度",
    "销量环比下滑幅度",
    "订单量下滑占比",
    "下滑SPU数占比",
    "动销SPU下滑占比",
    "在售SPU下滑占比",
)
TOP_X = (
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
)
CATEGORY = (
    "品类下滑幅度",
    "品类下滑贡献占比",
)
AGE_BANDS = ("0-10天", "11-30天", "30-90天", "90天以上")
AGE_METRICS = ("动销率", "下滑贡献占比")
PARENT_GROUPS = (
    "上期GMV/销量占比",
    "本期GMV/销量占比",
    "下滑贡献占比",
    "下滑权重指数",
)
STRATEGY_DIMENSIONS = ("原创款", "跟卖款", "裂变款")
L2_LEAVES = (
    ("商品检查单", "违规"),
    ("商品检查单", "库存"),
    ("商品检查单", "商品评分"),
    ("商品检查单", "超预算(关停)"),
    ("商品检查单", "roas环比变化"),
    ("商品检查单", "在售时长"),
    ("商品检查单", "加价率"),
    ("商品检查单", "价格"),
    ("商品检查单", "流量异常（建议调价未调价）"),
    ("商品检查单", "件单价"),
    ("平台风控", "流量异常SPU数/占比"),
    ("平台风控", "违规SPU数/占比"),
    ("店铺运营", "活动覆盖率"),
    ("店铺运营", "流量加速覆盖率"),
    ("店铺绩效", "用户评价"),
    ("店铺绩效", "非买家责任退货退款率"),
    ("店铺绩效", "48小时发货率"),
    ("店铺绩效", "延迟到货率"),
    ("店铺绩效", "24小时回复率"),
    ("店铺绩效", "售后准时率"),
    ("店铺绩效", "爆旺款率"),
    ("店铺绩效", "售罄健康分"),
    ("商品运营", "推广Roas"),
    ("商品运营", "上新SPU数"),
    ("商品运营", "件单价"),
)
DRILL_TRIGGERS = (
    "店铺绩效异常",
    "非买家责任退款退货率",
    "延迟发货（48小时发货）",
    "延迟到货",
)
YELLOW_LABELS = (
    "库存",
    "推广 roas",
    "流量异常（建议调价未调价）",
    "流量异常SPU数占比",
    "推广 Roas",
)
SCREENSHOT_SPELLINGS = (
    "推广roas",
    "流量异常SPU数/占比",
    "推广Roas",
)


def test_l1_catalog_has_twenty_seven_display_names() -> None:
    """6 整体 + 11 TOP X + 2 品类 + 8 售龄，合计 27。父分组不是取数字段。"""
    names = _texts("l1_display_names")
    ages = _pairs("l1_age_displays")
    assert names == OVERALL + TOP_X + CATEGORY
    assert ages == tuple((band, metric) for band in AGE_BANDS for metric in AGE_METRICS)
    assert len(names) + len(ages) == 27
    assert not set(PARENT_GROUPS) & set(names)
    assert "店铺下滑症状" not in names
    assert "单品下滑症状" not in names


def test_product_strategy_keeps_dimensions_and_does_not_invent_metrics() -> None:
    """维度是原创款、跟卖款、裂变款。额外指标名已拍板为空，不计入 27 项。"""
    dimensions = _texts("product_strategy_dimensions")
    metrics = _texts("product_strategy_metric_names")
    names = _texts("l1_display_names")
    assert dimensions == STRATEGY_DIMENSIONS
    assert metrics == ()
    assert not set(dimensions) & set(names)


def test_l2_catalog_has_twenty_five_checklist_leaves() -> None:
    """商品检查单 10、平台风控 2、店铺运营 2、店铺绩效 8、商品运营 3。"""
    leaves = _pairs("l2_leaves")
    assert leaves == L2_LEAVES
    assert len(leaves) == 25
    groups = ("商品检查单", "平台风控", "店铺运营", "店铺绩效", "商品运营")
    counts = dict.fromkeys(groups, 0)
    for group, _leaf in leaves:
        counts[group] += 1
    assert counts == {
        "商品检查单": 10,
        "平台风控": 2,
        "店铺运营": 2,
        "店铺绩效": 8,
        "商品运营": 3,
    }
    assert all(leaf != "推广roas" for _group, leaf in leaves)
    unit_prices = [group for group, leaf in leaves if leaf == "件单价"]
    assert unit_prices == ["商品检查单", "商品运营"]
    leaf_names = {leaf for _group, leaf in leaves}
    assert "症状结论总结" not in leaf_names
    assert "异常归因结论" not in leaf_names
    assert "商品评价" not in leaf_names
    assert "物流履约" not in leaf_names
    assert "客户服务" not in leaf_names


def test_drill_triggers_keep_requirement_wording() -> None:
    """§6.3 用需求正文，不改写成检查单叶子。"""
    triggers = _texts("drill_triggers")
    leaves = _pairs("l2_leaves")
    leaf_names = {leaf for _group, leaf in leaves}
    assert triggers == DRILL_TRIGGERS
    assert "非买家责任退货退款率" in leaf_names
    assert "48小时发货率" in leaf_names
    assert "非买家责任退货退款率" not in triggers
    assert "48小时发货率" not in triggers
    assert "非买家责任退款退货率" not in leaf_names
    assert "延迟发货（48小时发货）" not in leaf_names


def test_yellow_labels_stay_unfetchable_without_numbers() -> None:
    """黄标五条原文，库存即使截图未标黄也 SKIP，不产生数值。"""
    assert _texts("yellow_labels") == YELLOW_LABELS
    gate = _fn("metric_gate")
    for name in YELLOW_LABELS:
        row = gate(name)
        assert _field(row, "fetchable") is False
        assert _field(row, "skipped") is True
        assert _field(row, "value") is None


def test_shutdown_spend_and_roas_change_stay_fetchable() -> None:
    """推广花费（关停）与 roas环比变化可取数。超预算(关停)不是第六条黄标。"""
    labels = _texts("yellow_labels")
    gate = _fn("metric_gate")
    assert "推广花费（关停）" not in labels
    assert "roas环比变化" not in labels
    assert "超预算(关停)" not in labels
    for name in ("推广花费（关停）", "roas环比变化", "超预算(关停)"):
        row = gate(name)
        assert _field(row, "fetchable") is True
        assert _field(row, "skipped") is False


def test_screenshot_spellings_do_not_replace_yellow_labels() -> None:
    """推广roas、流量异常SPU数/占比、推广Roas 不替换黄标原文。"""
    labels = _texts("yellow_labels")
    gate = _fn("metric_gate")
    assert labels == YELLOW_LABELS
    for name in SCREENSHOT_SPELLINGS:
        assert name not in labels
        row = gate(name)
        assert _field(row, "fetchable") is True
        assert _field(row, "skipped") is False
    bare = gate("流量异常")
    assert _field(bare, "fetchable") is True
    assert _field(bare, "skipped") is False


def test_red_screenshot_names_stay_fetchable() -> None:
    """订单量下滑占比、在售SPU下滑占比不因截图标红而不可取数。"""
    gate = _fn("metric_gate")
    labels = _texts("yellow_labels")
    for name in ("订单量下滑占比", "在售SPU下滑占比"):
        assert name not in labels
        row = gate(name)
        assert _field(row, "fetchable") is True
        assert _field(row, "skipped") is False


def _texts(name: str) -> tuple[str, ...]:
    value = _fn(name)()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        _absent(f"{name} did not return display strings")
    return tuple(str(item) for item in value)


def _pairs(name: str) -> tuple[tuple[str, str], ...]:
    rows = _fn(name)()
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
        _absent(f"{name} did not return display pairs")
    pairs: list[tuple[str, str]] = []
    for row in rows:
        if isinstance(row, (str, bytes)) or not isinstance(row, Sequence) or len(row) != 2:
            _absent(f"{name} did not return display pairs")
        pairs.append((str(row[0]), str(row[1])))
    return tuple(pairs)


def _fn(name: str) -> Any:
    function = getattr(_module(), name, None)
    if not callable(function):
        _absent(f"{name} is not implemented")
    return function


def _module() -> Any:
    try:
        return importlib.import_module("octop.infra.diagnosis.fetch_catalog")
    except ImportError as exc:
        _absent(f"octop.infra.diagnosis.fetch_catalog is absent ({exc})")


def _field(row: Any, name: str) -> Any:
    if isinstance(row, Mapping):
        return row[name]
    return getattr(row, name)


def _absent(detail: str) -> NoReturn:
    pytest.fail(f"display-name catalog is absent: {detail}")
