"""RED: pop direction for C-S11/C-S14 and summed store weights.

Direction is the sign of (本期-上期)/上期×100%. Zero and a value that cannot
be computed do not hit. The 5% worsening bands are not the hit line.
individual_weight sums non-common hits. total_weight sums every hit.
"""

from __future__ import annotations

import importlib
from typing import Any

import pytest

from octop.infra.diagnosis.hit_weights import metric_weight_percent, pop_direction_hits
from octop.infra.diagnosis.pop_rules import worsening_grade
from octop.infra.diagnosis.snapshot_store import build_snapshot, write_snapshot
from octop.infra.diagnosis.symptom_engine import individual_priority, score_band


def test_direction_is_the_sign_and_ignores_five_percent_bands() -> None:
    """上升是环比大于 0，下降是小于 0。等于 0 或上期为 0 不命中。"""
    percent = _fn("octop.infra.diagnosis.pop_rules", "pop_percent")
    direction = _fn("octop.infra.diagnosis.pop_rules", "pop_direction")
    assert percent(1.04, 1.0) == pytest.approx(4)
    assert percent(0.96, 1.0) == pytest.approx(-4)
    assert direction(1.04, 1.0) == "上升"
    assert direction(0.96, 1.0) == "下降"
    assert direction(1.0, 1.0) is None
    assert direction(1.0, 0.0) is None
    assert worsening_grade(4, polarity="negative") is None
    assert worsening_grade(-4, polarity="positive") is None
    assert pop_direction_hits("C-S11", direction(1.04, 1.0)) is True
    assert pop_direction_hits("C-S14", direction(0.96, 1.0)) is True
    assert pop_direction_hits("C-S11", "下降") is False
    assert pop_direction_hits("C-S14", "上升") is False


def test_individual_weight_drops_common_hits_and_total_keeps_them() -> None:
    """个体权重去掉共性。总权重保留共性。多命中不再当成 0。"""
    individual = _fn("octop.infra.diagnosis.hit_weights", "individual_weight")
    total = _fn("octop.infra.diagnosis.hit_weights", "total_weight")
    hits = ("C-S07", "C-S09", "C-S11")
    assert individual(hits, ("C-S09",)) == metric_weight_percent("C-S07") + metric_weight_percent(
        "C-S11"
    )
    assert total(hits) == (
        metric_weight_percent("C-S07")
        + metric_weight_percent("C-S09")
        + metric_weight_percent("C-S11")
    )
    assert individual(("C-S08", "C-S10"), ()) == 20
    assert individual_priority(35, 4.0) == "P0"
    assert individual_priority(20, 4.0) == "P1"
    assert individual_priority(5, 4.0) == "P2"
    assert individual_priority(5, 3.4) == "P0"


def test_multi_hit_fixture_sorts_top5_and_grades_direction_hits(tmp_path: Any) -> None:
    """多命中店按个体权重、总权重、绩效分排序，并命中 C-S11 / C-S14。"""
    module = importlib.import_module("octop.infra.diagnosis.fixture_run")
    data_dir = tmp_path / "snaps"
    _write(data_dir, "m", 4.0, _overrides_m())
    _write(data_dir, "a", 4.0, _overrides_a())
    _write(data_dir, "b", 3.8, _overrides_b())
    _write(data_dir, "c", 4.2, _overrides_c())
    _write(data_dir, "s", 3.4, {"售后准时率": (0.90, None)})
    _write(data_dir, "d", 4.5, {"延迟发货率": (0.10, None)})
    report = module.run_fixture(
        data_dir=str(data_dir),
        stores=("m", "a", "b", "c", "s", "d"),
        llm=None,
    )
    by_store = {row["store_id"]: row for row in report["store_weights"]}
    assert by_store["m"]["hits"] == ("C-S11", "C-S14", "C-S16")
    assert by_store["m"]["individual_weight"] == 35
    assert by_store["m"]["total_weight"] == 35
    assert by_store["a"]["individual_weight"] == 20
    assert by_store["a"]["total_weight"] == 25
    assert by_store["b"]["individual_weight"] == 20
    assert by_store["b"]["total_weight"] == 20
    assert by_store["c"]["individual_weight"] == 15
    assert by_store["s"]["individual_weight"] == 5
    assert set(report["groups"]["P0"]) == {"m", "s"}
    assert set(report["groups"]["P1"]) == {"a", "b", "c"}
    assert report["groups"]["P2"] == ()
    assert report["top5"] == ("m", "a", "b", "c", "s")
    assert "d" not in report["top5"]
    assert "总权重" not in " ".join(report["gaps"])


def _overrides_m() -> dict[str, tuple[float, float | None]]:
    return {
        "缺货率": (1.04, 1.0),
        "爆旺款率": (0.96, 1.0),
        "活动报名率": (0.80, None),
    }


def _overrides_a() -> dict[str, tuple[float, float | None]]:
    return {
        "售罄健康分": (90, None),
        "延迟发货率": (0.10, None),
    }


def _overrides_b() -> dict[str, tuple[float, float | None]]:
    return {
        "非买家责任退货退款率": (0.05, None),
        "延迟到货率": (0.03, None),
    }


def _overrides_c() -> dict[str, tuple[float, float | None]]:
    return {
        "用户评价分": (3.0, None),
        "24 小时回复率": (0.80, None),
    }


def _write(
    data_dir: Any,
    shop_id: str,
    mall_check_score: float,
    overrides: dict[str, tuple[float, float | None]],
) -> None:
    latest = {
        "用户评价分": 4.5,
        "非买家责任退货退款率": 0.01,
        "延迟发货率": 0.01,
        "延迟到货率": 0.01,
        "缺货率": 1.0,
        "24 小时回复率": 0.95,
        "售后准时率": 0.96,
        "爆旺款率": 1.0,
        "售罄健康分": 96,
        "活动报名率": 0.95,
    }
    prev = {"缺货率": 1.0, "爆旺款率": 0.9}
    for name, (value, previous) in overrides.items():
        latest[name] = value
        if previous is not None:
            prev[name] = previous
    document = build_snapshot(
        shop=shop_id,
        subject="主体",
        owner="负责人",
        mall_check_score=mall_check_score,
        perf_score=mall_check_score,
        score_level=score_band(mall_check_score),
        rows=tuple(
            {"performance_indicator": name, "indicator_data_detail": value}
            for name, value in latest.items()
        ),
    )
    metrics = document["store_performance"]["metrics"]
    for name, previous in prev.items():
        metrics[name]["prev"] = previous
    write_snapshot(str(data_dir), shop_id, document)


def _fn(module_name: str, name: str) -> Any:
    module = importlib.import_module(module_name)
    function = getattr(module, name, None)
    if not callable(function):
        pytest.fail(f"{name} is not implemented")
    return function
