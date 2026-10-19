"""RED: analysis_guide routing table and drill routes.

The body uses the locked hit lines. C-S09 stays ≥10%. The other six metrics
say 无明细下钻能力.
"""

from __future__ import annotations

import importlib
from typing import Any

import pytest

from octop.infra.diagnosis.flow_b import load_skills, soul_steps
from octop.infra.diagnosis.snapshot_store import build_snapshot, performance_table, write_snapshot
from octop.infra.diagnosis.symptom_engine import score_band


def test_analysis_guide_body_uses_locked_lines() -> None:
    """分流表正文留在 analysis_guide。不带回 ≥2%。其余三份正文另写，不改这条口径。"""
    loaded = tuple(load_skills())
    guide = next(item for item in loaded if item["name"] == "analysis_guide")
    body = str(guide["body"])
    assert body == _fn("analysis_guide_body")()
    assert "无明细下钻能力" in body
    assert "≥10%" in body
    assert "≥2%" not in body
    for name in ("绩效分", "用户评价分", "非买家责任退货退款率", "延迟发货率", "延迟到货率"):
        assert name in body
    for name in ("缺货率", "24 小时回复率", "售后准时率", "爆旺款率", "售罄健康分", "活动报名率"):
        assert name in body
    others = [item for item in loaded if item["name"] != "analysis_guide"]
    assert [item["name"] for item in others] == [
        "metrics_catalog",
        "drilldown_playbook",
        "query_tasks",
    ]
    assert all(str(item["body"]).strip() for item in others)
    assert all("≥2%" not in str(item["body"]) for item in loaded)
    assert all(":8787" not in str(item["body"]) for item in loaded)
    assert soul_steps()[0].startswith("① read_file")


def test_drill_routes_cover_five_and_mark_six() -> None:
    """可下钻五项挂路由。其余六项写无明细下钻能力。"""
    route = _fn("drill_route")
    mark = _fn("undrillable_mark")
    assert route("绩效分") == performance_table()
    assert route("C-S07") == "评价"
    assert route("C-S08") == "售后"
    assert route("C-S09") == "发货"
    assert route("C-S10") == "到货"
    for metric_id in ("C-S11", "C-S12", "C-S13", "C-S14", "C-S15", "C-S16"):
        assert route(metric_id) is None
        assert mark(metric_id) == "无明细下钻能力"
    assert mark("C-S07") == ""


def test_fixture_hangs_the_drill_route(tmp_path: Any) -> None:
    """命中项带上路由或无明细下钻能力。"""
    module = importlib.import_module("octop.infra.diagnosis.fixture_run")
    document = build_snapshot(
        shop="one",
        subject="主体",
        owner="负责人",
        mall_check_score=4.0,
        perf_score=4.0,
        score_level=score_band(4.0),
        rows=(
            {"performance_indicator": "用户评价分", "indicator_data_detail": 3.0},
            {
                "performance_indicator": "缺货率",
                "indicator_data_detail": 1.04,
                "prev": 1.0,
            },
        ),
    )
    write_snapshot(str(tmp_path), "one", document)
    report = module.run_fixture(data_dir=str(tmp_path), stores=("one",), llm=None)
    by_metric = {item["metric_id"]: item for item in report["drills"]}
    assert by_metric["C-S07"]["route"] == "评价"
    assert by_metric["C-S07"]["mark"] == ""
    assert by_metric["C-S11"]["route"] is None
    assert by_metric["C-S11"]["mark"] == "无明细下钻能力"
    assert "分流表" not in " ".join(report["gaps"])
    assert "≥2%" not in str(_fn("analysis_guide_body")())


def _fn(name: str) -> Any:
    module = importlib.import_module("octop.infra.diagnosis.flow_b")
    function = getattr(module, name, None)
    if not callable(function):
        pytest.fail(f"{name} is not implemented")
    return function
