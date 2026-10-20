"""Store-perf catalog availability and orchestrator pass-through.

The five tool names stay. Nodes call the existing client. A mock transport
stands in for the external service. No new client and no embedded service.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from octop.infra.connectors.catalog import get_catalog_entry
from octop.infra.diagnosis.orchestrator import DiagnosisOrchestrator
from octop.infra.diagnosis.snapshot_store import performance_table
from octop.infra.diagnosis.store_perf_client import (
    API_KEY_ENV,
    BASE_URL_ENV,
    StorePerfClient,
    client_from_env,
    tool_http,
    tool_names,
)

_TOOLS = (
    "get_data_latest",
    "submit_preload",
    "run_analysis",
    "drill_metric",
    "get_report",
)
_WINDOW = {"start": "2026-10-01", "end": "2026-10-07"}
_RUN = "run-1"
_STORE = "shop-9"


def test_store_perf_catalog_is_available_with_the_same_five_tools() -> None:
    """目录阶段是 available。五个工具名不变。"""
    entry = get_catalog_entry("store-perf")
    assert entry is not None
    assert entry.phase == "available"
    assert entry.allowed_tools == _TOOLS
    assert tool_names() == _TOOLS


def test_nodes_pass_run_id_and_store_id_through_the_existing_client() -> None:
    """编排节点把 run_id / store_id 交给已有客户端的五次调用。"""
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        seen.append(
            {
                "method": request.method,
                "path": request.url.path,
                "auth": request.headers.get("authorization"),
                "query": dict(request.url.params),
                "body": body,
            }
        )
        return httpx.Response(
            200,
            json={
                "table": performance_table(),
                "columns": ["store_id"],
                "rows": [{"store_id": _STORE}],
                "read_only": True,
            },
        )

    client = client_from_env(
        {BASE_URL_ENV: "http://store-perf.invalid", API_KEY_ENV: ""},
        transport=httpx.MockTransport(handler),
    )
    assert isinstance(client, StorePerfClient)
    orchestrator = DiagnosisOrchestrator(attribution_limit=3, store_perf=client)
    report = orchestrator.submit(
        client_request_id="mcp-1",
        stores=(_STORE,),
        preload_status="COMPLETED",
        row_count=1,
        snapshot_text="快照原文",
        window=_WINDOW,
        drill_metric="延迟发货率",
        drill_top=3,
    )
    calls = report["store_perf_calls"]
    assert [item["tool"] for item in calls] == list(_TOOLS)
    assert [item["node"] for item in calls] == [
        "ensure_data_ready",
        "ensure_data_ready",
        "analysis_run",
        "drill_metric",
        "summarize",
    ]
    for item in calls:
        assert item["run_id"] == _RUN
        assert item["store_id"] == _STORE
        assert item["args"]["run_id"] == _RUN
        assert item["args"]["store_id"] == _STORE
    assert report["llm_calls"] == 0
    assert len(seen) == 5
    for tool, request in zip(_TOOLS, seen, strict=True):
        method, path = tool_http(tool)
        assert request["method"] == method
        assert request["path"] == path
        assert request["auth"] is None
        if method == "GET":
            assert request["query"]["store"] == _STORE
            assert json.loads(request["query"]["window"]) == _WINDOW
            assert "run_id" not in request["query"]
        else:
            assert request["body"]["store"] == _STORE
            assert request["body"]["window"] == _WINDOW
            assert "run_id" not in request["body"]
            assert "store_id" not in request["body"]
    drill = seen[3]["body"]
    assert drill["metric"] == "延迟发货率"
    assert drill["top"] == 3
    again = orchestrator.submit(
        client_request_id="mcp-1",
        stores=(_STORE, "other"),
        preload_status="COMPLETED",
        row_count=1,
        snapshot_text="快照原文",
        window=_WINDOW,
        drill_metric="延迟发货率",
        drill_top=3,
    )
    assert again["run_id"] == _RUN
    assert len(seen) == 5
