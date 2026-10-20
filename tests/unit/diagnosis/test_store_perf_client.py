"""RED: Octop calls an external :8787. It does not embed the service.

The request parameters are store, window, metric, and top. Response tables
and columns stay on the promoted names. A mock transport stands in for :8787.
"""

from __future__ import annotations

import importlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

from octop.infra.connectors.catalog import get_catalog_entry
from octop.infra.diagnosis.fetch_catalog import l1_display_names
from octop.infra.diagnosis.hit_weights import (
    entity_avg_field,
    fulfillment_column_names,
    store_score_field,
    strategy_metric_names,
)
from octop.infra.diagnosis.l1_semantic import (
    active_spu_metric,
    age_active_rate_metric,
    age_clock_field,
    category_dimension,
    on_sale_spu_metric,
    overall_decline_fields,
    overall_decline_source,
    slice_overview_fields,
    yellow_metric_names,
)
from octop.infra.diagnosis.promoted_contracts import (
    detail_tables,
    kickoff_metric_ids,
    performance_score_ids,
    prefixed_metric_ids,
    q4_output_names,
    q4_physical_fields,
    second_level_metric_names,
)
from octop.infra.diagnosis.snapshot_store import (
    documented_ratio_fields,
    fulfillment_side_keys,
    fulfillment_time_fields,
    performance_business_time,
    performance_partition,
    performance_row_key,
    performance_store_keys,
    performance_table,
)

_REPO = Path(__file__).resolve().parents[3]
_IDENT = re.compile(r"[a-z][a-z0-9_]*")
_WINDOW = {"start": "2026-10-01", "end": "2026-10-07"}


def _mod() -> Any:
    return importlib.import_module("octop.infra.diagnosis.store_perf_client")


def _locked_names() -> frozenset[str]:
    names: set[str] = set()
    names.add(performance_table())
    names.add(performance_partition().split("=", 1)[0])
    names.add(performance_business_time())
    names.add(performance_row_key())
    names.update(performance_store_keys())
    names.update(fulfillment_side_keys())
    names.update(fulfillment_time_fields())
    names.update(field for field, _purpose in q4_physical_fields())
    names.update(q4_output_names())
    names.add(store_score_field())
    names.add(entity_avg_field())
    names.update(overall_decline_fields())
    names.add(overall_decline_source())
    names.update(slice_overview_fields())
    names.add(active_spu_metric())
    names.add(on_sale_spu_metric())
    names.add(category_dimension())
    table, column = age_clock_field().split(".", 1)
    names.add(table)
    names.add(column)
    names.add(age_active_rate_metric())
    names.update(table_name for _label, table_name in detail_tables())
    for metric in second_level_metric_names():
        for predicate in documented_ratio_fields(metric):
            names.update(_IDENT.findall(predicate))
    return frozenset(names)


def _client(module: Any, handler: Any) -> Any:
    return module.StorePerfClient(
        base_url="http://127.0.0.1:8787",
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )


def _ok(table: str, columns: list[str], rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {"table": table, "columns": columns, "rows": rows, "read_only": True}


def test_env_placeholders_have_no_odps_secret() -> None:
    """凭据只是服务 API Key 和 base URL。示例文件里没有 ODPS 密钥。"""
    module = _mod()
    assert module.API_KEY_ENV == "CONNECTOR_STORE_PERF_API_KEY"
    assert module.BASE_URL_ENV == "STORE_PERF_BASE_URL"
    example = (_REPO / ".env.example").read_text(encoding="utf-8")
    assert "ODPS_ACCESS_ID" not in example
    assert "ODPS_ACCESS_KEY" not in example
    assert "ODPS_PROJECT" not in example
    assert "ODPS_ENDPOINT" not in example
    found: dict[str, str] = {}
    for line in example.splitlines():
        if line.startswith(module.API_KEY_ENV + "="):
            found["key"] = line.split("=", 1)[1].split("#", 1)[0].strip()
        if line.startswith(module.BASE_URL_ENV + "="):
            found["url"] = line.split("=", 1)[1].split("#", 1)[0].strip()
    assert found == {"key": "", "url": ""}
    with pytest.raises(module.StorePerfError) as raised:
        module.client_from_env({})
    assert raised.value.code == "missing_config"


def test_empty_api_key_builds_client_when_base_url_is_set() -> None:
    """有 base URL 时空 Key 可以建客户端。缺 URL 仍是 missing_config。"""
    module = _mod()
    seen: dict[str, Any] = {}

    def latest(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(
            200,
            json=_ok(performance_table(), ["store_id"], [{"store_id": "634418230343667"}]),
        )

    client = module.client_from_env(
        {
            module.BASE_URL_ENV: "http://127.0.0.1:8787",
            module.API_KEY_ENV: "",
        },
        transport=httpx.MockTransport(latest),
    )
    result = client.call(
        "get_data_latest",
        {"store": "634418230343667", "window": {"start": "2026-10-11", "end": "2026-10-17"}},
    )
    assert seen["auth"] is None
    assert result["read_only"] is True
    assert result["rows"] == [{"store_id": "634418230343667"}]
    blank = module.client_from_env({module.BASE_URL_ENV: "http://127.0.0.1:8787"})
    assert blank is not None
    with pytest.raises(module.StorePerfError) as raised:
        module.client_from_env({module.API_KEY_ENV: "present"})
    assert raised.value.code == "missing_config"
    with pytest.raises(module.StorePerfError) as raised:
        module.client_from_env({module.BASE_URL_ENV: "   "})
    assert raised.value.code == "missing_config"


def test_timeouts_tools_and_catalog_are_available() -> None:
    """五个工具沿用目录名。目录阶段是 available。超时不超过设计值。"""
    module = _mod()
    entry = get_catalog_entry("store-perf")
    assert entry is not None
    assert entry.phase == "available"
    assert entry.allowed_tools == module.tool_names()
    assert module.tool_names() == (
        "get_data_latest",
        "submit_preload",
        "run_analysis",
        "drill_metric",
        "get_report",
    )
    assert module.tool_http("get_data_latest") == ("GET", "/data/latest")
    assert module.tool_http("submit_preload") == ("POST", "/data/preload")
    assert module.tool_http("run_analysis") == ("POST", "/analysis/run")
    assert module.tool_http("drill_metric") == ("POST", "/drill")
    assert module.tool_http("get_report") == ("GET", "/detail-excel")
    assert module.tool_timeout_seconds("submit_preload") == 30 * 60
    assert module.tool_timeout_seconds("drill_metric") == 300
    assert module.tool_timeout_seconds("run_analysis") == 900
    assert module.tool_timeout_seconds("get_data_latest") <= 300
    assert module.tool_timeout_seconds("get_report") <= 300


def test_accepted_names_are_the_promoted_columns_only() -> None:
    """响应只接受已锁表名和列名。近义名、语义层 id、空策略名和 TOP X 不在里面。"""
    module = _mod()
    accepted = module.accepted_names()
    assert accepted == _locked_names()
    assert "store_id" in accepted
    assert "shop_id" in accepted
    assert "storeId" not in accepted
    assert "shopId" not in accepted
    assert "perf_score" not in accepted
    assert "原创款" not in accepted
    assert strategy_metric_names() == ()
    assert fulfillment_column_names() == ()
    for display in l1_display_names():
        if display.startswith("Top x") or display in {
            "订单量下滑占比",
            "下滑SPU数占比",
            "动销SPU下滑占比",
            "在售SPU下滑占比",
        }:
            assert display not in accepted
    semantic = {metric_id for _name, metric_id in kickoff_metric_ids()}
    assert "temu_store_late_shipment_rate" in semantic
    assert semantic.isdisjoint(accepted)
    assert set(prefixed_metric_ids()).isdisjoint(accepted)
    assert set(performance_score_ids()).isdisjoint(accepted)
    assert not (_REPO / "src" / "octop" / "infra" / "diagnosis" / "sql").exists()


def test_mock_latest_keeps_store_id_and_rejects_a_synonym() -> None:
    """get_data_latest 是只读。storeId 不会改写成 store_id。"""
    module = _mod()
    seen: dict[str, Any] = {}

    def latest(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["auth"] = request.headers.get("authorization")
        seen["query"] = dict(request.url.params)
        seen["timeout"] = request.extensions["timeout"]["read"]
        return httpx.Response(
            200,
            json=_ok(
                performance_table(),
                ["store_id", "performance_indicator", "indicator_data_detail"],
                [
                    {
                        "store_id": "s-1",
                        "performance_indicator": "延迟发货率",
                        "indicator_data_detail": 0.1,
                    }
                ],
            ),
        )

    client = _client(module, latest)
    result = client.call(
        "get_data_latest",
        {"store": "s-1", "window": dict(_WINDOW)},
    )
    assert seen["method"] == "GET"
    assert seen["path"] == "/data/latest"
    assert seen["auth"] == "Bearer test-key"
    assert seen["query"]["store"] == "s-1"
    assert json.loads(seen["query"]["window"]) == _WINDOW
    assert seen["timeout"] == module.tool_timeout_seconds("get_data_latest")
    assert result["rows"] == [
        {
            "store_id": "s-1",
            "performance_indicator": "延迟发货率",
            "indicator_data_detail": 0.1,
        }
    ]
    assert "storeId" not in result["rows"][0]

    def synonym(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_ok(performance_table(), ["storeId"], [{"storeId": "s-1"}]),
        )

    with pytest.raises(module.StorePerfError) as raised:
        _client(module, synonym).call(
            "get_data_latest",
            {"store": "s-1", "window": dict(_WINDOW)},
        )
    assert raised.value.code == "unknown_column"


def test_drill_keeps_shop_id_and_blocks_writes() -> None:
    """履约表保留 shop_id。SQL、黄标和语义层 id 不会发出去。"""
    module = _mod()
    seen: dict[str, Any] = {}

    def drill(request: httpx.Request) -> httpx.Response:
        seen["called"] = True
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content)
        seen["timeout"] = request.extensions["timeout"]["read"]
        return httpx.Response(
            200,
            json=_ok(
                "dwm_robot_self_order_detail_df",
                ["shop_id", "shop_name", "ship_time", "parent_shipping_time"],
                [{"shop_id": "shop-9", "shop_name": "九店", "ship_time": "t"}],
            ),
        )

    result = _client(module, drill).call(
        "drill_metric",
        {
            "store": "s-1",
            "window": dict(_WINDOW),
            "metric": "48小时发货率",
            "top": 10,
        },
    )
    assert seen["method"] == "POST"
    assert seen["path"] == "/drill"
    assert seen["timeout"] == 300
    assert seen["body"] == {
        "store": "s-1",
        "window": _WINDOW,
        "metric": "延迟发货率",
        "top": 10,
    }
    assert result["rows"][0]["shop_id"] == "shop-9"
    assert "store_id" not in result["rows"][0]

    def boom(_request: httpx.Request) -> httpx.Response:
        seen["blocked"] = True
        return httpx.Response(500)

    blocked = _client(module, boom)
    for params, code in (
        (
            {
                "store": "s-1",
                "window": dict(_WINDOW),
                "metric": "延迟发货率",
                "top": 10,
                "sql": "x",
            },
            "sql_rejected",
        ),
        (
            {"store": "s-1", "window": dict(_WINDOW), "metric": yellow_metric_names()[0], "top": 1},
            "yellow_metric",
        ),
        (
            {
                "store": "s-1",
                "window": dict(_WINDOW),
                "metric": "temu_store_late_shipment_rate",
                "top": 1,
            },
            "unknown_metric",
        ),
        (
            {"store": "s-1", "window": dict(_WINDOW), "metric": "活动覆盖率", "top": 1},
            "unknown_metric",
        ),
    ):
        seen["blocked"] = False
        with pytest.raises(module.StorePerfError) as raised:
            blocked.call("drill_metric", params)
        assert raised.value.code == code
        assert seen["blocked"] is False


def test_preload_and_analysis_timeouts_and_read_only_gate() -> None:
    """预加载不超过 30 分钟，分析不超过 900 秒。read_only 不是真就拒绝。"""
    module = _mod()
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["timeout"] = request.extensions["timeout"]["read"]
        seen["body"] = json.loads(request.content) if request.content else None
        if request.url.path == "/analysis/run":
            return httpx.Response(
                200,
                json=_ok(performance_table(), ["store_id"], [{"store_id": "s-1"}])
                | {"read_only": False},
            )
        payload = _ok(performance_table(), ["store_id"], [{"store_id": "s-1"}])
        payload["job_id"] = "not-a-locked-column"
        return httpx.Response(200, json=payload)

    client = _client(module, handler)
    preloaded = client.call("submit_preload", {"store": "s-1", "window": dict(_WINDOW)})
    assert seen["path"] == "/data/preload"
    assert seen["timeout"] == 30 * 60
    assert seen["body"] == {"store": "s-1", "window": _WINDOW}
    assert set(preloaded) == {"table", "columns", "rows", "read_only"}
    assert "job_id" not in preloaded

    with pytest.raises(module.StorePerfError) as raised:
        client.call("run_analysis", {"store": "s-1", "window": dict(_WINDOW)})
    assert seen["path"] == "/analysis/run"
    assert seen["timeout"] == 900
    assert raised.value.code == "write_rejected"


def test_client_source_does_not_embed_the_service() -> None:
    """客户端源码不内嵌 pyodps、uvicorn 或 SQL。"""
    module = _mod()
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "pyodps" not in source
    assert "pyodps" not in sys.modules
    assert "uvicorn" not in source
    assert "ODPS_" not in source
    assert "SELECT" not in source
    assert "INSERT" not in source
    assert isinstance(module.accepted_names(), frozenset)
    assert isinstance(module.tool_names(), tuple)
    assert isinstance(yellow_metric_names(), tuple)
