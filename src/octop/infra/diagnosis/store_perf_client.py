"""HTTP client for an external store-perf service.

Octop does not host that process. Request fields are store, window, metric,
and top. Response table and column names stay on the promoted contract.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import cast

import httpx

from octop.infra.diagnosis.hit_weights import (
    entity_avg_field,
    locked_metric_name,
    store_score_field,
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

API_KEY_ENV = "CONNECTOR_STORE_PERF_API_KEY"
BASE_URL_ENV = "STORE_PERF_BASE_URL"

_READ_TIMEOUT_SECONDS = 60
_TOOLS: tuple[tuple[str, str, str, int, frozenset[str]], ...] = (
    (
        "get_data_latest",
        "GET",
        "/data/latest",
        _READ_TIMEOUT_SECONDS,
        frozenset({"store", "window"}),
    ),
    ("submit_preload", "POST", "/data/preload", 30 * 60, frozenset({"store", "window"})),
    ("run_analysis", "POST", "/analysis/run", 900, frozenset({"store", "window"})),
    (
        "drill_metric",
        "POST",
        "/drill",
        300,
        frozenset({"store", "window", "metric", "top"}),
    ),
    ("get_report", "GET", "/detail-excel", _READ_TIMEOUT_SECONDS, frozenset({"store", "window"})),
)
_FORBIDDEN = frozenset({"sql", "statement", "query"})
_IDENT = re.compile(r"[a-z][a-z0-9_]*")
_SCORE_DRILL = "绩效分"


class StorePerfError(Exception):
    """Contract or transport failure. ``code`` is the stable test key."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def tool_names() -> tuple[str, ...]:
    """The five catalog tools, in catalog order."""
    return tuple(row[0] for row in _TOOLS)


def tool_http(tool: str) -> tuple[str, str]:
    """HTTP method and path for one tool."""
    for name, method, path, _timeout, _keys in _TOOLS:
        if name == tool:
            return (method, path)
    raise StorePerfError("unknown_tool")


def tool_timeout_seconds(tool: str) -> int:
    """Ceiling for one tool. Preload, drill, and analysis follow the design table."""
    for name, _method, _path, timeout, _keys in _TOOLS:
        if name == tool:
            return timeout
    raise StorePerfError("unknown_tool")


def accepted_names() -> frozenset[str]:
    """Promoted table and column names. Near-synonyms are absent."""
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


class StorePerfClient:
    """Calls the external service with the caller's API key."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._transport = transport

    def call(self, tool: str, params: Mapping[str, object]) -> dict[str, object]:
        """Send one tool call and return the locked response shape."""
        body = _prepare(tool, params)
        method, path = tool_http(tool)
        timeout = tool_timeout_seconds(tool)
        url = self._base_url + path
        headers = {"Authorization": f"Bearer {self._api_key}"}
        with httpx.Client(transport=self._transport, timeout=httpx.Timeout(timeout)) as client:
            if method == "GET":
                response = client.get(url, params=_query(body), headers=headers)
            else:
                response = client.post(url, json=body, headers=headers)
        if response.status_code != 200:
            raise StorePerfError("http_status")
        return _response(response.json())


def client_from_env(
    environ: Mapping[str, str],
    *,
    transport: httpx.BaseTransport | None = None,
) -> StorePerfClient:
    """Build a client from the service key and base URL."""
    key = environ.get(API_KEY_ENV, "").strip()
    url = environ.get(BASE_URL_ENV, "").strip()
    if not key or not url:
        raise StorePerfError("missing_config")
    return StorePerfClient(base_url=url, api_key=key, transport=transport)


def _keys_for(tool: str) -> frozenset[str]:
    for name, _method, _path, _timeout, keys in _TOOLS:
        if name == tool:
            return keys
    raise StorePerfError("unknown_tool")


def _prepare(tool: str, params: Mapping[str, object]) -> dict[str, object]:
    if tool not in tool_names():
        raise StorePerfError("unknown_tool")
    if _FORBIDDEN.intersection(params):
        raise StorePerfError("sql_rejected")
    allowed = _keys_for(tool)
    if set(params).difference(allowed):
        raise StorePerfError("extra_param")
    if allowed.difference(params):
        raise StorePerfError("missing_param")
    store = params["store"]
    if not isinstance(store, str) or not store:
        raise StorePerfError("bad_store")
    body: dict[str, object] = {"store": store, "window": _window(params["window"])}
    if "metric" in allowed:
        body["metric"] = _metric(params["metric"])
    if "top" in allowed:
        body["top"] = _top(params["top"])
    return body


def _window(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise StorePerfError("bad_window")
    raw = cast(Mapping[object, object], value)
    if set(raw) != {"start", "end"}:
        raise StorePerfError("bad_window")
    start = raw["start"]
    end = raw["end"]
    if not isinstance(start, str) or not isinstance(end, str) or not start or not end:
        raise StorePerfError("bad_window")
    return {"start": start, "end": end}


def _metric(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise StorePerfError("unknown_metric")
    if value in yellow_metric_names():
        raise StorePerfError("yellow_metric")
    if value == _SCORE_DRILL:
        return value
    locked = locked_metric_name(value)
    if locked is None:
        raise StorePerfError("unknown_metric")
    return locked


def _top(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise StorePerfError("bad_top")
    return value


def _query(body: Mapping[str, object]) -> dict[str, str]:
    window = body["window"]
    return {
        "store": str(body["store"]),
        "window": json.dumps(window, ensure_ascii=False),
    }


def _response(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise StorePerfError("bad_payload")
    raw = cast(dict[object, object], payload)
    if raw.get("read_only") is not True:
        raise StorePerfError("write_rejected")
    table = raw.get("table")
    columns = raw.get("columns")
    rows = raw.get("rows")
    accepted = accepted_names()
    if not isinstance(table, str) or table not in accepted:
        raise StorePerfError("unknown_table")
    if not isinstance(columns, list):
        raise StorePerfError("bad_payload")
    column_names: list[str] = []
    for column in columns:
        if not isinstance(column, str) or column not in accepted:
            raise StorePerfError("unknown_column")
        column_names.append(column)
    if not isinstance(rows, list):
        raise StorePerfError("bad_payload")
    declared = set(column_names)
    clean_rows: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise StorePerfError("bad_payload")
        item = cast(dict[object, object], row)
        clean: dict[str, object] = {}
        for key, cell in item.items():
            if not isinstance(key, str) or key not in declared:
                raise StorePerfError("bad_payload")
            clean[key] = cell
        clean_rows.append(clean)
    return {
        "table": table,
        "columns": column_names,
        "rows": clean_rows,
        "read_only": True,
    }
