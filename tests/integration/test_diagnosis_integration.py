"""RED fake-agent path for flow B.

Collection succeeds. The test fails because ``flow_b`` is absent.
"""

from __future__ import annotations

import importlib
from typing import Any

import pytest

from octop.infra.connectors.catalog import get_catalog_entry
from octop.infra.diagnosis.orchestrator import DiagnosisOrchestrator


def test_fake_agent_flow_b_keeps_flow_a_free_of_llm() -> None:
    """假 Agent 只在解读段被调用；流程 A 仍是零 LLM。门禁失败换会话。"""
    module = _module()
    calls: list[str] = []

    def _interpret() -> dict[str, Any]:
        calls.append("interpret")
        return {
            "headline": "摘要",
            "overall": "总体",
            "findings": [
                {
                    "title": "发现",
                    "severity": "一般",
                    "analysis": "分析",
                    "evidence": ["0.08"],
                    "data_refs": ["0.08"],
                }
            ],
            "actions": [{"title": "建议", "detail": "说明"}],
            "risks": [],
            "越阈指标": "待验证",
            "业务后果": "待验证",
            "绩效影响": "待验证",
            "平台后果": "待验证",
        }

    ok = module.diagnose_item(
        run_id="run-1",
        store_id="s1",
        attempt=1,
        conclusion=None,
        slice_values=("0.08",),
        llm=_interpret,
    )
    assert calls == ["interpret"]
    assert ok["result"] == "OK"
    assert ok["llm_calls"] == 1
    assert ok["stage1_llm_calls"] == 0
    assert ok["threads"] == ("diag:run-1:s1:a1",)

    def _invent() -> dict[str, Any]:
        bad = _interpret()
        bad["findings"][0]["data_refs"] = ["99"]
        return bad

    failed = module.diagnose_item(
        run_id="run-1",
        store_id="s2",
        attempt=1,
        conclusion=None,
        slice_values=("0.08",),
        llm=_invent,
    )
    assert failed["result"] == "FAIL"
    assert failed["status"] == "FAILED"
    assert failed["threads"] == ("diag:run-1:s2:a1", "diag:run-1:s2:a2")

    report = module.synthesize_report(
        (
            {"store_id": "s1", "status": ok["status"]},
            {"store_id": "s2", "status": failed["status"]},
        )
    )
    assert report["partial"] is True
    assert report["appendix"] == ("s2",)
    assert report["sections"][0] == "〇 执行摘要"
    assert report["sections"][-1] == "五 逐店明细"

    flow_a = DiagnosisOrchestrator(attribution_limit=3, llm=_interpret).submit(
        client_request_id="flow-a",
        stores=("s1",),
        preload_status="COMPLETED",
        row_count=1,
        snapshot_text="快照原文",
    )
    assert flow_a["llm_calls"] == 0
    entry = get_catalog_entry("store-perf")
    assert entry is not None
    assert entry.auth_kind == "api_key"
    assert entry.doc_url == "https://ucnbkepnx9u9.feishu.cn/wiki/UGlmwS7rsiqRs2kKpcEcLwuInbU"
    assert entry.icon == "store-perf"
    assert entry.phase == "available"
    visible = " ".join(
        part for part in (entry.description, entry.auth_hint) if isinstance(part, str)
    )
    assert "占位" not in visible
    assert "待拍板" not in visible
    assert "tencent-docs" not in visible
    assert entry.allowed_tools == (
        "get_data_latest",
        "submit_preload",
        "run_analysis",
        "drill_metric",
        "get_report",
    )
    assert "POST /drill" in entry.description
    assert "POST /analysis/run" in entry.description
    assert "GET /detail-excel" in entry.description


def _module() -> Any:
    try:
        return importlib.import_module("octop.infra.diagnosis.flow_b")
    except ImportError as exc:
        pytest.fail(f"flow B is absent: {exc}")
