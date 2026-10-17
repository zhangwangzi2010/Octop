"""RED acceptance for a background diagnosis fixture.

The runner is absent. These tests do not invent thresholds, drill routes,
or a total-weight formula.
"""

from __future__ import annotations

import importlib
from typing import Any

import pytest

from octop.infra.diagnosis.hit_weights import metric_weight_percent
from octop.infra.diagnosis.snapshot_store import build_snapshot, write_snapshot
from octop.infra.diagnosis.symptom_engine import score_band


def test_three_store_fixture_reaches_partial_from_snapshot_files(tmp_path: Any) -> None:
    """健康店跳过，个体其次，共性最后。编造数字进附录。报告数字来自快照。"""
    module = _module()
    data_dir = tmp_path / "snaps"
    _write_store(
        data_dir,
        "healthy",
        mall_check_score=4.5,
        review=4.5,
        late_ship=0.01,
    )
    _write_store(
        data_dir,
        "individual",
        mall_check_score=3.4,
        review=3.4,
        late_ship=0.1,
    )
    _write_store(
        data_dir,
        "fabricated",
        mall_check_score=4.6,
        review=4.8,
        late_ship=0.1,
    )
    report = module.run_fixture(
        data_dir=str(data_dir),
        stores=("healthy", "individual", "fabricated"),
        llm=_fake_llm,
    )
    assert report["status"] == "PARTIAL"
    assert report["partial"] is True
    assert "fabricated" in report["appendix"]
    assert report["order"] == ("SKIP", "individual", "commonality")
    assert report["llm_calls"] == 0
    assert report["yellow_values"] == ()
    assert report["groups"]["P0"] == ("individual",)
    assert "individual" in report["top5"]
    assert len(report["top5"]) <= 5
    assert "延迟发货率" in report["commonality"]
    assert "〇 执行摘要" in report["sections"]
    assert "fabricated" in report["threads"][-1]
    assert report["threads"][-1].endswith(":a2")
    assert 999 not in report["numbers"]
    assert set(report["numbers"]) <= _snapshot_numbers(data_dir)
    assert "分流表" not in " ".join(report["gaps"])
    assert "一级派生" in " ".join(report["gaps"])
    assert "总权重" not in " ".join(report["gaps"])
    assert metric_weight_percent("C-S07") == 10
    assert score_band(3.4) == "高危"


def test_timeout_and_cancel_stop_the_running_checkpoint() -> None:
    """超时和取消都停在正在执行的检查点，不再诊断后面的店。"""
    module = _module()
    stopped = module.stop_at_checkpoint(action="timeout")
    assert stopped["continued"] is False
    assert stopped["diagnosed"] == ()
    cancelled = module.stop_at_checkpoint(action="cancel")
    assert cancelled["status"] == "CANCELLED"
    assert cancelled["continued"] is False
    assert cancelled["diagnosed"] == ()


def _fake_llm(store_id: str, slice_values: tuple[object, ...]) -> dict[str, Any]:
    cited: object = 999 if store_id == "fabricated" else slice_values[0]
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


def _write_store(
    data_dir: Any,
    shop_id: str,
    *,
    mall_check_score: float,
    review: float,
    late_ship: float,
) -> None:
    document = build_snapshot(
        shop=shop_id,
        subject="主体",
        owner="负责人",
        mall_check_score=mall_check_score,
        perf_score=mall_check_score,
        score_level=score_band(mall_check_score),
        rows=(
            {"performance_indicator": "用户评价分", "indicator_data_detail": review},
            {"performance_indicator": "延迟发货率", "indicator_data_detail": late_ship},
            {"performance_indicator": "非买家责任退货退款率", "indicator_data_detail": 0.01},
            {"performance_indicator": "延迟到货率", "indicator_data_detail": 0.01},
            {"performance_indicator": "24 小时回复率", "indicator_data_detail": 0.95},
            {"performance_indicator": "售后准时率", "indicator_data_detail": 0.96},
            {"performance_indicator": "售罄健康分", "indicator_data_detail": 96},
            {"performance_indicator": "活动报名率", "indicator_data_detail": 0.95},
        ),
    )
    write_snapshot(str(data_dir), shop_id, document)


def _snapshot_numbers(data_dir: Any) -> set[float]:
    found: set[float] = set()
    for path in data_dir.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        found.update(_floats_in(text))
    return found


def _floats_in(text: str) -> set[float]:
    import json

    raw = json.loads(text)

    def walk(value: object) -> set[float]:
        if isinstance(value, bool):
            return set()
        if isinstance(value, (int, float)):
            return {float(value)}
        if isinstance(value, dict):
            found: set[float] = set()
            for item in value.values():
                found.update(walk(item))
            return found
        if isinstance(value, list):
            found = set()
            for item in value:
                found.update(walk(item))
            return found
        return set()

    return walk(raw)


def _module() -> Any:
    try:
        return importlib.import_module("octop.infra.diagnosis.fixture_run")
    except ImportError as exc:
        pytest.fail(f"fixture run is absent: {exc}")
