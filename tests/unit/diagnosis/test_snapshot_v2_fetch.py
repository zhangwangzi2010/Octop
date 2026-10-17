"""RED contracts for schema v2 snapshot files and the two-level fetch.

``octop.infra.diagnosis.snapshot_store`` does not exist yet. These tests fail
because that API is absent. They persist and query only names already written
in the promoted contracts or the diagnosis modules on this branch.

Expected surface once the module exists:

- ``performance_table() -> str``
- ``performance_partition() -> str``
- ``performance_business_time() -> str``
- ``performance_row_key() -> str``
- ``performance_store_keys() -> tuple[str, str]``
- ``fulfillment_side_keys() -> tuple[str, str]``
- ``fulfillment_time_fields() -> tuple[str, str]``
- ``fulfillment_has_business_date() -> bool``
- ``documented_ratio_fields(metric_name) -> tuple[str, ...]``
- ``build_snapshot(...) -> dict``
- ``write_snapshot(data_dir, shop_id, document) -> str``
- ``read_snapshot(data_dir, shop_id) -> dict``
- ``two_level_fetch(document, sources=None) -> Mapping``
- ``read_store_fetch(data_dir, shop_id) -> Mapping``
"""

from __future__ import annotations

import importlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NoReturn

import pytest

from octop.infra.diagnosis.fetch_catalog import (
    l1_age_displays,
    l1_display_names,
    l2_leaves,
    yellow_labels,
)
from octop.infra.diagnosis.l1_semantic import (
    active_spu_metric,
    category_dimension,
    on_sale_spu_metric,
    overall_decline_fields,
    slice_overview_fields,
)
from octop.infra.diagnosis.promoted_contracts import q4_output_names, snapshot_path
from octop.infra.diagnosis.snapshot_json import metric_json_keys, snapshot_shape_fields

_MODULE = "octop.infra.diagnosis.snapshot_store"


def test_performance_query_uses_the_written_table() -> None:
    """绩效主表、分区、业务时间和行键用契约里已写出的名字。"""
    assert _call("performance_table") == "ai_nlsql.dwd_sto_temu_store_performance_df"
    assert _call("performance_partition") == "ds=max_pt"
    assert _call("performance_business_time") == "business_date"
    assert _call("performance_row_key") == "performance_indicator"
    assert _call("performance_store_keys") == ("store_id", "store_name")


def test_fulfillment_side_keeps_shop_keys_and_has_no_business_date() -> None:
    """履约侧键和时间字段按原文，并且没有 business_date。"""
    assert _call("fulfillment_side_keys") == ("shop_id", "shop_name")
    assert _call("fulfillment_time_fields") == ("order_time", "pay_time")
    assert _call("fulfillment_has_business_date") is False


def test_documented_ratio_fields_stop_at_the_written_pair() -> None:
    """延迟发货和延迟到货只返回已写出的分子分母，其余指标没有列名。"""
    late_ship = _call("documented_ratio_fields", "延迟发货率")
    late_arrival = _call("documented_ratio_fields", "延迟到货率")
    assert late_ship == (
        "parent_shipping_time > expect_ship_latest_time",
        "已发货且 ship_time IS NOT NULL",
    )
    assert late_arrival == (
        "parent_receipt_time > latest_delivery_time",
        "parent_receipt_time IS NOT NULL",
    )
    assert _call("documented_ratio_fields", "缺货率") == ()
    assert len(late_ship) == 2
    assert len(late_arrival) == 2


def test_snapshot_path_has_no_version_segment(tmp_path: Path) -> None:
    """一店一文件路径是 {data_dir}/{shop_id}.json，没有版本段。"""
    path = _call("write_snapshot", str(tmp_path), "shop-1", _document())
    assert path == snapshot_path(str(tmp_path), "shop-1")
    assert Path(path).name == "shop-1.json"
    assert "v2" not in Path(path).parts
    assert _call("read_snapshot", str(tmp_path), "shop-1")["店铺"] == "一店"


def test_two_shops_get_two_files(tmp_path: Path) -> None:
    """两家店铺各自一份 schema v2 快照。"""
    _call("write_snapshot", str(tmp_path), "shop-a", _document(shop="甲"))
    _call("write_snapshot", str(tmp_path), "shop-b", _document(shop="乙"))
    assert _call("read_snapshot", str(tmp_path), "shop-a")["店铺"] == "甲"
    assert _call("read_snapshot", str(tmp_path), "shop-b")["店铺"] == "乙"
    assert {path.name for path in tmp_path.iterdir()} == {"shop-a.json", "shop-b.json"}


def test_written_json_keeps_only_the_promoted_keys(tmp_path: Path) -> None:
    """落盘只留形状字段、规范分、Q4 短名和可选 prev。窗口与物理列名不入库。"""
    document = _document()
    document["window_start"] = "2026-10-01"
    document["window_end"] = "2026-10-15"
    document["store_performance"]["extra"] = 1
    document["store_performance"]["metrics"]["推广 roas"] = {"latest": 1}
    document["store_performance"]["metrics"]["延迟发货率"]["indicator_data_detail"] = 0.2
    document["store_performance"]["metrics"]["延迟发货率"]["prev"] = 0.2
    _call("write_snapshot", str(tmp_path), "shop-1", document)
    loaded = json.loads((tmp_path / "shop-1.json").read_text(encoding="utf-8"))
    assert set(loaded) == set(snapshot_shape_fields())
    performance = loaded["store_performance"]
    assert set(performance) == {"mall_check_score", "perf_score", "score_level", "metrics"}
    assert performance["mall_check_score"] == 4.1
    assert performance["perf_score"] == 3.8
    assert performance["mall_check_score"] != performance["perf_score"]
    assert set(performance["metrics"]) == set(metric_json_keys())
    late_ship = performance["metrics"]["延迟发货率"]
    assert set(late_ship) == {*q4_output_names(), "prev"}
    assert late_ship["prev"] == 0.2
    assert "indicator_data_detail" not in late_ship
    assert "window_start" not in loaded
    assert "window_end" not in loaded
    assert "business_date" not in loaded
    assert "store_id" not in loaded


def test_build_snapshot_maps_physical_columns_onto_q4_keys() -> None:
    """绩效行用物理列读入，快照键仍是 kickoff 写法下的 Q4 短名。"""
    document = _call(
        "build_snapshot",
        shop="一店",
        subject="主体甲",
        owner="负责人甲",
        mall_check_score=4.1,
        perf_score=3.8,
        score_level="正常",
        rows=(
            {
                "store_id": "s1",
                "store_name": "一店",
                "business_date": "2026-10-15",
                "performance_indicator": "延迟发货率",
                "indicator_data_detail": 0.1,
                "indicator_data_over_peers_rate": 0.4,
                "indicator_data_next_level_threshold": 0.05,
            },
            {
                "performance_indicator": "24小时回复率",
                "indicator_data_detail": 0.5,
            },
            {
                "performance_indicator": "用户评价分",
                "indicator_data_detail": 4.25,
            },
            {
                "performance_indicator": "24 小时回复率",
                "indicator_data_detail": 0.8,
                "indicator_data_over_peers_rate": 0.2,
                "indicator_data_next_level_threshold": 0.9,
            },
        ),
    )
    metrics = document["store_performance"]["metrics"]
    assert metrics["延迟发货率"] == {
        "latest": 0.1,
        "over_peers": 0.4,
        "next_level": 0.05,
    }
    assert metrics["用户评价分"]["latest"] == 4.25
    assert metrics["24 小时回复率"]["latest"] == 0.8
    assert metrics["24 小时回复率"]["over_peers"] == 0.2
    assert "24小时回复率" not in metrics
    assert metrics["缺货率"] == {"latest": None, "over_peers": None, "next_level": None}
    assert "store_id" not in document
    assert "business_date" not in document


def test_two_level_fetch_lists_the_frozen_displays() -> None:
    """第一级 27 个展示名，第二级 25 个叶子，顺序跟目录一致。"""
    fetched = _call("two_level_fetch", _document())
    level1 = _items(fetched, "level1")
    level2 = _items(fetched, "level2")
    assert [(item["band"], item["name"]) for item in level1] == [
        ("", name) for name in l1_display_names()
    ] + [(band, metric) for band, metric in l1_age_displays()]
    assert [(item["group"], item["name"]) for item in level2] == list(l2_leaves())
    assert [item["name"] for item in _items(fetched, "yellow")] == list(yellow_labels())


def test_yellow_metrics_are_skipped_with_empty_details() -> None:
    """五条黄标不查询、不替代，SKIP，明细为空，标记为指标及相关明细空缺。"""
    fetched = _call("two_level_fetch", _document())
    yellow = _items(fetched, "yellow")
    assert len(yellow) == 5
    for item in yellow:
        assert item["queried"] is False
        assert item["skipped"] is True
        assert item["value"] is None
        assert item["details"] == ()
        assert item["mark"] == "指标及相关明细空缺"
    by_leaf = {(item["group"], item["name"]): item for item in _items(fetched, "level2")}
    stock = by_leaf[("商品检查单", "库存")]
    assert stock["skipped"] is True
    assert stock["queried"] is False
    assert stock["value"] is None
    assert stock["details"] == ()
    assert by_leaf[("商品检查单", "超预算(关停)")]["skipped"] is False
    assert by_leaf[("商品检查单", "roas环比变化")]["skipped"] is False
    assert by_leaf[("商品运营", "推广Roas")]["skipped"] is False
    assert by_leaf[("平台风控", "流量异常SPU数/占比")]["skipped"] is False
    assert by_leaf[("商品运营", "推广Roas")]["mark"] == ""
    assert by_leaf[("平台风控", "流量异常SPU数/占比")]["mark"] == ""


def test_level2_reads_only_exact_snapshot_keys() -> None:
    """叶子与快照键逐字相同才读到 latest；空格和用词不同的名字保持缺口。"""
    fetched = _call("two_level_fetch", _document())
    by_leaf = {(item["group"], item["name"]): item for item in _items(fetched, "level2")}
    refund = by_leaf[("店铺绩效", "非买家责任退货退款率")]
    assert refund["queried"] is True
    assert refund["skipped"] is False
    assert refund["value"] == 0.08
    assert dict(refund["details"]) == {
        "latest": 0.08,
        "over_peers": 0.3,
        "next_level": 0.05,
    }
    assert "indicator_data_detail" not in dict(refund["details"])
    reply = by_leaf[("店铺绩效", "24小时回复率")]
    assert reply["queried"] is False
    assert reply["value"] is None
    assert reply["details"] == ()
    ship = by_leaf[("店铺绩效", "48小时发货率")]
    assert ship["queried"] is False
    assert ship["value"] is None
    prices = [
        by_leaf[("商品检查单", "件单价")],
        by_leaf[("商品运营", "件单价")],
    ]
    assert prices[0]["queried"] is False
    assert prices[1]["queried"] is False
    assert prices[0] is not prices[1]


def test_level1_reports_named_fields_without_a_derived_value() -> None:
    """已写出的语义字段挂在展示名上；环比、占比和贡献不算出数值。"""
    fetched = _call(
        "two_level_fetch",
        _document(),
        sources={"sales_amount": 10.0, "ecommerce.metric.active_spu_rate": 0.4},
    )
    by_name = {(item["band"], item["name"]): item for item in _items(fetched, "level1")}
    gmv = by_name[("", "GMV环比下滑幅度")]
    assert gmv["fields"] == (overall_decline_fields()[0],)
    assert gmv["queried"] is True
    assert gmv["derived"] is True
    assert gmv["value"] is None
    assert gmv["mark"] == ""
    quantity = by_name[("", "销量环比下滑幅度")]
    assert quantity["fields"] == (overall_decline_fields()[1],)
    orders = by_name[("", "订单量下滑占比")]
    assert orders["fields"] == (overall_decline_fields()[2],)
    assert orders["value"] is None
    missing = by_name[("", "下滑SPU数占比")]
    assert missing["fields"] == ()
    assert missing["queried"] is False
    assert missing["value"] is None
    assert missing["skipped"] is False
    assert by_name[("", "动销SPU下滑占比")]["fields"] == (active_spu_metric(),)
    assert by_name[("", "在售SPU下滑占比")]["fields"] == (on_sale_spu_metric(),)
    category = by_name[("", "品类下滑幅度")]
    assert category["group"] == "品类"
    assert category["fields"] == (*slice_overview_fields(), category_dimension())
    assert category["value"] is None
    top = by_name[("", "Top x 下滑款清单")]
    assert top["group"] == "Top"
    assert top["fields"] == slice_overview_fields()
    assert top["value"] is None
    age_rate = by_name[("0-10天", "动销率")]
    assert age_rate["fields"] == ("ecommerce.metric.active_spu_rate",)
    assert age_rate["queried"] is True
    assert age_rate["derived"] is False
    assert age_rate["value"] is None
    assert age_rate["band"] == "0-10天"
    assert by_name[("30-90天", "动销率")]["band"] != "30–90"
    contribution = by_name[("90天以上", "下滑贡献占比")]
    assert contribution["fields"] == slice_overview_fields()
    assert contribution["derived"] is True
    assert contribution["value"] is None


def test_run_shop_ids_read_the_two_level_path(tmp_path: Path) -> None:
    """用写入时的 shop_id 读回两级结果，不经过 LLM。"""
    _call("write_snapshot", str(tmp_path), "shop-1", _document())
    fetched = _call("read_store_fetch", str(tmp_path), "shop-1")
    assert "llm_calls" not in fetched
    assert len(_items(fetched, "level1")) == 27
    assert len(_items(fetched, "level2")) == 25
    refund = next(
        item
        for item in _items(fetched, "level2")
        if item["group"] == "店铺绩效" and item["name"] == "非买家责任退货退款率"
    )
    assert refund["value"] == 0.08
    yellow = next(item for item in _items(fetched, "yellow") if item["name"] == "库存")
    assert yellow["skipped"] is True
    assert yellow["details"] == ()


def _document(shop: str = "一店") -> dict[str, Any]:
    metrics = {
        key: {"latest": None, "over_peers": None, "next_level": None} for key in metric_json_keys()
    }
    metrics["非买家责任退货退款率"] = {
        "latest": 0.08,
        "over_peers": 0.3,
        "next_level": 0.05,
    }
    metrics["延迟发货率"] = {"latest": 0.1, "over_peers": None, "next_level": None}
    metrics["用户评价分"] = {"latest": 4.25, "over_peers": None, "next_level": None}
    return {
        "店铺": shop,
        "主体": "主体甲",
        "负责人": "负责人甲",
        "store_performance": {
            "mall_check_score": 4.1,
            "perf_score": 3.8,
            "score_level": "正常",
            "metrics": metrics,
        },
    }


def _items(fetched: Mapping[str, Any], key: str) -> tuple[Mapping[str, Any], ...]:
    value = fetched[key]
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        _absent(f"{key} did not return fetch items")
    return tuple(item for item in value if isinstance(item, Mapping))


def _call(name: str, *args: Any, **kwargs: Any) -> Any:
    return _fn(name)(*args, **kwargs)


def _fn(name: str) -> Any:
    function = getattr(_module(), name, None)
    if not callable(function):
        _absent(f"{name} is not implemented")
    return function


def _module() -> Any:
    try:
        return importlib.import_module(_MODULE)
    except ImportError as exc:
        _absent(f"{_MODULE} is absent ({exc})")


def _absent(detail: str) -> NoReturn:
    pytest.fail(f"schema v2 fetch is absent: {detail}")
