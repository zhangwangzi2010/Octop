"""Report body details that a snapshot can check.

P0/P1/P2 follow the locked Top5 key. Each suggestion carries the evidence
triple. PARTIAL lists FAILED and SKIPPED in the body. No real LLM.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from octop.infra.diagnosis.l1_semantic import yellow_metric_names
from octop.infra.diagnosis.remaining_contracts import chosen_detail_limit
from octop.infra.diagnosis.snapshot_store import (
    build_snapshot,
    performance_table,
    write_snapshot,
)
from octop.infra.diagnosis.snapshot_structure import parse_period
from octop.infra.diagnosis.symptom_engine import score_band

_WINDOW = "最近 60 天（不含今天）"
_DETAIL = chosen_detail_limit()


def test_priority_groups_follow_the_top5_weight_key(tmp_path: Any) -> None:
    """低权重店先写入，分组仍按个体权重、总权重、绩效分排。"""
    module = _module()
    data_dir = tmp_path / "snaps"
    _write(data_dir, "p_low", 4.1, {"活动报名率": 0.8})
    _write(data_dir, "p_high", 4.0, {"非买家责任退货退款率": 0.05, "延迟到货率": 0.03})
    _write(data_dir, "filler", 4.5, {})
    report = module.run_fixture(
        data_dir=str(data_dir),
        stores=("p_low", "p_high", "filler"),
        llm=_citing_llm,
    )
    body = str(report["body"])
    assert report["groups"]["P1"] == ("p_high", "p_low")
    assert report["top5"] == ("p_high", "p_low")
    lines = body.splitlines()
    assert "P1 p_high、p_low" in lines
    assert "Top5 p_high、p_low" in lines
    assert lines.index("p_high") < lines.index("p_low")
    refund = _line(body, "非买家责任退货退款率 ")
    arrival = _line(body, "延迟到货率 ")
    campaign = _line(body, "活动报名率 ")
    assert body.index(refund) < body.index(arrival) < body.index(campaign)
    assert "指标值 0.05" in refund
    assert "sheet 售后" in refund
    assert "指标值 0.03" in arrival
    assert "sheet 到货" in arrival
    assert "指标值 0.8" in campaign
    assert "无明细下钻能力" in campaign
    assert "sheet" not in campaign
    for line in (refund, arrival, campaign):
        assert f"明细条数 {_DETAIL}" in line
        assert f"时间范围 {_WINDOW}" in line
    assert not any(line.startswith("整改 ") for line in lines)
    assert "高危提示" not in body
    assert "SKIPPED filler" in body.splitlines()
    assert report["llm_calls"] == 0
    assert "999" not in body
    _assert_no_forbidden(body)


def test_three_store_body_carries_evidence_partial_and_danger(tmp_path: Any) -> None:
    """共性店低于 3.5 带高危提示。Top5 证据来自快照。附录写进正文。"""
    module = _module()
    data_dir = tmp_path / "snaps"
    _write(data_dir, "healthy", 4.5, {"用户评价分": 4.5, "延迟发货率": 0.01})
    _write(data_dir, "individual", 3.4, {"用户评价分": 3.4, "延迟发货率": 0.1})
    _write(data_dir, "fabricated", 4.6, {"用户评价分": 4.8, "延迟发货率": 0.1})
    report = module.run_fixture(
        data_dir=str(data_dir),
        stores=("healthy", "individual", "fabricated"),
        llm=_fake_llm,
    )
    body = str(report["body"])
    window = parse_period(_WINDOW, today=date(2026, 10, 19))
    assert isinstance(window, tuple)
    assert len(window) == 60
    assert report["status"] == "PARTIAL"
    assert report["llm_calls"] == 0
    assert report["appendix"] == ("healthy", "fabricated")
    assert "⭐ 延迟发货率" in body.splitlines()
    assert "individual 3.4 高危 高危提示" in body.splitlines()
    assert "fabricated 4.6 优秀" in body.splitlines()
    assert body.count("高危提示") == 1
    four = body.index("四 整改优先级")
    five = body.index("五 逐店明细")
    assert four < body.index("整改 延迟发货率") < five
    review = _line(body, "用户评价分 ")
    ship = _line(body, "延迟发货率 ")
    assert five < body.index(review) < body.index(ship)
    assert "指标值 3.4" in review
    assert "sheet 评价" in review
    assert "指标值 0.1" in ship
    assert "sheet 发货" in ship
    for line in (review, ship):
        assert f"明细条数 {_DETAIL}" in line
        assert f"时间范围 {_WINDOW}" in line
    skipped = body.index("SKIPPED healthy")
    failed = body.index("FAILED fabricated")
    assert five < skipped < failed
    assert "999" not in body
    assert 999 not in report["numbers"]
    assert 60 not in report["numbers"]
    assert 3.4 in report["numbers"]
    assert 0.1 in report["numbers"]
    _assert_no_forbidden(body)


def _assert_no_forbidden(body: str) -> None:
    assert ":8787" not in body
    assert "SELECT" not in body
    assert performance_table() not in body
    for name in yellow_metric_names():
        assert name not in body


def _line(body: str, prefix: str) -> str:
    return next(line for line in body.splitlines() if line.startswith(prefix))


def _citing_llm(store_id: str, slice_values: tuple[object, ...]) -> dict[str, Any]:
    del store_id
    cited: object = slice_values[0]
    return _conclusion(cited)


def _fake_llm(store_id: str, slice_values: tuple[object, ...]) -> dict[str, Any]:
    cited: object = 999 if store_id == "fabricated" else slice_values[0]
    return _conclusion(cited)


def _conclusion(cited: object) -> dict[str, Any]:
    return {
        "headline": "摘要",
        "overall": "总体",
        "findings": [
            {
                "title": "发现",
                "severity": "一般",
                "analysis": "分析",
                "evidence": [cited],
                "data_refs": [cited],
            }
        ],
        "actions": [{"title": "建议", "detail": "说明"}],
        "risks": [],
        "越阈指标": "待验证",
        "业务后果": "待验证",
        "绩效影响": "待验证",
        "平台后果": "待验证",
    }


def _write(
    data_dir: Any, shop_id: str, mall_check_score: float, overrides: dict[str, float]
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
    latest.update(overrides)
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
    write_snapshot(str(data_dir), shop_id, document)


def _module() -> Any:
    import importlib

    return importlib.import_module("octop.infra.diagnosis.fixture_run")
