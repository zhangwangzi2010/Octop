"""RED: runtime level-1 values from the locked derived formulas.

Pop, decline contribution, and the weight index cover Top, category, and
age, with GMV and quantity kept apart. Names without a formula stay empty
and are marked gap. TOP X's X is not chosen here.
"""

from __future__ import annotations

import importlib
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from octop.infra.diagnosis.l1_semantic import age_bands, day_30_age_band, derived_formula
from octop.infra.diagnosis.snapshot_json import metric_json_keys


def test_live_minimal_computes_pop_contribution_and_weight_index() -> None:
    """环比、贡献占比、权重指数按已锁公式现算，GMV 与销量分开。"""
    live = _fn("live_minimal")
    window = _cls("MeasureWindow")
    result = live(
        overall={
            "sales_amount": window(current=80, previous=100),
            "sales_quantity": window(current=50, previous=40),
        },
        slices={
            "Top": {
                "sales_amount": window(
                    current=80,
                    previous=100,
                    slice_changes=(-20.0, 10.0, -20.0),
                    slice_previous_total=200,
                ),
                "sales_quantity": window(
                    current=50,
                    previous=40,
                    slice_changes=(10.0, -4.0),
                    slice_previous_total=80,
                ),
            },
            "品类": {
                "sales_amount": window(
                    current=80,
                    previous=100,
                    slice_changes=(-20.0, 10.0, -20.0),
                    slice_previous_total=200,
                ),
                "sales_quantity": window(
                    current=50,
                    previous=40,
                    slice_changes=(10.0, -4.0),
                    slice_previous_total=80,
                ),
            },
            "30–89": {
                "sales_amount": window(
                    current=80,
                    previous=100,
                    slice_changes=(-20.0, -20.0),
                    slice_previous_total=200,
                ),
            },
        },
    )
    assert result["displays"]["GMV环比下滑幅度"] == pytest.approx(-20)
    assert result["displays"]["销量环比下滑幅度"] == pytest.approx(25)
    assert result["slices"]["品类"]["sales_amount"]["contribution"] == pytest.approx(0.5)
    assert result["slices"]["品类"]["sales_amount"]["weight_index"] == pytest.approx(0.25)
    assert result["slices"]["品类"]["sales_quantity"]["contribution"] == pytest.approx(1)
    assert result["slices"]["品类"]["sales_quantity"]["weight_index"] == pytest.approx(0.5)
    assert result["slices"]["Top"]["sales_quantity"]["pop"] == pytest.approx(25)
    assert result["slices"]["30–89"]["sales_amount"]["contribution"] == pytest.approx(0.5)
    assert derived_formula("环比") is None


def test_formula_gaps_and_unknown_age_spellings_stay_empty() -> None:
    """无公式项、TOP X 和截图售龄串不产生数字。"""
    live = _fn("live_minimal")
    window = _cls("MeasureWindow")
    result = live(
        slices={
            "11-30天": {"sales_amount": window(current=80, previous=100)},
            day_30_age_band(): {"sales_amount": window(current=80, previous=100)},
        }
    )
    assert result["displays"]["GMV环比下滑幅度"] is None
    assert result["top_x"] is None
    assert "11-30天" not in result["slices"]
    assert day_30_age_band() not in result["slices"]
    assert day_30_age_band() not in age_bands()
    for name in (
        "订单量下滑占比",
        "下滑SPU数占比",
        "动销SPU下滑占比",
        "在售SPU下滑占比",
        "Top x 下滑款清单",
        "Top x GMV 下滑贡献占比",
        "品类下滑贡献占比",
    ):
        assert name in result["gaps"]
    assert result["gap_mark"] == "gap"
    assert _fn("measure_result")("品类", window(current=1, previous=0))["pop"] is None


def test_two_level_fetch_applies_windows_and_marks_gaps() -> None:
    """读取时现算已有公式的展示值，其余标 gap。"""
    fetch = _fetch()
    window = _cls("MeasureWindow")
    fetched = fetch(
        _document(),
        windows={
            "overall": {"sales_amount": window(current=80, previous=100)},
        },
    )
    by_name = {(item["band"], item["name"]): item for item in _items(fetched["level1"])}
    assert by_name[("", "GMV环比下滑幅度")]["value"] == pytest.approx(-20)
    orders = by_name[("", "订单量下滑占比")]
    assert orders["value"] is None
    assert orders["mark"] == "gap"
    assert by_name[("", "Top x 下滑款清单")]["mark"] == "gap"
    assert by_name[("", "Top x 下滑款清单")]["value"] is None


def _document() -> dict[str, Any]:
    metrics = {
        key: {"latest": None, "over_peers": None, "next_level": None} for key in metric_json_keys()
    }
    return {
        "店铺": "一店",
        "主体": "主体甲",
        "负责人": "负责人甲",
        "store_performance": {
            "mall_check_score": 4.1,
            "perf_score": 3.8,
            "score_level": "正常",
            "metrics": metrics,
        },
    }


def _items(value: object) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        pytest.fail("level1 did not return items")
    return tuple(item for item in value if isinstance(item, Mapping))


def _fetch() -> Any:
    module = importlib.import_module("octop.infra.diagnosis.snapshot_store")
    return module.two_level_fetch


def _fn(name: str) -> Any:
    module = importlib.import_module("octop.infra.diagnosis.derived_metrics")
    function = getattr(module, name, None)
    if not callable(function):
        pytest.fail(f"{name} is not implemented")
    return function


def _cls(name: str) -> Any:
    module = importlib.import_module("octop.infra.diagnosis.derived_metrics")
    value = getattr(module, name, None)
    if not isinstance(value, type):
        pytest.fail(f"{name} is not implemented")
    return value
